# -*- coding: utf-8 -*-
import os
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCHEDULE_TRACKER_FILE = os.path.join("workspace", "schedule_tracker.txt")

def get_youtube_service():
    creds = Credentials(
        None,
        refresh_token=os.environ['REFRESH_TOKEN'],
        client_id=os.environ['CLIENT_ID'],
        client_secret=os.environ['CLIENT_SECRET'],
        token_uri="https://oauth2.googleapis.com/token"
    )
    return build('youtube', 'v3', credentials=creds)

def get_next_schedule_time_iso():
    now_utc = datetime.now(timezone.utc)
    base_time = now_utc + timedelta(hours=1)

    if os.path.exists(SCHEDULE_TRACKER_FILE):
        try:
            with open(SCHEDULE_TRACKER_FILE, "r", encoding="utf-8") as sf:
                last_time = datetime.fromisoformat(sf.read().strip())
                if last_time > now_utc: base_time = last_time + timedelta(hours=1)
        except Exception: pass

    try:
        with open(SCHEDULE_TRACKER_FILE, "w", encoding="utf-8") as sf:
            sf.write(base_time.isoformat())
    except Exception: pass

    return base_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')

def upload_to_youtube(yt, video_file, title, thumbnail_path, description, tags, schedule_upload=True):
    print(f"Now Uploading: '{title}'")
    try:
        status_dict = {'privacyStatus': 'private', 'publishAt': get_next_schedule_time_iso()} if schedule_upload else {'privacyStatus': 'public'}

        body = {
            'snippet': {
                'title': title[:100],
                'description': description if description else title,
                'tags': tags if tags else ['Job Circular BD', 'Govt Job Circular 2026']
            },
            'status': status_dict 
        }
        media_vid = MediaFileUpload(video_file, chunksize=1024*1024, resumable=True)
        res = yt.videos().insert(part="snippet,status", body=body, media_body=media_vid).execute()
        video_id = res['id']
        print(f"» Successfully Uploaded & Scheduled! Video Link: https://youtu.be/{video_id}")
        
        if thumbnail_path and os.path.exists(thumbnail_path):
            try: 
                media_thmb = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
                yt.thumbnails().set(videoId=video_id, media_body=media_thmb).execute()
                print("» Attached Custom Thumbnail!")
            except Exception as e: print(f"⚠️ Custom Thumbnail Add Failed: {e}")
        return True
    except Exception as e:
        print("\n❌ Upload failed! Error:", e)
        return False
