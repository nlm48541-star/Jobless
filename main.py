# -*- coding: utf-8 -*-
import os, json, shutil, traceback
from feed_manager import check_new_articles_and_prepare_folders, clean_filename, is_forbidden_article, WORKSPACE_DIR
from ai_service import generate_job_content
from audio_engine import generate_voiceover_audio_pipeline
from thumbnail import generate_dynamic_thumbnail
from video_editor import render_video_slideshow
from youtube_uploader import get_youtube_service, upload_to_youtube

TMP_DIR = "temp_assets"
LIVESTREAM_DIR = "workspace_live"

def process_ready_videos(yt):
    print("\nScanning Drive folders for Videos / AI Processing...")
    if not os.path.exists(WORKSPACE_DIR): return
    if not os.path.exists(TMP_DIR): os.makedirs(TMP_DIR, exist_ok=True)

    folders = [f for f in os.listdir(WORKSPACE_DIR) if os.path.isdir(os.path.join(WORKSPACE_DIR, f)) and f.lower() != "shorts"]
    
    for folder_name in folders:
        folder_path = os.path.join(WORKSPACE_DIR, folder_name)
        try:
            # ১. যদি কোনো ফোল্ডারের নামে 'এনজিও' বা 'ব্যাংক' থাকে, সাথে সাথে ডিলিট
            if is_forbidden_article(folder_name):
                print(f"🚫 [FILTERED] Deleting forbidden folder '{folder_name}' (এনজিও / ব্যাংক).")
                shutil.rmtree(folder_path, ignore_errors=True)
                continue

            custom_audio_file, txt_path = None, None
            img_files = []
            
            for file in sorted(os.listdir(folder_path)):
                ext = file.lower().split('.')[-1]
                if ext in ['mp3', 'wav', 'm4a', 'aac']:
                    # যদি আগের ব্যর্থ রানের voiceover.mp3 থাকে তা ইগনোর করে ফ্রেশ জেনারেট করবে
                    if file.lower() == "voiceover.mp3":
                        try: os.remove(os.path.join(folder_path, file))
                        except Exception: pass
                    else:
                        custom_audio_file = file
                elif ext in ['txt']: 
                    txt_path = os.path.join(folder_path, file)
                elif ext in ['jpg', 'jpeg', 'png', 'webp']: 
                    img_files.append(os.path.join(folder_path, file))
                    
            # ২. কোনো ফোল্ডারে ছবি না থাকলে ডিলিট
            if not img_files:
                print(f"🗑️ Deleting empty folder '{folder_name}' (No images found).")
                shutil.rmtree(folder_path, ignore_errors=True)
                continue

            raw_title = folder_name
            if txt_path and os.path.exists(txt_path):
                try:
                    with open(txt_path, 'r', encoding='utf-8') as tf:
                        raw_title = tf.read().strip()
                except Exception: pass

            if is_forbidden_article(raw_title):
                print(f"🚫 [FILTERED] Deleting '{folder_name}' (Title contains এনজিও / ব্যাংক).")
                shutil.rmtree(folder_path, ignore_errors=True)
                continue

            print(f"\n========== Process started: {folder_name} ==========")

            # ৩. এআই দিয়ে স্ক্রিপ্ট ও মেটাডাটা তৈরি
            opt_title, voiceover_script, thumb_meta, video_desc, video_tags = generate_job_content(raw_title, img_files)
            
            if not opt_title or not voiceover_script:
                print(f"🛑 [CANCELLED] All AI models failed for '{folder_name}'. Video creation aborted.")
                continue

            video_title = opt_title

            # ৪. ElevenLabs Eleven v3 দিয়ে ফ্রেশ বাংলা অডিও তৈরি
            if not custom_audio_file:
                gen_audio_path = os.path.join(folder_path, "voiceover.mp3")
                audio_success = generate_voiceover_audio_pipeline(voiceover_script, gen_audio_path)
                if not audio_success or not os.path.exists(gen_audio_path):
                    print(f"🛑 [CANCELLED] ElevenLabs audio synthesis failed for '{folder_name}'. Aborting.")
                    continue
                audio_path = gen_audio_path
            else:
                audio_path = os.path.join(folder_path, custom_audio_file)

            # ৫. থাম্বনেইল জেনারেশন
            thumbnail_path = os.path.join(TMP_DIR, "thumbnail.jpg")
            if os.path.exists(thumbnail_path): os.remove(thumbnail_path)
            generate_dynamic_thumbnail(raw_title, thumbnail_path, thumb_meta=thumb_meta)

            # ৬. ১৬:৯ ল্যান্ডস্কেপ ভিডিও রেন্ডার ও আপলোড
            out_video_file = os.path.join(TMP_DIR, "final_out.mp4")
            if os.path.exists(out_video_file): os.remove(out_video_file)

            print("Rendering 16:9 Landscape slideshow for YouTube upload...")
            render_video_slideshow(audio_path, img_files, out_video_file, is_vertical=False)
            
            upload_success = upload_to_youtube(
                yt, out_video_file, video_title, 
                thumbnail_path if os.path.exists(thumbnail_path) else None,
                description=video_desc,
                tags=video_tags,
                schedule_upload=True
            )
            
            # ৭. ৯:১৬ পোর্ট্রেট ভিডিও (JobLive)
            if upload_success:
                try:
                    if not os.path.exists(LIVESTREAM_DIR): os.makedirs(LIVESTREAM_DIR, exist_ok=True)
                    safe_name = clean_filename(video_title)[:45].strip()
                    live_video_file = os.path.join(LIVESTREAM_DIR, f"{safe_name}.mp4")
                    
                    print(f"Rendering 9:16 Vertical slideshow for JobLive: {live_video_file}")
                    render_video_slideshow(audio_path, img_files, live_video_file, is_vertical=True)
                except Exception as live_err:
                    print(f"⚠️ JobLive notice: {live_err}")

                shutil.rmtree(folder_path, ignore_errors=True)
                print(f"✅ Folder '{folder_name}' successfully processed and uploaded.\n")

        except Exception as folder_error:
            print(f"\n❌ Error in folder '{folder_name}': {folder_error}")
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
                try: os.remove(file_path)
                except Exception: pass

if __name__ == "__main__":
    print("\n====== [ Google Drive Bot Active | Auto Filter & AI Engine ] ======\n")
    try:
        yt_service = get_youtube_service()
        
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
