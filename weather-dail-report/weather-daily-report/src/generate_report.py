import json
import os

def create_prompt_for_state(state, data):
    """Creates a detailed prompt for the LLM to synthesize a weather report for a single state."""
    
    # Extracting forecast discussions
    discussions_text = ""
    if data.get('discussions'):
        for discussion in data['discussions']:
            discussions_text += f"- **{discussion['office_id']}**: \n{discussion['discussion']}\n\n"
    else:
        discussions_text = "No forecast discussions available.\n"

    # Extracting active alerts
    alerts_text = "No active alerts."
    if data.get('alerts'):
        alerts_list = []
        for alert in data['alerts']:
            props = alert.get('properties', {})
            headline = props.get('headline', 'No headline')
            description = props.get('description', 'No description')
            alerts_list.append(f"- {headline}: {description}")
        if alerts_list:
            alerts_text = "\n".join(alerts_list)

    # Extracting river conditions
    river_text = "No rivers are currently at or above flood stage in the monitored areas for this state."
    if data.get('river_conditions'):
        river_list = []
        for river_info in data['river_conditions']:
            river_list.append(f"- {river_info['station_id']}: {river_info['river_data']}")
        if river_list:
            river_text = "\n".join(river_list)


    prompt = f"""You are an expert meteorologist synthesizing a weather report for emergency management clients. Your tone should be professional, clear, and concise.

Based on the following raw data, please generate a one-paragraph summary for **{state}**.

The summary must:
1.  Provide a general weather outlook for the state.
2.  Explicitly mention any specific hazards (flooding, thunderstorms, rip currents, etc.).
3.  If there are active alerts, seamlessly integrate them into the narrative. Use the following HTML tags for emphasis:
    -   For Warnings: `<span style="color:#cc0000; font-weight:bold;">WARNING</span>`
    -   For Watches: `<span style="color:#e67300; font-weight:bold;">WATCH</span>`
    -   For Advisories: `<span style="color:#ffcc00; font-weight:bold;">ADVISORY</span>`
4.  If there are no major hazards, state that clearly, for example: "No active river flood warnings or watches at this time."
5.  End with an italicized confirmation of which offices were checked, like: `_All offices (Office1, Office2) confirm no active warnings._`

**Raw Data for {state}:**

**Forecast Discussions:**
{discussions_text}
**Active Alerts:**
{alerts_text}

**Current River Conditions:**
{river_text}

**Please generate the synthesized paragraph for {state} now.**"""
    return prompt

def main():
    """Main function to generate prompts from the fetched weather data."""
    print("Starting prompt generation...")
    try:
        with open('output/weather_data.json', 'r') as f:
            weather_data = json.load(f)
    except FileNotFoundError:
        print("Error: 'output/weather_data.json' not found. Run 'fetch_weather.py' first.")
        return
    except json.JSONDecodeError:
        print("Error: Could not decode 'output/weather_data.json'.")
        return

    all_prompts = {}
    for state, data in weather_data.items():
        prompt = create_prompt_for_state(state, data)
        all_prompts[state] = prompt

    try:
        with open('output/prompts_for_llm.json', 'w') as f:
            json.dump(all_prompts, f, indent=4)
        print("Successfully generated all prompts and saved to 'output/prompts_for_llm.json'")
    except IOError as e:
        print(f"Error writing to 'output/prompts_for_llm.json': {e}")


if __name__ == "__main__":
    main() 