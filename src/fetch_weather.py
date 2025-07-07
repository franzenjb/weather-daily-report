# This script will fetch and clean weather data. 

import json
import requests
from datetime import datetime
from src.utils import get_nhc_data, get_wpc_data, get_nwps_data

def get_nws_discussions(offices):
    """
    Fetches the latest Area Forecast Discussion (AFD) for each NWS office.
    """
    print("Fetching Area Forecast Discussions from NWS API...")
    discussions = {}
    headers = {"User-Agent": "Weather Report Generator (github.com/your-repo)"}

    for office in offices:
        office_code = office['code']
        print(f"  Fetching AFD for {office['office']} ({office_code})...")
        # The API endpoint for AFD products for a specific office
        afd_url = f"https://api.weather.gov/products/types/AFD/locations/{office_code}"
        
        try:
            # Get the list of available discussions
            response = requests.get(afd_url, headers=headers, timeout=15)
            response.raise_for_status()
            product_list = response.json().get('@graph', [])

            if not product_list:
                print(f"    No AFD products found for {office_code}.")
                discussions[office_code] = {"error": "No AFD products found."}
                continue

            # Fetch the actual content of the latest discussion
            latest_product_url = product_list[0].get('@id')
            product_response = requests.get(latest_product_url, headers=headers, timeout=15)
            product_response.raise_for_status()
            product_data = product_response.json()
            
            discussions[office_code] = {
                "office_code": office_code,
                "state": office['state'],
                "product_text": product_data.get('productText', 'Discussion text not available.')
            }

        except requests.exceptions.RequestException as e:
            print(f"    Failed to get AFD for {office_code}: {e}")
            discussions[office_code] = {"error": str(e)}

    return discussions

def get_nws_alerts():
    """
    Fetches active weather alerts from the NWS API for the specified states.
    """
    print("Fetching active alerts from NWS API...")
    target_areas = ["AL", "FL", "GA", "MS", "NC", "SC", "TN", "VI"]
    api_url = f"https://api.weather.gov/alerts/active?area={','.join(target_areas)}"
    headers = {"User-Agent": "Weather Report Generator (github.com/your-repo)", "Accept": "application/geo+json"}
    
    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        alerts = response.json().get('features', [])
        print(f"  Found {len(alerts)} active alerts.")
        return alerts
    except requests.exceptions.RequestException as e:
        print(f"  Could not fetch NWS API data: {e}")
        return [{"error": str(e)}]

def main():
    """
    Main function to orchestrate data fetching for LLM synthesis.
    """
    with open('data/nws_offices.json', 'r') as f:
        offices = json.load(f)

    nws_discussions = get_nws_discussions(offices)
    nws_alerts = get_nws_alerts()
    nhc_data = get_nhc_data()
    # nwps_data = get_nwps_data() # Temporarily disabled due to API issues
    wpc_data = get_wpc_data() # Placeholder remains

    weather_data = {
        "generated_time": datetime.utcnow().isoformat(),
        "nws_discussions": nws_discussions,
        "nws_alerts": nws_alerts,
        "nhc": nhc_data,
        # "nwps": nwps_data,
        "wpc": wpc_data,
    }

    with open('output/weather_data.json', 'w') as f:
        json.dump(weather_data, f, indent=4)
    
    print("Weather data and discussions saved to output/weather_data.json")

if __name__ == "__main__":
    main() 