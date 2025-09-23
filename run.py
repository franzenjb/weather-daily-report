# This is the main orchestrator script.
# It will run all the steps daily to generate the weather report.

from src import fetch_weather
from src import generate_report
import time

def main():
    """
    Main orchestrator to run all steps.
    """
    print("--- Starting Daily Weather Report Generation ---")
    start_time = time.time()
    
    # Step 1: Fetch all weather data
    print("\n[Step 1/2] Fetching weather data...")
    try:
        fetch_weather.main()
        print("[Step 1/2] Data fetching complete.")
    except Exception as e:
        print(f"!!! An error occurred during data fetching: {e}")
        return  # Exit if fetching fails
    
    # Step 2: Generate the HTML report
    print("\n[Step 2/2] Generating HTML report...")
    try:
        generate_report.main()
        print("[Step 2/2] Report generation complete.")
    except Exception as e:
        print(f"!!! An error occurred during report generation: {e}")
        return
    
    end_time = time.time()
    print(f"\n--- Weather Report Generation Finished in {end_time - start_time:.2f} seconds ---")
    print("Final report is available at: output/summary.html")

if __name__ == "__main__":
    main()