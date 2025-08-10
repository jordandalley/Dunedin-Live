import os
import pytz
import shutil
import subprocess
import google_auth_oauthlib.flow
import googleapiclient.discovery
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload


# Local Timezone
TIMEZONE = os.environ.get("TZ", "UTC")

# Path where auth tokens and client secrets json files are stored
AUTH_TOKEN_PATH = os.environ.get("AUTH_TOKEN_PATH", "/data/oauth")

# Image path to image-capturer directory
TIMELAPSE_IMAGE_PATH = os.environ.get("TIMELAPSE_IMAGE_PATH", "/data/images")

# Video output / upload path
VIDEO_OUTPUT_PATH = os.environ.get("VIDEO_OUTPUT_PATH", "/data/video")

# Youtube Video Title
YOUTUBE_TITLE = os.environ.get("YOUTUBE_TITLE", "Dunedin, NZ: Timelapse")

# Youtube Video Description
YOUTUBE_DESCRIPTION = os.environ.get("YOUTUBE_DESCRIPTION", "")

# Youtube video tags (comma-separated -> list)
YOUTUBE_VIDEO_TAGS = os.environ.get("YOUTUBE_VIDEO_TAGS", "").split(",")

# Youtube Category ID
YOUTUBE_CATEGORY_ID = os.environ.get("YOUTUBE_CATEGORY_ID", "19")

# Youtube Privacy Status
YOUTUBE_PRIVACY = os.environ.get("YOUTUBE_PRIVACY", "public")

# Cleanup Images (string to bool)
CLEANUP_IMAGES = os.environ.get("CLEANUP_IMAGES", "true").lower() in ("true", "1", "yes")

# Define the scopes
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_yesterdays_date(tz):
    now = datetime.now(pytz.timezone(tz))
    yesterday = now - timedelta(days=1)
    yesterday_str = yesterday.strftime('%d-%m-%Y')
    return yesterday_str

def create_timelapse_video(inputdir,outputdir):
    # Create the output directory if it doesn't exist
    os.makedirs(outputdir, exist_ok=True)
    # Create video file full path
    outputfile = outputdir + "/tmp.mp4"
    # Clean up old timelapse video if it exists
    if os.path.isfile(outputfile):
        try:
            os.remove(outputfile)
            print(f"Cleaning up old video {outputfile}...")
        except Exception as e:
            print(f"An error occurred while deleting the file: {e}")
    else:
        print(f"Old video file {outputfile} does not exist, moving on...")
    # Define ffmpeg params (software encoding)
    ffmpeg = [
        'ffmpeg',
        '-framerate', '30',
        '-pattern_type', 'glob',
        '-i', inputdir + '/' + '*.jpg',
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-r', '30',
        outputfile
    ]
    # ffmpeg params for qsv hwaccel
    #ffmpeg = [
    #    'ffmpeg',
    #    '-hwaccel', 'qsv',
    #    '-hwaccel_output_format', 'qsv',
    #    '-framerate', '30',
    #    '-pattern_type', 'glob',
    #    '-i', inputdir + '/' + '*.jpg',
    #    '-c:v', 'h264_qsv',
    #    '-pix_fmt', 'nv12', # used by older ffmpeg
    #    '-r', '30',
    #    '-qp', '18',
    #     '-b:v', '20M',
    #    outputfile
    #]
    # Run ffmpeg
    print("Running ffmpeg, this may take a while...")
    try:
        result = subprocess.run(ffmpeg, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("FFmpeg process completed successfully")
        print(result.stdout.decode('utf-8'))
    except subprocess.CalledProcessError as e:
        print("An error occurred while running FFmpeg")
        print(e.stderr.decode('utf-8'))

def cleanup_images(choice,imgdir):
    if choice:
        print(f"Deleting {imgdir}...")
        try:
            shutil.rmtree(imgdir)
            print(f"Directory {imgdir} and all its contents have been deleted successfully.")
        except Exception as e:
            print(f"An error occurred while deleting the directory: {e}")
    else:
        print("Skipping cleanup...")

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

    # Build the YouTube Data API service
    youtube = googleapiclient.discovery.build('youtube', 'v3', credentials=creds)
    return youtube

def upload_video(youtube, video_file, title, yesterdaystr, description, tags, category_id, privacy_status):
    print("Uploading video to Youtube...")
    body = {
        "snippet": {
            "title": f"{yesterdaystr} - {title}",
            "description": description,
            "tags": tags,
            "categoryId": category_id
        },
        "status": {
            "privacyStatus": privacy_status
        }
    }

    media_body = MediaFileUpload(video_file, chunksize=-1, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media_body
    )

    response = request.execute()
    print(f"Video uploaded. Video ID: {response['id']}")

if __name__ == "__main__":
    # Create a variable with yesterday's date string in it
    YESTERDAY_STRING = get_yesterdays_date(TIMEZONE)
    # Creare the full path to process using the image path and yesterdays date
    IMGDIR = TIMELAPSE_IMAGE_PATH + "/" + YESTERDAY_STRING
    # Check if the directory exists
    if os.path.isdir(IMGDIR):
        print(f"The directory {IMGDIR} exists, beginning processing...")
        # Create timelapse video
        create_timelapse_video(IMGDIR, VIDEO_OUTPUT_PATH)
        # Clean up images
        cleanup_images(CLEANUP_IMAGES, IMGDIR)
        # Authenticate to Youtube
        youtube = get_authenticated_service()
        # Upload video to Youtube
        upload_video(youtube, VIDEO_OUTPUT_PATH + "/tmp.mp4", YOUTUBE_TITLE, YESTERDAY_STRING, YOUTUBE_DESCRIPTION, YOUTUBE_VIDEO_TAGS, YOUTUBE_CATEGORY_ID, YOUTUBE_PRIVACY)
    else:
        print(f"The directory {IMGDIR} does not exist, nothing to do.")
