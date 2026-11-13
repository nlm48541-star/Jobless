# -*- coding: utf-8 -*-
import asyncio
import os
import re
import shutil
import subprocess
import time
from pathlib import Path


def clean_script_for_speech(raw_text):
    if not raw_text:
        return ""
    text = re.sub(r'[\*\_\|\#\~]', '', str(raw_text))
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'https?://\S+|wa\.me/\S+', '', text)
    text = re.sub(r'[\<\>\{\}\(\)\@\$\^\&\+\=\_\\\/]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def synthesize_with_edge_fallback(speech_text, output_audio_path):
    """ব্যাকআপ: Microsoft Edge TTS (bn-BD-PradeepNeural)"""
    print("\n--- [BACKUP AUDIO] Microsoft Edge TTS (bn-BD-PradeepNeural) ---")
    if not speech_text:
        return False

    raw_mp3 = str(output_audio_path) + ".edge.mp3"
    try:
        import edge_tts

        voice_name = os.environ.get("EDGE_TTS_VOICE", "bn-BD-PradeepNeural").strip() or "bn-BD-PradeepNeural"
        start_t = time.time()

        async def _make():
            communicate = edge_tts.Communicate(speech_text, voice_name, rate="+0%", pitch="+0Hz")
            await communicate.save(raw_mp3)

        asyncio.run(_make())

        if os.path.exists(raw_mp3) and os.path.getsize(raw_mp3) > 1000:
            if str(output_audio_path).lower().endswith(".wav") and shutil.which("ffmpeg"):
                subprocess.run(
                    ["ffmpeg", "-y", "-i", raw_mp3, "-ar", "24000", "-ac", "1", str(output_audio_path)],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                os.remove(raw_mp3)
            else:
                os.replace(raw_mp3, output_audio_path)

            audio_mb = round(os.path.getsize(output_audio_path) / (1024 * 1024), 2)
            print(f"  ✅ [SUCCESS] Generated via Edge TTS Backup! ({audio_mb} MB in {round(time.time() - start_t, 2)}s)")
            return True
    except Exception as e:
        print(f"  ⚠️ Edge TTS backup failed: {e}")
    finally:
        if os.path.exists(raw_mp3):
            try:
                os.remove(raw_mp3)
            except Exception:
                pass

    return False


def generate_voiceover_batch_pipeline(batch_items, batch_work_dir):
    """
    ১. প্রাইমারি: Kaggle IndicF5_Bangladeshi (সবগুলো অডিও মাত্র ১টি ব্যাচ রিকোয়েস্টে)
    ২. ব্যাকআপ: Microsoft Edge TTS (যদি কোনো কারণে Kaggle ব্যর্থ হয়)
    """
    if not batch_items:
        return {}

    os.makedirs(batch_work_dir, exist_ok=True)
    cleaned_tasks = []
    for item in batch_items:
        sp_text = clean_script_for_speech(item["text"])
        cleaned_tasks.append({
            "filename": item["filename"],
            "text": sp_text,
            "target_path": item["target_path"],
        })

    print("\n" + "=" * 65)
    print("🎙️ [AUDIO ENGINE] Primary: Kaggle IndicF5_Bangladeshi | Backup: Edge TTS")
    print(f"📦 Total Scripts Queued: {len(cleaned_tasks)}")
    for idx, t in enumerate(cleaned_tasks, 1):
        print(f"  #{idx}: {t['filename']} | {len(t['text'].split())} words | {len(t['text'])} chars")
    print("=" * 65)

    results = {}

    # ১. প্রাইমারি: Kaggle IndicF5_Bangladeshi (১ বারের ব্যাচ রিকোয়েস্ট)
    try:
        from kaggle_tts import generate_voices_batch
        default_voice = os.environ.get("KAGGLE_DEFAULT_VOICE", "male").strip().lower()
        generated_map = generate_voices_batch(
            tasks=[{"filename": t["filename"], "text": t["text"]} for t in cleaned_tasks],
            output_dir=batch_work_dir,
            default_voice=default_voice,
        )
        for t in cleaned_tasks:
            src = generated_map.get(t["filename"])
            dst = Path(t["target_path"])
            if src and Path(src).exists() and Path(src).stat().st_size > 1000:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                results[t["filename"]] = str(dst)
                print(f"  🎵 Saved '{t['filename']}' -> {dst}")

        if len(results) == len(cleaned_tasks):
            return results
    except Exception as e:
        print(f"\n⚠️ [Kaggle TTS Failed] ({e}) — Switching to Microsoft Edge TTS backup...")

    # ২. ব্যাকআপ: শুধু যেগুলো Kaggle থেকে আসেনি সেগুলোর জন্য Edge TTS
    for t in cleaned_tasks:
        if t["filename"] in results:
            continue
        dst = t["target_path"]
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        if synthesize_with_edge_fallback(t["text"], dst):
            if os.path.exists(dst) and os.path.getsize(dst) > 1000:
                results[t["filename"]] = dst

    return results


def generate_voiceover_audio_pipeline(text, output_audio_path):
    """একক অডিও জেনারেশনের হেল্পার ফাংশন"""
    fname = os.path.basename(output_audio_path)
    res = generate_voiceover_batch_pipeline(
        [{"filename": fname, "text": text, "target_path": output_audio_path}],
        batch_work_dir=os.path.join("temp_assets", "single_audio"),
    )
    return fname in res
