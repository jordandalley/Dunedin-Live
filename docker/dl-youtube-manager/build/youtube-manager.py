import os
import time
import datetime
import pytz
import subprocess
import google_auth_oauthlib.flow
import googleapiclient.discovery
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import random

# OAuth scope for YouTube Data API
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

# Youtube Stream Key
STREAM_KEY = os.getenv("STREAM_KEY")

# Path where auth tokens and client secrets json files are stored
AUTH_TOKEN_PATH = os.getenv("AUTH_TOKEN_PATH")

# Your timezone
TIMEZONE = os.getenv("TZ", "Pacific/Auckland")

# Camera RTSP URL
CAMERA_RTSP_URL = os.getenv("CAMERA_RTSP_URL")

# Retry settings
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "10"))
INITIAL_DELAY = int(os.getenv("INITIAL_DELAY", "10"))
BACKOFF_FACTOR = int(os.getenv("BACKOFF_FACTOR", "2"))

# Set the stream title and description
STREAM_TITLE = os.getenv("STREAM_TITLE")
STREAM_DESCRIPTION = os.getenv("STREAM_DESCRIPTION")

def get_next_rollover_time(timezone_str):
    """Calculates the exact datetime of the next 3:00 AM or 3:00 PM."""
    tz = pytz.timezone(timezone_str)
    now = datetime.datetime.now(tz)

    # Candidate times for today
    candidate_3am = now.replace(hour=3, minute=0, second=0, microsecond=0)
    candidate_3pm = now.replace(hour=15, minute=0, second=0, microsecond=0)

    if now < candidate_3am:
        return candidate_3am
    elif now < candidate_3pm:
        return candidate_3pm
    else:
        # If it's past 3 PM, the next rollover is 3 AM tomorrow
        return candidate_3am + datetime.timedelta(days=1)

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
                        delay += random.uniform(0, 1)
                        print(f"Retrying in {delay:.2f} seconds after failure: {e}")
        return wrapper
    return decorator

@retry_with_exponential_backoff()
def get_authenticated_service():
    creds = None
    if os.path.exists(f'{AUTH_TOKEN_PATH}/token.json'):
        creds = Credentials.from_authorized_user_file(f'{AUTH_TOKEN_PATH}/token.json')
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                f'{AUTH_TOKEN_PATH}/client_secrets.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open(f'{AUTH_TOKEN_PATH}/token.json', 'w') as token:
            token.write(creds.to_json())

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
    for broadcast in response.get('items', []):
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
    request.execute()

@retry_with_exponential_backoff()
def start_new_broadcast(youtube, next_rollover_time):
    current_time = datetime.datetime.now(pytz.timezone(TIMEZONE))
    new_stream_title = f'{STREAM_TITLE}: {current_time.strftime("%d-%m-%Y %H:%M")} to {next_rollover_time.strftime("%H:%M")}'

    liveBroadcastStart = youtube.liveBroadcasts().insert(
        part="snippet,status,contentDetails",
        body={
          "snippet": {
            "title": new_stream_title,
            "description": STREAM_DESCRIPTION,
            "scheduledStartTime": current_time.isoformat(),
            "scheduledEndTime": next_rollover_time.isoformat()
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
    liveBroadcastBind.execute()

@retry_with_exponential_backoff()
def unbind_stream_from_broadcast(youtube, broadcast_id):
    liveBroadcastBind = youtube.liveBroadcasts().bind(
        part="id,contentDetails",
        id=broadcast_id,
    )
    liveBroadcastBind.execute()

def run_ffmpeg_until(rtsp_url, stream_key, end_time, tz_str):
    """Runs ffmpeg, monitors it for premature crashes, and terminates it exactly at end_time."""
    youtube_rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    tz = pytz.timezone(tz_str)

    ffmpeg_cmd = [
        "ffmpeg",
        "-err_detect", "ignore_err",
        "-probesize", "5000000",
        "-analyzeduration", "5000000",
        "-timeout", "5000000",
        "-use_wallclock_as_timestamps", "1",
        "-thread_queue_size", "5120",
        "-rtsp_transport", "udp",
        "-i", rtsp_url,
        "-thread_queue_size", "5120",
        "-f", "lavfi",
        "-i", "anullsrc=cl=mono:r=44100",
        "-dn",
        "-sn",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "8k",
        "-ar", "44100",
        "-f", "flv",
        "-rtmp_enhanced_codecs", "hvc1,av01",
        youtube_rtmp_url
    ]

    print(f"Starting ffmpeg stream to {youtube_rtmp_url}...")
    process = subprocess.Popen(ffmpeg_cmd)

    try:
        while datetime.datetime.now(tz) < end_time:
            # Check if ffmpeg exited unexpectedly (e.g. camera network drop)
            if process.poll() is not None:
                print("FFmpeg exited prematurely! Restarting in 5 seconds...")
                time.sleep(5)
                process = subprocess.Popen(ffmpeg_cmd)
            time.sleep(1)

        print("Scheduled rollover time reached. Terminating ffmpeg...")
        process.terminate()
        try:
            # Wait gracefully for it to wrap up
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            print("FFmpeg didn't terminate gracefully. Forcing kill...")
            process.kill()

    except KeyboardInterrupt:
        print("Manual interrupt received. Terminating ffmpeg...")
        process.terminate()
        raise

def main():
    print("Starting Dunedin-Live YouTube Daemon...")

    print("Authenticating to the Youtube API")
    youtube = get_authenticated_service()

    while True:
        print(f"\n--- Starting New Stream Cycle ---")

        print("Finding stream ID by stream key...")
        stream_id = find_stream_id_by_key(youtube, STREAM_KEY)

        print("Checking for active broadcasts...")
        current_broadcast_id = find_broadcast_id_by_stream_id(youtube, stream_id)
        next_rollover = get_next_rollover_time(TIMEZONE)

        active_broadcast = None

        if current_broadcast_id:
            broadcast_status = is_broadcast_streaming(youtube, current_broadcast_id)
            if broadcast_status in ["live", "ready"]:
                print(f"Found existing broadcast ({current_broadcast_id}) in '{broadcast_status}' state.")
                print("Skipping teardown. Resuming ffmpeg into the existing stream...")
                active_broadcast = current_broadcast_id
            else:
                print(f"Existing broadcast ({current_broadcast_id}) is in '{broadcast_status}' state. Tearing it down...")
                try:
                    stop_broadcast_by_id(youtube, current_broadcast_id)
                    unbind_stream_from_broadcast(youtube, current_broadcast_id)
                except Exception as e:
                    print(f"Warning: Failed to cleanly tear down old broadcast: {e}")

        if not active_broadcast:
            print("Creating new broadcast...")
            active_broadcast = start_new_broadcast(youtube, next_rollover)
            print(f"Broadcast started with ID: {active_broadcast}")

            print("Binding stream ID to broadcast ID...")
            bind_stream_to_broadcast(youtube, stream_id, active_broadcast)

        print(f"Daemon will run ffmpeg until exact rollover at: {next_rollover.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        run_ffmpeg_until(CAMERA_RTSP_URL, STREAM_KEY, next_rollover, TIMEZONE)

        # This code only executes once the exact rollover time hits
        print("\n*** Scheduled rollover time reached! ***")
        print("Tearing down the broadcast to prepare for the next cycle...")
        try:
            stop_broadcast_by_id(youtube, active_broadcast)
            unbind_stream_from_broadcast(youtube, active_broadcast)
        except Exception as e:
            print(f"Warning: Failed to cleanly tear down broadcast during rollover: {e}")

if __name__ == "__main__":
    main()
