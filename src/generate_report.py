import openai
import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup
from pytz import timezone

# --- Environment and API Key Setup ---
load_dotenv()
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env = Environment(loader=FileSystemLoader(os.path.join(_project_root, 'template')))

# --- Path Definitions ---
_output_dir = os.path.join(_project_root, 'output')
_weather_data_path = os.path.join(_output_dir, 'weather_data.json')
_prompts_path = os.path.join(_output_dir, 'prompts_for_llm.json')
_output_html_path = os.path.join(_output_dir, 'index.html')


def format_alert(alert):
    """
    Formats a single alert from the NWS API into an HTML list item.
    """
    properties = alert.get('properties', {})
    event = properties.get('event', 'Unknown Event')
    headline = properties.get('headline', 'No headline available.')
    severity = properties.get('severity', 'Unknown')
    area_desc = properties.get('areaDesc', 'Unknown area')
    
    color_map = {'Extreme': '#cc0000', 'Severe': '#cc0000', 'Moderate': '#e67300'}
    color = color_map.get(severity, '#ffcc00') # Default to yellow for Minor/Unknown
    
    level_map = {'Extreme': 'WARNING', 'Severe': 'WARNING', 'Moderate': 'WATCH'}
    level = level_map.get(severity, 'ADVISORY')
    
    return (f'<li><span style="color:{color}; font-weight:bold;">{level}</span>: {event} for {area_desc}.'
            f'<br><i style="font-size:13px;">{headline}</i></li>')


def create_llm_prompt(state_name, discussions, alerts, offices):
    """
    Creates a detailed, concise prompt for the LLM.
    """
    office_list_str = ", ".join(offices)
    discussions_str = "".join(f"\n\n---\nDiscussion from {d['office_code'].upper()}:\n{d.get('product_text', 'Not available.')}" for d in discussions)
    alerts_str = "".join(f"\n- {a.get('properties', {}).get('headline')}" for a in alerts) if alerts else "No active alerts."

    prompt = f"""You are an expert meteorologist writing a 5-Day Outlook for an emergency management agency.
Your task is to synthesize the provided data for {state_name} into a scannable, **extremely concise** summary.

GUIDELINES:
1.  **Format:** Write a single HTML paragraph (`<p>...</p>`). Start with `<strong>{state_name}:</strong>`.
2.  **Content:** Focus **only** on actionable intelligence. Mention primary threats and locations. Omit conversational filler.
3.  **Brevity is Key:** If there are no significant hazards, write ONLY: `<strong>{state_name}:</strong> All offices ({office_list_str}) confirm no significant weather threats are forecast.`
4.  **HTML Tags:** Use `<span style="color:#cc0000; font-weight:bold;">WARNING</span>` or `<span style="color:#ffcc00; font-weight:bold;">ADVISORY</span>` for emphasis where critical. Do NOT use markdown.

DATA FOR {state_name}:
- Offices: {office_list_str}
- Active Alerts: {alerts_str}
- Forecast Discussions: {discussions_str}
"""
    return prompt

def get_llm_summary(prompt, client):
    """
    Gets the summary from the LLM and cleans it.
    """
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2, # Lower temperature for more deterministic output
            max_tokens=400 
        )
        # Clean the response: remove backticks, "html" markers, and leading/trailing whitespace
        clean_response = re.sub(r'^```html\s*|\s*```$', '', completion.choices[0].message.content, flags=re.MULTILINE).strip()
        return clean_response
    except Exception as e:
        print(f"  Error calling OpenAI API: {e}")
        return f"<p><strong>Error:</strong> Could not generate summary. {e}</p>"


def get_general_recommendations(alerts):
    """Generates a static block of HTML with general recommendations."""
    recs = set()
    rec_map = {
        "Flood": "Do not drive through flooded roadways.",
        "Rip Current": "Avoid swimming in hazardous surf conditions.",
        "Tornado": "Monitor local weather and be prepared to take shelter.",
        "Thunderstorm": "Seek shelter during thunderstorms.",
        "Hurricane": "Follow instructions from local emergency management.",
        "Heat": "Stay hydrated and avoid strenuous activity during peak heat."
    }
    for alert in alerts:
        event = alert.get('properties', {}).get('event', '').lower()
        for keyword, rec in rec_map.items():
            if keyword.lower() in event:
                recs.add(rec)
    
    rec_html = "".join(f"<li>{rec}</li>" for rec in recs) if recs else "<li>Monitor local conditions.</li>"
    return f"""
<h3 style="color:#990000; font-weight:bold;">Recommendations</h3>
<h4 style="color:#990000; font-weight:bold;">Immediate Actions</h4>
<ul>{rec_html}</ul>
<h4 style="color:#990000; font-weight:bold;">5-Day Monitoring</h4>
<ul><li>Monitor NWS local offices for new or updated advisories.</li><li>Track NHC updates.</li></ul>
"""

def get_tropical_outlook(nhc_data):
    """Formats the NHC data into a static HTML block."""
    # This function remains largely the same
    formation_chance = nhc_data.get('formation_chance_7day', '0')
    summary = nhc_data.get('summary', 'No new tropical cyclones are expected during the next 7 days.')
    return f"""
<div style="background-color:#f0e8e4; border-left:4px solid #7a1d1d; padding:15px; margin-bottom:20px;">
<h3 style="color:#7a1d1d; font-weight:bold; font-size:18px; margin:0 0 8px;">Tropical Weather Outlook</h3>
<p style="color:#000000; margin:0 0 5px;">{summary}</p>
<div style="text-align:center;">
<div style="display:inline-block; background-color:#7a1d1d; color:#ffffff; padding:2px 8px; font-size:30px; font-weight:bold;">
Formation Chance (7-Day): <span style="font-size:30px;">{formation_chance}%</span>
</div></div></div>
"""

def main():
    os.makedirs(_output_dir, exist_ok=True)
    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    with open(_weather_data_path, 'r') as f:
        weather_data = json.load(f)

    nws_offices_by_state = {
        "Tennessee": ["OHX", "MEG", "MRX"], "Mississippi": ["JAN"], "Alabama": ["BMX", "MOB", "HUN"],
        "Georgia": ["FFC", "JAX"], "Florida": ["TAE", "TBW", "MFL", "MLB"], "North Carolina": ["RAH", "ILM", "MHX"],
        "South Carolina": ["CHS", "GSP", "CAE"], "U.S. Virgin Islands": ["SJU"]
    }
    
    states_data = {}
    all_alerts = weather_data.get('nws_alerts', [])
    for state, offices in nws_offices_by_state.items():
        # Associate alerts with states by checking if the state's abbreviation (e.g., "NC")
        # is present in the alert's 'areaDesc' field. This is more reliable.
        state_code = [k for k, v in {"TN": "Tennessee", "MS": "Mississippi", "AL": "Alabama", "GA": "Georgia", "FL": "Florida", "NC": "North Carolina", "SC": "South Carolina", "VI": "U.S. Virgin Islands"}.items() if v == state][0]
        
        state_alerts = [
            a for a in all_alerts 
            if f", {state_code}" in a['properties'].get('areaDesc', '')
        ]

        states_data[state] = {
            'discussions': [d for c, d in weather_data.get('nws_discussions', {}).items() if c.lower() in [o.lower() for o in offices]],
            'alerts': state_alerts,
            'offices': offices
        }

    prompts_for_llm = {}
    all_states_summary_html = ""
    for state_name, data in states_data.items():
        print(f"Generating summary for {state_name}...")
        prompt = create_llm_prompt(state_name, data['discussions'], data['alerts'], data['offices'])
        prompts_for_llm[state_name] = prompt
        summary_html = get_llm_summary(prompt, client)
        
        # Append the summary paragraph
        all_states_summary_html += f"{summary_html}"

        # If there are alerts, format them and append them
        if data['alerts']:
            formatted_alerts_html = "".join([format_alert(a) for a in data['alerts']])
            all_states_summary_html += (
                f'<div style="margin-top:5px; margin-left:15px; border-left: 2px solid #cc0000; padding-left:8px;">'
                f'<strong style="font-size:15px;">Active Alerts:</strong><ul>{formatted_alerts_html}</ul></div>'
            )
        
        # Add a break after each state entry
        all_states_summary_html += "<br><br>"

    # --- Timezone-Aware Timestamp ---
    eastern = timezone('US/Eastern')
    now_utc = datetime.now(timezone('UTC'))
    now_eastern = now_utc.astimezone(eastern)

    header_html = f"""
<p style="color:#000000; font-style:italic;">Weather.gov map checked at {now_eastern.strftime('%-I:%M %p %Z, %B %-d, %Y')}.</p>
<h2 style="color:#990000; font-weight:bold;">5-Day Outlook for {now_eastern.strftime('%B %-d, %Y')}</h2>
"""
    tropical_outlook_html = get_tropical_outlook(weather_data.get('nhc', {}))
    threats_header_html = '<h3 style="color:#990000; font-weight:bold;">State-by-State Threats</h3>'
    recommendations_html = get_general_recommendations(all_alerts)

    desktop_content = (header_html + tropical_outlook_html + threats_header_html + 
                       all_states_summary_html + recommendations_html)
    
    template = _env.get_template('base_template.html')
    final_html = template.render(
        now_timestamp=int(now_eastern.timestamp()),
        desktop_content=Markup(desktop_content)
    )

    with open(_output_html_path, 'w') as f:
        f.write(final_html)

    with open(_prompts_path, 'w') as f:
        json.dump(prompts_for_llm, f, indent=4)
        
    print(f"Weather report template saved to {_output_html_path}")

if __name__ == "__main__":
    main() 