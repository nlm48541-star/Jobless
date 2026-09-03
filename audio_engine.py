# -*- coding: utf-8 -*-
import os, re, time, json, requests

FREE_PERMITTED_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
TRACKER_FILE = os.path.join("workspace", "eleven_key_tracker.txt")

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

def get_tts_engine_order():
    """
    🌟 সিক্রেট থেকে ব্যবহারকারীর পছন্দের TTS ইঞ্জিন ক্রম বের করে
    মানসমূহ: eleven, bharat, mms, piper
    """
    raw_setting = os.environ.get("TTS_ENGINE", os.environ.get("TTS_PROVIDER", "")).strip().lower()
    enable_eleven = os.environ.get("ENABLE_ELEVENLABS", "true").strip().lower()

    default_order = ["eleven", "bharat", "mms", "piper"]
    if enable_eleven in ["false", "0", "no", "off"]:
        default_order = ["bharat", "mms", "piper"]

    if not raw_setting:
        return default_order

    tokens = [t.strip() for t in re.split(r'[\r\n,;]+', raw_setting) if t.strip()]
    valid_engines = []
    for t in tokens:
        if "eleven" in t and "eleven" not in valid_engines:
            valid_engines.append("eleven")
        elif ("bharat" in t or "indic" in t) and "bharat" not in valid_engines:
            valid_engines.append("bharat")
        elif ("mms" in t or "meta" in t or "facebook" in t) and "mms" not in valid_engines:
            valid_engines.append("mms")
        elif "piper" in t and "piper" not in valid_engines:
            valid_engines.append("piper")

    return valid_engines if valid_engines else default_order

# =========================================================================
# 🌟 ১. ElevenLabs স্পিচ ইঞ্জিন
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

def synthesize_with_elevenlabs(speech_text, output_audio_path):
    print("\n--- [ENGINE: ElevenLabs v3] ---")
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
                print(f"  ✅ [SUCCESS] Generated via ElevenLabs Key #{key_num}! ({audio_mb} MB, {elapsed}s)")
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
# 🌟 ২. AI4Bharat Indic-TTS ইঞ্জিন
# =========================================================================
def synthesize_with_ai4bharat(speech_text, output_audio_path):
    print("\n--- [ENGINE: AI4Bharat Indic-TTS] ---")
    hf_token = os.environ.get("HF_TOKEN", os.environ.get("HUGGINGFACE_TOKEN", "")).strip()
    headers = {"Content-Type": "application/json"}
    if hf_token: headers["Authorization"] = f"Bearer {hf_token}"

    hf_endpoints = [
        "https://api-inference.huggingface.co/models/ai4bharat/indic-parler-tts",
        "https://api-inference.huggingface.co/models/ai4bharat/indic-tts-coqui-indo_aryan-gpu--t4"
    ]

    for ep in hf_endpoints:
        try:
            model_name = ep.split('/')[-1]
            print(f"  🎙️ Synthesizing with AI4Bharat ({model_name})...")
            payload = {"inputs": speech_text, "parameters": {"language": "bn", "speaker": "male"}}
            resp = requests.post(ep, headers=headers, json=payload, timeout=60)
            if resp.status_code == 200 and len(resp.content) > 4000:
                with open(output_audio_path, "wb") as f:
                    f.write(resp.content)
                audio_mb = round(len(resp.content) / (1024 * 1024), 2)
                print(f"  ✅ [SUCCESS] Generated via AI4Bharat! ({audio_mb} MB)")
                return True
        except Exception as e:
            print(f"  ⚠️ AI4Bharat notice: {e}")

    try:
        print("  🎙️ Attempting AI4Bharat Dhruva Bhashini Gateway...")
        dhruva_url = "https://api.dhruva.ai4bharat.org/services/inference/pipeline"
        dhruva_payload = {
            "pipelineTasks": [{"taskType": "tts", "config": {"language": {"sourceLanguage": "bn"}, "gender": "male", "samplingRate": 22050}}],
            "inputData": {"input": [{"source": speech_text}]}
        }
        d_resp = requests.post(dhruva_url, headers=headers, json=dhruva_payload, timeout=45)
        if d_resp.status_code == 200:
            import base64
            audio_b64 = d_resp.json()['pipelineResponse'][0]['audio'][0]['audioContent']
            with open(output_audio_path, "wb") as f:
                f.write(base64.b64decode(audio_b64))
            print("  ✅ [SUCCESS] Generated via AI4Bharat Dhruva!")
            return True
    except Exception: pass

    return False

# =========================================================================
# 🌟 ৩. Facebook / Meta MMS-TTS ইঞ্জিন (Meta Massively Multilingual Speech)
# =========================================================================
def synthesize_with_meta_mms(speech_text, output_audio_path):
    print("\n--- [ENGINE: Facebook Meta MMS-TTS (facebook/mms-tts-ben)] ---")
    hf_token = os.environ.get("HF_TOKEN", os.environ.get("HUGGINGFACE_TOKEN", "")).strip()
    headers = {"Content-Type": "application/json"}
    if hf_token: headers["Authorization"] = f"Bearer {hf_token}"

    mms_url = "https://api-inference.huggingface.co/models/facebook/mms-tts-ben"
    payload = {"inputs": speech_text}

    try:
        print("  🎙️ Synthesizing with Meta MMS Bengali Neural Model...")
        start_time = time.time()
        resp = requests.post(mms_url, headers=headers, json=payload, timeout=90)
        elapsed = round(time.time() - start_time, 2)

        if resp.status_code == 200 and len(resp.content) > 3000:
            with open(output_audio_path, "wb") as f:
                f.write(resp.content)
            audio_mb = round(len(resp.content) / (1024 * 1024), 2)
            print(f"  ✅ [SUCCESS] Generated via Meta MMS-TTS! ({audio_mb} MB, {elapsed}s)")
            return True
        else:
            print(f"  ⚠️ Meta MMS returned {resp.status_code}: {resp.text[:120]}")
    except Exception as e:
        print(f"  ⚠️ Meta MMS error: {e}")

    return False

# =========================================================================
# 🌟 ৪. Piper Neural TTS ইঞ্জিন
# =========================================================================
def synthesize_with_piper(speech_text, output_audio_path):
    print("\n--- [ENGINE: Piper Neural TTS] ---")
    hf_token = os.environ.get("HF_TOKEN", os.environ.get("HUGGINGFACE_TOKEN", "")).strip()
    headers = {"Content-Type": "application/json"}
    if hf_token: headers["Authorization"] = f"Bearer {hf_token}"

    piper_endpoints = [
        "https://api-inference.huggingface.co/models/rhasspy/piper-voices",
        "https://api-inference.huggingface.co/models/facebook/mms-tts-ben"
    ]

    for url in piper_endpoints:
        try:
            print(f"  🎙️ Synthesizing with Piper TTS ({url.split('/')[-1]})...")
            payload = {"inputs": speech_text, "parameters": {"language": "bn"}}
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code == 200 and len(resp.content) > 3000:
                with open(output_audio_path, "wb") as f:
                    f.write(resp.content)
                print("  ✅ [SUCCESS] Generated via Piper TTS!")
                return True
        except Exception: pass

    return False

# =========================================================================
# 🌟 জরুরি নিউরাল ব্যাকআপ (Emergency Fail-Safe)
# =========================================================================
def synthesize_with_emergency_neural(speech_text, output_audio_path):
    try:
        import asyncio, edge_tts
        print("\n--- [ENGINE: Emergency Native Neural TTS Backup] ---")
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
    print("🎙️ [AUDIO ENGINE] Multi-TTS Synthesis Pipeline Active")
    print(f"📊 [Text Stats] Chars: {clean_chars} | Words: {words}")
    print(f"📝 [Preview]: \"{speech_text[:120]}...\"")
    print("="*65)

    engine_order = get_tts_engine_order()
    print(f"⚙️ [Execution Plan] Target Priority: {' ➔ '.join(engine_order)}")

    # ব্যবহারকারীর পছন্দের ক্রম অনুযায়ী একের পর এক ইঞ্জিন ট্রাই করবে
    for engine in engine_order:
        success = False
        if engine == "eleven":
            success = synthesize_with_elevenlabs(speech_text, output_audio_path)
        elif engine == "bharat":
            success = synthesize_with_ai4bharat(speech_text, output_audio_path)
        elif engine == "mms":
            success = synthesize_with_meta_mms(speech_text, output_audio_path)
        elif engine == "piper":
            success = synthesize_with_piper(speech_text, output_audio_path)

        if success and os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
            print("\n" + "="*65)
            print(f"🎉 [FINAL RESULT] Voiceover successfully rendered via '{engine.upper()}'!")
            print("="*65 + "\n")
            return True

        print(f"⚠️ '{engine.upper()}' failed or skipped. Moving to next provider...")

    # সব প্রাইমারি ইঞ্জিন ফেইল করলে জরুরি ব্যাকআপ
    print("\n⚠️ All selected engines failed. Activating Emergency Neural Backup...")
    if synthesize_with_emergency_neural(speech_text, output_audio_path):
        return True

    print("\n❌ [CRITICAL] Voiceover generation failed across all TTS engines.")
    return False
