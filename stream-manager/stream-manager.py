import os
import time
import datetime
import pytz
import requests
import json
import google_auth_oauthlib.flow
import googleapiclient.discovery
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import random

# OAuth scope for YouTube Data API
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

# Youtube Stream Key
STREAM_KEY = ""

# Path where auth tokens and client secrets json files are stored
AUTH_TOKEN_PATH = "/home/jdalley/dunedin-live/oauth-files"

# Your timezone
TIMEZONE = "Pacific/Auckland"

# Restreamer IP and Port
RESTREAMER_IP = "192.168.52.12"
RESTREAMER_PORT = "8380"
RESTREAMER_USER = ""
RESTREAMER_PASSWORD = ""
RESTREAMER_YOUTUBE_API_COMMAND_PATH = "/api/v3/process/restreamer-ui%3Aegress%3Ayoutube%3A00089a01-1463-46ca-b7e1-cd577a1fb0e4/command"

# Retry settings
MAX_RETRIES = 10
INITIAL_DELAY = 10
BACKOFF_FACTOR = 2

# Set the stream title and description
STREAM_TITLE = 'Dunedin, NZ - Live Webcam (4K)'
STREAM_DESCRIPTION = 'This 4K stream runs on Quic Broadband - For FREE signup visit https://account.quic.nz/refer/282731 and use the code R282731EPGJMG on checkout. This stream is rolled over every 12 hours, at 3:00am and 3:00pm NZ time. Please subscribe to find the latest live stream easily! Stream shot on a Provision ISR DI-380IPEN-MVF-V3 Camera provided by SWL: https://www.swl.co.nz/. Higher quality direct stream available here: https://dunedin-live.dalleyfamily.net/'

def get_restreaner_access_token():
    url = f'http://{RESTREAMER_IP}:{RESTREAMER_PORT}/api/login'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }
    data = {
        'username': RESTREAMER_USER,
        'password': RESTREAMER_PASSWORD
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        access_token = response.json()['access_token']
        return access_token
    else:
        print(f"Failed to get access token. Status code: {response.status_code}")

def toggle_restreamer_youtube_stream(access_token,command):
    url = f'http://{RESTREAMER_IP}:{RESTREAMER_PORT}{RESTREAMER_YOUTUBE_API_COMMAND_PATH}'
    headers = {
        'Authorization': f"Bearer {access_token}",
        'Content-Type': 'application/json'
    }
    data = {
        'command': command
    }

    response = requests.put(url, headers=headers, json=data)
    if response.status_code == 200:
        print(f"Successfully executed '{command}' against youtube stream: {response.status_code}")
    else:
        print(f"Failed to toggle the youtube stream: {response.status_code}")

# Retry decorator with exponential backoff
def retry_with_exponential_backoff(max_retries=MAX_RETRIES, initial_delay=INITIAL_DELAY, backoff_factor=BACKOFF_FACTOR):
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    else:
                        time.sleep(delay)
                        delay *= backoff_factor
                        # Optionally add jitter to the delay to prevent Thundering Herd problem
                        delay += random.uniform(0, 1)
                        print(f"Retrying in {delay:.2f} seconds after failure: {e}")
        return wrapper
    return decorator

@retry_with_exponential_backoff()
def get_authenticated_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists(f'{AUTH_TOKEN_PATH}/token.json'):
        creds = Credentials.from_authorized_user_file(f'{AUTH_TOKEN_PATH}/token.json')
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                f'{AUTH_TOKEN_PATH}/client_secrets.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(f'{AUTH_TOKEN_PATH}/token.json', 'w') as token:
            token.write(creds.to_json())

    # Build the YouTube API client
    youtube = googleapiclient.discovery.build('youtube', 'v3', credentials=creds)
    return youtube

@retry_with_exponential_backoff()
def find_stream_id_by_key(youtube, stream_key):
    request = youtube.liveStreams().list(
        part="id,snippet,cdn",
        mine=True
    )
    response = request.execute()
    for stream in response.get('items', []):
        cdn_info = stream.get('cdn', {})
        if cdn_info.get('ingestionInfo', {}).get('streamName') == stream_key:
            return stream['id']
    raise ValueError("Stream key not found or 'cdn' information is missing")

@retry_with_exponential_backoff()
def find_broadcast_id_by_stream_id(youtube, stream_id):
    request = youtube.liveBroadcasts().list(
        part="id,contentDetails",
        broadcastStatus="active",
        broadcastType="all"
    )
    response = request.execute()
    for broadcast in response['items']:
        if broadcast['contentDetails']['boundStreamId'] == stream_id:
            return broadcast['id']
    return None

@retry_with_exponential_backoff()
def is_broadcast_streaming(youtube, broadcast_id):
    request = youtube.liveBroadcasts().list(
        part="id,status",
        id=broadcast_id
    )
    response = request.execute()
    return response['items'][0]['status']['lifeCycleStatus']

@retry_with_exponential_backoff()
def stop_broadcast_by_id(youtube, broadcast_id):
    request = youtube.liveBroadcasts().transition(
        broadcastStatus="complete",
        id=broadcast_id,
        part="id,status"
    )
    response = request.execute()

@retry_with_exponential_backoff()
def start_new_broadcast(youtube):
    current_time = datetime.datetime.now(pytz.timezone(TIMEZONE))
    scheduled_end_time = current_time + datetime.timedelta(hours=11, minutes=59)
    new_stream_title = f'{STREAM_TITLE}: {current_time.strftime("%d-%m-%Y %H:%M")} to {scheduled_end_time.strftime("%H:%M")}'

    liveBroadcastStart = youtube.liveBroadcasts().insert(
        part="snippet,status,contentDetails",
        body={
          "snippet": {
            "title": new_stream_title,
            "description": STREAM_DESCRIPTION,
            "scheduledStartTime": current_time.isoformat(),  # Start immediately
            "scheduledEndTime": scheduled_end_time.isoformat() # End the broadcast at 11 hours 59 minutes from start time
          },
          "contentDetails": {
            "enableAutoStart": "true",
            "enableAutoStop": "false",
            "enableDvr": "true",
            "latencyPreference": "normal",
            "recordFromStart": "true"
          },
          "status": {
            "privacyStatus": "public"
          }
        }
    )
    liveBroadcastStartResponse = liveBroadcastStart.execute()
    return liveBroadcastStartResponse['id']

@retry_with_exponential_backoff()
def bind_stream_to_broadcast(youtube, stream_id, broadcast_id):
    liveBroadcastBind = youtube.liveBroadcasts().bind(
        part="id,contentDetails",
        id=broadcast_id,
        streamId=stream_id
    )
    liveBroadcastBind = liveBroadcastBind.execute()

@retry_with_exponential_backoff()
def unbind_stream_from_broadcast(youtube, broadcast_id):
    liveBroadcastBind = youtube.liveBroadcasts().bind(
        part="id,contentDetails",
        id=broadcast_id,
    )
    liveBroadcastBind = liveBroadcastBind.execute()

def main():
    restreamer_access_token = get_restreaner_access_token()
    restreamer_toggle = toggle_restreamer_youtube_stream(restreamer_access_token,"stop")
    # Initialize the YouTube Data API service
    print(f"Authenticating to the Youtube API")
    youtube = get_authenticated_service()
    print(f"Finding stream ID by stream key: {STREAM_KEY}")
    stream_id = find_stream_id_by_key(youtube, STREAM_KEY)
    print(f"Found stream ID: {stream_id}")
    print(f"Finding any active broadcasts by the stream ID...")
    current_broadcast_id = find_broadcast_id_by_stream_id(youtube, stream_id)
    if current_broadcast_id:
        print(f"Broadcast currently in progress, with id: {current_broadcast_id}")
        print(f"Check if broadcast is live...")
        broadcast_active = is_broadcast_streaming(youtube, current_broadcast_id)
        if broadcast_active == "live":
            print(f"Broadcast is live, killing...")
            stop_broadcast_by_id(youtube, current_broadcast_id)
            print(f"Unbinding current stream from broadcast")
            unbind_stream_from_broadcast(youtube, current_broadcast_id)
        else:
            print(f"Unbinding current stream from broadcast")
            unbind_stream_from_broadcast(youtube, current_broadcast_id)
    else:
        print(f"Existing broadcast not found.")
    print(f"Creating new broadcast...")
    broadcast_id = start_new_broadcast(youtube)
    print(f"Broadcast started with ID: {broadcast_id}")
    print(f"Binding stream ID to broadcast ID")
    bind_stream_to_broadcast(youtube, stream_id, broadcast_id)
    print(f"Stream bound, starting restreamer youtube process...")
    restreamer_toggle = toggle_restreamer_youtube_stream(restreamer_access_token,"start")

if __name__ == "__main__":
    main()
