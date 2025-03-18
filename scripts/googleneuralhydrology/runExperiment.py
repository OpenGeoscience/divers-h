import json
import os
import subprocess
import shutil
import time
import logging
import click

# Define the shell script path
SHELL_SCRIPT = "/media/bryon.lewis/Elements/DIVERSH/GoogleNeuralHydrology/run_demo1.sh"  # Adjust as necessary
EXPERIMENTS_PATH="/media/bryon.lewis/Elements/DIVERSH/GoogleNeuralHydrology/Experiments"
# Configure logging
logging.basicConfig(
    filename="hru_processing.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

@click.command()
@click.argument("hru_ids_file", type=click.Path(exists=True))
@click.option("--wait-time", default=60, help="Max seconds to wait for test_results.nc.")
@click.option("--poll-interval", default=5, help="Time in seconds between file existence checks.")
def run_hru_tasks(hru_ids_file, wait_time, poll_interval):
    """Runs a shell script for each HRU ID, waits for output, and organizes NetCDF files."""

    with open(hru_ids_file, "r") as f:
        hru_ids = json.load(f)

    total_ids = len(hru_ids)
    results_dir = "netcdf_results"
    os.makedirs(results_dir, exist_ok=True)

    logging.info(f"Starting HRU processing for {total_ids} HRU IDs.")

    for index, hru_id in enumerate(hru_ids, start=1):
        click.echo(f"Processing HRU ID {hru_id} ({index}/{total_ids})...")
        logging.info(f"Processing HRU ID: {hru_id} ({index}/{total_ids})")

        # Check if the files already exist
        existing_netcdf_file = os.path.join(results_dir, f"{hru_id}.nc")
        existing_exp_dir = os.path.join(EXPERIMENTS_PATH, hru_id)

        if os.path.exists(existing_netcdf_file):
            click.echo(f"Skipping HRU ID {hru_id} because the data already exists.")
            logging.info(f"Skipping HRU ID {hru_id} because the data already exists.")
            continue  # Skip this HRU ID
        if os.path.exists(existing_exp_dir):
            for root, _, files in os.walk(existing_exp_dir):
                if "test_results.nc" in files:
                    test_results_path = os.path.join(root, "test_results.nc")
                    break
            
            if test_results_path:
                new_file_path = os.path.join(results_dir, f"{hru_id}.nc")
                shutil.move(test_results_path, new_file_path)
                click.echo(f"Moved {test_results_path} → {new_file_path} ({index}/{total_ids} complete)")
                logging.info(f"Moved {test_results_path} → {new_file_path} ({index}/{total_ids} complete)")
                continue

        # Run shell script and wait for it to complete (suppress subprocess logging)
        cmd = [SHELL_SCRIPT, "-b", hru_id]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logging.info(f"Successfully executed shell script for HRU ID: {hru_id}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Shell script failed for HRU ID {hru_id}: {e}")
            continue

        # Wait and check for the test_results.nc file
        exp_base = os.path.join(EXPERIMENTS_PATH, hru_id)
        test_results_path = None
        elapsed_time = 0

        while elapsed_time < wait_time:
            for root, _, files in os.walk(exp_base):
                if "test_results.nc" in files:
                    test_results_path = os.path.join(root, "test_results.nc")
                    break
            
            if test_results_path:
                break  # Exit loop once the file is found

            time.sleep(poll_interval)
            click.echo(f"Waiting for test_results.nc for HRU ID {hru_id}... ({elapsed_time}s elapsed)")
            logging.info(f"Waiting for test_results.nc for HRU ID {hru_id}... ({elapsed_time}s elapsed)")
            elapsed_time += poll_interval

        if test_results_path:
            new_file_path = os.path.join(results_dir, f"{hru_id}.nc")
            shutil.move(test_results_path, new_file_path)
            click.echo(f"Moved {test_results_path} → {new_file_path} ({index}/{total_ids} complete)")
            logging.info(f"Moved {test_results_path} → {new_file_path} ({index}/{total_ids} complete)")
        else:
            click.echo(f"Warning: test_results.nc not found for {hru_id} after {wait_time} seconds.")
            logging.warning(f"test_results.nc not found for HRU ID {hru_id} after {wait_time} seconds.")

    logging.info(f"HRU processing completed. {index}/{total_ids} processed.")

if __name__ == "__main__":
    run_hru_tasks()
