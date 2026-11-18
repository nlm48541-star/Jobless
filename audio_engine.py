# -*- coding: utf-8 -*-
import io
import os
import re
import shutil
import subprocess
import time
import wave
from pathlib import Path


def clean_script_for_speech(raw_text):
    if not raw_text:
        return ""
    text = re.sub(r'<think>.*?</think>', '', str(raw_text), flags=re.DOTALL)
    # অদৃশ্য ইউনিকোড চিহ্ন দূর করা
    text = re.sub(r'[\u200b-\u200f\ufeff\u202a-\u202e\xa0]', ' ', text)
    text = re.sub(r'[\*\_\|\#\~`]', '', text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'https?://\S+|wa\.me/\S+', '', text)
    text = re.sub(r'[\<\>\{\}\(\)\@\$\^\&\+\=\_\\\/]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def split_text_into_chunks(text, max_chars=320):
    """লম্বা স্ক্রিপ্টকে দাঁড়ি ও চিহ্নের ভিত্তিতে নিরাপদ অংশে ভাগ করে যাতে মডেলে কোনো মেমোরি বা লেন্থ এরর না হয়"""
    raw_parts = re.split(r'([।\?\!\n]+)', str(text))
    chunks = []
    current = ""
    for p in raw_parts:
        current += p
        if any(sym in p for sym in ['।', '?', '!', '\n']) or len(current) >= max_chars:
            if current.strip():
                chunks.append(current.strip())
            current = ""
    if current.strip():
        chunks.append(current.strip())
    return chunks or [text]


def combine_wav_bytes(wav_bytes_list):
    """একাধিক WAV অডিও বাইটকে জোড়া লাগিয়ে একটি পূর্ণাঙ্গ একক WAV বাইটে রূপান্তর করে"""
    if not wav_bytes_list:
        return b""
    if len(wav_bytes_list) == 1:
        return wav_bytes_list[0]

    out_buf = io.BytesIO()
    with wave.open(io.BytesIO(wav_bytes_list[0]), 'rb') as first_wav:
        params = first_wav.getparams()
        with wave.open(out_buf, 'wb') as merged_wav:
            merged_wav.setparams(params)
            merged_wav.writeframes(first_wav.readframes(first_wav.getnframes()))
            for wb in wav_bytes_list[1:]:
                with wave.open(io.BytesIO(wb), 'rb') as w:
                    merged_wav.writeframes(w.readframes(w.getnframes()))
    return out_buf.getvalue()


def synthesize_with_ninada_fallback(speech_text, output_audio_path):
    """
    🌟 ব্যাকআপ অডিও ইঞ্জিন: Ninada v5.1.2 (Male)
    সরাসরি GitHub Actions CPU-তে সম্পূর্ণ ওপেন-সোর্স লোকাল জেনারেশন + FFmpeg atempo=0.92 স্বাভাবিক গতি
    """
    print("\n--- [BACKUP AUDIO] Ninada v5.1.2 (Male | atempo=0.92) ---")
    if not speech_text:
        return False

    out_wav = Path(output_audio_path).resolve()
    tmp_wav = out_wav.with_suffix(".ninada_raw.wav")

    try:
        from ninada import Ninada

        start_t = time.time()
        tts = Ninada(lang="bn")

        # বড় স্ক্রিপ্ট নিরাপদে চালানোর জন্য চাঙ্কিং
        chunks = split_text_into_chunks(speech_text, max_chars=300)
        wav_chunks = []

        for ch in chunks:
            ch_clean = ch.strip()
            if not ch_clean:
                continue
            ch_bytes = tts.speak(ch_clean, lang="bn", voice="male")
            if ch_bytes and len(ch_bytes) > 200:
                wav_chunks.append(ch_bytes)

        if not wav_chunks:
            print("  ⚠️ Ninada থেকে কোনো অডিও আসেনি।")
            return False

        merged_wav_bytes = combine_wav_bytes(wav_chunks)
        with open(tmp_wav, "wb") as f:
            f.write(merged_wav_bytes)

        # FFmpeg দিয়ে স্বাভাবিক প্রমিত গতি (atempo=0.92) ও স্ট্যান্ডার্ড ২৪ kHz PCM_16 ফরম্যাট নিশ্চিত করা
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(tmp_wav),
                "-filter:a", "atempo=0.92",
                "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le",
                str(out_wav)
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

        if tmp_wav.exists():
            tmp_wav.unlink()

        if out_wav.exists() and out_wav.stat().st_size > 1000:
            audio_mb = round(out_wav.stat().st_size / (1024 * 1024), 2)
            dur = round(time.time() - start_t, 2)
            print(f"  ✅ [SUCCESS] Generated via Ninada Male Backup! ({audio_mb} MB in {dur}s)")
            return True

    except Exception as e:
        print(f"  ⚠️ Ninada backup failed: {e}")
        if tmp_wav.exists():
            try:
                tmp_wav.unlink()
            except Exception:
                pass

    return False


def generate_voiceover_batch_pipeline(batch_items, batch_work_dir):
    """
    ১. প্রাইমারি: Kaggle IndicF5_Bangladeshi (সব অডিও মাত্র ১টি ব্যাচ রিকোয়েস্টে ডুয়াল-T4 GPU-তে)
    ২. ব্যাকআপ: Ninada v5.1.2 Male (Kaggle অফলাইন বা ব্যর্থ হলে সরাসরি GitHub Actions CPU-তে)
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
    print("🎙️ [AUDIO ENGINE] Primary: Kaggle IndicF5_Bangladeshi | Backup: Ninada v5.1.2 (Male)")
    print(f"📦 Total Scripts Queued: {len(cleaned_tasks)}")
    for idx, t in enumerate(cleaned_tasks, 1):
        print(f"  #{idx}: {t['filename']} | {len(t['text'].split())} words | {len(t['text'])} chars")
    print("=" * 65)

    results = {}

    # ১. প্রাইমারি: Kaggle IndicF5_Bangladeshi (১ বারের ব্যাচ রিকোয়েস্ট, speed=0.93, nfe_step=16)
    try:
        from kaggle_tts import generate_voices_batch
        default_voice = os.environ.get("KAGGLE_DEFAULT_VOICE", "male").strip().lower()
        speech_speed = float(os.environ.get("KAGGLE_SPEECH_SPEED", "0.93"))
        nfe_step = int(os.environ.get("KAGGLE_NFE_STEP", "16"))
        generated_map = generate_voices_batch(
            tasks=[{"filename": t["filename"], "text": t["text"]} for t in cleaned_tasks],
            output_dir=batch_work_dir,
            default_voice=default_voice,
            speech_speed=speech_speed,
            nfe_step=nfe_step,
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
        print(f"\n⚠️ [Kaggle TTS Failed] ({e}) — Switching to Ninada v5.1.2 backup...")

    # ২. ব্যাকআপ: Kaggle থেকে যেগুলো তৈরি হয়নি, সেগুলোর জন্য Ninada v5.1.2 Male
    for t in cleaned_tasks:
        if t["filename"] in results:
            continue
        dst = t["target_path"]
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        if synthesize_with_ninada_fallback(t["text"], dst):
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
