import asyncio
import subprocess
import os

def run_script(script_name):
    """Runs a Python script and waits for it to complete."""
    try:
        # We need to specify the python executable from the virtual environment
        python_executable = os.path.join(os.path.dirname(os.path.realpath(__file__)), '.venv', 'bin', 'python')
        
        # Fallback to just 'python' if venv is not found (e.g., when running in a different setup)
        if not os.path.exists(python_executable):
            python_executable = 'python'

        process = subprocess.run([python_executable, script_name], check=True, capture_output=True, text=True)
        print(f"--- {script_name} output ---")
        print(process.stdout)
        if process.stderr:
            print(f"--- {script_name} errors ---")
            print(process.stderr)
        print(f"--- End of {script_name} ---")
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_name}:")
        print(e.stdout)
        print(e.stderr)
    except FileNotFoundError:
        print(f"Error: The command 'python' was not found.")
        print("Please ensure Python is installed and in your PATH, or the virtual environment is set up correctly.")


async def main():
    print("=========================================")
    print("Starting Daily Weather Report Generation")
    print("=========================================\n")
    
    # Step 1: Fetch all the latest data from the APIs
    # This script is async and needs to be run with asyncio
    print("Step 1: Fetching latest weather data...")
    
    # Since this main function is async, we can't use subprocess.run which is blocking.
    # We will use asyncio's subprocess capabilities.
    fetch_process = await asyncio.create_subprocess_exec(
        'python', 'src/fetch_weather.py',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await fetch_process.communicate()

    print("--- src/fetch_weather.py output ---")
    if stdout:
        print(stdout.decode())
    if stderr:
        print("--- src/fetch_weather.py errors ---")
        print(stderr.decode())
    print("--- End of src/fetch_weather.py ---\n")

    if fetch_process.returncode != 0:
        print("fetch_weather.py failed. Aborting report generation.")
        return

    # Step 2: Generate the prompts for the LLM
    print("Step 2: Generating prompts for LLM...")
    run_script('src/generate_report.py')
    
    # The final step of synthesizing the report and creating the HTML
    # would be done by the user or a subsequent LLM call using the generated prompts.
    # For this project, we stop here.
    
    print("\n=========================================")
    print("Report Generation Process Finished.")
    print("Next step: Use 'output/prompts_for_llm.json' with your LLM to generate summaries.")
    print("=========================================")


if __name__ == '__main__':
    # On Windows, we might need to set a different event loop policy
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main()) 