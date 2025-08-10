import os
import requests
from requests.auth import HTTPBasicAuth
import time

# Timestamp helper
def ts():
    return time.strftime("[%Y-%m-%d %H:%M:%S]")

# Load environment variables with defaults where appropriate
apiUrl = os.getenv('API_URL', 'https://api.metservice.com/mobile/nz/weatherData')
apiKey = os.getenv('API_KEY')
lat = os.getenv('LAT')
lon = os.getenv('LON')

cameraUrl = os.getenv('CAMERA_URL')
cameraUsername = os.getenv('CAMERA_USERNAME')
cameraPassword = os.getenv('CAMERA_PASSWORD')

updateFreq = int(os.getenv('UPDATE_INTERVAL', 600))  # Seconds between updates

# Validate required environment variables
required_vars = {
    "API_KEY": apiKey,
    "LAT": lat,
    "LON": lon,
    "CAMERA_URL": cameraUrl,
    "CAMERA_USERNAME": cameraUsername,
    "CAMERA_PASSWORD": cameraPassword
}
missing = [var for var, val in required_vars.items() if not val]
if missing:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

def get_weather_data(apiUrl, apiKey, lat, lon):
    """Fetch weather data from Metservice API and return as list of (key, value) tuples."""
    headers = {
        'Accept': '*/*',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/125.000 Mobile Safari/537.36',
        'Accept-Language': 'en-CA;q=1.0',
        'Accept-Encoding': 'br;q=1.0, gzip;q=0.9, deflate;q=0.8',
        'Connection': 'keep-alive',
        'apiKey': apiKey
    }

    fullApiUrl = f"{apiUrl}/{lat}/{lon}"
    try:
        response = requests.get(fullApiUrl, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"{ts()} Network/API error while fetching weather data: {e}")
        return None

    try:
        data = response.json()
    except ValueError:
        snippet = response.text[:200] + ("..." if len(response.text) > 200 else "")
        print(f"{ts()} Error: Response not JSON: {snippet}")
        return None

    obs = data.get('result', {}).get('observationData')
    if not obs:
        print(f"{ts()} Warning: No observation data in API response")
        return None

    return list(obs.items())

def updateOSD(cameraUrl, cameraUsername, cameraPassword, observationArray):
    """Send updated weather info to the camera OSD."""
    try:
        wxString1 = (
            "T: " + next((v for k, v in observationArray if k == 'temperature'), "?")
            + chr(186) + "C  H: " + next((v for k, v in observationArray if k == 'relativeHumidity'), "?") + "%"
        )
        wxString2 = (
            "W: " + next((v for k, v in observationArray if k == 'windDirection'), "?")
            + " " + next((v for k, v in observationArray if k == 'windSpeed'), "?")
            + "-" + next((v for k, v in observationArray if k == 'windGustSpeed'), "?") + " kph"
        )

        xml_data_raw = f"""<?xml version="1.0" encoding="UTF-8"?>
        <config xmlns="http://www.ipc.com/ver10" version="1.7">
          <types>
            <dateFormat>
              <enum>year-month-day</enum>
              <enum>month-day-year</enum>
              <enum>day-month-year</enum>
            </dateFormat>
            <osdOverlayType>
              <enum>TEXT</enum>
              <enum>IMAGE</enum>
            </osdOverlayType>
          </types>
          <imageOsd>
            <time>
              <switch type="boolean">true</switch>
              <X type="uint32">300</X>
              <Y type="uint32">420</Y>
              <dateFormat type="dateFormat">day-month-year</dateFormat>
            </time>
            <channelName>
              <switch type="boolean">false</switch>
                <X type="uint32">75</X>
                <Y type="uint32">100</Y>
                <name type="string"><![CDATA[DI-380IPEN-MVF-V3]]></name>
            </channelName>
            <textOverLay type="list" count="4">
              <item>
                <switch type="boolean">true</switch>
                <X type="uint32">9200</X>
                <Y type="uint32">460</Y>
                <showLevel type="uint32">0</showLevel>
                <flickerSwitch type="boolean">false</flickerSwitch>
                <osdOverlayType type="osdOverlayType">IMAGE</osdOverlayType>
                <value type="string" maxLen="32"><![CDATA[Picture]]></value>
              </item>
              <item>
                <switch type="boolean">true</switch>
                <X type="uint32">300</X>
                <Y type="uint32">700</Y>
                <showLevel type="uint32">0</showLevel>
                <flickerSwitch type="boolean">false</flickerSwitch>
                <osdOverlayType type="osdOverlayType">TEXT</osdOverlayType>
                <value type="string" maxLen="32"><![CDATA[{wxString1}]]></value>
              </item>
              <item>
                <switch type="boolean">true</switch>
                <X type="uint32">304</X>
                <Y type="uint32">960</Y>
                <showLevel type="uint32">0</showLevel>
                <flickerSwitch type="boolean">true</flickerSwitch>
                <osdOverlayType type="osdOverlayType">TEXT</osdOverlayType>
                <value type="string" maxLen="32"><![CDATA[{wxString2}]]></value>
              </item>
              <item>
                <switch type="boolean">false</switch>
                <X type="uint32">125</X>
                <Y type="uint32">4800</Y>
                <showLevel type="uint32">0</showLevel>
                <flickerSwitch type="boolean">false</flickerSwitch>
                <osdOverlayType type="osdOverlayType">TEXT</osdOverlayType>
                <value type="string" maxLen="32"><![CDATA[]]></value>
              </item>
            </textOverLay>
          </imageOsd>
        </config>"""

        headers = {"Content-Type": "application/xml"}
        response = requests.post(
            cameraUrl,
            data=xml_data_raw.encode('utf-8'),
            headers=headers,
            auth=HTTPBasicAuth(cameraUsername, cameraPassword),
            verify=False,
            timeout=10
        )
        response.raise_for_status()
        print(f"{ts()} Camera OSD updated successfully (HTTP {response.status_code})")

    except requests.RequestException as e:
        print(f"{ts()} Camera update failed: {e}")
    except Exception as e:
        print(f"{ts()} Unexpected error updating camera: {type(e).__name__}: {e}")

def main_loop():
    while True:
        try:
            print(f"{ts()} Fetching weather data from {apiUrl} for lat {lat}, lon {lon}...")
            observationArray = get_weather_data(apiUrl, apiKey, lat, lon)
            if observationArray:
                print(f"{ts()} Updating Camera OSD at {cameraUrl}...")
                updateOSD(cameraUrl, cameraUsername, cameraPassword, observationArray)
            else:
                print(f"{ts()} No weather data available. Skipping camera update.")

        except Exception as e:
            print(f"{ts()} Unexpected error in main loop: {type(e).__name__}: {e}")

        time.sleep(updateFreq)

if __name__ == "__main__":
    main_loop()
