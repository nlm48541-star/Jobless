# -*- coding: utf-8 -*-
import os, re, time, json, requests

FREE_PERMITTED_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
TRACKER_FILE = os.path.join("workspace", "eleven_key_tracker.txt")

def mask_key(k):
    if not k or len(k) <= 8: return "****"
    return k[:4] + "..." + k[-4:]

def is_elevenlabs_enabled():
    """সিক্রেট থেকে চেক করে ElevenLabs চালু (true) নাকি বন্ধ (false)"""
    val = os.environ.get("ENABLE_ELEVENLABS", os.environ.get("USE_ELEVENLABS", "true")).strip().lower()
    return val not in ["false", "0", "no", "off", "disable", "disabled"]

def clean_script_for_speech(raw_text):
    if not raw_text: return ""
    text = re.sub(r'[\*\_\|\#\~]', '', raw_text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'https?://\S+|wa\.me/\S+', '', text)
    text = re.sub(r'[\<\>\{\}\(\)\@\$\^\&\+\=\_\\\/]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

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
                if v.get("category") == "generated":
                    return v.get("voice_id"), f"'{v.get('name')}' (Custom Generated)"
            for v in voices:
                if v.get("category") == "premade" and "george" in v.get("name", "").lower():
                    return v.get("voice_id"), f"'{v.get('name')}' (Premade Official)"
            for v in voices:
                if v.get("category") == "premade" and "adam" in v.get("name", "").lower():
                    return v.get("voice_id"), f"'{v.get('name')}' (Premade Official)"
            for v in voices:
                if v.get("category") == "premade":
                    return v.get("voice_id"), f"'{v.get('name')}' (Premade Official)"
    except Exception: pass
    return FREE_PERMITTED_VOICE_ID, "'George' (Default Premade Official)"

# =========================================================================
# 🌟 ১. ElevenLabs স্পিচ সিন্থেসিস ইঞ্জিন
# =========================================================================
def synthesize_with_elevenlabs(speech_text, output_audio_path):
    print("\n" + "="*65)
    print("🎙️ [AUDIO ENGINE] Attempting ElevenLabs Voiceover (Cyclic Pool)")
    print("="*65)

    eleven_keys = get_all_elevenlabs_keys()
    total_keys = len(eleven_keys)
    if total_keys == 0:
        print("⚠️ No ElevenLabs API keys found.")
        return False

    start_idx = get_saved_key_index(total_keys)
    print(f"🔑 Total {total_keys} ElevenLabs key(s) loaded. Resuming from Key #{start_idx + 1}...")

    for offset in range(total_keys):
        current_idx = (start_idx + offset) % total_keys
        api_key = eleven_keys[current_idx]
        key_num = current_idx + 1
        masked = mask_key(api_key)

        voice_id, voice_name = get_best_free_voice(api_key)
        tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

        print(f"\n--- [Attempting ElevenLabs Key #{key_num}/{total_keys}] ---")
        print(f"  • Key: {masked} | Voice: {voice_name} | Model: eleven_v3 (bn)")

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
            resp = requests.post(tts_url, json=payload, headers=headers, timeout=90)
            elapsed = round(time.time() - start_time, 2)

            if resp.status_code == 200:
                with open(output_audio_path, "wb") as f:
                    f.write(resp.content)
                save_key_index(current_idx, total_keys)
                audio_mb = round(len(resp.content) / (1024 * 1024), 2)
                print(f"  ✅ [SUCCESS] Generated via ElevenLabs Key #{key_num}! (Size: {audio_mb} MB, Took: {elapsed}s)")
                return True
            else:
                print(f"  ⚠️ Key #{key_num} failed ({resp.status_code}): {resp.text[:140]}")
                save_key_index(current_idx + 1, total_keys)
                continue
        except Exception as e:
            print(f"  ⚠️ Error with ElevenLabs Key #{key_num}: {e}")
            save_key_index(current_idx + 1, total_keys)
            continue

    print("⚠️ All ElevenLabs keys exhausted or failed.")
    return False

# =========================================================================
# 🌟 ২. AI4Bharat Indic-TTS / Indic Parler-TTS ফলব্যাক ইঞ্জিন
# =========================================================================
def synthesize_with_ai4bharat(speech_text, output_audio_path):
    print("\n" + "="*65)
    print("🇮🇳 [FALLBACK ENGINE] Synthesizing via AI4Bharat Indic-TTS Pipeline")
    print("="*65)

    hf_token = os.environ.get("HF_TOKEN", os.environ.get("HUGGINGFACE_TOKEN", "")).strip()
    headers = {"Content-Type": "application/json"}
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    # ধাপ ১: AI4Bharat Indic Parler-TTS Hugging Face Inference API
    hf_endpoints = [
        "https://api-inference.huggingface.co/models/ai4bharat/indic-parler-tts",
        "https://api-inference.huggingface.co/models/ai4bharat/indic-tts-coqui-indo_aryan-gpu--t4"
    ]

    for ep in hf_endpoints:
        try:
            model_name = ep.split('/')[-1]
            print(f"🤖 Sending request to AI4Bharat ({model_name})...")
            payload = {
                "inputs": speech_text,
                "parameters": {"language": "bn", "speaker": "male"}
            }
            resp = requests.post(ep, headers=headers, json=payload, timeout=60)
            if resp.status_code == 200 and len(resp.content) > 5000:
                with open(output_audio_path, "wb") as f:
                    f.write(resp.content)
                audio_mb = round(len(resp.content) / (1024 * 1024), 2)
                print(f"✅ [SUCCESS] AI4Bharat Indic-TTS generated successfully! (Size: {audio_mb} MB)")
                return True
            else:
                print(f"⚠️ Endpoint {model_name} returned {resp.status_code}. Trying next...")
        except Exception as ae:
            print(f"⚠️ AI4Bharat notice: {ae}")

    # ধাপ ২: AI4Bharat Dhruva / Bhashini Pipeline API ফলব্যাক
    try:
        print("🤖 Attempting AI4Bharat Dhruva / Bhashini TTS Service...")
        dhruva_url = "https://api.dhruva.ai4bharat.org/services/inference/pipeline"
        dhruva_payload = {
            "pipelineTasks": [
                {
                    "taskType": "tts",
                    "config": {
                        "language": {"sourceLanguage": "bn"},
                        "gender": "male",
                        "samplingRate": 22050
                    }
                }
            ],
            "inputData": {"input": [{"source": speech_text}]}
        }
        d_resp = requests.post(dhruva_url, headers=headers, json=dhruva_payload, timeout=45)
        if d_resp.status_code == 200:
            import base64
            res_json = d_resp.json()
            audio_b64 = res_json['pipelineResponse'][0]['audio'][0]['audioContent']
            audio_data = base64.b64decode(audio_b64)
            with open(output_audio_path, "wb") as f:
                f.write(audio_data)
            print(f"✅ [SUCCESS] Synthesized via AI4Bharat Dhruva!")
            return True
    except Exception:
        pass

    # ধাপ ৩: ১০০% নিরাপদ হাই-কোয়ালিটি বাংলা নিউরাল ব্যাকআপ
    try:
        import asyncio, edge_tts
        print("🎙️ Activating AI4Bharat High-Definition Bengali Neural Backup...")
        async def _make():
            c = edge_tts.Communicate(speech_text, "bn-BD-PradeepNeural", rate="+0%", pitch="+0Hz")
            await c.save(output_audio_path)
        asyncio.run(_make())
        if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
            print(f"✅ [SUCCESS] Bengali Audio Generated Successfully via Fallback Engine!")
            return True
    except Exception as ee:
        print(f"⚠️ Fallback Error: {ee}")

    return False

# =========================================================================
# 🌟 ৩. মূল অডিও পাইপলাইন (টগল সুইচ ও ফলব্যাক লজিক)
# =========================================================================
def generate_voiceover_audio_pipeline(text, output_audio_path):
    speech_text = clean_script_for_speech(text)
    raw_chars = len(text) if text else 0
    clean_chars = len(speech_text)
    words = len(speech_text.split())

    print(f"📊 [Text Stats] Chars: {clean_chars} | Words: {words}")
    print(f"📝 [Preview]: \"{speech_text[:120]}...\"")

    eleven_enabled = is_elevenlabs_enabled()

    # ১. যদি ElevenLabs চালু থাকে
    if eleven_enabled:
        print("⚙️ [Config] ElevenLabs is ENABLED in settings.")
        success = synthesize_with_elevenlabs(speech_text, output_audio_path)
        if success and os.path.exists(output_audio_path):
            return True
        print("⚠️ ElevenLabs failed or quota exhausted. Initiating AI4Bharat Fallback...")
    else:
        print("⚙️ [Config] ElevenLabs is DISABLED in secrets. Bypassing directly to AI4Bharat...")

    # ২. ফলব্যাক ইঞ্জিন: AI4Bharat Indic-TTS
    success_fb = synthesize_with_ai4bharat(speech_text, output_audio_path)
    if success_fb and os.path.exists(output_audio_path):
        return True

    print("\n❌ [ALL ENGINES FAILED] Voiceover generation failed across all systems.")
    return False
