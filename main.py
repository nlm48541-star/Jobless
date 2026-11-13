# -*- coding: utf-8 -*-
import os, shutil, traceback
from PIL import Image

from feed_manager import (
    check_new_articles_and_prepare_folders, clean_filename, is_forbidden_article,
    WORKSPACE_DIR, scrape_article_content_and_images
)
from ai_service import generate_job_content
from audio_engine import generate_voiceover_batch_pipeline
from thumbnail import generate_dynamic_thumbnail
from video_editor import render_video_slideshow
from youtube_uploader import get_youtube_service, upload_to_youtube
from manual_processor import prepare_manual_drive_job, finalize_manual_drive_job

TMP_DIR = "temp_assets"
LIVESTREAM_DIR = "workspace_live"
HISTORY_FILE = os.path.join(WORKSPACE_DIR, "history.txt")

MAX_VIDEOS_PER_RUN = 2


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


def prepare_workspace_video_jobs():
    """ধাপ ১: সব বৈধ ফোল্ডারের AI স্ক্রিপ্ট ও মেটাডাটা আগে তৈরি করে নেয় (অডিও বাদে)"""
    print("\nScanning Drive folders for AI Script Generation...")
    if not os.path.exists(WORKSPACE_DIR):
        return []

    folders = [f for f in os.listdir(WORKSPACE_DIR) if os.path.isdir(os.path.join(WORKSPACE_DIR, f)) and f.lower() != "shorts"]
    prepared_jobs = []

    for folder_name in sorted(folders):
        if len(prepared_jobs) >= MAX_VIDEOS_PER_RUN:
            print(f"🛑 Reached batch limit of {MAX_VIDEOS_PER_RUN} videos for this run. Remaining will process next hour.")
            break

        folder_path = os.path.join(WORKSPACE_DIR, folder_name)
        try:
            if is_forbidden_article(folder_name):
                shutil.rmtree(folder_path, ignore_errors=True)
                continue

            existing_audio_file, txt_path, link_path, article_txt_path = None, None, None, None
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
                elif f_lower == "article.txt":
                    article_txt_path = os.path.join(folder_path, file)
                elif any(k in f_lower for k in ["thumbnail", "thumb"]) and ext in ['jpg', 'jpeg', 'png', 'webp']:
                    custom_thumb_path = os.path.join(folder_path, file)
                    continue
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

            article_text = ""
            if article_txt_path and os.path.exists(article_txt_path):
                try:
                    with open(article_txt_path, 'r', encoding='utf-8') as af:
                        article_text = af.read().strip()
                except Exception: pass
            elif article_link:
                _, article_text, _ = scrape_article_content_and_images(article_link)

            source_text = article_text if article_text else raw_title

            if is_forbidden_article(raw_title):
                shutil.rmtree(folder_path, ignore_errors=True)
                continue

            print(f"\n========== [SCRIPT PHASE {len(prepared_jobs) + 1}/{MAX_VIDEOS_PER_RUN}]: {folder_name} ==========")
            opt_title, voiceover_script, thumb_meta, video_desc, video_tags = generate_job_content(raw_title, source_text, img_files)

            if not opt_title or not voiceover_script or len(voiceover_script.split()) < 25:
                print(f"🛑 [CANCELLED] Full script generation failed for '{folder_name}'.")
                continue

            prepared_jobs.append({
                "folder_name": folder_name,
                "folder_path": folder_path,
                "raw_title": raw_title,
                "article_link": article_link,
                "video_title": opt_title,
                "voiceover_script": voiceover_script,
                "thumb_meta": thumb_meta,
                "video_desc": video_desc,
                "video_tags": video_tags,
                "img_files": img_files,
                "custom_thumb_path": custom_thumb_path,
                "existing_audio_file": existing_audio_file,
            })

        except Exception:
            traceback.print_exc()

    return prepared_jobs


def finalize_workspace_video_job(yt, job, audio_path):
    """ধাপ ৩: অডিও পাওয়ার পর ওয়ার্কস্পেস ভিডিও রেন্ডার ও আপলোড"""
    folder_name = job["folder_name"]
    folder_path = job["folder_path"]
    os.makedirs(TMP_DIR, exist_ok=True)

    thumbnail_path = os.path.join(TMP_DIR, "thumbnail.jpg")
    if os.path.exists(thumbnail_path): os.remove(thumbnail_path)

    custom_thumb_path = job["custom_thumb_path"]
    if custom_thumb_path and os.path.exists(custom_thumb_path):
        with Image.open(custom_thumb_path) as c_thumb:
            c_thumb.convert("RGB").save(thumbnail_path, "JPEG", quality=100, subsampling=0)
    else:
        generate_dynamic_thumbnail(job["raw_title"], thumbnail_path, thumb_meta=job["thumb_meta"])

    out_video_file = os.path.join(TMP_DIR, "final_out.mp4")
    if os.path.exists(out_video_file): os.remove(out_video_file)

    print(f"Rendering 16:9 Video for '{folder_name}'...")
    render_video_slideshow(audio_path, job["img_files"], out_video_file, is_vertical=False)

    upload_success = upload_to_youtube(
        yt, out_video_file, job["video_title"],
        thumbnail_path if os.path.exists(thumbnail_path) else None,
        description=job["video_desc"], tags=job["video_tags"], schedule_upload=True
    )

    if upload_success:
        add_to_history(job["raw_title"])
        if job["article_link"]:
            add_to_history(job["article_link"])

        try:
            os.makedirs(LIVESTREAM_DIR, exist_ok=True)
            safe_name = clean_filename(job["video_title"])[:45].strip()
            live_video_file = os.path.join(LIVESTREAM_DIR, f"{safe_name}.mp4")
            render_video_slideshow(audio_path, job["img_files"], live_video_file, is_vertical=True)
        except Exception: pass

        shutil.rmtree(folder_path, ignore_errors=True)
        print(f"✅ Folder '{folder_name}' successfully uploaded.\n")


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
    print("\n====== [ Google Drive Bot Active | Batch Kaggle TTS Engine ] ======\n")
    try:
        os.makedirs(TMP_DIR, exist_ok=True)
        yt_service = get_youtube_service()

        # ---------------- ধাপ ১: সব স্ক্রিপ্ট আগে জেনারেট করা ----------------
        manual_job = None
        try:
            manual_job = prepare_manual_drive_job()
        except Exception:
            traceback.print_exc()

        try:
            check_new_articles_and_prepare_folders()
        except Exception:
            traceback.print_exc()

        workspace_jobs = []
        try:
            workspace_jobs = prepare_workspace_video_jobs()
        except Exception:
            traceback.print_exc()

        # ---------------- ধাপ ২: মাত্র ১টি কমান্ডে সবগুলো অডিও একসাথে তৈরি ----------------
        batch_tasks = []
        manual_audio_target = None

        if manual_job:
            if manual_job["custom_audio_file"]:
                manual_audio_target = manual_job["custom_audio_file"]
                print(f"🎵 [MANUAL PRE-EXISTING AUDIO] Using '{os.path.basename(manual_audio_target)}'")
            else:
                manual_audio_target = os.path.join(TMP_DIR, "manual_voiceover.wav")
                batch_tasks.append({
                    "filename": "manual_voiceover.wav",
                    "text": manual_job["voiceover_script"],
                    "target_path": manual_audio_target,
                })

        for idx, job in enumerate(workspace_jobs):
            if job["existing_audio_file"]:
                job["audio_target"] = os.path.join(job["folder_path"], job["existing_audio_file"])
                print(f"🎵 [PRE-EXISTING AUDIO] Using '{job['existing_audio_file']}' for '{job['folder_name']}'")
            else:
                target_wav = os.path.join(job["folder_path"], "voiceover.wav")
                job["audio_target"] = target_wav
                batch_tasks.append({
                    "filename": f"ws_{idx}_voiceover.wav",
                    "text": job["voiceover_script"],
                    "target_path": target_wav,
                })

        if batch_tasks:
            generate_voiceover_batch_pipeline(batch_tasks, os.path.join(TMP_DIR, "batch_audio"))
        else:
            print("ℹ️ কোনো নতুন ভয়েসওভার তৈরির প্রয়োজন নেই (Kaggle GPU কল স্কিপ করা হলো)।")

        # ---------------- ধাপ ৩: ভিডিও রেন্ডার ও YouTube আপলোড ----------------
        if manual_job and manual_audio_target and os.path.exists(manual_audio_target):
            try:
                finalize_manual_drive_job(yt_service, manual_job, manual_audio_target)
            except Exception:
                traceback.print_exc()

        for job in workspace_jobs:
            audio_target = job.get("audio_target")
            if not audio_target or not os.path.exists(audio_target):
                print(f"⚠️ Audio missing for '{job['folder_name']}'. Skipping.")
                continue
            try:
                finalize_workspace_video_job(yt_service, job, audio_target)
            except Exception:
                traceback.print_exc()

        try:
            process_shorts_folder(yt_service)
        except Exception:
            traceback.print_exc()

    except Exception:
        traceback.print_exc()
    finally:
        if os.path.exists(TMP_DIR): shutil.rmtree(TMP_DIR, ignore_errors=True)
        print("\nAll Tasks Finalized Perfectly.\n======================================")
