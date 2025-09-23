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
    
    headers = {"User-Agent": "Weather Report Generator (for personal use)"} # A user-agent is required
    
    for office_code in office_codes:
        api_url = f"https://api.weather.gov/products/types/AFD/locations/{office_code}"
        try:
            # Get the list of recent AFD products
            response = requests.get(api_url, headers=headers, timeout=15)
            response.raise_for_status()
            product_list = response.json().get('@graph', [])
            
            if product_list:
                # Get the URL of the latest AFD product
                latest_product_url = product_list[0].get('@id')
                if latest_product_url:
                    print(f"  Fetching AFD for {office_code}...")
                    # Fetch the actual product text
                    product_response = requests.get(latest_product_url, headers=headers, timeout=15)
                    product_response.raise_for_status()
                    product_data = product_response.json()
                    discussions[office_code] = {
                        "office_code": office_code, 
                        "product_text": product_data.get('productText', 'Could not retrieve discussion text.')
                    }
                else:
                    print(f"  No AFD product URL found for {office_code}.")
                    discussions[office_code] = {"office_code": office_code, "product_text": "No discussion URL found."}
            else:
                print(f"  No AFD products found for {office_code}.")
                discussions[office_code] = {"office_code": office_code, "product_text": "No discussion products found."}

        except requests.exceptions.RequestException as e:
            print(f"  Could not fetch AFD for {office_code}: {e}")
            discussions[office_code] = {"office_code": office_code, "product_text": f"Error fetching discussion: {e}"}

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