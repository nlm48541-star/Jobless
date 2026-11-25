# -*- coding: utf-8 -*-
import json
import os
import re
import shutil
import subprocess
import time
import unicodedata
from pathlib import Path

os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "300"

_NINADA_INSTANCE = None

PHONE_DIGIT_WORDS = {
    '0': "জিরো", '1': "ওয়ান", '2': "টু", '3': "থ্রি", '4': "ফোর",
    '5': "ফাইভ", '6': "সিক্স", '7': "সেভেন", '8': "এইট", '9': "নাইন"
}

BN_ORDINALS = {
    "১ম": "প্রথম", "২য়": "দ্বিতীয়", "২য়": "দ্বিতীয়",
    "৩য়": "তৃতীয়", "৩য়": "তৃতীয়", "৪র্থ": "চতুর্থ",
    "৫ম": "পঞ্চম", "৬ষ্ঠ": "ষষ্ঠ", "৭ম": "সপ্তম",
    "৮ম": "অষ্টম", "৯ম": "নবম", "১০ম": "দশম"
}

NUM_WORDS_1_TO_99 = {
    0: "শূন্য", 1: "এক", 2: "দুই", 3: "তিন", 4: "চার", 5: "পাঁচ", 6: "ছয়", 7: "সাত", 8: "আট", 9: "নয়",
    10: "দশ", 11: "এগারো", 12: "বারো", 13: "তেরো", 14: "চৌদ্দ", 15: "পনেরো", 16: "ষোলো", 17: "সতেরো", 18: "আঠারো", 19: "উনিশ",
    20: "বিশ", 21: "একুশ", 22: "বাইশ", 23: "তেইশ", 24: "চব্বিশ", 25: "পঁচিশ", 26: "ছাব্বিশ", 27: "সাতাশ", 28: "আঠাশ", 29: "উনত্রিশ",
    30: "ত্রিশ", 31: "একত্রিশ", 32: "বত্রিশ", 33: "তেত্রিশ", 34: "চৌত্রিশ", 35: "পঁয়ত্রিশ", 36: "ছত্রিশ", 37: "সাঁইত্রিশ", 38: "আটত্রিশ", 39: "উনচল্লিশ",
    40: "চল্লিশ", 41: "একচল্লিশ", 42: "বিয়াল্লিশ", 43: "তেতাল্লিশ", 44: "চুয়াল্লিশ", 45: "পঁয়তাল্লিশ", 46: "ছেচল্লিশ", 47: "সাতচল্লিশ", 48: "আটচল্লিশ", 49: "উনপঞ্চাশ",
    50: "পঞ্চাশ", 51: "একান্ন", 52: "বায়ান্ন", 53: "তিপ্পান্ন", 54: "চুয়ান্ন", 55: "পঞ্চান্ন", 56: "ছাপ্পান্ন", 57: "সাতান্ন", 58: "আটান্ন", 59: "উনষাট",
    60: "ষাট", 61: "একষট্টি", 62: "বাষট্টি", 63: "তেষট্টি", 64: "চৌষট্টি", 65: "পঁয়ষট্টি", 66: "ছেষট্টি", 67: "সাতষট্টি", 68: "আটষট্টি", 69: "উনসত্তর",
    70: "সত্তর", 71: "একাত্তর", 72: "বাহাত্তর", 73: "তিয়াত্তর", 74: "চৌহাত্তর", 75: "পঁচাত্তর", 76: "ছিয়াত্তর", 77: "সাতাত্তর", 78: "আটাত্তর", 79: "উনাশি",
    80: "আশি", 81: "একাশি", 82: "বিরাশি", 83: "তিরাশি", 84: "চুরাশি", 85: "পঁচাশি", 86: "ছিয়াশি", 87: "সাতাশি", 88: "অষ্টআশি", 89: "ঊননব্বই",
    90: "নব্বই", 91: "একানব্বই", 92: "বানব্বই", 93: "তিরানব্বই", 94: "চুরানব্বই", 95: "পঁচানব্বই", 96: "ছিয়ানব্বই", 97: "সাতানব্বই", 98: "আটানব্বই", 99: "নিরানব্বই"
}

COMMON_ENG_TO_BN = {
    "whatsapp": "হোয়াটসঅ্যাপ", "ssc": "এসএসসি", "hsc": "এইচএসসি",
    "bsc": "বিএসসি", "msc": "এমএসসি", "bba": "বিবিএ", "mba": "এমবিএ",
    "cgpa": "সিজিপিএ", "gpa": "জিপিএ", "ngo": "এনজিও", "pdf": "পিডিএফ",
    "online": "অনলাইন", "email": "ইমেইল", "circular": "সার্কুলার",
    "job": "জব", "bank": "ব্যাংক", "diploma": "ডিপ্লোমা",
    "sms": "এসএমএস", "cv": "সিভি", "nid": "এনআইডি",
    "bepza": "বেপজা", "biwtc": "বিআইডব্লিউটিসি", "bcs": "বিসিএস",
    "brta": "বিআরটিএ", "bmet": "বিএমইটি", "pwd": "পিডব্লিউডি",
    "desco": "ডেসকো", "bpdb": "বিপিডিবি", "pgcb": "পিজিসিবি",
    "reb": "আরইবি", "ntrca": "এনটিআরসিএ", "dpe": "ডিপিই",
    "lgd": "এলজিডি", "hr": "এইচআর", "it": "আইটি",
    "ltd": "লিমিটেড", "limited": "লিমিটেড", "tax": "ট্যাক্স",
    "grade": "গ্রেড", "post": "পোস্ট", "office": "অফিস",
    "dhaka": "ঢাকা", "bogra": "বগুড়া", "bd": "বিডি"
}


def int_to_bangla_words(n):
    if n in NUM_WORDS_1_TO_99:
        return NUM_WORDS_1_TO_99[n]
    parts = []
    if n >= 10000000:
        parts.append(int_to_bangla_words(n // 10000000) + " কোটি")
        n %= 10000000
    if n >= 100000:
        parts.append(int_to_bangla_words(n // 100000) + " লক্ষ")
        n %= 100000
    if n >= 1000:
        parts.append(int_to_bangla_words(n // 1000) + " হাজার")
        n %= 1000
    if n >= 100:
        h = n // 100
        n %= 100
        parts.append("একশত" if h == 1 else (int_to_bangla_words(h) + " শত"))
    if n > 0:
        parts.append(NUM_WORDS_1_TO_99.get(n, str(n)))
    return " ".join(parts)


def convert_all_numbers_to_bangla_words(text):
    if not text:
        return ""
    text = unicodedata.normalize("NFC", str(text))
    bn_to_en = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

    text = re.sub(r'(?<=[0-9০-৯]),(?=[0-9০-৯])', '', text)

    def phone_replacer(match):
        raw_num = match.group(0)
        digits = [d for d in raw_num.translate(bn_to_en) if d.isdigit()]
        if "".join(digits).startswith("8801"):
            digits = digits[2:]
        return " ".join([PHONE_DIGIT_WORDS.get(d, d) for d in digits])

    text = re.sub(r'(?:\+?88)?[\s\-]?(?:01|০১)[\d০-৯]{3,4}[-\s]?[\d০-৯]{5,6}', phone_replacer, text)

    text = re.sub(r'([0-9০-৯]+)\s*(?:/=|/-|৳)(?:\s*টাকা)?', r'\1 টাকা', text)
    text = re.sub(r'৳\s*([0-9০-৯]+)(?:\s*টাকা)?', r'\1 টাকা', text)
    text = re.sub(r'([0-9০-৯]+(?:\.[0-9০-৯]+)?)\s*%', r'\1 শতাংশ', text)
    text = re.sub(r'([0-9০-৯]+)\s*\+', r'\1 প্লাস', text)
    text = re.sub(r'([0-9০-৯]+)\s*[-–—]\s*([0-9০-৯]+)', r'\1 থেকে \2', text)

    ord_pat = "|".join(re.escape(k) for k in BN_ORDINALS)
    text = re.sub(
        rf'(?<![\u0980-\u09FF0-9০-৯])({ord_pat})(?![\u0980-\u09FF0-9০-৯])',
        lambda m: BN_ORDINALS.get(m.group(1), m.group(1)),
        text,
    )

    text = re.sub(r'([0-9০-৯]+)\s*নং(?=\s|[।,!?\)]|$)', r'\1 নম্বর', text)

    def tomo_replacer(match):
        try:
            return f"{int_to_bangla_words(int(match.group(1).translate(bn_to_en)))}তম"
        except Exception:
            return match.group(0)

    text = re.sub(r'([0-9০-৯]+)\s*তম', tomo_replacer, text)

    def dec_replacer(match):
        try:
            left = int_to_bangla_words(int(match.group(1).translate(bn_to_en)))
            right = " ".join(NUM_WORDS_1_TO_99.get(int(ch.translate(bn_to_en)), ch) for ch in match.group(2))
            return f"{left} দশমিক {right}"
        except Exception:
            return match.group(0)

    text = re.sub(r'([0-9০-৯]+)\.([0-9০-৯]+)', dec_replacer, text)

    def num_replacer(match):
        num_str = match.group(0)
        if len(num_str) > 10:
            return " ".join(NUM_WORDS_1_TO_99.get(int(ch.translate(bn_to_en)), ch) for ch in num_str)
        try:
            return int_to_bangla_words(int(num_str.translate(bn_to_en)))
        except Exception:
            return num_str

    text = re.sub(r'[\d০-৯]+', num_replacer, text)
    return text


def clean_script_for_speech(raw_text):
    if not raw_text:
        return ""
    text = unicodedata.normalize("NFC", str(raw_text))
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'[\u200b-\u200f\ufeff\u202a-\u202e\xa0]', ' ', text)
    for eng, bn in COMMON_ENG_TO_BN.items():
        text = re.sub(rf'\b{eng}\b', bn, text, flags=re.IGNORECASE)
    text = re.sub(r'https?://\S+|wa\.me/\S+', '', text)
    text = convert_all_numbers_to_bangla_words(text)
    text = re.sub(r'[\*\_\|\#\~\[\]\{\}\<\>\@\$\^\&\+\=\_\\\/\(\)]', ' ', text)
    # শুধুমাত্র বাংলা বর্ণমালা ও বিরামচিহ্ন রাখা (ইংরেজি অক্ষরে Ninada-র বিকৃতি দূর করে)
    text = re.sub(r'[^\u0980-\u09FF\s,।?!]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _get_ninada_tts():
    global _NINADA_INSTANCE
    if _NINADA_INSTANCE is None:
        from ninada import Ninada
        print("  [🎙️ Ninada TTS] Initializing Ninada v5 (lang='bn', voice='male')...")
        _NINADA_INSTANCE = Ninada(lang="bn")
    return _NINADA_INSTANCE


def _apply_ninada_tempo_and_mastering(raw_wav_path: Path, out_audio_path: Path):
    """Ninada-র কাঁচা অডিওতে স্বাভাবিক গতি (0.92x) ও স্টুডিও EQ/Compressor/Loudnorm মাস্টারিং"""
    if not shutil.which("ffmpeg"):
        shutil.copy2(raw_wav_path, out_audio_path)
        return

    af_chain = (
        "atempo=0.92,"
        "highpass=f=80,"
        "equalizer=f=250:t=q:w=1.2:g=2.5,"
        "equalizer=f=4500:t=q:w=1.5:g=-3.5,"
        "acompressor=threshold=-18dB:ratio=2.5:attack=10:release=100,"
        "loudnorm=I=-16:TP=-1.5:LRA=11"
    )
    cmd = ["ffmpeg", "-y", "-i", str(raw_wav_path), "-af", af_chain]
    if str(out_audio_path).lower().endswith(".mp3"):
        cmd.extend(["-c:a", "libmp3lame", "-b:a", "320k", "-ar", "44100", "-ac", "1"])
    else:
        cmd.extend(["-c:a", "pcm_s16le", "-ar", "24000", "-ac", "1"])
    cmd.append(str(out_audio_path))

    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode != 0 or not out_audio_path.exists() or out_audio_path.stat().st_size < 1000:
        shutil.copy2(raw_wav_path, out_audio_path)


def _finalize_kaggle_audio(raw_wav_path: Path, out_audio_path: Path):
    """Kaggle IndicF5 থেকে পাওয়া WAV-কে স্টুডিও মাস্টারিং ও PCM_16 WAV / 320k MP3 ফরম্যাটে সেভ করে"""
    out_audio_path.parent.mkdir(parents=True, exist_ok=True)
    if not shutil.which("ffmpeg"):
        shutil.copy2(raw_wav_path, out_audio_path)
        return

    af_chain = (
        "highpass=f=75,"
        "equalizer=f=220:t=q:w=1.2:g=1.8,"
        "equalizer=f=6000:t=q:w=1.5:g=-1.5,"
        "acompressor=threshold=-20dB:ratio=2.2:attack=10:release=120,"
        "loudnorm=I=-14:TP=-1.0:LRA=9"
    )
    is_mp3 = str(out_audio_path).lower().endswith(".mp3")

    cmd = ["ffmpeg", "-y", "-i", str(raw_wav_path), "-af", af_chain]
    if is_mp3:
        cmd.extend(["-c:a", "libmp3lame", "-b:a", "320k", "-ar", "44100", "-ac", "1"])
    else:
        cmd.extend(["-c:a", "pcm_s16le", "-ar", "24000", "-ac", "1"])
    cmd.append(str(out_audio_path))

    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode != 0 or not out_audio_path.exists() or out_audio_path.stat().st_size < 1000:
        if is_mp3:
            fallback_cmd = [
                "ffmpeg", "-y", "-i", str(raw_wav_path),
                "-c:a", "libmp3lame", "-b:a", "320k", "-ar", "44100", "-ac", "1",
                str(out_audio_path),
            ]
            subprocess.run(fallback_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            shutil.copy2(raw_wav_path, out_audio_path)


def _ninada_render_text_to_mastered_wav(tts, speech_text, raw_wav_path: Path, out_wav_path: Path):
    """একটি সম্পূর্ণ অংশ/সেগমেন্টকে Ninada-র নিজস্ব স্মুথ সিন্থেসিস + স্টুডিও মাস্টারিং দিয়ে তৈরি করে"""
    import numpy as np
    import soundfile as sf

    wav_bytes = None
    try:
        wav_bytes = tts.speak(speech_text, lang="bn", voice="male")
    except Exception:
        wav_bytes = None

    if wav_bytes and len(wav_bytes) > 2000:
        raw_wav_path.write_bytes(wav_bytes)
    else:
        sentences = [s.strip() for s in re.split(r'(?<=[।!?])\s+', speech_text) if len(s.strip()) > 3]
        if not sentences:
            sentences = [speech_text]

        chunks_pcm = []
        sr = 24000
        pause = np.zeros(int(sr * 0.25), dtype=np.float32)

        for idx, s in enumerate(sentences):
            b = tts.speak(s, lang="bn", voice="male")
            if b and len(b) > 1000:
                c_wav = out_wav_path.with_suffix(f".nchunk_{idx}.wav")
                c_wav.write_bytes(b)
                data, c_sr = sf.read(str(c_wav), dtype="float32")
                sr = c_sr
                if c_wav.exists():
                    c_wav.unlink()
                chunks_pcm.append(np.asarray(data, dtype=np.float32).reshape(-1))
                if idx < len(sentences) - 1:
                    chunks_pcm.append(pause)

        if not chunks_pcm:
            return False
        merged = np.concatenate(chunks_pcm) if len(chunks_pcm) > 1 else chunks_pcm[0]
        sf.write(str(raw_wav_path), merged, sr, subtype="PCM_16")

    _apply_ninada_tempo_and_mastering(raw_wav_path, out_wav_path)
    return out_wav_path.exists() and out_wav_path.stat().st_size > 1000


def synthesize_with_ninada_fallback(speech_text, output_audio_path, segments=None, timings_output_path=None):
    """
    🌟 ব্যাকআপ অডিও ইঞ্জিন: Ninada v5 (Male) + স্টুডিও মাস্টারিং
    সরাসরি GitHub Actions CPU-তে পরিষ্কার বাংলা ও স্টুডিও EQ সহ অডিও + নির্ভুল timings.json তৈরি করে।
    """
    print("\n--- [BACKUP AUDIO] Ninada v5 (Male | Mastered + atempo=0.92) ---")
    if not speech_text and not segments:
        return False

    out_wav = Path(output_audio_path).resolve()
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    tmp_files = []

    for attempt in range(3):
        try:
            import numpy as np
            import soundfile as sf

            tts = _get_ninada_tts()
            start_t = time.time()

            if segments and isinstance(segments, list):
                sr_final = 24000
                inter_pause = np.zeros(int(sr_final * 0.28), dtype=np.float32)
                seg_arrays = []
                seg_timings = []
                cursor_samples = 0
                total_segs = len(segments)

                for s_idx, seg in enumerate(segments):
                    seg_id = str(seg.get("id", f"seg_{s_idx}"))
                    seg_text = clean_script_for_speech(seg.get("text", ""))
                    seg_raw = out_wav.with_name(f"{out_wav.stem}_s{s_idx:03d}_raw.wav")
                    seg_mastered = out_wav.with_name(f"{out_wav.stem}_s{s_idx:03d}_master.wav")
                    tmp_files.extend([seg_raw, seg_mastered])

                    seg_arr = None
                    if seg_text and _ninada_render_text_to_mastered_wav(tts, seg_text, seg_raw, seg_mastered):
                        data, d_sr = sf.read(str(seg_mastered), dtype="float32")
                        if int(d_sr) == sr_final and len(data) > 0:
                            seg_arr = np.asarray(data, dtype=np.float32).reshape(-1)

                    if seg_arr is None or len(seg_arr) == 0:
                        seg_arr = np.zeros(int(sr_final * 0.5), dtype=np.float32)

                    seg_start = cursor_samples / float(sr_final)
                    seg_arrays.append(seg_arr)
                    cursor_samples += len(seg_arr)

                    if s_idx < total_segs - 1:
                        seg_arrays.append(inter_pause)
                        cursor_samples += len(inter_pause)

                    seg_end = cursor_samples / float(sr_final)
                    seg_timings.append({
                        "id": seg_id,
                        "start": round(seg_start, 4),
                        "end": round(seg_end, 4),
                        "duration": round(seg_end - seg_start, 4),
                    })

                merged_all = np.concatenate(seg_arrays) if len(seg_arrays) > 1 else seg_arrays[0]
                sf.write(str(out_wav), merged_all, sr_final, subtype="PCM_16")

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
                if not _ninada_render_text_to_mastered_wav(tts, speech_text, tmp_wav, out_wav):
                    raise RuntimeError("Ninada returned empty audio")

            if out_wav.exists() and out_wav.stat().st_size > 1000:
                audio_mb = round(out_wav.stat().st_size / (1024 * 1024), 2)
                dur = round(time.time() - start_t, 2)
                print(f"  ✅ [Ninada Backup SUCCESS] Mastered audio ready! ({audio_mb} MB in {dur}s)")
                return True

        except Exception as e:
            print(f"  ⚠️ [Ninada Attempt #{attempt+1}] {e}")
            time.sleep(1.5)
        finally:
            for tf in tmp_files:
                try:
                    if Path(tf).exists():
                        Path(tf).unlink()
                except Exception:
                    pass
            tmp_files = []

    return False


def synthesize_with_ninada(speech_text, output_audio_path):
    return synthesize_with_ninada_fallback(speech_text, output_audio_path)


def generate_voiceover_batch_pipeline(batch_items, batch_work_dir):
    """
    ১. প্রাইমারি: Kaggle IndicF5_Bangladeshi (সব অডিও ও সেগমেন্ট মাত্র ১টি ব্যাচ রিকোয়েস্টে ডুয়াল-T4 GPU-তে, nfe_step=64)
    ২. ব্যাকআপ: Ninada v5 Male (স্টুডিও মাস্টার্ড — Kaggle অফলাইন বা ব্যর্থ হলে GitHub Actions CPU-তে)
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
    print("🎙️ [AUDIO ENGINE] Primary: Kaggle IndicF5_Bangladeshi (nfe=64) | Backup: Ninada v5 (Mastered)")
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
            dst = Path(t["target_path"]).resolve()
            if src and Path(src).exists() and Path(src).stat().st_size > 1000:
                _finalize_kaggle_audio(Path(src), dst)
                try:
                    Path(src).unlink()
                except Exception:
                    pass
                if dst.exists() and dst.stat().st_size > 1000:
                    results[t["filename"]] = str(dst)
                    print(f"  🎵 Mastered & Saved '{t['filename']}' -> {dst}")

                    src_timings = Path(batch_work_dir) / t["timings_filename"]
                    if src_timings.exists():
                        t_dst = Path(t["timings_target_path"])
                        t_dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(src_timings), str(t_dst))
                        print(f"  ⏱️ Saved segment timings -> {t_dst}")

        if len(results) == len(cleaned_tasks):
            return results
    except Exception as e:
        print(f"\n⚠️ [Kaggle TTS Failed] ({e}) — Switching to Ninada v5 (Mastered) backup...")

    # ২. ব্যাকআপ: Ninada v5 Male (Mastered)
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
