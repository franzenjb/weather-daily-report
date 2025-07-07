import json
import asyncio
from src.utils import fetch_all_state_data

STATE_CODES = {
    "Tennessee": "TN",
    "Mississippi": "MS",
    "Alabama": "AL",
    "Georgia": "GA",
    "Florida": "FL",
    "North Carolina": "NC",
    "South Carolina": "SC",
    "U.S. Virgin Islands": "VI"
}

async def main():
    """Main function to orchestrate the fetching of weather data."""
    print("Starting weather data fetch...")
    try:
        with open('data/nws_offices.json', 'r') as f:
            nws_offices = json.load(f)
    except FileNotFoundError:
        print("Error: 'data/nws_offices.json' not found.")
        return
    except json.JSONDecodeError:
        print("Error: Could not decode 'data/nws_offices.json'.")
        return

    all_weather_data = {}

    for state, offices in nws_offices.items():
        print(f"--- Processing {state} ---")
        state_code = STATE_CODES.get(state)
        if not state_code:
            print(f"Warning: No state code found for {state}. Skipping alerts.")
            continue
        
        weather_data = await fetch_all_state_data(state, offices, state_code)
        all_weather_data[state] = weather_data

    try:
        with open('output/weather_data.json', 'w') as f:
            json.dump(all_weather_data, f, indent=4)
        print("\nSuccessfully fetched all data and saved to 'output/weather_data.json'")
    except IOError as e:
        print(f"Error writing to 'output/weather_data.json': {e}")


if __name__ == "__main__":
    asyncio.run(main()) 