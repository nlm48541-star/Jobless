import os, json, time, re, shutil
import requests, feedparser
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from PIL import Image
import numpy as np

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from moviepy.editor import AudioFileClip, VideoClip, concatenate_videoclips, VideoFileClip

WORKSPACE_DIR = "workspace" # Rclone Sync Location
TMP_DIR = "temp_assets"     # Temp Files processing

def get_youtube_service():
    creds = Credentials(
        None,
        refresh_token=os.environ['REFRESH_TOKEN'],
        client_id=os.environ['CLIENT_ID'],
        client_secret=os.environ['CLIENT_SECRET'],
        token_uri="https://oauth2.googleapis.com/token"
    )
    return build('youtube', 'v3', credentials=creds)

def clean_filename(text):
    return re.sub(r'[\\/*?:"<>|]', "", text)

def download_image(url, output_path):
    try:
        req = requests.get(url, stream=True, timeout=10)
        if req.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(req.content)
            return True
    except: pass
    return False

# ==================== [ 1. FEED PARSING (Anti-Redownload Loop) ] ====================
def check_new_articles_and_prepare_folders():
    print("Checking for new RSS items (Last 24 Hours)...")
    if not os.path.exists(WORKSPACE_DIR): os.makedirs(WORKSPACE_DIR)

    with open('config.json', 'r', encoding='utf-8') as f:
        rss_links = json.load(f)['rss_links']

    time_limit = datetime.now() - timedelta(hours=24)
    existing_folders = [f for f in os.listdir(WORKSPACE_DIR) if os.path.isdir(os.path.join(WORKSPACE_DIR, f))]
    
    # Tracking completed articles to avoid infinite downloads
    history_file = os.path.join(WORKSPACE_DIR, "history.txt")
    history_logs = []
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            history_logs = f.read().splitlines()

    for feed_url in rss_links:
        print(f"Parsing Feed: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
        except: continue
        
        for entry in feed.entries:
            try: published_time = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            except: continue

            if published_time >= time_limit:
                folder_title = clean_filename(entry.title).strip()
                # Check history logs and current folder existence to prevent loop redownloading
                if not folder_title or folder_title in existing_folders or folder_title in history_logs: 
                    continue 

                # নতুন ফোল্ডার তৈরি 
                print(f"New Article Found: {folder_title}. Generating...")
                folder_path = os.path.join(WORKSPACE_DIR, folder_title)
                os.makedirs(folder_path)
                existing_folders.append(folder_title)
                
                # history তে লগ এড করা 
                history_logs.append(folder_title)
                with open(history_file, 'a', encoding='utf-8') as hf:
                    hf.write(f"{folder_title}\n")

                with open(os.path.join(folder_path, "title.txt"), "w", encoding="utf-8") as text_file:
                    text_file.write(entry.title)

                content = entry.content[0].value if hasattr(entry, 'content') else getattr(entry, 'summary', "")
                images = BeautifulSoup(content, 'html.parser').find_all('img')
                
                img_count = 1
                for img in images:
                    src = img.get('src')
                    if src and src.startswith("http"):
                        img_path = os.path.join(folder_path, f"{img_count}.jpg")
                        if download_image(src, img_path):
                            img_count += 1

# ==================== [ 2. FRAME ENGINE ] ====================
def make_video_frame(img_path, duration):
    TARGET_W, TARGET_H = 1920, 1080
    pil_img = Image.open(img_path).convert("RGB")
    w, h = pil_img.size
    ratio = w / h

    if ratio >= 1.777: 
        new_h, new_w = TARGET_H, int((TARGET_H / h) * w)
    else:
        new_w, new_h = TARGET_W, int((TARGET_W / w) * h)
    if new_h < TARGET_H:
        new_h, new_w = TARGET_H, int((TARGET_H / h) * w)

    resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
    img_np = np.array(resized)
    
    def make_frame(t):
        progress = t / duration if duration > 0 else 0
        y = int(progress * (new_h - TARGET_H)) if (new_h - TARGET_H) > 0 else 0 
        x = int(progress * (new_w - TARGET_W)) if (new_w - TARGET_W) > 0 else 0 
        return img_np[y:y+TARGET_H, x:x+TARGET_W]
        
    return VideoClip(make_frame, duration=duration)

# ==================== [ 3. MOVIEPY PROCESS ] ====================
def process_ready_videos(yt):
    print("\nScanning Drive folders for Audios...")
    if not os.path.exists(WORKSPACE_DIR): return
    if not os.path.exists(TMP_DIR): os.makedirs(TMP_DIR)
    
    folders = [f for f in os.listdir(WORKSPACE_DIR) if os.path.isdir(os.path.join(WORKSPACE_DIR, f))]
    
    for folder_name in folders:
        folder_path = os.path.join(WORKSPACE_DIR, folder_name)
        
        # ফোল্ডার প্রসেস লজিক (যা ট্রাই-ক্যাচ দিয়ে সম্পূর্ণ সুরক্ষিত)
        try:
            audio_file, txt_path = None, None
            img_files = []
            for file in sorted(os.listdir(folder_path)):
                ext = file.lower().split('.')[-1]
                if ext in ['mp3', 'wav', 'm4a', 'aac']: audio_file = file
                elif ext in ['txt']: txt_path = os.path.join(folder_path, file)
                elif ext in ['jpg', 'jpeg', 'png']: img_files.append(os.path.join(folder_path, file))
                    
            if not audio_file: 
                continue
                
            print(f"========== Process started: {folder_name} ==========")
            audio_path = os.path.join(folder_path, audio_file)
            
            video_title = folder_name
            if txt_path and os.path.exists(txt_path):
                with open(txt_path, 'r', encoding='utf-8') as tf:
                    video_title = tf.read().strip()

            if not img_files:
                print("No images found inside folder, skipping...")
                continue
                
            # মেমোরি ক্লিনআপ: আগের লুপের তৈরি করা ফাইল রিমুভ করা
            thumbnail_path = os.path.join(TMP_DIR, "thumbnail.jpg")
            if os.path.exists(thumbnail_path): os.remove(thumbnail_path)
            
            out_video_file = os.path.join(TMP_DIR, "final_out.mp4")
            if os.path.exists(out_video_file): os.remove(out_video_file)

            # ক্রপিং এবং থাম্বনেইল ডিসিশন 
            wide_img, video_imgs = None, []
            for lp in img_files:
                try:
                    img = Image.open(lp)
                    if (img.width / img.height) >= 1.769:
                        wide_img = lp
                        break
                except: pass
                    
            if wide_img:
                img = Image.open(wide_img).convert("RGB")
                scale = max(720/img.size[1], 1280/img.size[0])
                rs_img = img.resize((int(img.size[0]*scale), int(img.size[1]*scale)), Image.LANCZOS)
                left = (rs_img.width - 1280) // 2
                rs_img.crop((left, 0, left+1280, 720)).save(thumbnail_path, "JPEG", quality=95)
                video_imgs = [ip for ip in img_files if ip != wide_img]
                if not video_imgs: video_imgs.append(wide_img)
            else:
                img = Image.open(img_files[0]).convert("RGB")
                scale = max(720/img.size[1], 1280/img.size[0])
                rs_img = img.resize((int(img.size[0]*scale), int(img.size[1]*scale)), Image.LANCZOS)
                rs_img.crop((0, 0, 1280, 720)).save(thumbnail_path, "JPEG", quality=95)
                video_imgs = img_files

            # মুভি এডিটিং শুরু
            audio_clip = AudioFileClip(audio_path)
            clips = [make_video_frame(v, audio_clip.duration / len(video_imgs)) for v in video_imgs]
            
            final_video = concatenate_videoclips(clips).set_audio(audio_clip)
            
            # --- Outro.mp4 ভিডিওর শেষে যুক্ত করার ম্যাজিক (গুগল ড্রাইভ সোর্স থেকে) ---
            outro = None
            outro_path = os.path.join(WORKSPACE_DIR, "Outro.mp4")
            if os.path.exists(outro_path):
                print("Outro.mp4 found in Drive, attaching at the end...")
                try:
                    outro = VideoFileClip(outro_path)
                    if outro.size != (1920, 1080): outro = outro.resize((1920, 1080))
                    final_video = concatenate_videoclips([final_video, outro], method="compose")
                except Exception as ex:
                    print(f"Error appending outro: {ex}")
                
            print("Rendering started, Please wait...")
            final_video.write_videofile(
                out_video_file, fps=24, codec="libx264", 
                audio_codec="aac", threads=4, preset="ultrafast", logger=None
            )
            
            # ভিডিও ও অডিও ফাইল ক্লোজ করা 
            final_video.close()
            audio_clip.close()
            if outro: outro.close()
            
            # YouTube-এ আপলোডিং
            upload_success = upload_to_youtube(
                yt, out_video_file, video_title, 
                thumbnail_path if os.path.exists(thumbnail_path) else None
            )
            
            # আপলোড সফল হলে ফোল্ডার ডিলিট করা
            if upload_success: 
                print("Task Accomplished! Requesting Drive Cleanup.")
                shutil.rmtree(folder_path)

        except Exception as folder_error:
            print(f"\n❌ Error occurred while processing folder '{folder_name}': {folder_error}")
            print("Moving on to the next available folder...\n")

# ==================== [ 4. YOUTUBE API ] ====================
def upload_to_youtube(yt, video_file, title, thumbnail_path):
    print(f"Now Uploading: '{title}'")
    try:
        body = {
            'snippet': { 'title': title[:100], 'description': "Bot Generated Latest Govt Job Details & Update.\nAutomated video uploading bot running properly.", 'tags': ['Job Circular BD', 'Today Govt Jobs'] },
            'status': { 'privacyStatus': 'private' }
        }
        media_vid = MediaFileUpload(video_file, resumable=True)
        res = yt.videos().insert(part="snippet,status", body=body, media_body=media_vid).execute()
        video_id = res['id']
        print(f"» Successfully Uploaded as Private! Video Link: https://youtu.be/{video_id}")
        
        if thumbnail_path:
            try: 
                media_thmb = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
                yt.thumbnails().set(videoId=video_id, media_body=media_thmb).execute()
                print("» Attached perfect Custom Thumbnail!")
            except Exception as e: print("\n⚠️ Custom Thumbnail Add Failed! -> Note: Check if YouTube Account is Phone Verified!\n")
        return True
    except Exception as e:
        print("\n❌ Upload failed by error API limits! Detail:", e)
        return False


if __name__ == "__main__":
    print("\n====== [ Google Drive Bot Active | Process Start ] ======\n")
    try:
        yt_service = get_youtube_service()
        check_new_articles_and_prepare_folders()
        process_ready_videos(yt_service)
    except Exception as critical:
        print("\nFATAL ERROR DETECTED: ", critical)
    finally:
        # প্রসেস সম্পূর্ণ শেষে শুধু Temporary Folder ডিলিট করবে, Workspace ঠিক থাকবে 
        if os.path.exists(TMP_DIR): shutil.rmtree(TMP_DIR)
        print("\nAll Tasks Finalized Perfectly.\n======================================")