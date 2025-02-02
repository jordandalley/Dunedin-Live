import requests
from requests.auth import HTTPBasicAuth
import json

# Metservice API variables
apiUrl = 'https://api.metservice.com/mobile/nz/weatherData'
apiKey = ''
lat = '-45.87416'
lon = '170.50361'
# Camera API variables
cameraUrl = "http://192.168.53.4/SetImageOsdConfig"
cameraUsername = ''
cameraPassword = ''

def get_weather_data(apiUrl, apiKey, lat, lon):

    # Create headers for API call
    headers = {
        'Accept': '*/*',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/125.000 Mobile Safari/537.36',
        'Accept-Language': 'en-CA;q=1.0',
        'Accept-Encoding': 'br;q=1.0, gzip;q=0.9, deflate;q=0.8',
        'Connection': 'keep-alive',
        'apiKey': apiKey
    }

    # Construct the full URL using f-string
    fullApiUrl = f"{apiUrl}/{lat}/{lon}"

    # Send the GET request
    response = requests.get(fullApiUrl, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        try:
            # Parse the JSON response
            data = response.json()
            # Grab only the current observations
            json = data.get('result', {}).get('observationData', None)
            # Convert the current observations into an array
            return list(json.items())

        except ValueError:
            # If JSON parsing fails, print the raw response
            print(f"Error: Response is not in JSON format. Raw response: {response.text}")
    else:
        print(f"Error {response.status_code}: {response.text}")

def updateOSD(cameraUrl,cameraUsername,cameraPassword,observationArray):
    tempAndHumString = 'Temp: ' + next((value for key, value in observationArray if key == 'temperature'), None) + chr(186) + 'C' + chr(10) + 'Humi: ' + next((value for key, value in observationArray if key == 'relativeHumidity'), None) + '%'
    windString = 'Wind: ' + next((value for key, value in observationArray if key == 'windDirection'), None) + ' ' + next((value for key, value in observationArray if key == 'windSpeed'), None) + '-' + next((value for key, value in observationArray if key == 'windGustSpeed'), None) + 'kph'
    # The XML data to send
    xml_data_raw = """<?xml version="1.0" encoding="UTF-8"?>
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
          <Y type="uint32">400</Y>
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
            <Y type="uint32">800</Y>
            <showLevel type="uint32">0</showLevel>
            <flickerSwitch type="boolean">false</flickerSwitch>
            <osdOverlayType type="osdOverlayType">TEXT</osdOverlayType>
            <value type="string" maxLen="32"><![CDATA[""" + tempAndHumString + """]]></value>
          </item>
          <item>
            <switch type="boolean">true</switch>
            <X type="uint32">300</X>
            <Y type="uint32">1370</Y>
            <showLevel type="uint32">0</showLevel>
            <flickerSwitch type="boolean">false</flickerSwitch>
            <osdOverlayType type="osdOverlayType">TEXT</osdOverlayType>
            <value type="string" maxLen="32"><![CDATA[""" + windString  + """]]></value>
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
    xml_data = xml_data_raw.encode('utf-8')
    # Set the headers to indicate XML content
    headers = {
        "Content-Type": "application/xml",
    }

    # Send the POST request (disable SSL verification for insecure endpoint)
    response = requests.post(cameraUrl, data=xml_data, headers=headers, auth=HTTPBasicAuth(cameraUsername, cameraPassword), verify=False)

    # Check if the request was successful
    if response.status_code != 200:
        print(f"Request failed with status code {response.status_code}")

# Get the latest observations from the Metservice mobile API and put it into an array variable
observationArray = get_weather_data(apiUrl, apiKey, lat, lon)
# Update the camera OSD with the latest weather dara
updateOSD(cameraUrl,cameraUsername,cameraPassword,observationArray)
