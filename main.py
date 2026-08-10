# -*- coding: utf-8 -*-
import os, json, time, re, shutil
import requests, feedparser
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from PIL import Image
import numpy as np

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from moviepy.editor import AudioFileClip, VideoClip, concatenate_videoclips, ImageClip, CompositeVideoClip

WORKSPACE_DIR = "workspace"      # Rclone Sync Location
LIVESTREAM_DIR = "workspace_live" # JobLive folder source
TMP_DIR = "temp_assets"          # Temp Files processing

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
        req = requests.get(url, timeout=10)
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

    if not os.path.exists('config.json'):
        print("config.json not found!")
        return

    with open('config.json', 'r', encoding='utf-8') as f:
        rss_links = json.load(f).get('rss_links', [])

    time_limit = datetime.now() - timedelta(hours=24)
    existing_folders = [f for f in os.listdir(WORKSPACE_DIR) if os.path.isdir(os.path.join(WORKSPACE_DIR, f))]
    
    # history.txt ট্র্যাকিং লজিক 
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
                if folder_title.lower() == "shorts":
                    continue
                if not folder_title or folder_title in existing_folders or folder_title in history_logs: 
                    continue 

                # নতুন ফোল্ডার তৈরি 
                print(f"New Article Found: {folder_title}. Generating...")
                folder_path = os.path.join(WORKSPACE_DIR, folder_title)
                os.makedirs(folder_path)
                existing_folders.append(folder_title)
                
                # history তে সেভ করা
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

# ==================== [ 2. DYNAMIC FRAME ENGINE (Supports 16:9 & Advanced 9:16) ] ====================
def make_video_frame(img_path, duration, target_w=1920, target_h=1080):
    pil_img = Image.open(img_path).convert("RGB")
    w, h = pil_img.size
    ratio = w / h
    target_ratio = target_w / target_h

    is_vertical = target_w < target_h # ৯:১৬ মোড চেক করা 

    if is_vertical:
        # রুল ১: ৯:১৬ এর চেয়েও লম্বালম্বি ছবি (Ratio < 9/16) হলে জুম এবং উপর-নিচে স্ক্রল হবে 
        if ratio < (9.0 / 16.0) - 0.01:
            new_w = target_w
            new_h = int((target_w / w) * h)
            if new_h < target_h:
                new_h = target_h
                
            resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
            img_np = np.array(resized)
            
            def make_frame(t):
                progress = t / duration if duration > 0 else 0
                y = int(progress * (new_h - target_h)) if (new_h - target_h) > 0 else 0 
                x = 0
                return img_np[y:y+target_h, x:x+target_w]
            
            return VideoClip(make_frame, duration=duration)
            
        # রুল ২: মাঝারি সাইজের ছবি (9/16 <= Ratio < 16/9) হলে ক্রপ না করে ব্ল্যাক ক্যানভাসে বসাবে 
        elif (9.0 / 16.0) - 0.01 <= ratio < (16.0 / 9.0) - 0.01:
            scale_w = target_w / w
            scale_h = target_h / h
            scale = min(scale_w, scale_h)
            
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
            
            # কালো ব্যাকগ্রাউন্ডের ক্যানভাস তৈরি 
            canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
            offset_x = (target_w - new_w) // 2
            offset_y = (target_h - new_h) // 2
            canvas.paste(resized, (offset_x, offset_y))
            
            img_np = np.array(canvas)
            
            def make_frame(t):
                return img_np
                
            return VideoClip(make_frame, duration=duration)
            
        # রুল ৩: চওড়া ছবি (Ratio >= 16/9) আসলে বাম-ডান স্ক্রল করবে
        else:
            new_h = target_h
            new_w = int((target_h / h) * w)
            if new_w < target_w:
                new_w = target_w
                
            resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
            img_np = np.array(resized)
            
            def make_frame(t):
                progress = t / duration if duration > 0 else 0
                y = 0
                x = int(progress * (new_w - target_w)) if (new_w - target_w) > 0 else 0 
                return img_np[y:y+target_h, x:x+target_w]
                
            return VideoClip(make_frame, duration=duration)
            
    else:
        # ১৬:৯ ল্যান্ডস্কেপ মোড (ইউটিউবের জন্য)
        if ratio >= target_ratio: 
            new_h = target_h
            new_w = int((target_h / h) * w)
        else:
            new_w = target_w
            new_h = int((target_w / w) * h)
            
        if new_w < target_w:
            new_w = target_w
            new_h = int((new_w / w) * h)
        if new_h < target_h:
            new_h = target_h
            new_w = int((new_h / h) * w)

        resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
        img_np = np.array(resized)
        
        def make_frame(t):
            progress = t / duration if duration > 0 else 0
            y = int(progress * (new_h - target_h)) if (new_h - target_h) > 0 else 0 
            x = int(progress * (new_w - target_w)) if (new_w - target_w) > 0 else 0 
            return img_np[y:y+target_h, x:x+target_w]
            
        return VideoClip(make_frame, duration=duration)

# ==================== [ 🌟 DYNAMIC WATERMARK/FRONT OVERLAY ENGINE ] ====================
def apply_front_overlay(main_clip, target_w, target_h):
    front_path = "front.png"
    if os.path.exists(front_path):
        try:
            print(f"Applying front.png overlay at the bottom-center of the video...")
            # ছবি লোড করা এবং ডিউরেশন ভিডিওর সমান করা
            front_clip = ImageClip(front_path).set_duration(main_clip.duration)
            
            # ডায়নামিকালি উইডথ রিসাইজ (স্ক্রিনের উইডথ-এর ৪০% রাখা হবে)
            scaled_w = int(target_w * 0.40)
            front_clip = front_clip.resize(width=scaled_w)
            
            # পজিশন নির্ধারণ (নিচে মাঝখানে ৫% সেফটি মার্জিন সহ)
            margin = int(target_h * 0.05)
            y_pos = target_h - front_clip.h - margin
            front_clip = front_clip.set_position(("center", y_pos))
            
            # ভিডিওর উপরে কম্পোজিট ওভারলে হিসেবে যুক্ত করা 
            main_clip = CompositeVideoClip([main_clip, front_clip]).set_audio(main_clip.audio)
        except Exception as e:
            print(f"Error applying front.png overlay: {e}")
    else:
        print("front.png was not found in the root directory. Skipping overlay.")
    return main_clip

# ==================== [ 3. MOVIEPY PROCESS ] ====================
def process_ready_videos(yt):
    print("\nScanning Drive folders for Audios...")
    if not os.path.exists(WORKSPACE_DIR): return
    if not os.path.exists(TMP_DIR): os.makedirs(TMP_DIR)
    
    folders = [f for f in os.listdir(WORKSPACE_DIR) if os.path.isdir(os.path.join(WORKSPACE_DIR, f)) and f.lower() != "shorts"]
    
    for folder_name in folders:
        folder_path = os.path.join(WORKSPACE_DIR, folder_name)
        
        try:
            audio_file, txt_path = None, None
            img_files = []
            for file in sorted(os.listdir(folder_path)):
                ext = file.lower().split('.')[-1]
                if ext in ['mp3', 'wav', 'm4a', 'aac']: 
                    audio_file = file
                elif ext in ['txt']: 
                    txt_path = os.path.join(folder_path, file)
                elif ext in ['jpg', 'jpeg', 'png', 'webp']: 
                    img_files.append(os.path.join(folder_path, file))
                    
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
                
            # আগের ওভাররাইট ক্লিনিং
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
                scale = max(720 / img.height, 1280 / img.width)
                rs_img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
                left = (rs_img.width - 1280) // 2
                rs_img.crop((left, 0, left+1280, 720)).save(thumbnail_path, "JPEG", quality=95)
                video_imgs = [ip for ip in img_files if ip != wide_img]
                if not video_imgs: video_imgs.append(wide_img)
            else:
                img = Image.open(img_files[0]).convert("RGB")
                scale = max(720 / img.height, 1280 / img.width)
                rs_img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
                rs_img.crop((0, 0, 1280, 720)).save(thumbnail_path, "JPEG", quality=95)
                video_imgs = img_files

            # মুভি এডিটিং শুরু
            audio_clip = AudioFileClip(audio_path)
            per_img_duration = audio_clip.duration / len(video_imgs)
            
            # ------------------ [১ম কাজ: ১৬:৯ ল্যান্ডস্কেপ ভিডিও (ইউটিউবের জন্য)] ------------------
            print("Rendering 16:9 Landscape slideshow for YouTube upload...")
            yt_clips = [make_video_frame(v, per_img_duration, target_w=1920, target_h=1080) for v in video_imgs]
            youtube_video = concatenate_videoclips(yt_clips).set_audio(audio_clip)
            
            # 🌟 ইউটিউব ভিডিওতে front.png ওভারলে যুক্ত করা 
            youtube_video = apply_front_overlay(youtube_video, target_w=1920, target_h=1080)
            
            youtube_video.write_videofile(
                out_video_file, fps=30, codec="libx264", 
                audio_codec="aac", threads=4, preset="ultrafast",
                ffmpeg_params=["-g", "60", "-keyint_min", "60", "-sc_threshold", "0", "-pix_fmt", "yuv420p"],
                logger=None
            )
            
            # YouTube-এ আপলোডিং
            upload_success = upload_to_youtube(
                yt, out_video_file, video_title, 
                thumbnail_path if os.path.exists(thumbnail_path) else None
            )
            
            youtube_video.close()
            for c in yt_clips: c.close()
            
            # ------------------ [২য় কাজ: ৯:১৬ পোর্ট্রেট ভিডিও (JobLive গুগল ড্রাইভের জন্য)] ------------------
            if upload_success:
                if not os.path.exists(LIVESTREAM_DIR):
                    os.makedirs(LIVESTREAM_DIR)
                    
                safe_video_title = clean_filename(video_title)
                live_video_file = os.path.join(LIVESTREAM_DIR, f"{safe_video_title}.mp4")
                
                print(f"Rendering 9:16 Vertical slideshow for JobLive: {live_video_file}")
                live_clips = [make_video_frame(v, per_img_duration, target_w=1080, target_h=1920) for v in video_imgs]
                live_video = concatenate_videoclips(live_clips).set_audio(audio_clip)
                
                # 🌟 JobLive ড্রাইভ কপিতেও front.png ওভারলে যুক্ত করা 
                live_video = apply_front_overlay(live_video, target_w=1080, target_h=1920)
                
                live_video.write_videofile(
                    live_video_file, fps=30, codec="libx264", 
                    audio_codec="aac", threads=4, preset="ultrafast",
                    ffmpeg_params=["-g", "60", "-keyint_min", "60", "-sc_threshold", "0", "-pix_fmt", "yuv420p"],
                    logger=None
                )
                
                live_video.close()
                for c in live_clips: c.close()
                
                # ড্রাইভ ফোল্ডার ক্লিনআপ
                print("Task Accomplished! Requesting Drive Cleanup.")
                shutil.rmtree(folder_path, ignore_errors=True)
            else:
                print("❌ YouTube upload failed! Skipping JobLive copy and deletion to prevent data loss.")
                
            audio_clip.close()

        except Exception as folder_error:
            print(f"\n❌ Error occurred while processing folder '{folder_name}': {folder_error}")
            print("Moving on to the next available folder...\n")

# ==================== [ 4. DEDICATED SHORTS LOADER (Anti-Deletion keep system) ] ====================
def process_shorts_folder(yt):
    print("\nScanning for pre-made Shorts in 'Shorts' folder...")
    shorts_dir = None
    if os.path.exists(WORKSPACE_DIR):
        for f in os.listdir(WORKSPACE_DIR):
            if f.lower() == "shorts" and os.path.isdir(os.path.join(WORKSPACE_DIR, f)):
                shorts_dir = os.path.join(WORKSPACE_DIR, f)
                break
                
    if not shorts_dir:
        print("No 'Shorts' folder found in Google Drive. Skipping Shorts process.")
        return
        
    keep_file = os.path.join(shorts_dir, ".keep")
    if not os.path.exists(keep_file):
        try:
            with open(keep_file, 'w') as kf:
                kf.write("keep")
            print("Created .keep file inside Shorts folder to preserve it.")
        except Exception as ke:
            print("Failed to create .keep file:", ke)
                
    for file in os.listdir(shorts_dir):
        if file == ".keep": 
            continue
            
        file_path = os.path.join(shorts_dir, file)
        if os.path.isdir(file_path): continue 
        
        ext = file.lower().split('.')[-1]
        if ext in ['mp4', 'mov', 'mkv', 'avi']:
            video_title = os.path.splitext(file)[0]
            print(f"\n========== Processing Short Video: {video_title} ==========")
            
            upload_success = upload_to_youtube(yt, file_path, video_title, thumbnail_path=None)
            
            if upload_success:
                print(f"Deleting uploaded Short locally: {file}")
                try: os.remove(file_path)
                except Exception as r_e: print("File delete error:", r_e)

# ==================== [ 5. YOUTUBE API ] ====================
def upload_to_youtube(yt, video_file, title, thumbnail_path):
    print(f"Now Uploading: '{title}'")
    try:
        description_text = "" 
        
        body = {
            'snippet': { 
                'title': title[:100], 
                'description': description_text, 
                'tags': ['Job Circular BD', 'Today Govt Jobs'] 
            },
            'status': { 'privacyStatus': 'public' } 
        }
        media_vid = MediaFileUpload(video_file, chunksize=1024*1024, resumable=True)
        res = yt.videos().insert(part="snippet,status", body=body, media_body=media_vid).execute()
        video_id = res['id']
        print(f"» Successfully Uploaded! Video Link: https://youtu.be/{video_id}")
        
        if thumbnail_path:
            try: 
                media_thmb = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
                yt.thumbnails().set(videoId=video_id, media_body=media_thmb).execute()
                print("» Attached perfect Custom Thumbnail!")
            except Exception as e: 
                print("\n⚠️ Custom Thumbnail Add Failed! -> Check if YouTube Account is Phone Verified!\n")
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
        process_shorts_folder(yt_service) 
    except Exception as critical:
        print("\nFATAL ERROR DETECTED: ", critical)
    finally:
        if os.path.exists(TMP_DIR): shutil.rmtree(TMP_DIR, ignore_errors=True)
        print("\nAll Tasks Finalized Perfectly.\n======================================")
