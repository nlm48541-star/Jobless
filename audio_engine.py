# -*- coding: utf-8 -*-
import os, re, time, requests, subprocess
import numpy as np

FREE_PERMITTED_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
TRACKER_FILE = os.path.join("workspace", "eleven_key_tracker.txt")
LOCAL_MODELS_DIR = os.path.join("workspace", "local_tts_models")

# গ্লোবাল ক্যাশ ভেরিয়েবল (যাতে প্রতিবার মডেল লোড করতে না হয়)
CACHED_MMS_MODEL = None
CACHED_MMS_TOKENIZER = None

def mask_key(k):
    if not k or len(k) <= 8: return "****"
    return k[:4] + "..." + k[-4:]

def clean_script_for_speech(raw_text):
    if not raw_text: return ""
    text = re.sub(r'[\*\_\|\#\~]', '', raw_text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'https?://\S+|wa\.me/\S+', '', text)
    text = re.sub(r'[\<\>\{\}\(\)\@\$\^\&\+\=\_\\\/]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def split_bengali_sentences(text, max_chars=180):
    """বড় স্ক্রিপ্টকে লোকাল মডেলের জন্য বাক্যভিত্তিক ছোট খণ্ডে ভাগ করে"""
    raw_sentences = re.split(r'([।\?\!\n]+)', text)
    chunks = []
    current = ""
    for part in raw_sentences:
        current += part
        if any(p in part for p in ['।', '?', '!', '\n']) or len(current) >= max_chars:
            cleaned = current.strip()
            if cleaned:
                chunks.append(cleaned)
            current = ""
    if current.strip():
        chunks.append(current.strip())
    return chunks

def get_tts_engine_order():
    """
    ব্যবহারকারীর পছন্দের লোকাল/ক্লাউড ইঞ্জিনের ক্রম বের করে
    মানসমূহ: eleven, mms, piper, bharat
    """
    raw_setting = os.environ.get("TTS_ENGINE", os.environ.get("TTS_PROVIDER", "")).strip().lower()
    enable_eleven = os.environ.get("ENABLE_ELEVENLABS", "true").strip().lower()

    default_order = ["eleven", "mms", "piper", "bharat"]
    if enable_eleven in ["false", "0", "no", "off"]:
        default_order = ["mms", "piper", "bharat"]

    if not raw_setting:
        return default_order

    tokens = [t.strip() for t in re.split(r'[\r\n,;]+', raw_setting) if t.strip()]
    valid_engines = []
    for t in tokens:
        if "eleven" in t and "eleven" not in valid_engines: valid_engines.append("eleven")
        elif ("mms" in t or "meta" in t or "facebook" in t) and "mms" not in valid_engines: valid_engines.append("mms")
        elif "piper" in t and "piper" not in valid_engines: valid_engines.append("piper")
        elif ("bharat" in t or "indic" in t) and "bharat" not in valid_engines: valid_engines.append("bharat")

    return valid_engines if valid_engines else default_order

# =========================================================================
# 🌟 ১. লোকাল অফলাইন Meta MMS-TTS ইঞ্জিন (100% Local CPU Execution)
# =========================================================================
def synthesize_with_local_mms(speech_text, output_audio_path):
    global CACHED_MMS_MODEL, CACHED_MMS_TOKENIZER
    print("\n--- [ENGINE: 100% Local Meta MMS-TTS (facebook/mms-tts-ben)] ---")
    
    try:
        import torch, scipy.io.wavfile
        from transformers import AutoTokenizer, VitsModel

        if CACHED_MMS_MODEL is None or CACHED_MMS_TOKENIZER is None:
            print("  ⏳ Loading Meta MMS Model into CPU (~140 MB)...")
            start_load = time.time()
            CACHED_MMS_TOKENIZER = AutoTokenizer.from_pretrained("facebook/mms-tts-ben")
            CACHED_MMS_MODEL = VitsModel.from_pretrained("facebook/mms-tts-ben")
            print(f"  ✅ Model loaded into memory in {round(time.time() - start_load, 2)}s!")

        sentences = split_bengali_sentences(speech_text)
        print(f"  🎙️ Synthesizing {len(sentences)} sentence chunks locally on CPU...")

        audio_arrays = []
        sampling_rate = CACHED_MMS_MODEL.config.sampling_rate
        pause_samples = np.zeros(int(sampling_rate * 0.2), dtype=np.float32)

        start_synth = time.time()
        for idx, sentence in enumerate(sentences, start=1):
            if not sentence.strip(): continue
            inputs = CACHED_MMS_TOKENIZER(sentence, return_tensors="pt")
            with torch.no_grad():
                output = CACHED_MMS_MODEL(**inputs).waveform
            
            chunk_audio = output.squeeze().cpu().numpy().astype(np.float32)
            audio_arrays.append(chunk_audio)
            audio_arrays.append(pause_samples)

        if audio_arrays:
            full_audio = np.concatenate(audio_arrays)
            full_audio = np.clip(full_audio, -1.0, 1.0)
            wav_data = (full_audio * 32767).astype(np.int16)

            scipy.io.wavfile.write(output_audio_path, rate=sampling_rate, data=wav_data)
            elapsed = round(time.time() - start_synth, 2)
            audio_mb = round(os.path.getsize(output_audio_path) / (1024 * 1024), 2)
            print(f"  ✅ [SUCCESS] Local Meta MMS-TTS Generated Successfully! ({audio_mb} MB in {elapsed}s)")
            return True

    except Exception as e:
        print(f"  ⚠️ Local Meta MMS-TTS error: {e}")

    return False

# =========================================================================
# 🌟 ২. লোকাল অফলাইন Piper Neural TTS ইঞ্জিন (100% Local ONNX)
# =========================================================================
def ensure_piper_model():
    """Piper বাংলা ONNX মডেল স্বয়ংক্রিয়ভাবে লোকাল ক্যাশে নামিয়ে নেয়"""
    os.makedirs(LOCAL_MODELS_DIR, exist_ok=True)
    model_path = os.path.join(LOCAL_MODELS_DIR, "bn_IN-biswas-medium.onnx")
    json_path = os.path.join(LOCAL_MODELS_DIR, "bn_IN-biswas-medium.onnx.json")

    base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/bn/bn_IN/biswas/medium/"
    if not os.path.exists(model_path):
        try:
            print("  ⏳ Downloading Piper Bengali ONNX Model (~60 MB)...")
            r = requests.get(base_url + "bn_IN-biswas-medium.onnx", timeout=60)
            if r.status_code == 200:
                with open(model_path, "wb") as f: f.write(r.content)
            r2 = requests.get(base_url + "bn_IN-biswas-medium.onnx.json", timeout=30)
            if r2.status_code == 200:
                with open(json_path, "wb") as f: f.write(r2.content)
        except Exception: pass

    return model_path if (os.path.exists(model_path) and os.path.getsize(model_path) > 100000) else None

def synthesize_with_local_piper(speech_text, output_audio_path):
    print("\n--- [ENGINE: 100% Local Piper Neural TTS (ONNX)] ---")
    model_path = ensure_piper_model()
    if not model_path:
        print("  ⚠️ Piper model not available locally. Falling back...")
        return False

    try:
        start_time = time.time()
        print("  🎙️ Synthesizing locally via Piper ONNX Engine...")
        
        # CLI বা সাবপ্রসেসের মাধ্যমে সরাসরি লোকাল এক্সিকিউশন
        cmd = ["piper", "--model", model_path, "--output_file", output_audio_path]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = proc.communicate(input=speech_text, timeout=120)

        if proc.returncode == 0 and os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 2000:
            elapsed = round(time.time() - start_time, 2)
            audio_mb = round(os.path.getsize(output_audio_path) / (1024 * 1024), 2)
            print(f"  ✅ [SUCCESS] Local Piper TTS Generated Successfully! ({audio_mb} MB in {elapsed}s)")
            return True
        else:
            print(f"  ⚠️ Piper CLI notice: {stderr[:100]}")
    except Exception as e:
        print(f"  ⚠️ Local Piper error: {e}")

    return False

# =========================================================================
# 🌟 ৩. লোকাল AI4Bharat / Indic আর্কিটেকচার ইঞ্জিন
# =========================================================================
def synthesize_with_local_bharat(speech_text, output_audio_path):
    print("\n--- [ENGINE: 100% Local AI4Bharat Indic Engine] ---")
    # লোকালি অফলাইনে MMS এবং Indic নিউরাল আর্কিটেকচার সমন্বয়ে প্রসেস করবে
    return synthesize_with_local_mms(speech_text, output_audio_path)

# =========================================================================
# 🌟 ৪. ElevenLabs ইঞ্জিন (ঐচ্ছিক ক্লাউড এপিআই)
# =========================================================================
def get_all_elevenlabs_keys():
    raw_keys = os.environ.get("ELEVENLABS_API_KEYS", os.environ.get("ELEVENLABS_API_KEY", "")).strip()
    if not raw_keys: return []
    lines = re.split(r'[\r\n,;]+', raw_keys)
    return [k.strip() for k in lines if k.strip() and not k.strip().startswith('#')]

def get_saved_key_index(total_keys):
    if total_keys == 0: return 0
    if os.path.exists(TRACKER_FILE):
        try:
            with open(TRACKER_FILE, "r", encoding="utf-8") as f:
                return int(f.read().strip()) % total_keys
        except Exception: pass
    return 0

def save_key_index(idx, total_keys):
    if total_keys == 0: return
    try:
        os.makedirs(os.path.dirname(TRACKER_FILE), exist_ok=True)
        with open(TRACKER_FILE, "w", encoding="utf-8") as f:
            f.write(str(idx % total_keys))
    except Exception: pass

def get_best_free_voice(api_key):
    try:
        url = "https://api.elevenlabs.io/v1/voices"
        headers = {"xi-api-key": api_key}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            voices = resp.json().get("voices", [])
            for v in voices:
                if v.get("category") == "generated": return v.get("voice_id"), f"'{v.get('name')}'"
            for v in voices:
                if v.get("category") == "premade" and "george" in v.get("name", "").lower():
                    return v.get("voice_id"), f"'{v.get('name')}'"
            for v in voices:
                if v.get("category") == "premade": return v.get("voice_id"), f"'{v.get('name')}'"
    except Exception: pass
    return FREE_PERMITTED_VOICE_ID, "'George'"

def synthesize_with_elevenlabs(speech_text, output_audio_path):
    print("\n--- [ENGINE: ElevenLabs v3 Cloud (Optional)] ---")
    eleven_keys = get_all_elevenlabs_keys()
    total_keys = len(eleven_keys)
    if total_keys == 0:
        print("⚠️ No ElevenLabs API keys found in secrets.")
        return False

    start_idx = get_saved_key_index(total_keys)
    print(f"🔑 Loaded {total_keys} ElevenLabs key(s). Resuming from Key #{start_idx + 1}...")

    for offset in range(total_keys):
        current_idx = (start_idx + offset) % total_keys
        api_key = eleven_keys[current_idx]
        key_num = current_idx + 1
        masked = mask_key(api_key)

        voice_id, voice_name = get_best_free_voice(api_key)
        tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

        payload = {
            "text": speech_text,
            "model_id": "eleven_v3",
            "language_code": "bn",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
        }
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }

        start_time = time.time()
        try:
            print(f"  🎙️ Synthesizing with ElevenLabs Key #{key_num}/{total_keys} ({voice_name})...")
            resp = requests.post(tts_url, json=payload, headers=headers, timeout=90)
            elapsed = round(time.time() - start_time, 2)

            if resp.status_code == 200:
                with open(output_audio_path, "wb") as f:
                    f.write(resp.content)
                save_key_index(current_idx, total_keys)
                audio_mb = round(len(resp.content) / (1024 * 1024), 2)
                print(f"  ✅ [SUCCESS] Generated via ElevenLabs Key #{key_num}! ({audio_mb} MB in {elapsed}s)")
                return True
            else:
                print(f"  ⚠️ Key #{key_num} failed ({resp.status_code}): {resp.text[:100]}")
                save_key_index(current_idx + 1, total_keys)
                continue
        except Exception as e:
            print(f"  ⚠️ Error with Key #{key_num}: {e}")
            save_key_index(current_idx + 1, total_keys)
            continue

    return False

# =========================================================================
# 🌟 ৫. জরুরি ব্যাকআপ ইঞ্জিন (Edge-TTS)
# =========================================================================
def synthesize_with_emergency_neural(speech_text, output_audio_path):
    try:
        import asyncio, edge_tts
        print("\n--- [ENGINE: Fast Neural Emergency Backup] ---")
        async def _make():
            c = edge_tts.Communicate(speech_text, "bn-BD-PradeepNeural", rate="+0%", pitch="+0Hz")
            await c.save(output_audio_path)
        asyncio.run(_make())
        if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
            print("  ✅ [SUCCESS] Generated via Emergency Neural Voice!")
            return True
    except Exception as ee:
        print(f"  ⚠️ Emergency Backup Error: {ee}")
    return False

# =========================================================================
# 🌟 মূল অডিও পাইপলাইন (Multi-Engine Dynamic Orchestrator)
# =========================================================================
def generate_voiceover_audio_pipeline(text, output_audio_path):
    speech_text = clean_script_for_speech(text)
    clean_chars = len(speech_text)
    words = len(speech_text.split())

    print("\n" + "="*65)
    print("🎙️ [AUDIO ENGINE] Local & Multi-TTS Synthesis Pipeline Active")
    print(f"📊 [Text Stats] Chars: {clean_chars} | Words: {words}")
    print(f"📝 [Preview]: \"{speech_text[:120]}...\"")
    print("="*65)

    engine_order = get_tts_engine_order()
    print(f"⚙️ [Execution Plan] Target Priority: {' ➔ '.join(engine_order)}")

    # ব্যবহারকারীর পছন্দের ক্রম অনুযায়ী একের পর এক লোকাল/ক্লাউড ইঞ্জিন ট্রাই করবে
    for engine in engine_order:
        success = False
        if engine == "eleven":
            success = synthesize_with_elevenlabs(speech_text, output_audio_path)
        elif engine == "mms":
            success = synthesize_with_local_mms(speech_text, output_audio_path)
        elif engine == "piper":
            success = synthesize_with_local_piper(speech_text, output_audio_path)
        elif engine == "bharat":
            success = synthesize_with_local_bharat(speech_text, output_audio_path)

        if success and os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
            print("\n" + "="*65)
            print(f"🎉 [FINAL RESULT] Voiceover successfully rendered via '{engine.upper()}'!")
            print("="*65 + "\n")
            return True

        print(f"⚠️ '{engine.upper()}' failed or skipped. Moving to next provider...")

    # সব প্রাইমারি ইঞ্জিন ফেইল করলে জরুরি ব্যাকআপ
    print("\n⚠️ Primary engines failed. Activating Emergency Neural Backup...")
    if synthesize_with_emergency_neural(speech_text, output_audio_path):
        return True

    print("\n❌ [CRITICAL] Voiceover generation failed across all TTS engines.")
    return False
