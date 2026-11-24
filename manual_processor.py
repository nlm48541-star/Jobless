# -*- coding: utf-8 -*-
import json, os, shutil, subprocess
from PIL import Image

from ai_service import (
    generate_job_content_with_data, convert_all_numbers_in_script,
    extract_verified_job_data, generate_seo_metadata, generate_thumbnail_metadata,
    sanitize_youtube_tags, DEFAULT_BASE_TAGS, clean_script_for_speech
)
from audio_engine import generate_voiceover_audio_pipeline
from thumbnail import generate_dynamic_thumbnail
from video_editor import render_video_slideshow
from motion_renderer import render_motion_video
from youtube_uploader import upload_to_youtube
from feed_manager import scrape_article_content_and_images, download_image, clean_filename

MANUAL_DIR = "manual_workspace"
TMP_DIR = "temp_assets"
LIVESTREAM_DIR = "workspace_live"


def _load_segment_timings(audio_path):
    t_path = str(audio_path) + ".timings.json"
    if os.path.exists(t_path):
        try:
            with open(t_path, "r", encoding="utf-8") as tf:
                data = json.load(tf)
                segs = data.get("segments")
                if isinstance(segs, list) and segs:
                    return segs
        except Exception:
            pass
    return None


def is_manual_mode_enabled():
    val = os.environ.get("ENABLE_MANUAL_FOLDER", "false").strip().lower()
    folder_id = os.environ.get("MANUAL_DRIVE_FOLDER_ID", "").strip()
    return val in ["true", "1", "yes", "on"] and bool(folder_id)


def sync_manual_folder_from_drive(folder_id):
    os.makedirs(MANUAL_DIR, exist_ok=True)
    cmd = ["rclone", "sync", "gdrive:", MANUAL_DIR, f"--drive-root-folder-id={folder_id}", "--fast-list"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return res.returncode == 0
    except Exception as e:
        print(f"⚠️ Error syncing manual folder from drive: {e}")
        return False


def clean_manual_folder_on_drive(folder_id):
    print("🧹 [CLEANUP] Emptying Google Drive manual folder...")
    cmd_delete = ["rclone", "delete", "gdrive:", f"--drive-root-folder-id={folder_id}", "--drive-use-trash=false", "--fast-list"]
    cmd_rmdirs = ["rclone", "rmdirs", "gdrive:", f"--drive-root-folder-id={folder_id}", "--leave-root"]
    try:
        subprocess.run(cmd_delete, capture_output=True, text=True, timeout=60)
        subprocess.run(cmd_rmdirs, capture_output=True, text=True, timeout=60)
        print("✅ [CLEANUP] Google Drive manual folder successfully emptied!")
    except Exception as e:
        print(f"⚠️ Failed to empty manual folder: {e}")


def prepare_manual_drive_job():
    """ধাপ ১: ম্যানুয়াল ড্রাইভের ফাইল ও AI স্ক্রিপ্ট প্রস্তুত করে (ছবি ছাড়া হলেও মোশন গ্রাফিক্স মোডে)"""
    if not is_manual_mode_enabled():
        return None

    folder_id = os.environ.get("MANUAL_DRIVE_FOLDER_ID", "").strip()
    print("\n" + "=" * 65)
    print("🚨 [MANUAL DRIVE BOT] Checking Emergency Google Drive Folder...")
    print("=" * 65)

    if not sync_manual_folder_from_drive(folder_id) or not os.path.exists(MANUAL_DIR):
        return None

    all_files = os.listdir(MANUAL_DIR)
    if not all_files or all(f.startswith('.') for f in all_files):
        print("ℹ️ Manual Google Drive folder is empty.")
        return None

    img_files = []
    custom_audio_file = None
    custom_thumb_path = None
    script_txt_path = None
    link_txt_path = None
    title_txt_path = None
    article_txt_path = None

    for f in sorted(all_files):
        f_path = os.path.join(MANUAL_DIR, f)
        if os.path.isdir(f_path):
            continue
        f_lower = f.lower()
        ext = f_lower.split('.')[-1]

        if any(k in f_lower for k in ["thumbnail", "thumb"]) and ext in ['jpg', 'jpeg', 'png', 'webp']:
            custom_thumb_path = f_path
            continue
        elif ext in ['jpg', 'jpeg', 'png', 'webp']:
            img_files.append(f_path)
        elif ext in ['mp3', 'wav', 'm4a', 'aac']:
            custom_audio_file = f_path
        elif f_lower == "script.txt":
            script_txt_path = f_path
        elif f_lower == "link.txt":
            link_txt_path = f_path
        elif f_lower == "title.txt":
            title_txt_path = f_path
        elif f_lower == "article.txt":
            article_txt_path = f_path

    article_link = ""
    scraped_title = ""
    article_text = ""

    if link_txt_path and os.path.exists(link_txt_path):
        try:
            with open(link_txt_path, "r", encoding="utf-8") as lf:
                article_link = lf.read().strip()
            if article_link:
                scraped_title, article_text, img_urls = scrape_article_content_and_images(article_link)
                if not img_files and img_urls:
                    for idx, s_url in enumerate(img_urls[:5], start=1):
                        save_p = os.path.join(MANUAL_DIR, f"{idx}.jpg")
                        if download_image(s_url, save_p, referer_url=article_link):
                            img_files.append(save_p)
        except Exception as e:
            print(f"⚠️ Notice on link processing: {e}")

    if not article_text and article_txt_path and os.path.exists(article_txt_path):
        try:
            with open(article_txt_path, "r", encoding="utf-8") as af:
                article_text = af.read().strip()
        except Exception:
            pass

    video_title = "নিয়োগ বিজ্ঞপ্তি"
    if title_txt_path and os.path.exists(title_txt_path):
        try:
            with open(title_txt_path, "r", encoding="utf-8") as tf:
                video_title = tf.read().strip()
        except Exception:
            pass
    elif scraped_title:
        video_title = scraped_title

    user_provided_script = ""
    if script_txt_path and os.path.exists(script_txt_path):
        print("📄 [FOUND script.txt] Using user's custom script directly!")
        try:
            with open(script_txt_path, "r", encoding="utf-8") as sf:
                user_provided_script = sf.read().strip()
        except Exception:
            pass

    # ছবি এবং টেক্সট কোনোটিই না থাকলে বাতিল
    if not img_files and not article_text and not user_provided_script:
        print("❌ Neither circular images nor article text available. Aborting manual job.")
        return None

    use_motion = (len(img_files) == 0)
    thumb_meta = {}
    video_desc = ""
    video_tags = DEFAULT_BASE_TAGS
    voiceover_script = ""
    verified_data = {}
    script_segments = None

    if user_provided_script:
        cleaned_user_script = clean_script_for_speech(user_provided_script)
        voiceover_script = convert_all_numbers_in_script(cleaned_user_script)
        try:
            verified_data = extract_verified_job_data(video_title, article_text or user_provided_script, img_paths=img_files or None) or {
                "organization": video_title[:35],
                "org_short": " ".join(video_title.split()[:4]),
                "job_category": "সরকারি চাকরি",
                "total_vacancies": "",
                "posts": [{"post_name": "বিভিন্ন পদে নিয়োগ", "vacancy_count": "বিজ্ঞপ্তি অনুযায়ী", "salary_scale": "নির্ধারিত স্কেল", "educational_qualification": "বিজ্ঞপ্তি অনুযায়ী", "application_fee": "বিজ্ঞপ্তি অনুযায়ী", "key_duties": "সংশ্লিষ্ট দায়িত্ব পালন"}],
            }
            seo = generate_seo_metadata(verified_data, video_title)
            if seo:
                video_desc = seo.get("video_description", video_title)
                video_tags = sanitize_youtube_tags(seo.get("specific_tags", []) + DEFAULT_BASE_TAGS)
            thumb = generate_thumbnail_metadata(verified_data, video_title)
            if thumb:
                thumb_meta = thumb
        except Exception:
            pass
    else:
        print("🤖 [ARTICLE TEXT MODE] Generating accurate segmented script & structured data...")
        source_text = article_text if article_text else video_title
        ai_res = generate_job_content_with_data(video_title, source_text, img_files if img_files else None)
        opt_title, voiceover_script, thumb_meta, video_desc, video_tags, verified_data = ai_res
        if opt_title:
            video_title = opt_title
        if isinstance(verified_data, dict):
            script_segments = verified_data.get("script_segments")

    if not voiceover_script and not custom_audio_file:
        print("❌ Failed to obtain voiceover script or audio.")
        return None

    return {
        "folder_id": folder_id,
        "video_title": video_title,
        "voiceover_script": voiceover_script,
        "script_segments": script_segments,
        "thumb_meta": thumb_meta,
        "video_desc": video_desc,
        "video_tags": video_tags,
        "verified_data": verified_data,
        "use_motion_graphics": use_motion,
        "img_files": img_files,
        "custom_thumb_path": custom_thumb_path,
        "custom_audio_file": custom_audio_file,
    }


def finalize_manual_drive_job(yt, job, audio_path):
    """ধাপ ৩: প্রস্তুত হওয়া অডিও ও টাইমস্ট্যাম্প দিয়ে স্লাইডশো অথবা মোশন গ্রাফিক্স ভিডিও রেন্ডার ও আপলোড"""
    if not job or not audio_path or not os.path.exists(audio_path):
        return

    os.makedirs(TMP_DIR, exist_ok=True)
    video_title = job["video_title"]
    thumbnail_path = os.path.join(TMP_DIR, "manual_thumbnail.jpg")
    if os.path.exists(thumbnail_path):
        os.remove(thumbnail_path)

    custom_thumb_path = job["custom_thumb_path"]
    if custom_thumb_path and os.path.exists(custom_thumb_path):
        print(f"🖼️ [CUSTOM THUMBNAIL] Using '{os.path.basename(custom_thumb_path)}' directly.")
        with Image.open(custom_thumb_path) as c_thumb:
            c_thumb.convert("RGB").save(thumbnail_path, "JPEG", quality=100, subsampling=0)
    else:
        generate_dynamic_thumbnail(video_title, thumbnail_path, thumb_meta=job["thumb_meta"])

    out_video_file = os.path.join(TMP_DIR, "manual_out.mp4")
    if os.path.exists(out_video_file):
        os.remove(out_video_file)

    segment_timings = _load_segment_timings(audio_path)

    if job.get("use_motion_graphics"):
        render_motion_video(
            job.get("verified_data", {}), job.get("voiceover_script", ""),
            video_title, audio_path, out_video_file, is_vertical=False, segment_timings=segment_timings
        )
    else:
        render_video_slideshow(audio_path, job["img_files"], out_video_file, is_vertical=False)

    upload_success = upload_to_youtube(
        yt, out_video_file, video_title,
        thumbnail_path if os.path.exists(thumbnail_path) else None,
        description=job["video_desc"], tags=job["video_tags"], schedule_upload=True
    )

    if upload_success:
        try:
            os.makedirs(LIVESTREAM_DIR, exist_ok=True)
            safe_name = clean_filename(video_title)[:40].strip()
            live_video_file = os.path.join(LIVESTREAM_DIR, f"{safe_name}.mp4")
            if job.get("use_motion_graphics"):
                render_motion_video(
                    job.get("verified_data", {}), job.get("voiceover_script", ""),
                    video_title, audio_path, live_video_file, is_vertical=True, segment_timings=segment_timings
                )
            else:
                render_video_slideshow(audio_path, job["img_files"], live_video_file, is_vertical=True)
        except Exception:
            pass

        clean_manual_folder_on_drive(job["folder_id"])
        shutil.rmtree(MANUAL_DIR, ignore_errors=True)
        print("🎉 [SUCCESS] Manual Video Uploaded & Google Drive Emptied!\n")


def process_manual_drive_folder(yt):
    job = prepare_manual_drive_job()
    if not job:
        return
    audio_path = job["custom_audio_file"]
    if not audio_path:
        os.makedirs(TMP_DIR, exist_ok=True)
        audio_path = os.path.join(TMP_DIR, "manual_voiceover.wav")
        if not generate_voiceover_audio_pipeline(
            job["voiceover_script"],
            audio_path,
            segments=job.get("script_segments") if job.get("use_motion_graphics") else None,
            timings_output_path=audio_path + ".timings.json",
        ):
            return
    finalize_manual_drive_job(yt, job, audio_path)
