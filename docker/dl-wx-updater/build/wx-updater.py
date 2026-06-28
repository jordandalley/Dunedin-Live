import requests
import re
import ast
import json
import os
import time
from requests.auth import HTTPBasicAuth

# Load environment variables with defaults where appropriate
metserviceApi = os.getenv('MET_API_URL', 'https://api.metservice.com/mobile/nz/weatherData')
metserviceApiKey = os.getenv('MET_API_KEY')
lat = os.getenv('MET_LAT')
lon = os.getenv('MET_LON')
portotagoApi = os.getenv('PO_API_URL', 'https://dvp.portotago.co.nz/dvp/graphs/htmx/get-graph/4?dashboardName=&graphViewConfigId=3')
userAgent = 'Mozilla/5.0 (Linux; Android 10; K; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/125.000 Mobile Safari/537.36'

cameraUrl = os.getenv('CAMERA_URL')
cameraUsername = os.getenv('CAMERA_USERNAME')
cameraPassword = os.getenv('CAMERA_PASSWORD')

updateFreq = int(os.getenv('UPDATE_INTERVAL', 600))  # Seconds between updates

# Validate required environment variables
required_vars = {
    "MET_API_KEY": metserviceApiKey,
    "MET_LAT": lat,
    "MET_LON": lon,
    "CAMERA_URL": cameraUrl,
    "CAMERA_USERNAME": cameraUsername,
    "CAMERA_PASSWORD": cameraPassword
}

missing = [var for var, val in required_vars.items() if not val]

if missing:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

# Timestamp helper
def ts():
    return time.strftime("[%Y-%m-%d %H:%M:%S]")

def get_met_obs(metserviceApi, metserviceApiKey, lat, lon, userAgent):
    """Fetch weather data from Metservice API."""

    headers = {
        'Accept': '*/*',
        'User-Agent': userAgent,
        'Accept-Language': 'en-CA;q=1.0',
        'Accept-Encoding': 'br;q=1.0, gzip;q=0.9, deflate;q=0.8',
        'Connection': 'keep-alive',
        'apiKey': metserviceApiKey
    }

    fullmetserviceApi = f"{metserviceApi}/{lat}/{lon}"

    try:
        response = requests.get(fullmetserviceApi, headers=headers, timeout=10)
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

    observationArray = list(obs.items())

    wxString1 = (
        "T: " + next((v for k, v in observationArray if k == 'temperature'), "?")
        + chr(186) + "C  H: " + next((v for k, v in observationArray if k == 'relativeHumidity'), "?") + "%"
    )

    return wxString1


def get_portotago_obs(portotagoApi, userAgent):

    headers = {
        "User-Agent": userAgent
    }

    # knots to km/hr conversion
    kts_to_kmh = 1.852

    try:
        response = requests.get(portotagoApi, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"{ts()} Network error fetching Port Otago data: {e}")
        return None

    html = response.text

    # This looks for 'const infoConfig = ' and captures the '{...}' before the ';'
    matches = re.findall(r"const infoConfig\s*=\s*(\{.*?\});", html)

    weather_data = []
    for match in matches:
        try:
            parsed_dict = ast.literal_eval(match)
            weather_data.append(parsed_dict)
        except Exception:
            continue

    if not weather_data or 'values' not in weather_data[0]:
        return None

    try:
        kts_speed = float(weather_data[0]['values'][0]['current_value'])
        kts_gust = float(weather_data[0]['values'][1]['current_value'])

        # Convert KTS to KMH
        windSpeed = str(round(kts_speed * kts_to_kmh))
        windGustSpeed = str(round(kts_gust * kts_to_kmh))
        windDirection = weather_data[0]['values'][2]['metadata']
    except (IndexError, KeyError, ValueError):
        return None

    # FIXED: Replaced brittle string manipulation with safe f-string substitution and defaults
    wd = windDirection if windDirection else "?"
    ws = windSpeed if windSpeed else "?"
    wg = windGustSpeed if windGustSpeed else "?"

    wxString2 = f"W: {wd} {ws}-{wg} kph"
    return wxString2

def updateOSD(cameraUrl, cameraUsername, cameraPassword, wxString1, wxString2):
    """Send updated weather info to the camera OSD."""
    try:
        # FIXED: Reverted back to triple quotes for valid Python multiline f-string formatting
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
              <X type="uint32">100</X>
              <Y type="uint32">100</Y>
              <dateFormat type="dateFormat">day-month-year</dateFormat>
            </time>
            <channelName>
              <switch type="boolean">false</switch>
                <X type="uint32">0</X>
                <Y type="uint32">0</Y>
                <name type="string"><![CDATA[DI-380IPEN-MVF-V3]]></name>
            </channelName>
            <textOverLay type="list" count="4">
              <item>
                <switch type="boolean">false</switch>
                <X type="uint32">0</X>
                <Y type="uint32">0</Y>
                <showLevel type="uint32">0</showLevel>
                <flickerSwitch type="boolean">false</flickerSwitch>
                <osdOverlayType type="osdOverlayType">IMAGE</osdOverlayType>
                <value type="string" maxLen="32"><![CDATA[Picture]]></value>
              </item>
              <item>
                <switch type="boolean">true</switch>
                <X type="uint32">100</X>
                <Y type="uint32">380</Y>
                <showLevel type="uint32">0</showLevel>
                <flickerSwitch type="boolean">true</flickerSwitch>
                <osdOverlayType type="osdOverlayType">TEXT</osdOverlayType>
                <value type="string" maxLen="32"><![CDATA[{wxString1}
{wxString2}]]></value>
              </item>
              <item>
                <switch type="boolean">false</switch>
                <X type="uint32">0</X>
                <Y type="uint32">0</Y>
                <showLevel type="uint32">0</showLevel>
                <flickerSwitch type="boolean">true</flickerSwitch>
                <osdOverlayType type="osdOverlayType">TEXT</osdOverlayType>
                <value type="string" maxLen="32"><![CDATA[]]></value>
              </item>
              <item>
                <switch type="boolean">false</switch>
                <X type="uint32">0</X>
                <Y type="uint32">0</Y>
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
            print(f"{ts()} Fetching weather data from {metserviceApi} for lat {lat}, lon {lon}...")
            wxString1 = get_met_obs(metserviceApi, metserviceApiKey, lat, lon, userAgent)
            print(f"{ts()} Fetching weather data from {portotagoApi}...")
            wxString2 = get_portotago_obs(portotagoApi, userAgent)
            print(f"{ts()} Results -> MetService: {wxString1} | Port Otago: {wxString2}")
            if wxString1 and wxString2:
                print(f"{ts()} Updating Camera OSD at {cameraUrl}...")
                updateOSD(cameraUrl, cameraUsername, cameraPassword, wxString1, wxString2)
            else:
                print(f"{ts()} No weather data available. Skipping camera update.")

        except Exception as e:
            print(f"{ts()} Unexpected error in main loop: {type(e).__name__}: {e}")

        time.sleep(updateFreq)

if __name__ == "__main__":
    main_loop()
