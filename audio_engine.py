# -*- coding: utf-8 -*-
import os, re, time, base64, requests

FISH_TRACKER_FILE = os.path.join("workspace", "fish_key_tracker.txt")
MODAL_TRACKER_FILE = os.path.join("workspace", "modal_key_tracker.txt")

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

def split_text_into_chunks(text, max_chars=400):
    raw_parts = re.split(r'([।\?\!\n]+)', text)
    chunks = []
    current = ""
    for p in raw_parts:
        current += p
        if any(sym in p for sym in ['।', '?', '!', '\n']) or len(current) >= max_chars:
            if current.strip(): chunks.append(current.strip())
            current = ""
    if current.strip(): chunks.append(current.strip())
    return chunks

def get_saved_index(file_path, total):
    if total == 0: return 0
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return int(f.read().strip()) % total
        except Exception: pass
    return 0

def save_index(file_path, idx, total):
    if total == 0: return
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(str(idx % total))
    except Exception: pass

# =========================================================================
# 🌟 ১. Gemini 3.8 Flash TTS ইঞ্জিন (Official google-genai SDK)
# =========================================================================

def get_all_gemini_keys():
    raw_keys = os.environ.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEYS", "")).strip()
    if not raw_keys: return []
    lines = re.split(r'[\r\n,;]+', raw_keys)
    return [k.strip() for k in lines if k.strip() and not k.strip().startswith('#')]

def synthesize_with_gemini(speech_text, output_audio_path):
    print("\n--- [ENGINE: Gemini 3.8 Flash TTS (Custom Voice)] ---")
    gemini_keys = get_all_gemini_keys()
    if not gemini_keys:
        print("  ⚠️ 'GEMINI_API_KEY' not found in environment secrets.")
        return False

    voice_id = os.environ.get("GEMINI_VOICE_ID", "voice_z3e67k0f8p8c").strip() or "voice_z3e67k0f8p8c"
    delivery_style = os.environ.get("GEMINI_DELIVERY_STYLE", "Natural, calm, warm and articulate Bengali pronunciation").strip()

    try:
        from google import genai
    except ImportError:
        print("  ⚠️ 'google-genai' library is not installed.")
        return False

    for idx, api_key in enumerate(gemini_keys, 1):
        masked = mask_key(api_key)
        print(f"  🚀 Attempting Gemini Key #{idx}/{len(gemini_keys)} (Key: {masked})")
        start_t = time.time()
        try:
            client = genai.Client(api_key=api_key)
            interaction = client.interactions.create(
                model="gemini-3.8-flash-tts",
                input=[{
                    "type": "user_input",
                    "content": [{
                        "type": "text",
                        "text": speech_text,
                        "annotations": [{
                            "type": "speech_metadata",
                            "style": delivery_style
                        }]
                    }]
                }],
                response_format={"type": "audio"},
                generation_config={
                    "speech_config": [{"voice": voice_id}]
                }
            )

            if hasattr(interaction, 'output_audio') and hasattr(interaction.output_audio, 'data'):
                audio_bytes = base64.b64decode(interaction.output_audio.data)
                if len(audio_bytes) > 2000:
                    with open(output_audio_path, "wb") as f:
                        f.write(audio_bytes)
                    elapsed = round(time.time() - start_t, 2)
                    audio_mb = round(os.path.getsize(output_audio_path) / (1024 * 1024), 2)
                    print(f"  ✅ [SUCCESS] Generated via Gemini 3.8 Flash TTS! (Voice: {voice_id}, {audio_mb} MB in {elapsed}s)")
                    return True

            print(f"  ⚠️ Gemini Key #{idx} returned unexpected response structure.")
        except Exception as e:
            print(f"  ⚠️ Gemini Key #{idx} error: {e}")

    return False

# =========================================================================
# 🌟 ২. Fish Audio Drama 3 ইঞ্জিন
# =========================================================================

def get_all_fish_keys():
    raw_keys = os.environ.get("FISH_API_KEYS", os.environ.get("FISH_API_KEY", "")).strip()
    if not raw_keys: return []
    lines = re.split(r'[\r\n,;]+', raw_keys)
    return [k.strip() for k in lines if k.strip() and not k.strip().startswith('#')]

def synthesize_with_fish_audio(speech_text, output_audio_path):
    print("\n--- [ENGINE: Fish Audio (Drama 3)] ---")
    fish_keys = get_all_fish_keys()
    total_keys = len(fish_keys)
    voice_id = os.environ.get("FISH_VOICE_ID", "").strip()

    if total_keys == 0:
        return False

    url = "https://api.fish.audio/v1/tts"
    start_idx = get_saved_index(FISH_TRACKER_FILE, total_keys)
    chunks = split_text_into_chunks(speech_text, max_chars=400)

    for offset in range(total_keys):
        cur_idx = (start_idx + offset) % total_keys
        api_key = fish_keys[cur_idx]
        key_num = cur_idx + 1

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "model": "drama-3-preview"
        }

        audio_bytes_list = []
        key_failed = False
        start_time = time.time()

        for chunk in chunks:
            payload = {"text": chunk, "format": "mp3", "mp3_bitrate": 128}
            if voice_id: payload["reference_id"] = voice_id

            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=60)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    audio_bytes_list.append(resp.content)
                else:
                    key_failed = True
                    break
            except Exception:
                key_failed = True
                break

        if not key_failed and len(audio_bytes_list) == len(chunks):
            with open(output_audio_path, "wb") as f:
                for b in audio_bytes_list: f.write(b)
            save_index(FISH_TRACKER_FILE, cur_idx, total_keys)
            return True
        else:
            save_index(FISH_TRACKER_FILE, cur_idx + 1, total_keys)
            continue

    return False

# =========================================================================
# 🌟 ৩. Modal ক্লাউড জিপিইউ ইঞ্জিন
# =========================================================================

def get_sample_voice_b64():
    for fname in ["sample_voice.mp3", "sample_voice.wav", "Photos/sample_voice.mp3", "Photos/sample_voice.wav"]:
        if os.path.exists(fname) and os.path.getsize(fname) > 1000:
            try:
                with open(fname, "rb") as f: return base64.b64encode(f.read()).decode('utf-8')
            except Exception: pass
    return None

def get_all_modal_endpoints():
    raw_urls = os.environ.get("MODAL_ENDPOINTS", os.environ.get("MODAL_URLS", "")).strip()
    if not raw_urls: return []
    lines = re.split(r'[\r\n,;]+', raw_urls)
    return [u.strip() for u in lines if u.strip() and u.strip().startswith("http")]

def synthesize_with_modal_cyclic(speech_text, output_audio_path):
    endpoints = get_all_modal_endpoints()
    total_acc = len(endpoints)
    if total_acc == 0:
        return False

    start_idx = get_saved_index(MODAL_TRACKER_FILE, total_acc)
    chosen_model = os.environ.get("TTS_MODEL", "cosyvoice").strip().lower()
    sample_b64 = get_sample_voice_b64()

    for offset in range(total_acc):
        cur_idx = (start_idx + offset) % total_acc
        endpoint_url = endpoints[cur_idx]
        payload = {"text": speech_text, "model": chosen_model, "sample_voice_b64": sample_b64}

        try:
            resp = requests.post(endpoint_url, json=payload, timeout=150)
            if resp.status_code == 200 and len(resp.content) > 3000:
                with open(output_audio_path, "wb") as f: f.write(resp.content)
                save_index(MODAL_TRACKER_FILE, cur_idx, total_acc)
                return True
            else:
                save_index(MODAL_TRACKER_FILE, cur_idx + 1, total_acc)
                continue
        except Exception:
            save_index(MODAL_TRACKER_FILE, cur_idx + 1, total_acc)
            continue

    return False

# =========================================================================
# 🌟 ৪. Microsoft Edge Neural ব্যাকআপ ইঞ্জিন
# =========================================================================

def synthesize_with_edge_fallback(speech_text, output_audio_path):
    print("\n--- [ENGINE: Microsoft Neural Fallback (bn-BD-PradeepNeural)] ---")
    try:
        import asyncio, edge_tts
        start_t = time.time()
        async def _make():
            c = edge_tts.Communicate(speech_text, "bn-BD-PradeepNeural", rate="+0%", pitch="+0Hz")
            await c.save(output_audio_path)
        asyncio.run(_make())
        if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
            elapsed = round(time.time() - start_t, 2)
            audio_mb = round(os.path.getsize(output_audio_path) / (1024 * 1024), 2)
            print(f"  ✅ [SUCCESS] Generated via Microsoft Neural Engine! ({audio_mb} MB in {elapsed}s)")
            return True
    except Exception as e:
        print(f"  ⚠️ Edge fallback notice: {e}")
    return False

# =========================================================================
# 🌟 মাস্টার অডিও পাইপলাইন (Orchestrator)
# =========================================================================

def generate_voiceover_audio_pipeline(text, output_audio_path):
    speech_text = clean_script_for_speech(text)
    clean_chars = len(speech_text)
    words = len(speech_text.split())

    print("\n" + "="*65)
    print("🎙️ [AUDIO ENGINE] Multi-Tier Voice Synthesis Active")
    print(f"📊 [Text Stats] Chars: {clean_chars} | Words: {words}")
    print(f"📝 [Preview]: \"{speech_text[:120]}...\"")
    print("="*65)

    target_model = os.environ.get("TTS_MODEL", os.environ.get("TTS_ENGINE", "")).strip().lower()

    # 🌟 ১. যদি TTS_MODEL বা TTS_ENGINE এ 'gemini' দেওয়া থাকে:
    if "gemini" in target_model:
        if synthesize_with_gemini(speech_text, output_audio_path):
            if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
                print("\n🎉 [FINAL RESULT] Voiceover created via Gemini 3.8 Flash TTS!\n")
                return True
        print("⚠️ Gemini TTS failed or exhausted. Cascading to fallback engines...")

    # 🌟 ২. Fish Audio Drama 3
    if synthesize_with_fish_audio(speech_text, output_audio_path):
        if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
            print("\n🎉 [FINAL RESULT] Voiceover created via Fish Audio Drama 3!\n")
            return True

    # 🌟 ৩. Modal ক্লাউড জিপিইউ
    if synthesize_with_modal_cyclic(speech_text, output_audio_path):
        if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
            print("\n🎉 [FINAL RESULT] Voiceover created via Modal Cloud GPU!\n")
            return True

    # 🌟 ৪. চূড়ান্ত জরুরি ব্যাকআপ: Microsoft Edge Neural
    if synthesize_with_edge_fallback(speech_text, output_audio_path):
        if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
            print("\n🎉 [FINAL RESULT] Voiceover created via Microsoft Neural Backup!\n")
            return True

    print("\n❌ [CRITICAL] All audio engines failed.")
    return False
