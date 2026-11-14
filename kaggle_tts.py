# -*- coding: utf-8 -*-
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

KAGGLE_USERNAME = os.environ.get("KAGGLE_USERNAME", "yusufadnan").strip() or "yusufadnan"
KERNEL_SLUG_BASE = "indicf5-tts-worker"
DATASET_SLUG = "yusufadnan/indicf5-bd-bundle"


def _run_kaggle(args: List[str], stdin_text: Optional[str] = None) -> str:
    if not os.environ.get("KAGGLE_API_TOKEN") and not (Path.home() / ".kaggle" / "kaggle.json").exists():
        raise RuntimeError("KAGGLE_API_TOKEN সেট করা নেই! GitHub Secrets-এ KAGGLE_API_TOKEN যোগ করুন।")
    cmd = [sys.executable, "-m", "kaggle", *args]
    proc = subprocess.run(
        cmd,
        input=stdin_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Kaggle CLI ত্রুটি ({' '.join(args)}):\n{proc.stdout}")
    return proc.stdout


def _delete_kernel_safely(kernel_id: str):
    """আটকে থাকা বা পুরনো জব ডিলিট করে GPU স্লট ফ্রি করে"""
    try:
        _run_kaggle(["kernels", "delete", kernel_id, "-y"], stdin_text="yes\n")
        print(f"🧹 [Kaggle Cleanup] Deleted kernel '{kernel_id}' to free GPU slot.")
        time.sleep(5)
    except Exception:
        pass


def _cleanup_stale_workers():
    """আগের কোনো রানে জব QUEUED হয়ে থাকলে সেটি পরিষ্কার করে"""
    for suffix in ("", "-r2", "-r3"):
        kid = f"{KAGGLE_USERNAME}/{KERNEL_SLUG_BASE}{suffix}"
        try:
            st = _run_kaggle(["kernels", "status", kid]).lower()
            if any(x in st for x in ("queued", "running", "error", "cancel")):
                _delete_kernel_safely(kid)
        except Exception:
            pass


def _find_repo_reference_voice() -> tuple[Optional[Path], str]:
    """রিপোজিটরির ref_voice/ ফোল্ডার থেকে কাস্টম রেফারেন্স অডিও ও টেক্সট খুঁজে বের করে"""
    env_audio = os.environ.get("KAGGLE_REF_AUDIO_PATH", "").strip()
    env_text = os.environ.get("KAGGLE_REF_TEXT", "").strip()
    if env_audio and Path(env_audio).exists() and env_text:
        return Path(env_audio), env_text

    ref_dir = Path("ref_voice")
    if ref_dir.exists():
        txt_file = ref_dir / "ref_text.txt"
        ref_txt = txt_file.read_text(encoding="utf-8").strip() if txt_file.exists() else ""
        for ext in ("wav", "mp3", "m4a", "ogg", "flac"):
            cand = ref_dir / f"ref.{ext}"
            if cand.exists() and ref_txt:
                return cand, ref_txt
        for f in sorted(ref_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in {".wav", ".mp3", ".m4a", ".ogg", ".flac"} and ref_txt:
                return f, ref_txt
    return None, ""


def _build_worker_script(
    tasks: List[Dict[str, str]],
    ref_audio_b64: str,
    ref_ext: str,
    ref_text: str,
    default_voice: str,
) -> str:
    tasks_json = json.dumps(tasks, ensure_ascii=False)
    ref_text_json = json.dumps(ref_text, ensure_ascii=False)

    return f'''import base64
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

os.environ["MPLBACKEND"] = "Agg"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# ১. প্রাইভেট ডাটাসেট পাথ খুঁজে বের করা
BUNDLE_DIR = None
for candidate in [
    Path("/kaggle/input/indicf5-bd-bundle"),
    Path("/kaggle/input/datasets/yusufadnan/indicf5-bd-bundle"),
]:
    if (candidate / "model_40000.pt").exists():
        BUNDLE_DIR = candidate
        break

if BUNDLE_DIR is None:
    for p in Path("/kaggle/input").rglob("model_40000.pt"):
        BUNDLE_DIR = p.parent
        break

if BUNDLE_DIR is None:
    raise FileNotFoundError("indicf5-bd-bundle ডাটাসেট পাওয়া যায়নি!")

# ২. অফলাইন wheels ইনস্টল
wheels = sorted(str(p) for p in (BUNDLE_DIR / "wheels").glob("*.whl"))
if wheels:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "--no-index", "--no-deps", *wheels],
        check=True,
    )

sys.path.insert(0, str(BUNDLE_DIR))

import numpy as np
import soundfile as sf
import torch
import torchaudio

def _patched_load(fp, **kw):
    d, sr = sf.read(str(fp), dtype="float32")
    d = d[np.newaxis, :] if d.ndim == 1 else d.T
    return torch.from_numpy(d), sr
torchaudio.load = _patched_load

from f5_tts.infer.utils_infer import (
    get_tokenizer,
    infer_process,
    load_vocoder,
    n_mel_channels,
    preprocess_ref_audio_text,
)
from f5_tts.model import CFM, DiT

TASKS = json.loads({json.dumps(tasks_json)})
REF_AUDIO_B64 = {json.dumps(ref_audio_b64)}
REF_EXT = {json.dumps(ref_ext)}
CUSTOM_REF_TEXT = json.loads({json.dumps(ref_text_json)})
DEFAULT_VOICE = {json.dumps(default_voice)}


def split_bengali_for_indicf5(text: str, max_chars: int = 160):
    """লম্বা বাংলা স্ক্রিপ্টকে বাংলা দাঁড়ি (।) অনুযায়ী নিরাপদ ছোট অংশে ভাগ করে"""
    text = re.sub(r"\\s+", " ", text).strip()
    if not text:
        return []
    raw_sents = [s.strip() for s in re.split(r"(?<=[।\\.\\?\\!\\n])\\s*", text) if s.strip()]
    pieces = []
    for s in raw_sents:
        if len(s) <= max_chars:
            pieces.append(s)
        else:
            sub_parts = [p.strip() for p in re.split(r"(?<=[,;—\\-])\\s*", s) if p.strip()]
            for sp in sub_parts:
                if len(sp) <= max_chars:
                    pieces.append(sp)
                else:
                    words = sp.split()
                    cur = ""
                    for w in words:
                        if len(cur) + len(w) + 1 <= max_chars:
                            cur = f"{{cur}} {{w}}".strip()
                        else:
                            if cur:
                                pieces.append(cur)
                            cur = w
                    if cur:
                        pieces.append(cur)

    merged = []
    buf = ""
    for p in pieces:
        if not buf:
            buf = p
        elif len(buf) + len(p) + 1 <= max_chars:
            buf = f"{{buf}} {{p}}"
        else:
            if len(buf) < 25:
                buf = f"{{buf}} {{p}}"
            else:
                merged.append(buf)
                buf = p
    if buf:
        if merged and len(buf) < 25 and len(merged[-1]) + len(buf) + 1 <= max_chars + 40:
            merged[-1] = f"{{merged[-1]}} {{buf}}"
        else:
            merged.append(buf)
    return merged


# ৩. রেফারেন্স অডিও সেটআপ
if REF_AUDIO_B64:
    raw_ref = Path(f"/tmp/custom_ref_raw{{REF_EXT}}")
    raw_ref.write_bytes(base64.b64decode(REF_AUDIO_B64))
    ref_wav = Path("/tmp/custom_ref_24k.wav")
    if shutil.which("ffmpeg"):
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(raw_ref), "-ar", "24000", "-ac", "1", str(ref_wav)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    else:
        from pydub import AudioSegment
        AudioSegment.from_file(str(raw_ref)).set_frame_rate(24000).set_channels(1).export(str(ref_wav), format="wav")
    ref_text = CUSTOM_REF_TEXT.strip()
else:
    voice_file = "ref_female.wav" if DEFAULT_VOICE == "female" else "ref_male.wav"
    ref_wav = BUNDLE_DIR / "ref_voice" / voice_file
    ref_text = (BUNDLE_DIR / "ref_voice" / "ref_text.txt").read_text(encoding="utf-8").strip()

# ৪. মডেল ও Vocos মাত্র ১ বার লোড করা
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {{device}} | Total Audio Jobs: {{len(TASKS)}}")

vmap, vsize = get_tokenizer(str(BUNDLE_DIR / "vocab.txt"), "custom")
model = CFM(
    transformer=DiT(
        dim=1024, depth=22, heads=16, ff_mult=2,
        text_dim=512, conv_layers=4, text_num_embeds=vsize, mel_dim=n_mel_channels,
    ),
    mel_spec_kwargs=dict(
        n_fft=1024, hop_length=256, win_length=1024,
        n_mel_channels=n_mel_channels, target_sample_rate=24000, mel_spec_type="vocos",
    ),
    odeint_kwargs=dict(method="euler"),
    vocab_char_map=vmap,
)

ckpt = torch.load(str(BUNDLE_DIR / "model_40000.pt"), map_location="cpu", weights_only=False)
raw_sd = ckpt.get("ema_model_state_dict", ckpt.get("model_state_dict", ckpt))
cleaned = {{
    (k[10:] if k.startswith("ema_model.") else (k[7:] if k.startswith("module.") else k)): v
    for k, v in raw_sd.items()
    if k not in ("initted", "step")
}}
model.load_state_dict(cleaned, strict=False)
model = model.float().to(device).eval()

vocoder = load_vocoder(vocoder_name="vocos", is_local=True, local_path=str(BUNDLE_DIR / "vocos"), device=device)
clean_ref, clean_ref_txt = preprocess_ref_audio_text(str(ref_wav), ref_text)

# ৫. প্রতিটি স্ক্রিপ্ট স্মার্ট চাংকিং করে আলাদা আলাদা .wav তৈরি ও ZIP করা
out_dir = Path("/tmp/generated_wavs")
out_dir.mkdir(parents=True, exist_ok=True)
zip_path = Path("/kaggle/working/audio_bundle.zip")

with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for idx, item in enumerate(TASKS, 1):
        fname = item["filename"]
        txt = item["text"].strip()
        chunks = split_bengali_for_indicf5(txt, max_chars=160)
        print(f"[{{idx}}/{{len(TASKS)}}] Synthesizing {{fname}} ({{len(chunks)}} chunks)...")

        sr_final = 24000
        pause = np.zeros(int(sr_final * 0.16), dtype=np.float32)
        wav_parts = []
        for c_idx, ch in enumerate(chunks):
            wav_seg, sr_final, _ = infer_process(
                clean_ref, clean_ref_txt, ch, model, vocoder,
                mel_spec_type="vocos", device=device,
            )
            wav_parts.append(np.asarray(wav_seg, dtype=np.float32).reshape(-1))
            if c_idx < len(chunks) - 1:
                wav_parts.append(pause)

        final_wav = np.concatenate(wav_parts) if len(wav_parts) > 1 else wav_parts[0]
        wav_path = out_dir / fname
        sf.write(str(wav_path), final_wav, sr_final)
        zf.write(wav_path, arcname=fname)

print("✅ Batch synthesis complete!")
'''


def _push_with_fallback_slug(job_dir: Path, base_script: str, run_timeout_sec: int) -> str:
    """কোনো কারণে স্লাগ আটকে থাকলে বিকল্প স্লাগে পুশ করে"""
    suffixes = ("", "-r2", "-r3")
    last_err = None
    for suffix in suffixes:
        slug = f"{KERNEL_SLUG_BASE}{suffix}"
        kernel_id = f"{KAGGLE_USERNAME}/{slug}"
        metadata = {
            "id": kernel_id,
            "title": f"IndicF5 TTS Worker{suffix.upper()}",
            "code_file": "tts_job.py",
            "language": "python",
            "kernel_type": "script",
            "is_private": True,
            "enable_gpu": True,
            "enable_tpu": False,
            "enable_internet": False,
            "machine_shape": "NvidiaTeslaT4",
            "dataset_sources": [DATASET_SLUG],
            "competition_sources": [],
            "kernel_sources": [],
            "model_sources": [],
        }
        (job_dir / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        (job_dir / "tts_job.py").write_text(base_script, encoding="utf-8")
        try:
            push_out = _run_kaggle(["kernels", "push", "-p", str(job_dir), "-t", str(run_timeout_sec + 1200)])
            print("  ", push_out.strip())
            return kernel_id
        except Exception as exc:
            last_err = exc
            print(f"⚠️ Slug '{kernel_id}' push failed ({exc}). Trying next slug...")
    raise RuntimeError(f"Kaggle push failed on all slugs: {last_err}")


def generate_voices_batch(
    tasks: List[Dict[str, str]],
    output_dir: str | Path,
    ref_audio_path: Optional[str | Path] = None,
    ref_text: str = "",
    default_voice: str = "male",
    poll_interval: int = 20,
    max_attempts: int = 3,
    retry_interval_sec: int = 1200,  # ২০ মিনিট = ১২০০ সেকেন্ড
    run_timeout_sec: int = 900,      # GPU চালু হলে সর্বোচ্চ ১৫ মিনিট
) -> Dict[str, Path]:
    if not tasks:
        return {}

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not ref_audio_path:
        auto_ref, auto_txt = _find_repo_reference_voice()
        if auto_ref:
            ref_audio_path = auto_ref
            ref_text = auto_txt

    ref_b64 = ""
    ref_ext = ".wav"
    if ref_audio_path:
        rp = Path(ref_audio_path)
        if rp.exists() and ref_text.strip():
            print(f"🎤 [Kaggle TTS] Using Custom Reference Voice: {rp}")
            ref_b64 = base64.b64encode(rp.read_bytes()).decode("ascii")
            ref_ext = rp.suffix.lower() or ".wav"

    script_code = _build_worker_script(tasks, ref_b64, ref_ext, ref_text, default_voice)

    # শুরুর আগে পুরনো কোনো আটকে থাকা জব পরিষ্কার করা
    _cleanup_stale_workers()

    for attempt in range(1, max_attempts + 1):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            job_dir = tmp_path / "job"
            dl_dir = tmp_path / "out"
            job_dir.mkdir()
            dl_dir.mkdir()

            print(f"\n🚀 [Kaggle TTS | Attempt {attempt}/{max_attempts}] Pushing {len(tasks)} audio script(s)...")
            attempt_start = time.time()
            active_kernel_id = _push_with_fallback_slug(job_dir, script_code, run_timeout_sec)

            running_started_at = None
            time.sleep(10)

            while True:
                status_out = _run_kaggle(["kernels", "status", active_kernel_id]).strip()
                elapsed = int(time.time() - attempt_start)
                print(f"⏳ [Attempt {attempt}/{max_attempts} | {elapsed}s]: {status_out}")
                lower = status_out.lower()

                if "complete" in lower:
                    print("📥 [Kaggle TTS] Downloading generated audio bundle...")
                    _run_kaggle(["kernels", "output", active_kernel_id, "-p", str(dl_dir)])

                    zip_path = dl_dir / "audio_bundle.zip"
                    if not zip_path.exists():
                        raise FileNotFoundError(
                            f"audio_bundle.zip পাওয়া যায়নি! ফাইলসমূহ: {[p.name for p in dl_dir.iterdir()]}"
                        )

                    result_paths: Dict[str, Path] = {}
                    with zipfile.ZipFile(zip_path, "r") as zf:
                        zf.extractall(out_dir)
                        for item in tasks:
                            fname = item["filename"]
                            result_paths[fname] = out_dir / fname

                    print(f"✅ [Kaggle TTS] All {len(tasks)} audio file(s) ready on Attempt #{attempt}!")
                    return result_paths

                if "error" in lower or "cancel" in lower:
                    log_txt = ""
                    try:
                        _run_kaggle(["kernels", "output", active_kernel_id, "-p", str(dl_dir)])
                        log_files = list(dl_dir.glob("*.log"))
                        log_txt = log_files[0].read_text(encoding="utf-8", errors="ignore")[-1500:] if log_files else ""
                    except Exception:
                        pass
                    print(f"❌ [Attempt {attempt} Error]: {status_out}\n{log_txt}")
                    _delete_kernel_safely(active_kernel_id)
                    break

                if "running" in lower:
                    if running_started_at is None:
                        running_started_at = time.time()
                        print(f"⚡ [Attempt {attempt}] GPU RUNNING শুরু হয়েছে!")
                    if time.time() - running_started_at > run_timeout_sec:
                        print(f"⏰ [Attempt {attempt}] Running timeout ({run_timeout_sec}s) পার হয়েছে।")
                        _delete_kernel_safely(active_kernel_id)
                        break
                else:
                    # QUEUED অবস্থায় সর্বোচ্চ ২০ মিনিট অপেক্ষা
                    if time.time() - attempt_start >= retry_interval_sec:
                        print(f"⏰ [Attempt {attempt}] ২০ মিনিট ধরে QUEUED অবস্থায় আছে। বাতিল করে পরের চেষ্টা করা হচ্ছে...")
                        _delete_kernel_safely(active_kernel_id)
                        break

                time.sleep(poll_interval)

        # যদি কোনো জব দ্রুত (২০ মিনিটের আগে) এরর খেয়ে ভেঙে যায়, তবে বাকি সময় অপেক্ষা করে ২০ মিনিট পর পরের চেষ্টা করবে
        if attempt < max_attempts:
            remaining_wait = int(retry_interval_sec - (time.time() - attempt_start))
            if remaining_wait > 10:
                print(f"⏱️ পরবর্তী চেষ্টার আগে {remaining_wait} সেকেন্ড (২০ মিনিটের বিরতি) অপেক্ষা করা হচ্ছে...")
                time.sleep(remaining_wait)

    raise RuntimeError(f"Kaggle {max_attempts} বার (২০ মিনিট পরপর) চেষ্টা করেও GPU পায়নি।")
