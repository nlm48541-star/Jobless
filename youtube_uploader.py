# -*- coding: utf-8 -*-
import os, json
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

def get_video_description(video_title, config_data=None):
    """🌟 শুধুমাত্র আপনার description.txt বা config.json থেকে আপনার নিজস্ব ডেসক্রিপশন নেয়"""
    for desc_filename in ["description.txt", "default_description.txt"]:
        if os.path.exists(desc_filename):
            try:
                with open(desc_filename, "r", encoding="utf-8") as df:
                    custom_text = df.read().strip()
                    if custom_text: return custom_text.replace("{title}", video_title)
            except Exception: pass
                
    if config_data and isinstance(config_data, dict):
        desc = config_data.get("default_description", "").strip()
        if desc: return desc.replace("{title}", video_title)

    return video_title

def get_video_tags(config_data=None):
    """🌟 শুধুমাত্র আপনার tags.txt বা config.json থেকে আপনার নিজস্ব ট্যাগ নেয়"""
    if os.path.exists("tags.txt"):
        try:
            with open("tags.txt", "r", encoding="utf-8") as tf:
                content = tf.read().strip()
                if content: return [t.strip() for t in content.split(",") if t.strip()]
        except Exception: pass
            
    if config_data and isinstance(config_data, dict):
        tags = config_data.get("default_tags", [])
        if isinstance(tags, list) and len(tags) > 0: return tags

    return ['Job Circular BD', 'Today Govt Jobs', 'Govt Job Circular 2026', 'নিয়োগ বিজ্ঞপ্তি ২০২৬']

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

def upload_to_youtube(yt, video_file, title, thumbnail_path, config_data=None, schedule_upload=True):
    print(f"Now Uploading: '{title}'")
    try:
        final_description = get_video_description(title, config_data)
        final_tags = get_video_tags(config_data)
        
        status_dict = {'privacyStatus': 'private', 'publishAt': get_next_schedule_time_iso()} if schedule_upload else {'privacyStatus': 'public'}

        body = {
            'snippet': {'title': title[:100], 'description': final_description, 'tags': final_tags},
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
