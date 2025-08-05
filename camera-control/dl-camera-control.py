#!/usr/bin/env python3
from astral import LocationInfo
from astral.sun import sun
from datetime import date, datetime
import requests
from requests.auth import HTTPBasicAuth
from apscheduler.schedulers.background import BackgroundScheduler
import time
import pytz

# Camera credentials
cameraUsername = 'admin'
cameraPassword = 'dumbpassword'

# Set the camera shutter preferences here
shutter_setting = {
    "dawn": "1/25",
    "sunrise": "1/50",
    "sunset": "1/25",
    "dusk": "1/15"
}

### Do not edit past here ###

# Generate payload with upLimit
def shutter_payload(upLimit):
    return f"""<?xml version="1.0" encoding="utf-8"?>
<config>
  <image>
    <shutter>
      <mode>0</mode>
      <value>3</value>
      <upLimit>{upLimit}</upLimit>
    </shutter>
  </image>
  <cfgFile>normal</cfgFile>
</config>
"""

def do_api_call(event):
    now = datetime.now(tz).isoformat()
    event_setting = shutter_setting[event]
    shutter_code = shutter_speeds[event_setting]
    print(f"[{now}] Setting camera shutter to {event_setting} ({shutter_code}) for {event}...")
    payload = shutter_payload(shutter_code)

    try:
        response = requests.post(
            "http://192.168.53.4/SetImageConfig/1",
            headers=headers,
            data=payload.encode("utf-8"),
            auth=HTTPBasicAuth(cameraUsername, cameraPassword),
            verify=False
        )
        print(f"[{now}] Response: {response.status_code} {response.text}")
    except Exception as e:
        print(f"[{now}] ERROR during {event}: {e}")

def schedule_today_twilight():
    # Set today's date
    today = date.today()

    # Grab location information
    s = sun(dunedin.observer, date=today, tzinfo=tz)

    # Set dawn, sunrise, sunset, dusk times
    dawn = s["dawn"]
    sunrise = s["sunrise"]
    sunset = s["sunset"]
    dusk = s["dusk"]

    print(f"[{datetime.now(tz).isoformat()}] Scheduling dawn at {dawn}")
    scheduler.add_job(do_api_call, trigger='date', run_date=dawn, args=["dawn"])

    print(f"[{datetime.now(tz).isoformat()}] Scheduling sunrise at {sunrise}")
    scheduler.add_job(do_api_call, trigger='date', run_date=sunrise, args=["sunrise"])

    print(f"[{datetime.now(tz).isoformat()}] Scheduling sunset at {sunset}")
    scheduler.add_job(do_api_call, trigger='date', run_date=sunset, args=["sunset"])

    print(f"[{datetime.now(tz).isoformat()}] Scheduling dusk at {dusk}")
    scheduler.add_job(do_api_call, trigger='date', run_date=dusk, args=["dusk"])

# Set location to Dunedin, NZ
dunedin = LocationInfo("Dunedin", "New Zealand", "Pacific/Auckland", -45.8742, 170.5036)
tz = pytz.timezone(dunedin.timezone)

# Dict of shutter speeds supported by the camera
shutter_speeds = {
    "1/3": 0,
    "1/6": 1,
    "1/12": 2,
    "1/15": 3,
    "1/25": 4,
    "1/50": 5,
    "1/75": 6,
    "1/100": 7,
    "1/150": 8,
    "1/200": 9,
    "1/250": 10,
    "1/300": 11,
    "1/500": 12,
    "1/750": 13,
    "1/1000": 14,
    "1/2000": 15,
    "1/4000": 16,
    "1/10000": 17,
    "1/100000": 18
}

# Minimal headers
headers = {
    'Accept': '*/*',
    'Accept-Language': 'en-NZ,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
    'Cache-Control': 'no-cache',
    'Content-Type': 'application/xml',
    'Pragma': 'no-cache',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
}

# Scheduler setup
scheduler = BackgroundScheduler(timezone=tz)
scheduler.start()

schedule_today_twilight()
scheduler.add_job(schedule_today_twilight, trigger='cron', hour=0, minute=1)

# Keep alive
try:
    while True:
        time.sleep(60)
except (KeyboardInterrupt, SystemExit):
    scheduler.shutdown()
