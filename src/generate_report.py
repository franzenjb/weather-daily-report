# This script will call OpenAI with a formatted prompt to generate the report. 

import json
from jinja2 import Environment, FileSystemLoader
from datetime import datetime, timedelta

def format_alert(alert):
    """
    Formats a single alert from the NWS API into an HTML string with color coding.
    """
    properties = alert.get('properties', {})
    event = properties.get('event', 'Unknown Event')
    headline = properties.get('headline', 'No headline available.')
    severity = properties.get('severity', 'Unknown')

    color = "#000000" # Default text color
    style = "font-weight:bold;"
    
    # Simple severity mapping
    if severity in ['Severe', 'Extreme']:
        color = '#cc0000'
        event_str = f'<span style="color:{color}; {style}">WARNING</span>: {headline}'
    elif severity == 'Moderate':
        color = '#e67300'
        event_str = f'<span style="color:{color}; {style}">WATCH</span>: {headline}'
    else: # Minor, Unknown
        color = '#ffcc00'
        event_str = f'<span style="color:{color}; {style}">ADVISORY</span>: {headline}'

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

def create_llm_prompt(state_name, office_discussions, state_alerts, river_data):
    """
    Creates a detailed prompt for an LLM to synthesize a weather report for a single state.
    """
    prompt = f"""You are an expert meteorologist synthesizing a weather report for emergency management clients. Your tone should be professional, clear, and concise.

Based on the following raw data, please generate a one-paragraph summary for **{state_name}**.

The summary must:
1.  Provide a general weather outlook for the state.
2.  Explicitly mention any specific hazards (flooding, thunderstorms, rip currents, etc.).
3.  If there are active alerts, seamlessly integrate them into the narrative. Use the following HTML tags for emphasis:
    -   For Warnings: `<span style="color:#cc0000; font-weight:bold;">WARNING</span>`
    -   For Watches: `<span style="color:#e67300; font-weight:bold;">WATCH</span>`
    -   For Advisories: `<span style="color:#ffcc00; font-weight:bold;">ADVISORY</span>`
4.  If there are no major hazards, state that clearly, for example: "No active river flood warnings or watches at this time."
5.  End with an italicized confirmation of which offices were checked, like: `_All offices (Office1, Office2) confirm no active warnings._`

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

def main():
    """
    Main function to generate prompts for LLM and a template for the final report.
    """
    env = Environment(loader=FileSystemLoader('template'), autoescape=True)
    template = env.get_template('base_template.html')

    with open('output/weather_data.json', 'r') as f:
        weather_data = json.load(f)

    now = datetime.now()
    template_data = {
        "update_time": now.strftime("%I:%M %p %Z"),
        "start_date": now.strftime("%B %d, %Y"),
        "end_date": (now + timedelta(days=4)).strftime("%B %d, %Y"),
    }

    nws_discussions = weather_data.get('nws_discussions', {})
    nws_alerts = weather_data.get('nws_alerts', [])
    nwps_data = weather_data.get('nwps', {}).get('gauges', [])
    
    # This file will hold the prompts for the user to run through an LLM
    prompts_for_llm = {}

    # Group discussions and alerts by state
    states_data = {}
    office_to_state_map = {}
    with open('data/nws_offices.json', 'r') as f:
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
        if alert.get("error"): continue
        # Alerts are issued by a specific office. We can use that to map them to a state.
        sending_office_code = alert.get('properties', {}).get('senderName', '').split(' ')[-1] # e.g., "NWS Jackson MS" -> "MS" is not reliable. Better to use office code.
        if not sending_office_code: # Fallback if senderName is not as expected
            sending_office_code = alert.get('properties', {}).get('sender', '').split(':')[-1] # e.g. "w-nws.webmaster@noaa.gov (NWS Jackson MS)" -> sometimes has office code.
        
        state = office_to_state_map.get(sending_office_code)
        if state:
            # Avoid duplicates
            if alert['properties']['id'] not in [a['properties']['id'] for a in states_data[state]['alerts']]:
                states_data[state]['alerts'].append(alert)

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
        prompt = create_llm_prompt(state_name, data['discussions'], data['alerts'], data.get('rivers', []))
        prompts_for_llm[state_name] = prompt
        
        # In a real application, you would send this prompt to an LLM.
        # Here, we will just put a placeholder in the template.
        template_data[state_template_map[state_name]] = f"[[LLM to synthesize summary for {state_name} using the generated prompt]]"

    with open('output/prompts_for_llm.json', 'w') as f:
        json.dump(prompts_for_llm, f, indent=4)
    print("Prompts for the LLM have been saved to output/prompts_for_llm.json")


    # Simplified recommendations
    template_data["immediate_actions"] = "<li>[[Generated by LLM based on all hazards]]</li>"
    template_data["monitoring_actions"] = "<li>Continue daily monitoring of NWS local offices for updates.</li>"

    # Process NHC data
    nhc_data = weather_data.get('nhc', {})
    template_data["tropical_outlook_summary"] = nhc_data.get('summary', 'Not available.')
    template_data["formation_chance"] = nhc_data.get('formation_chance_7day', '0')
    
    output_html = template.render(template_data)

    with open('output/index.html', 'w') as f:
        f.write(output_html)

    print("Weather report template saved to output/index.html")

if __name__ == "__main__":
    main() 