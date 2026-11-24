# -*- coding: utf-8 -*-
import io
import json
import os
import re
import shutil
import subprocess
import time
import unicodedata
import wave
from pathlib import Path


def clean_script_for_speech(raw_text):
    if not raw_text:
        return ""
    text = unicodedata.normalize("NFC", str(raw_text))
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
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


def _ninada_render_chunk_to_24k_wav(tts, text_str, raw_path, clean_path):
    chunks = split_text_into_chunks(text_str, max_chars=300)
    wav_chunks = []
    for ch in chunks:
        ch_clean = ch.strip()
        if not ch_clean:
            continue
        ch_bytes = tts.speak(ch_clean, lang="bn", voice="male")
        if ch_bytes and len(ch_bytes) > 200:
            wav_chunks.append(ch_bytes)

    if not wav_chunks:
        return False

    merged_wav_bytes = combine_wav_bytes(wav_chunks)
    with open(raw_path, "wb") as f:
        f.write(merged_wav_bytes)

    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(raw_path),
            "-filter:a", "atempo=0.92",
            "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le",
            str(clean_path)
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True
    )
    return clean_path.exists() and clean_path.stat().st_size > 100


def synthesize_with_ninada_fallback(speech_text, output_audio_path, segments=None, timings_output_path=None):
    """
    🌟 ব্যাকআপ অডিও ইঞ্জিন: Ninada v5.1.2 (Male)
    সরাসরি GitHub Actions CPU-তে সম্পূর্ণ ওপেন-সোর্স লোকাল জেনারেশন + FFmpeg atempo=0.92 স্বাভাবিক গতি।
    সেগমেন্ট দেওয়া থাকলে প্রতি সেগমেন্টের সঠিক দৈর্ঘ্য মাপাসহ timings.json তৈরি করে।
    """
    print("\n--- [BACKUP AUDIO] Ninada v5.1.2 (Male | atempo=0.92) ---")
    if not speech_text and not segments:
        return False

    out_wav = Path(output_audio_path).resolve()
    tmp_files = []

    try:
        from ninada import Ninada

        start_t = time.time()
        tts = Ninada(lang="bn")

        if segments and isinstance(segments, list):
            sr_final = 24000
            inter_pause_frames = b"\x00\x00" * int(sr_final * 0.28)
            inter_pause_samples = int(sr_final * 0.28)
            seg_pcm_list = []
            seg_timings = []
            cursor_samples = 0
            total_segs = len(segments)

            for s_idx, seg in enumerate(segments):
                seg_id = str(seg.get("id", f"seg_{s_idx}"))
                seg_text = clean_script_for_speech(seg.get("text", ""))
                seg_raw = out_wav.with_name(f"{out_wav.stem}_s{s_idx:03d}_raw.wav")
                seg_clean = out_wav.with_name(f"{out_wav.stem}_s{s_idx:03d}_24k.wav")
                tmp_files.extend([seg_raw, seg_clean])

                seg_frames = b""
                nframes = 0
                if seg_text and _ninada_render_chunk_to_24k_wav(tts, seg_text, seg_raw, seg_clean):
                    with wave.open(str(seg_clean), "rb") as w:
                        nframes = w.getnframes()
                        seg_frames = w.readframes(nframes)

                if nframes <= 0 or not seg_frames:
                    nframes = int(sr_final * 0.5)
                    seg_frames = b"\x00\x00" * nframes

                seg_start = cursor_samples / float(sr_final)
                seg_pcm_list.append(seg_frames)
                cursor_samples += nframes

                if s_idx < total_segs - 1:
                    seg_pcm_list.append(inter_pause_frames)
                    cursor_samples += inter_pause_samples

                seg_end = cursor_samples / float(sr_final)
                seg_timings.append({
                    "id": seg_id,
                    "start": round(seg_start, 4),
                    "end": round(seg_end, 4),
                    "duration": round(seg_end - seg_start, 4),
                })

            with wave.open(str(out_wav), "wb") as merged_out:
                merged_out.setnchannels(1)
                merged_out.setsampwidth(2)
                merged_out.setframerate(sr_final)
                for pcm in seg_pcm_list:
                    merged_out.writeframes(pcm)

            t_path = Path(timings_output_path) if timings_output_path else Path(str(out_wav) + ".timings.json")
            t_path.parent.mkdir(parents=True, exist_ok=True)
            t_path.write_text(
                json.dumps(
                    {
                        "sample_rate": sr_final,
                        "total_duration": round(cursor_samples / float(sr_final), 4),
                        "segments": seg_timings,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        else:
            tmp_wav = out_wav.with_suffix(".ninada_raw.wav")
            tmp_files.append(tmp_wav)
            if not _ninada_render_chunk_to_24k_wav(tts, speech_text, tmp_wav, out_wav):
                print("  ⚠️ Ninada থেকে কোনো অডিও আসেনি।")
                return False

        if out_wav.exists() and out_wav.stat().st_size > 1000:
            audio_mb = round(out_wav.stat().st_size / (1024 * 1024), 2)
            dur = round(time.time() - start_t, 2)
            print(f"  ✅ [SUCCESS] Generated via Ninada Male Backup! ({audio_mb} MB in {dur}s)")
            return True

    except Exception as e:
        print(f"  ⚠️ Ninada backup failed: {e}")
    finally:
        for tf in tmp_files:
            try:
                if Path(tf).exists():
                    Path(tf).unlink()
            except Exception:
                pass

    return False


def generate_voiceover_batch_pipeline(batch_items, batch_work_dir):
    """
    ১. প্রাইমারি: Kaggle IndicF5_Bangladeshi (সব অডিও ও সেগমেন্ট মাত্র ১টি ব্যাচ রিকোয়েস্টে ডুয়াল-T4 GPU-তে, nfe_step=64)
    ২. ব্যাকআপ: Ninada v5.1.2 Male (Kaggle অফলাইন বা ব্যর্থ হলে সরাসরি GitHub Actions CPU-তে)
    """
    if not batch_items:
        return {}

    os.makedirs(batch_work_dir, exist_ok=True)
    cleaned_tasks = []
    for item in batch_items:
        sp_text = clean_script_for_speech(item.get("text", ""))
        raw_segs = item.get("segments")
        cleaned_segs = None
        if raw_segs and isinstance(raw_segs, list):
            cleaned_segs = [
                {"id": str(s.get("id", f"seg_{idx}")), "text": clean_script_for_speech(s.get("text", ""))}
                for idx, s in enumerate(raw_segs)
            ]
            if not sp_text:
                sp_text = " ".join(s["text"] for s in cleaned_segs if s["text"])

        fname = item["filename"]
        timings_fname = f"{fname}.timings.json"
        timings_target = item.get("timings_target_path") or (item["target_path"] + ".timings.json")
        cleaned_tasks.append({
            "filename": fname,
            "text": sp_text,
            "segments": cleaned_segs,
            "timings_filename": timings_fname,
            "target_path": item["target_path"],
            "timings_target_path": timings_target,
        })

    print("\n" + "=" * 65)
    print("🎙️ [AUDIO ENGINE] Primary: Kaggle IndicF5_Bangladeshi | Backup: Ninada v5.1.2 (Male)")
    print(f"📦 Total Scripts Queued: {len(cleaned_tasks)}")
    for idx, t in enumerate(cleaned_tasks, 1):
        seg_info = f" | {len(t['segments'])} segments" if t["segments"] else ""
        print(f"  #{idx}: {t['filename']} | {len(t['text'].split())} words | {len(t['text'])} chars{seg_info}")
    print("=" * 65)

    results = {}

    # ১. প্রাইমারি: Kaggle IndicF5_Bangladeshi (nfe_step=64)
    try:
        from kaggle_tts import generate_voices_batch
        default_voice = os.environ.get("KAGGLE_DEFAULT_VOICE", "male").strip().lower()
        speech_speed = float(os.environ.get("KAGGLE_SPEECH_SPEED", "0.93"))
        nfe_step = int(os.environ.get("KAGGLE_NFE_STEP", "64"))

        kaggle_payload = []
        for t in cleaned_tasks:
            k_item = {"filename": t["filename"], "text": t["text"]}
            if t["segments"]:
                k_item["segments"] = t["segments"]
                k_item["timings_filename"] = t["timings_filename"]
            kaggle_payload.append(k_item)

        generated_map = generate_voices_batch(
            tasks=kaggle_payload,
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

                src_timings = Path(batch_work_dir) / t["timings_filename"]
                if src_timings.exists():
                    t_dst = Path(t["timings_target_path"])
                    t_dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src_timings), str(t_dst))
                    print(f"  ⏱️ Saved segment timings -> {t_dst}")

        if len(results) == len(cleaned_tasks):
            return results
    except Exception as e:
        print(f"\n⚠️ [Kaggle TTS Failed] ({e}) — Switching to Ninada v5.1.2 backup...")

    # ২. ব্যাকআপ: Ninada v5.1.2 Male
    for t in cleaned_tasks:
        if t["filename"] in results:
            continue
        dst = t["target_path"]
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        if synthesize_with_ninada_fallback(
            t["text"], dst,
            segments=t["segments"],
            timings_output_path=t["timings_target_path"],
        ):
            if os.path.exists(dst) and os.path.getsize(dst) > 1000:
                results[t["filename"]] = dst

    return results


def generate_voiceover_audio_pipeline(text, output_audio_path, segments=None, timings_output_path=None):
    """একক অডিও জেনারেশনের হেল্পার ফাংশন"""
    fname = os.path.basename(output_audio_path)
    res = generate_voiceover_batch_pipeline(
        [{
            "filename": fname,
            "text": text,
            "segments": segments,
            "target_path": output_audio_path,
            "timings_target_path": timings_output_path or (output_audio_path + ".timings.json"),
        }],
        batch_work_dir=os.path.join("temp_assets", "single_audio"),
    )
    return fname in res
