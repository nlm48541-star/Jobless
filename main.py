# -*- coding: utf-8 -*-
import os, json, shutil, traceback
from PIL import Image

from feed_manager import (
    check_new_articles_and_prepare_folders, clean_filename, is_forbidden_article, 
    WORKSPACE_DIR
)
from ai_service import generate_job_content
from audio_engine import generate_voiceover_audio_pipeline
from thumbnail import generate_dynamic_thumbnail
from video_editor import render_synchronized_video
from youtube_uploader import get_youtube_service, upload_to_youtube
from manual_processor import process_manual_drive_folder

TMP_DIR = "temp_assets"
LIVESTREAM_DIR = "workspace_live"
HISTORY_FILE = os.path.join(WORKSPACE_DIR, "history.txt")

def add_to_history(entry_text):
    if not entry_text or not str(entry_text).strip(): return
    clean_val = str(entry_text).strip()
    existing_records = set()
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as hf:
                existing_records = {line.strip().lower() for line in hf if line.strip()}
        except Exception: pass

    if clean_val.lower() not in existing_records:
        try:
            os.makedirs(WORKSPACE_DIR, exist_ok=True)
            with open(HISTORY_FILE, "a", encoding="utf-8") as hf:
                hf.write(f"{clean_val}\n")
            print(f"📝 [HISTORY] Saved: '{clean_val[:60]}'")
        except Exception: pass

def process_ready_videos(yt):
    print("\nScanning Drive folders for Videos / AI Processing...")
    if not os.path.exists(WORKSPACE_DIR): return
    if not os.path.exists(TMP_DIR): os.makedirs(TMP_DIR, exist_ok=True)

    folders = [f for f in os.listdir(WORKSPACE_DIR) if os.path.isdir(os.path.join(WORKSPACE_DIR, f)) and f.lower() != "shorts"]
    
    for folder_name in folders:
        folder_path = os.path.join(WORKSPACE_DIR, folder_name)
        try:
            if is_forbidden_article(folder_name):
                print(f"🚫 [FILTERED] Deleting forbidden folder '{folder_name}'.")
                shutil.rmtree(folder_path, ignore_errors=True)
                continue

            existing_audio_file, txt_path, link_path = None, None, None
            custom_thumb_path = None
            img_files = []
            
            for file in sorted(os.listdir(folder_path)):
                f_lower = file.lower()
                ext = f_lower.split('.')[-1]

                if ext in ['mp3', 'wav', 'm4a', 'aac']:
                    existing_audio_file = file
                elif f_lower == "title.txt":
                    txt_path = os.path.join(folder_path, file)
                elif f_lower == "link.txt":
                    link_path = os.path.join(folder_path, file)
                # 🌟 থাম্বনেইল ফাইল আলাদা শনাক্ত করা (ভিডিওর স্লাইড থেকে আলাদা থাকবে)
                elif f_lower in ["thumbnail.png", "thumbnail.jpg", "thumbnail.jpeg"]:
                    custom_thumb_path = os.path.join(folder_path, file)
                elif ext in ['jpg', 'jpeg', 'png', 'webp']: 
                    img_files.append(os.path.join(folder_path, file))
                    
            if not img_files:
                shutil.rmtree(folder_path, ignore_errors=True)
                continue

            raw_title = folder_name
            if txt_path and os.path.exists(txt_path):
                try:
                    with open(txt_path, 'r', encoding='utf-8') as tf:
                        raw_title = tf.read().strip()
                except Exception: pass

            article_link = ""
            if link_path and os.path.exists(link_path):
                try:
                    with open(link_path, 'r', encoding='utf-8') as lf:
                        article_link = lf.read().strip()
                except Exception: pass

            if is_forbidden_article(raw_title):
                shutil.rmtree(folder_path, ignore_errors=True)
                continue

            print(f"\n========== Process started: {folder_name} ==========")

            # এআই দিয়ে ১০+ মিনিটের সেগমেন্টেড স্ক্রিপ্ট তৈরি
            ai_res = generate_job_content(raw_title, img_files)
            opt_title, voiceover_script, segments, thumb_meta, video_desc, video_tags = ai_res

            if not opt_title or not voiceover_script:
                print(f"🛑 [CANCELLED] AI generation failed for '{folder_name}'.")
                continue

            video_title = opt_title

            # অডিও তৈরি
            if existing_audio_file:
                audio_path = os.path.join(folder_path, existing_audio_file)
                print(f"🎵 [PRE-EXISTING AUDIO] Using '{existing_audio_file}' directly.")
            else:
                gen_audio_path = os.path.join(folder_path, "voiceover.mp3")
                audio_success = generate_voiceover_audio_pipeline(voiceover_script, gen_audio_path)
                if not audio_success or not os.path.exists(gen_audio_path):
                    print(f"🛑 Audio synthesis failed for '{folder_name}'.")
                    continue
                audio_path = gen_audio_path

            # 🌟 থাম্বনেইল তৈরি (কাস্টম থাম্বনেইল থাকলে সেটি সরাসরি ব্যবহার, নতুবা ডায়নামিক জেনারেট)
            thumbnail_path = os.path.join(TMP_DIR, "thumbnail.jpg")
            if os.path.exists(thumbnail_path): os.remove(thumbnail_path)

            if custom_thumb_path and os.path.exists(custom_thumb_path):
                print(f"🖼️ [CUSTOM THUMBNAIL] Using '{os.path.basename(custom_thumb_path)}' directly (Bypassing dynamic generator).")
                with Image.open(custom_thumb_path) as c_thumb:
                    if c_thumb.mode in ("RGBA", "LA") or (c_thumb.mode == "P" and "transparency" in c_thumb.info):
                        bg = Image.new("RGB", c_thumb.size, (255, 255, 255))
                        bg.paste(c_thumb.convert("RGBA"), mask=c_thumb.convert("RGBA"))
                        bg.save(thumbnail_path, "JPEG", quality=100, subsampling=0)
                    else:
                        c_thumb.convert("RGB").save(thumbnail_path, "JPEG", quality=100, subsampling=0)
            else:
                generate_dynamic_thumbnail(raw_title, thumbnail_path, thumb_meta=thumb_meta)

            out_video_file = os.path.join(TMP_DIR, "final_out.mp4")
            if os.path.exists(out_video_file): os.remove(out_video_file)

            # অডিও-ভিজ্যুয়াল সিঙ্ক্রোনাইজড ভিডিও রেন্ডার
            print("Rendering 16:9 Synchronized Video for YouTube...")
            render_synchronized_video(audio_path, img_files, segments, out_video_file, is_vertical=False)
            
            upload_success = upload_to_youtube(
                yt, out_video_file, video_title, 
                thumbnail_path if os.path.exists(thumbnail_path) else None,
                description=video_desc,
                tags=video_tags,
                schedule_upload=True
            )
            
            if upload_success:
                add_to_history(raw_title)
                if article_link: add_to_history(article_link)

                try:
                    if not os.path.exists(LIVESTREAM_DIR): os.makedirs(LIVESTREAM_DIR, exist_ok=True)
                    safe_name = clean_filename(video_title)[:45].strip()
                    live_video_file = os.path.join(LIVESTREAM_DIR, f"{safe_name}.mp4")
                    render_synchronized_video(audio_path, img_files, segments, live_video_file, is_vertical=True)
                except Exception: pass

                shutil.rmtree(folder_path, ignore_errors=True)
                print(f"✅ Folder '{folder_name}' successfully processed and uploaded.\n")

        except Exception as folder_error:
            traceback.print_exc()

def process_shorts_folder(yt):
    shorts_dir = None
    if os.path.exists(WORKSPACE_DIR):
        for f in os.listdir(WORKSPACE_DIR):
            if f.lower() == "shorts" and os.path.isdir(os.path.join(WORKSPACE_DIR, f)):
                shorts_dir = os.path.join(WORKSPACE_DIR, f)
                break
    if not shorts_dir: return

    for file in os.listdir(shorts_dir):
        if file == ".keep": continue
        file_path = os.path.join(shorts_dir, file)
        if os.path.isdir(file_path): continue 
        
        ext = file.lower().split('.')[-1]
        if ext in ['mp4', 'mov', 'mkv', 'avi']:
            video_title = os.path.splitext(file)[0]
            upload_success = upload_to_youtube(
                yt, file_path, video_title, thumbnail_path=None, 
                description=video_title, tags=None, schedule_upload=True
            )
            if upload_success:
                add_to_history(f"[SHORTS] {video_title}")
                try: os.remove(file_path)
                except Exception: pass

if __name__ == "__main__":
    print("\n====== [ Google Drive Bot Active | Synchronized 10-Min Engine ] ======\n")
    try:
        yt_service = get_youtube_service()

        try: process_manual_drive_folder(yt_service)
        except Exception: traceback.print_exc()

        try: check_new_articles_and_prepare_folders()
        except Exception: traceback.print_exc()

        try: process_ready_videos(yt_service)
        except Exception: traceback.print_exc()

        try: process_shorts_folder(yt_service)
        except Exception: traceback.print_exc()

    except Exception:
        traceback.print_exc()
    finally:
        if os.path.exists(TMP_DIR): shutil.rmtree(TMP_DIR, ignore_errors=True)
        print("\nAll Tasks Finalized Perfectly.\n======================================")
