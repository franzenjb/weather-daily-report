import aiohttp
import asyncio
import json
from tqdm.asyncio import tqdm

# User-Agent header is required by the NWS API
HEADERS = {
    'User-Agent': 'EmergencyManagementWeatherBot/1.0 (dev.em.weather@example.com)'
}

async def get_nwps_data(session, state, station_id, station_info):
    # This function is currently disabled due to persistent API timeouts.
    # It remains as a placeholder for future functionality.
    return {
        "station_id": station_id,
        "river_data": "River data service is temporarily unavailable."
    }

async def get_nws_discussion(session, state, office_id):
    """Fetches the Area Forecast Discussion for a given NWS office."""
    url = f"https://api.weather.gov/products/types/AFD/locations/{office_id}"
    try:
        async with session.get(url, headers=HEADERS, timeout=15) as response:
            if response.status == 200:
                data = await response.json()
                if data.get('@graph'):
                    discussion_product = data['@graph'][0]
                    return {
                        "office_id": office_id,
                        "discussion": discussion_product.get('productText', 'No discussion text found.')
                    }
                else:
                    return {"office_id": office_id, "discussion": "No discussion data in expected format."}
            else:
                return {"office_id": office_id, "discussion": f"Failed to fetch discussion. Status: {response.status}"}
    except Exception as e:
        return {"office_id": office_id, "discussion": f"An error occurred: {e}"}

async def get_active_alerts_for_state(session, state_code):
    """Fetches active alerts for a given state."""
    url = f"https://api.weather.gov/alerts/active?area={state_code}"
    try:
        async with session.get(url, headers=HEADERS, timeout=15) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('features', [])
            else:
                return []
    except Exception:
        return []

async def fetch_all_state_data(state, offices, state_code):
    """Fetches all weather data for a single state asynchronously."""
    async with aiohttp.ClientSession() as session:
        # Fetch discussions
        discussion_tasks = [get_nws_discussion(session, state, office) for office in offices]
        discussions = await tqdm.gather(*discussion_tasks, desc=f"Fetching discussions for {state}")

        # Fetch alerts
        alerts = await get_active_alerts_for_state(session, state_code)

        # NWPS river data fetching is disabled
        river_conditions = []

        return {
            "discussions": discussions,
            "alerts": alerts,
            "river_conditions": river_conditions
        } 