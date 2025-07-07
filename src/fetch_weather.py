import requests
import json
import os

# --- Path Setup ---
# Get the absolute path of the directory where the script is located
_script_dir = os.path.dirname(os.path.abspath(__file__))
# Get the project root directory (assuming the script is in 'src')
_project_root = os.path.dirname(_script_dir)

# Define absolute paths
_nws_offices_path = os.path.join(_project_root, 'data', 'nws_offices.json')
_output_weather_data_path = os.path.join(_project_root, 'output', 'weather_data.json')


def get_office_codes():
    """
    Loads NWS office codes from a JSON file.
    """
    with open(_nws_offices_path, 'r') as f:
        offices = json.load(f)
    return [office['code'] for office in offices]

def get_area_forecast_discussions(office_codes):
    """
    Fetches Area Forecast Discussions for a list of NWS office codes.
    """
    discussions = {}
    print("Fetching Area Forecast Discussions from NWS API...")
    # This is a placeholder as the real API calls were removed in a previous step.
    # A full implementation would make HTTP requests to the NWS API here.
    for office_code in office_codes:
        print(f"  Fetching AFD for {office_code}...")
        discussions[office_code] = {"office_code": office_code, "product_text": f"This is a placeholder forecast discussion for {office_code}."}
    return discussions

def get_active_alerts_by_state(states):
    """
    Fetches active weather alerts from the NWS API for the specified states.
    """
    print("Fetching active alerts from NWS API...")
    # The API can take a comma-separated list of state/zone codes
    api_url = f"https://api.weather.gov/alerts/active?area={','.join(states)}"
    headers = {"User-Agent": "Weather Report Generator (for personal use)"} # A user-agent is required

    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        alerts = response.json().get('features', [])
        print(f"  Found {len(alerts)} active alerts.")
        return alerts
    except requests.exceptions.RequestException as e:
        print(f"  Could not fetch NWS API data: {e}")
        return [{"error": str(e)}]

def get_nhc_data():
    """
    Fetches data from the National Hurricane Center (NHC). Placeholder.
    """
    print("Fetching NHC data...")
    return {
        "summary": "Tropical cyclone formation is not expected during the next 7 days.",
        "formation_chance_7day": "0"
    }

def get_wpc_qpf_data():
    """
    Fetches the Weather Prediction Center Quantitative Precipitation Forecast data. Placeholder.
    """
    print("Fetching WPC QPF data...")
    return {"placeholder": "WPC QPF Data not implemented yet."}

def get_nwps_data():
    """
    Fetches National Water Prediction Service data. Placeholder.
    """
    return {"gauges": []}


def save_data(data):
    """
    Saves the combined weather data to a JSON file.
    """
    # Ensure the output directory exists before trying to write to it
    os.makedirs(os.path.dirname(_output_weather_data_path), exist_ok=True)
    
    with open(_output_weather_data_path, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Weather data and discussions saved to {_output_weather_data_path}")

def main():
    """
    Main function to fetch all data and save it.
    """
    office_codes = get_office_codes()
    nws_discussions = get_area_forecast_discussions(office_codes)
    
    states = ["TN", "MS", "AL", "GA", "FL", "NC", "SC", "VI"]
    nws_alerts = get_active_alerts_by_state(states)
    
    nhc_data = get_nhc_data()
    wpc_data = get_wpc_qpf_data()
    nwps_data = get_nwps_data()
    
    weather_data = {
        "nws_discussions": nws_discussions,
        "nws_alerts": nws_alerts,
        "nhc": nhc_data,
        "wpc_qpf": wpc_data,
        "nwps": nwps_data
    }
    
    save_data(weather_data)

if __name__ == "__main__":
    main()