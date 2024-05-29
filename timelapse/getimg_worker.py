import os
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import pytz
import time

# URL to Camera Snapshot API
CAMERA_API_URL = "http://192.168.50.3/GetSnapshot"

# Timezone
TIMEZONE = "Pacific/Auckland"

# Camera Username/Password (Consider using environment variables instead)
CAMERA_API_USER = ""
CAMERA_API_PASSWORD = ""

# Time interval between capturing frames (in seconds)
TIME_INTERVAL = 10

# Save Path
IMG_SAVE_PATH = "/mnt/Media2/Dunedin-Live"

def download_image(url, username, password, savepath, tz):
    try:
        response = requests.get(url, auth=HTTPBasicAuth(username, password), timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        current_time = datetime.now(pytz.timezone(tz))
        ts = current_time.strftime("%H:%M:%S")
        ds = current_time.strftime("%d-%m-%Y")
        outputpath = os.path.join(savepath, ds)
        os.makedirs(outputpath, exist_ok=True)  # Create the directory if it doesn't exist
        filepath = os.path.join(outputpath, f"{ts}.jpg")
        with open(filepath, 'wb') as f:
            f.write(response.content)
    except requests.exceptions.RequestException as e:
        print(f"Failed to download image: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def run_download_loop(ti):
    while True:
        download_image(CAMERA_API_URL, CAMERA_API_USER, CAMERA_API_PASSWORD, IMG_SAVE_PATH, TIMEZONE)
        time.sleep(ti)  # Sleep for x seconds before next image grab

if __name__ == "__main__":
    run_download_loop(TIME_INTERVAL)
