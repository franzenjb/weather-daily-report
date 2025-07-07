# This script will call OpenAI with a formatted prompt to generate the report. 

import json
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup
from datetime import datetime, timedelta
import openai
from dotenv import load_dotenv
import os
from pytz import timezone

# --- Path Setup ---
# Get the absolute path of the directory where the script is located
_script_dir = os.path.dirname(os.path.abspath(__file__))
# Get the project root directory (assuming the script is in 'src')
_project_root = os.path.dirname(_script_dir)

# Define absolute paths to be used throughout the script
_template_dir = os.path.join(_project_root, 'template')
_weather_data_path = os.path.join(_project_root, 'output', 'weather_data.json')
_nws_offices_path = os.path.join(_project_root, 'data', 'nws_offices.json')
_prompts_path = os.path.join(_project_root, 'output', 'prompts_for_llm.json')
_output_html_path = os.path.join(_project_root, 'output', 'index.html')

def format_alert(alert):
    """
    Formats a single alert from the NWS API into an HTML string with color coding.
    """
    properties = alert.get('properties', {})
    event = properties.get('event', 'Unknown Event')
    headline = properties.get('headline', 'No headline available.')
    severity = properties.get('severity', 'Unknown')
    area_desc = properties.get('areaDesc', 'Unknown area')

    color = "#000000" # Default text color
    style = "font-weight:bold;"
    
    # Simple severity mapping
    if severity in ['Severe', 'Extreme']:
        color = '#cc0000'
        # Example: WARNING: Flood Warning for Williamson County...
        event_str = f'<span style="color:{color}; {style}">WARNING</span>: {event} for {area_desc}.<br><i style="font-size:13px;">{headline}</i>'
    elif severity == 'Moderate':
        color = '#e67300'
        event_str = f'<span style="color:{color}; {style}">WATCH</span>: {event} for {area_desc}.<br><i style="font-size:13px;">{headline}</i>'
    else: # Minor, Unknown
        color = '#ffcc00'
        event_str = f'<span style="color:{color}; {style}">ADVISORY</span>: {event} for {area_desc}.<br><i style="font-size:13px;">{headline}</i>'

    return event_str

def generate_recommendations(alerts):
    """
    Generates a concise set of recommendations based on alert types.
    """
    recommendations = set()
    
    RECOMMENDATION_MAP = {
        "Flood": "Do not drive through flooded roadways. Turn around, don't drown.",
        "Rip Current": "Avoid swimming in hazardous surf conditions and obey posted flags.",
        "Beach Hazard": "Stay out of the water. Dangerous surf and current conditions are expected.",
        "Tornado": "Monitor local weather for updates. Be prepared to take shelter if a warning is issued.",
        "Thunderstorm": "When thunder roars, go indoors. Seek shelter during thunderstorms.",
        "Tropical Storm": "Prepare for tropical storm conditions. Secure loose outdoor objects.",
        "Hurricane": "Follow instructions from local emergency management. Evacuate if ordered.",
        "Heat": "Stay hydrated and avoid strenuous activity during the hottest part of the day.",
        "Fog": "Reduce speed and use low-beam headlights when driving in dense fog."
    }

    unique_events = {alert.get('properties', {}).get('event') for alert in alerts}

    for event in unique_events:
        if not event: continue
        for keyword, recommendation in RECOMMENDATION_MAP.items():
            if keyword.lower() in event.lower():
                recommendations.add(recommendation)

    if not recommendations:
        recommendations.add("Monitor local conditions and practice lightning safety during any thunderstorm activity.")

    return recommendations

def create_llm_prompt(state_name, office_discussions, state_alerts, river_data, office_codes):
    """
    Creates a detailed prompt for an LLM to synthesize a weather report for a single state.
    """
    office_list_str = ", ".join(office_codes)

    if state_alerts:
        closing_statement = f"<i>Report based on data from offices ({office_list_str}).</i>"
    else:
        closing_statement = f"<i>All offices ({office_list_str}) confirm no active warnings.</i>"

    prompt = f"""You are an expert meteorologist synthesizing a weather report for emergency management clients. Your tone should be professional, clear, and concise.

Based on the following raw data, please generate a one-paragraph summary for **{state_name}**.

Your summary MUST follow these rules:
1.  Provide a general weather outlook for the state.
2.  In the summary, you may refer to active hazards in general terms (e.g., "Several flood warnings are in effect...").
3.  Do NOT include the details of the alerts in your summary paragraph. The details will be listed separately below your summary.
4.  If there are no major hazards, state that clearly, for example: "No active river flood warnings or watches at this time."
5.  You MUST end your response with the following sentence EXACTLY as it is written, with no extra characters or formatting: `{closing_statement}`

**Raw Data for {state_name}:**

"""
    # Append Forecast Discussions
    prompt += "**Forecast Discussions:**\n"
    if office_discussions:
        for discussion in office_discussions:
            prompt += f"- **{discussion['office_code'].upper()}**: {discussion.get('product_text', 'Not available.')}\n\n"
    else:
        prompt += "- No forecast discussions available.\n\n"

    # Append Active Alerts
    prompt += "**Active Alerts:**\n"
    if state_alerts:
        for alert in state_alerts:
            props = alert.get('properties', {})
            prompt += f"- **{props.get('event')}** ({props.get('severity')}): {props.get('headline')}\n"
    else:
        prompt += "- No active alerts.\n"

    # Append River Data
    prompt += "\n**Current River Conditions:**\n"
    if river_data:
        for gauge in river_data:
            prompt += f"- **{gauge['name']} on the {gauge['waterbody']}**: Currently at **{gauge['status']}** flood stage. Observed value: {gauge['observed_value']} ft. Flood stage is {gauge['flood_stage']} ft.\n"
    else:
        prompt += "- No rivers are currently at or above flood stage in the monitored areas for this state.\n"
        
    prompt += f"\n**Please generate the synthesized paragraph for {state_name} now.**"
    return prompt

def get_llm_summary(prompt, client):
    """
    Calls the OpenAI API to get a summary based on the prompt.
    """
    if not client:
        return "[[LLM integration not configured. Skipping API call.]]"
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # Or another model like "gpt-4"
            messages=[
                # The system prompt is general, the user prompt contains detailed instructions.
                {"role": "system", "content": "You are an expert meteorologist synthesizing a weather report for emergency management clients. Your tone should be professional, clear, and concise."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling OpenAI API for a state: {e}")
        return "[[LLM summary generation failed for this state. Please check the logs.]]"

def main():
    """
    Main function to generate prompts for LLM and a template for the final report.
    """
    load_dotenv()
    
    # Initialize OpenAI client
    api_key = os.getenv("OPENAI_API_KEY")
    client = None
    if api_key:
        client = openai.OpenAI(api_key=api_key)
    else:
        print("WARNING: OPENAI_API_KEY not found. Report will use placeholder text.")
        print("Please create a .env file and add your key, e.g., OPENAI_API_KEY='your-key-here'")

    env = Environment(loader=FileSystemLoader(_template_dir), autoescape=True)
    template = env.get_template('base_template.html')

    with open(_weather_data_path, 'r') as f:
        weather_data = json.load(f)

    # Get the current time in the US/Eastern timezone
    eastern = timezone('US/Eastern')
    now_utc = datetime.now(timezone('UTC'))
    now_eastern = now_utc.astimezone(eastern)

    template_data = {
        "update_time": now_eastern.strftime("%I:%M %p %Z"),
        "start_date": now_eastern.strftime("%B %d, %Y"),
        "end_date": (now_eastern + timedelta(days=4)).strftime("%B %d, %Y"),
    }

    nws_discussions = weather_data.get('nws_discussions', {})
    nws_alerts = weather_data.get('nws_alerts', [])
    nwps_data = weather_data.get('nwps', {}).get('gauges', [])
    
    # This file will hold the prompts for the user to run through an LLM
    prompts_for_llm = {}

    # Group discussions and alerts by state
    states_data = {}
    office_to_state_map = {}
    with open(_nws_offices_path, 'r') as f:
        offices = json.load(f)
    for office in offices:
        state = office['state']
        office_code = office['code'].upper()
        if state not in states_data:
            states_data[state] = {"discussions": [], "alerts": [], "offices": [], "rivers": []}
        states_data[state]["offices"].append(office_code)
        office_to_state_map[office_code] = state

    # Create a reverse map from state code to state name
    state_name_map_rev = {v: k for k, v in {
        "TN": "Tennessee", "MS": "Mississippi", "AL": "Alabama", "GA": "Georgia",
        "FL": "Florida", "NC": "North Carolina", "SC": "South Carolina", "VI": "U.S. Virgin Islands"
    }.items()}

    for office_code, discussion in nws_discussions.items():
        state = office_to_state_map.get(office_code.upper())
        if state and state in states_data:
            states_data[state]['discussions'].append(discussion)

    for alert in nws_alerts:
        if alert.get("error"):
            continue

        # Correctly associate alerts with states by checking the 'areaDesc' field.
        # This is more reliable than using senderName.
        area_desc = alert.get('properties', {}).get('areaDesc', '')
        if not area_desc:
            continue

        for state_name, state_data in states_data.items():
            state_code = state_name_map_rev.get(state_name) # Get 'NC' from 'North Carolina'
            
            # Check if the state code (e.g., "NC") or state name is in the area description.
            # This handles cases like "Alamance, NC" and "Coastal North Carolina".
            if f", {state_code}" in area_desc or state_name in area_desc:
                # Avoid duplicates
                if alert['properties']['id'] not in [a['properties']['id'] for a in state_data['alerts']]:
                    state_data['alerts'].append(alert)

    # Group river data by state
    if nwps_data:
        for gauge in nwps_data:
            state_code = gauge.get('state')
            if state_code and state_code in state_name_map_rev:
                state_name = state_name_map_rev[state_code]
                if state_name in states_data:
                    states_data[state_name]['rivers'].append(gauge)

    # Create prompts and placeholders
    state_template_map = {
        "Tennessee": "tennessee_hazards", "Mississippi": "mississippi_hazards", "Alabama": "alabama_hazards",
        "Georgia": "georgia_hazards", "Florida": "florida_hazards", "North Carolina": "north_carolina_hazards",
        "South Carolina": "south_carolina_hazards", "U.S. Virgin Islands": "us_virgin_islands_hazards"
    }

    for state_name, data in states_data.items():
        prompt = create_llm_prompt(state_name, data['discussions'], data['alerts'], data.get('rivers', []), data['offices'])
        prompts_for_llm[state_name] = prompt
        
        print(f"Generating summary for {state_name}...")
        summary = get_llm_summary(prompt, client)
        if not summary: # Fallback if summary is empty
             summary = f"[[LLM to synthesize summary for {state_name} using the generated prompt]]"
        
        # Wrap the summary in Markup to ensure the HTML tags from the LLM are rendered correctly.
        template_data[state_template_map[state_name]] = Markup(summary)
        
        # Format and add the alerts for direct display in the template
        formatted_alerts = []
        if data['alerts']:
            for alert in data['alerts']:
                formatted_alerts.append(Markup(format_alert(alert)))
        
        # Generate the key for the alerts list (e.g., 'tennessee_alerts')
        alert_key = state_template_map[state_name].replace('_hazards', '_alerts')
        template_data[alert_key] = formatted_alerts

    with open(_prompts_path, 'w') as f:
        json.dump(prompts_for_llm, f, indent=4)
    print("Prompts for the LLM have been saved to output/prompts_for_llm.json")


    # Generate and add recommendations
    all_alerts = weather_data.get('nws_alerts', [])
    recommendations = generate_recommendations(all_alerts)
    if recommendations:
        # Wrap the generated HTML string in Markup to prevent auto-escaping by Jinja2
        template_data["immediate_actions"] = Markup("".join([f"<li>{rec}</li>" for rec in recommendations]))
    else:
        template_data["immediate_actions"] = Markup("<li>No specific immediate actions recommended based on current alerts.</li>")

    template_data["monitoring_actions"] = Markup("<li>Continue daily monitoring of NWS local offices for updates.</li>")

    # Process NHC data
    nhc_data = weather_data.get('nhc', {})
    template_data["tropical_outlook_summary"] = nhc_data.get('summary', 'Not available.')
    template_data["formation_chance"] = nhc_data.get('formation_chance_7day', '0')
    
    output_html = template.render(template_data)

    with open(_output_html_path, 'w') as f:
        f.write(output_html)

    print(f"Weather report template saved to {_output_html_path}")

if __name__ == "__main__":
    main() 