#!/usr/bin/env python3
from astral import LocationInfo
from astral.sun import sun
from datetime import date, datetime
import pytz
import requests
from requests.auth import HTTPBasicAuth
from apscheduler.schedulers.background import BackgroundScheduler
import time

# Location: Dunedin, NZ
dunedin = LocationInfo("Dunedin", "New Zealand", "Pacific/Auckland", -45.8742, 170.5036)
tz = pytz.timezone(dunedin.timezone)
cameraUsername = 'admin'
cameraPassword = 'dumbpassword'

# Headers (minimal but sufficient)
headers = {
    'Accept': '*/*',
    'Accept-Language': 'en-NZ,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
    'Cache-Control': 'no-cache',
    'Content-Type': 'application/xml',
    'Pragma': 'no-cache',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
}

# upLimit:
# 3 = 1/12, 4 = 1/25, 5 = 1/50
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
    payload = shutter_payload('5') if event == "civil_dawn" else shutter_payload('3')

    print(f"[{now}] Executing API call for {event}...")

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
    today = date.today()
    s = sun(dunedin.observer, date=today, tzinfo=tz)
    civil_dawn = s["dawn"]
    civil_dusk = s["dusk"]

    print(f"[{datetime.now(tz).isoformat()}] Scheduling civil_dawn at {civil_dawn}")
    print(f"[{datetime.now(tz).isoformat()}] Scheduling civil_dusk at {civil_dusk}")

    scheduler.add_job(do_api_call, trigger='date', run_date=civil_dawn, args=["civil_dawn"])
    scheduler.add_job(do_api_call, trigger='date', run_date=civil_dusk, args=["civil_dusk"])

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
