# -*- coding: utf-8 -*-
import os, re
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
                if last_time > now_utc:
                    base_time = last_time + timedelta(hours=1)
        except Exception:
            pass

    try:
        os.makedirs(os.path.dirname(SCHEDULE_TRACKER_FILE), exist_ok=True)
        with open(SCHEDULE_TRACKER_FILE, "w", encoding="utf-8") as sf:
            sf.write(base_time.isoformat())
    except Exception:
        pass

    return base_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')

def clean_youtube_tags(tags, max_total_chars=400):
    """ইউটিউবের জন্য ট্যাগ সম্পূর্ণ নিরাপদ ও ৪০০ ক্যারেক্টারের ভেতরে রাখে"""
    if not tags:
        return ['Job Circular BD', 'Govt Job Circular 2026']
    
    clean_tags = []
    current_length = 0
    
    for tag in tags:
        if not tag or not isinstance(tag, str):
            continue
        # ইমোজি ও ক্ষতিকর ক্যারেক্টার ফিল্টার
        cleaned = re.sub(r'[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\<\>\"\,\n\r]', '', tag)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        if not cleaned or len(cleaned) < 2:
            continue
            
        cleaned = cleaned[:50].strip()
        
        if cleaned not in clean_tags:
            tag_len = len(cleaned) + (1 if clean_tags else 0)
            if current_length + tag_len <= max_total_chars:
                clean_tags.append(cleaned)
                current_length += tag_len
            else:
                break
                
    return clean_tags if clean_tags else ['Job Circular BD', 'Govt Job 2026']

def upload_to_youtube(yt, video_file, title, thumbnail_path, description, tags, schedule_upload=True):
    # টাইটেল নিরাপদ করা (< ও > রিমুভ এবং ১০০ অক্ষরের মধ্যে সীমাবদ্ধ)
    safe_title = re.sub(r'[\<\>]', '', str(title)).strip()[:100]
    print(f"Now Uploading: '{safe_title}'")
    
    safe_tags = clean_youtube_tags(tags)
    
    try:
        status_dict = {'privacyStatus': 'private', 'publishAt': get_next_schedule_time_iso()} if schedule_upload else {'privacyStatus': 'public'}

        body = {
            'snippet': {
                'title': safe_title,
                'description': description if description else safe_title,
                'tags': safe_tags
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
            except Exception as e:
                print(f"⚠️ Custom Thumbnail Add Failed: {e}")
        return True

    except Exception as e:
        err_str = str(e)
        # যদি কোনো কারণে ট্যাগ জনিত 400 এরর আসে, ট্যাগ ছাড়াই সাথে সাথে ব্যাকআপ আপলোড করবে
        if "invalidTags" in err_str or "invalid video keywords" in err_str:
            print("⚠️ Tags caused error. Retrying upload without tags...")
            try:
                body['snippet']['tags'] = []
                media_vid = MediaFileUpload(video_file, chunksize=1024*1024, resumable=True)
                res = yt.videos().insert(part="snippet,status", body=body, media_body=media_vid).execute()
                video_id = res['id']
                print(f"» Successfully Uploaded (Without Tags)! Video Link: https://youtu.be/{video_id}")
                
                if thumbnail_path and os.path.exists(thumbnail_path):
                    try:
                        media_thmb = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
                        yt.thumbnails().set(videoId=video_id, media_body=media_thmb).execute()
                        print("» Attached Custom Thumbnail!")
                    except Exception:
                        pass
                return True
            except Exception as retry_err:
                print("\n❌ Retry Upload failed! Error:", retry_err)
                return False

        print("\n❌ Upload failed! Error:", e)
        return False
