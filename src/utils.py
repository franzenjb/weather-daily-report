# This file will contain shared functions used by other scripts. 

import requests
from bs4 import BeautifulSoup
import re
import time

def get_nhc_data():
    """
    Fetches data from the National Hurricane Center 7-day outlook.
    """
    print("Fetching NHC data...")
    nhc_url = "https://www.nhc.noaa.gov/gtwo.php?basin=atlc&fdays=7"
    nhc_data = {
        "summary": "No tropical cyclone activity is expected during the next 7 days.",
        "formation_chance_7day": "0",
        "details": [],
        "error": None
    }
    try:
        response = requests.get(nhc_url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # This parsing logic is based on current NHC page structure and may need updates if they change it.
        # Find all disturbance summary buttons to get formation chances
        disturbance_buttons = soup.find_all('button', id=re.compile(r'xshcontents\d+btn'))
        
        if not disturbance_buttons:
            # Check for the "no activity" text if no disturbance buttons are found
            summary_text_element = soup.find(string=re.compile("Tropical cyclone formation is not expected"))
            if summary_text_element:
                nhc_data["summary"] = summary_text_element.strip()
        else:
            highest_chance = 0
            details = []
            for button in disturbance_buttons:
                text = button.get_text()
                chance_search = re.search(r'7-Day Formation Chance: Low \((\d+)%\)', text)
                if chance_search:
                    chance = int(chance_search.group(1))
                    if chance > highest_chance:
                        highest_chance = chance
                    details.append(text.strip())

            if highest_chance > 0:
                 nhc_data["summary"] = f"One or more disturbances identified with up to {highest_chance}% chance of formation."
                 nhc_data["formation_chance_7day"] = str(highest_chance)
                 nhc_data["details"] = details

    except requests.exceptions.RequestException as e:
        print(f"  Could not fetch NHC data: {e}")
        nhc_data['error'] = str(e)
        nhc_data['summary'] = "Could not retrieve NHC Tropical Weather Outlook."

    return nhc_data

def get_wpc_data():
    """
    Fetches Quantitative Precipitation Forecast data.
    NOTE: This is a placeholder. WPC data is graphical and requires a more
    complex parsing strategy or a different data source.
    """
    print("Fetching WPC QPF data...")
    return {
        "summary": "Quantitative precipitation forecast data not yet implemented.",
        "error": "Not implemented"
    }

def get_nwps_data():
    """
    Fetches river gauge data, checking for forecast values exceeding flood stage.
    """
    print("Fetching river gauge data from NWPS API...")
    target_states = ["AL", "FL", "GA", "MS", "NC", "SC", "TN", "VI"]
    flooding_gauges = []
    
    for state in target_states:
        print(f"  Fetching gauge data for {state}...")
        try:
            url = f"https://api.water.noaa.gov/nwps/v1/gauges?state={state}"
            response = requests.get(url, timeout=45)
            response.raise_for_status()
            gauges = response.json()
            
            for gauge_id, gauge_data in gauges.items():
                forecast_val_str = gauge_data.get('forecast', {}).get('primary', {}).get('value')
                flood_stage_str = gauge_data.get('flood', {}).get('primary', {}).get('value')

                if forecast_val_str is not None and flood_stage_str is not None:
                    try:
                        if float(forecast_val_str) > float(flood_stage_str):
                            flooding_gauges.append({
                                "id": gauge_id,
                                "name": gauge_data.get('location'),
                                "state": state,
                                "status": gauge_data.get('status', 'forecasted flood'),
                                "waterbody": gauge_data.get('waterbody'),
                                "forecast_value": forecast_val_str,
                                "flood_stage": flood_stage_str
                            })
                    except (ValueError, TypeError):
                        # Couldn't convert values to float, skip this gauge
                        continue
            time.sleep(1)
        except requests.exceptions.RequestException as e:
            print(f"    Could not fetch NWPS data for {state}: {e}")
            continue
            
    print(f"  Found {len(flooding_gauges)} gauges forecasted to be in flood.")
    return {"gauges": flooding_gauges} 