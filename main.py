# -*- coding: utf-8 -*-
import os, json, time, re, shutil
import requests, feedparser
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import numpy as np

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from moviepy.editor import AudioFileClip, VideoClip, concatenate_videoclips, ImageClip, CompositeVideoClip

WORKSPACE_DIR = "workspace"      # Rclone Sync Location
LIVESTREAM_DIR = "workspace_live" # JobLive folder source
TMP_DIR = "temp_assets"          # Temp Files processing
FONT_PATH = "BengaliFont.ttf"    # Auto downloaded Bengali Font

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

# ==================== [ 🌟 YUSUF ADNAN TITLE TUNED THUMBNAIL ENGINE ] ====================
def ensure_bengali_font():
    if not os.path.exists(FONT_PATH):
        print("Downloading Bold Bengali font for News Thumbnails...")
        urls = [
            "https://github.com/google/fonts/raw/main/ofl/notosansbengali/NotoSansBengali%5Bwdth%2Cwght%5D.ttf",
            "https://raw.githubusercontent.com/maateen/kalpurush/master/Kalpurush.ttf"
        ]
        for url in urls:
            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 200 and len(r.content) > 10000:
                    with open(FONT_PATH, "wb") as f:
                        f.write(r.content)
                    print("Bengali font downloaded successfully.")
                    break
            except Exception as e:
                print(f"Font download attempt failed: {e}")

def parse_title_for_thumbnail(title):
    # ডিফল্ট ভ্যালু
    top_text = "সরকারি চাকরি নিয়োগ ২০২৬"
    main_text = "🔥 নতুন নিয়োগ বিজ্ঞপ্তি ২০২৬"
    sub_text = "৬৪ জেলা থেকে আবেদনের সুযোগ"
    bottom_text = "সকল জেলার পুরুষ ও মহিলা আবেদনযোগ্য"

    t = title.strip()
    
    # ১. ইংরেজি শর্ট কোড বা বন্ধনীর লেখা আলাদা করা (যেমন: BPDB, BRDB, CGA, TMSS NGO, AAUB)
    bracket_match = re.search(r'\((.*?)\)', t)
    short_code = bracket_match.group(1) if bracket_match else ""
    
    # ২. পদের সংখ্যা আলাদা করা (যেমন: ৫৮৭ পদে, ৪৮ পদে, ৫৭৫ পদে, ১৮৫ পদে)
    vac_match = re.search(r'(\d+|[০-৯]+)\s*পদে', t)
    vac_text = vac_match.group(0) if vac_match else ""

    # ৩. প্রতিষ্ঠানের নাম নিখুঁতভাবে ফিল্টার করা
    # যদি 'পদে' থাকে, তবে তার পর থেকে 'নিয়োগ' পর্যন্ত প্রতিষ্ঠানের নাম ধরা হবে 
    if "পদে" in t and "নিয়োগ" in t:
        try:
            org_part = t.split("পদে")[1].split("নিয়োগ")[0].strip()
            org_part = re.sub(r'\((.*?)\)', '', org_part).strip() # বন্ধনী রিমুভ
            if org_part:
                top_text = org_part
        except: pass
    elif "নিয়োগ" in t:
        try:
            org_part = t.split("নিয়োগ")[0].strip()
            org_part = re.sub(r'\((.*?)\)', '', org_part).strip()
            if org_part:
                top_text = org_part
        except: pass

    # ৪. কাস্টম স্পেশাল কেস ফিল্টারিং
    if "অফিসার ক্যাডেট" in t or "যোগ দিন" in t:
        top_text = "বাংলাদেশ সেনাবাহিনী"
        main_text = "🔥 অফিসার ক্যাডেট হিসেবে যোগ দিন"
        sub_text = "৮৯তম বিএমএ দীর্ঘমেয়াদী কোর্স"
    elif "এডমিট" in t or "কার্ড" in t:
        main_text = "🔥 পরীক্ষার এডমিট কার্ড প্রকাশ ২০২৬"
    elif "প্রশ্ন" in t or "সাজেশন" in t:
        main_text = "🔥 পরীক্ষার প্রশ্ন ও সাজেশন ২০২৬"
    elif "ফলাফল" in t or "রেজাল্ট" in t:
        main_text = "🔥 পরীক্ষার চূড়ান্ত ফলাফল প্রকাশ"
    else:
        main_text = "🔥 নতুন জরুরি নিয়োগ বিজ্ঞপ্তি ২০২৬"

    # ৫. সাব-টেক্সট সেটিং (পদের সংখ্যা বা শর্ট নেম হাইলাইট করা)
    if vac_text and short_code:
        sub_text = f"({vac_text}) {short_code} নিয়োগ বিজ্ঞপ্তি"
    elif vac_text:
        sub_text = f"({vac_text}) বড় নিয়োগ বিজ্ঞপ্তি প্রকাশিত"
    elif short_code:
        sub_text = f"({short_code}) নতুন নিয়োগ বিজ্ঞপ্তি"
    elif "গার্মেন্টস" in t or "টেক্সটাইল" in t:
        sub_text = "গার্মেন্টস ও টেক্সটাইল খাতে চাকরি"
    elif "মেডিক্যাল" in t or "হাসপাতাল" in t:
        sub_text = "মেডিকেল কলেজ ও হাসপাতালে নিয়োগ"

    return top_text, main_text, sub_text, bottom_text

def draw_text_box(draw, text, box, bg_color, text_color, font_path, max_font_size=55, radius=15):
    x1, y1, x2, y2 = box
    w_box = x2 - x1
    h_box = y2 - y1
    
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=bg_color)
    
    if font_path and os.path.exists(font_path):
        font_size = max_font_size
        
        # প্রতিষ্ঠানের নাম অনেক বড় হলে লেখাটিকে অটোমেটিক ২-লাইনে বিভক্ত করার স্মার্ট লজিক
        words = text.split()
        if len(text) > 28 and len(words) >= 2:
            mid = len(words) // 2
            line1 = " ".join(words[:mid])
            line2 = " ".join(words[mid:])
            lines = [line1, line2]
        else:
            lines = [text]
            
        # ফন্ট সাইজ অ্যাডজাস্টমেন্ট 
        while font_size > 18:
            font = ImageFont.truetype(font_path, font_size)
            max_line_w = max([font.getbbox(l)[2] - font.getbbox(l)[0] for l in lines])
            total_h = sum([font.getbbox(l)[3] - font.getbbox(l)[1] for l in lines]) + (len(lines)-1)*8
            if max_line_w <= w_box - 35 and total_h <= h_box - 15:
                break
            font_size -= 2
            
        # টেক্সট সেন্টারে ড্র করা
        total_h = sum([font.getbbox(l)[3] - font.getbbox(l)[1] for l in lines]) + (len(lines)-1)*8
        start_y = y1 + (h_box - total_h) / 2
        
        curr_y = start_y
        for line in lines:
            bbox = font.getbbox(line)
            lw = bbox[2] - bbox[0]
            lh = bbox[3] - bbox[1]
            lx = x1 + (w_box - lw) / 2
            draw.text((lx, curr_y - bbox[1]), line, fill=text_color, font=font)
            curr_y += lh + 8
    else:
        draw.text((x1 + 20, y1 + 10), text, fill=text_color)

def generate_dynamic_thumbnail(title, output_path):
    print(f"Generating Custom News Banner Thumbnail for: {title}")
    ensure_bengali_font()
    
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), "#071126") # Deep Dark Blue Background
    draw = ImageDraw.Draw(img)
    
    # Outer Yellow Border
    draw.rectangle([0, 0, W, H], outline="#facc15", width=14)
    
    top_text, main_text, sub_text, bottom_text = parse_title_for_thumbnail(title)
    
    # 1. Top Green Banner (প্রতিষ্ঠানের নাম)
    draw_text_box(draw, top_text, (30, 35, W - 30, 175), bg_color="#047857", text_color="#ffffff", font_path=FONT_PATH, max_font_size=60)
    
    # 2. Middle Red Highlight Banner (মূল হেডলাইন)
    draw_text_box(draw, main_text, (30, 195, W - 30, 375), bg_color="#dc2626", text_color="#ffffff", font_path=FONT_PATH, max_font_size=65)
    
    # 3. Sub Middle Yellow Banner (পদের সংখ্যা / যোগ্যতা)
    draw_text_box(draw, sub_text, (30, 395, W - 30, 545), bg_color="#facc15", text_color="#000000", font_path=FONT_PATH, max_font_size=55)
    
    # 4. Bottom Dark Banner (জেলার তথ্য)
    draw_text_box(draw, bottom_text, (30, 565, W - 30, 685), bg_color="#1e293b", text_color="#facc15", font_path=FONT_PATH, max_font_size=45)

    img.save(output_path, "JPEG", quality=95)
    print("Attractive Dynamic Thumbnail generated successfully!")

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

                print(f"New Article Found: {folder_title}. Generating...")
                folder_path = os.path.join(WORKSPACE_DIR, folder_title)
                os.makedirs(folder_path)
                existing_folders.append(folder_title)
                
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

    is_vertical = target_w < target_h 

    if is_vertical:
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
            
        elif (9.0 / 16.0) - 0.01 <= ratio < (16.0 / 9.0) - 0.01:
            scale_w = target_w / w
            scale_h = target_h / h
            scale = min(scale_w, scale_h)
            
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
            
            canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
            offset_x = (target_w - new_w) // 2
            offset_y = (target_h - new_h) // 2
            canvas.paste(resized, (offset_x, offset_y))
            
            img_np = np.array(canvas)
            
            def make_frame(t):
                return img_np
                
            return VideoClip(make_frame, duration=duration)
            
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

# ==================== [ DYNAMIC WATERMARK/FRONT OVERLAY ENGINE ] ====================
def apply_front_overlay(main_clip, target_w, target_h):
    front_path = "front.png"
    if os.path.exists(front_path):
        try:
            print("Applying front.png overlay at the bottom-center of the video...")
            front_clip = ImageClip(front_path).set_duration(main_clip.duration)
            
            scaled_w = int(target_w * 0.40)
            front_clip = front_clip.resize(width=scaled_w)
            
            margin = int(target_h * 0.05)
            y_pos = target_h - front_clip.h - margin
            front_clip = front_clip.set_position(("center", y_pos))
            
            main_clip = CompositeVideoClip([main_clip, front_clip]).set_audio(main_clip.audio)
        except Exception as e:
            print(f"Error applying front.png overlay: {e}")
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
                
            thumbnail_path = os.path.join(TMP_DIR, "thumbnail.jpg")
            if os.path.exists(thumbnail_path): os.remove(thumbnail_path)
            
            out_video_file = os.path.join(TMP_DIR, "final_out.mp4")
            if os.path.exists(out_video_file): os.remove(out_video_file)

            # 🌟 [আপনার টাইটেল অনুযায়ী টিউন করা ডায়নামিক নিউজ ব্যানার থাম্বনেইল তৈরি]
            generate_dynamic_thumbnail(video_title, thumbnail_path)
            video_imgs = img_files

            audio_clip = AudioFileClip(audio_path)
            per_img_duration = audio_clip.duration / len(video_imgs)
            
            # ------------------ [১ম কাজ: ১৬:৯ ল্যান্ডস্কেপ ভিডিও (ইউটিউবের জন্য)] ------------------
            print("Rendering 16:9 Landscape slideshow for YouTube upload...")
            yt_clips = [make_video_frame(v, per_img_duration, target_w=1920, target_h=1080) for v in video_imgs]
            youtube_video = concatenate_videoclips(yt_clips).set_audio(audio_clip)
            youtube_video = apply_front_overlay(youtube_video, target_w=1920, target_h=1080)
            
            youtube_video.write_videofile(
                out_video_file, fps=30, codec="libx264", 
                audio_codec="aac", threads=4, preset="ultrafast",
                ffmpeg_params=["-g", "60", "-keyint_min", "60", "-sc_threshold", "0", "-pix_fmt", "yuv420p"],
                logger=None
            )
            
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
                live_video = apply_front_overlay(live_video, target_w=1080, target_h=1920)
                
                live_video.write_videofile(
                    live_video_file, fps=30, codec="libx264", 
                    audio_codec="aac", threads=4, preset="ultrafast",
                    ffmpeg_params=["-g", "60", "-keyint_min", "60", "-sc_threshold", "0", "-pix_fmt", "yuv420p"],
                    logger=None
                )
                
                live_video.close()
                for c in live_clips: c.close()
                
                print("Task Accomplished! Requesting Drive Cleanup.")
                shutil.rmtree(folder_path, ignore_errors=True)
            else:
                print("❌ YouTube upload failed! Skipping JobLive copy and deletion to prevent data loss.")
                
            audio_clip.close()

        except Exception as folder_error:
            print(f"\n❌ Error occurred while processing folder '{folder_name}': {folder_error}")
            print("Moving on to the next available folder...\n")

# ==================== [ 4. DEDICATED SHORTS LOADER ] ====================
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