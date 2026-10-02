# -*- coding: utf-8 -*-
import os, re, time, base64, requests, json

WORKSPACE_DIR = "workspace"
TRACKER_FILE = "api_key_tracker.json"
WORKSPACE_TRACKER = os.path.join(WORKSPACE_DIR, "api_key_tracker.json")

def parse_multiline_keys(raw_text):
    if not raw_text: return []
    lines = re.split(r'[\r\n,;]+', str(raw_text))
    return [k.strip() for k in lines if k.strip() and not k.strip().startswith('#')]

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

def load_tracker():
    for p in [WORKSPACE_TRACKER, TRACKER_FILE]:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception: pass
    return {}

def save_tracker_index(service_name, index, total_keys):
    if total_keys == 0: return
    data = load_tracker()
    if service_name not in data: data[service_name] = {}
    data[service_name]["current_index"] = index % total_keys

    for p in [WORKSPACE_TRACKER, TRACKER_FILE]:
        try:
            os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception: pass

def get_keys_in_cyclic_order(service_name, raw_keys_str):
    keys = parse_multiline_keys(raw_keys_str)
    if not keys: return []
    total = len(keys)
    data = load_tracker()
    saved_idx = data.get(service_name, {}).get("current_index", 0) % total
    return [((saved_idx + i) % total, keys[(saved_idx + i) % total]) for i in range(total)]

# =========================================================================
# 🌟 ১. প্রথম প্রায়োরিটি: Gemini 3.8 Flash TTS (Custom Voice: voice_z3e67k0f8p8c)
# =========================================================================

def synthesize_with_gemini_tts(speech_text, output_audio_path):
    print("\n--- [AUDIO TIER 1] Gemini 3.8 Flash TTS (Custom Voice) ---")
    raw_gemini = os.environ.get("GEMINI_API_KEYS", os.environ.get("GEMINI_API_KEY", "")).strip()
    gemini_order = get_keys_in_cyclic_order("gemini_tts", raw_gemini)
    total_gemini = len(parse_multiline_keys(raw_gemini))

    if not gemini_order:
        print("  ⚠️ No 'GEMINI_API_KEYS' found. Moving to Tier 2...")
        return False

    voice_id = "voice_z3e67k0f8p8c"
    delivery_style = "Natural, calm, warm and articulate Bengali pronunciation"

    try:
        from google import genai
    except ImportError:
        print("  ⚠️ 'google-genai' library not installed.")
        return False

    print(f"🔑 Loaded {total_gemini} Gemini Key(s). Resuming from Key #{gemini_order[0][0] + 1}...")

    for actual_idx, api_key in gemini_order:
        key_num = actual_idx + 1
        masked = mask_key(api_key)
        print(f"\n  🚀 [Gemini Key #{key_num}/{total_gemini}] (Key: {masked})")
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
                    save_tracker_index("gemini_tts", actual_idx, total_gemini)
                    audio_mb = round(os.path.getsize(output_audio_path) / (1024 * 1024), 2)
                    print(f"  ✅ [SUCCESS] Generated via Gemini 3.8 Flash TTS! ({audio_mb} MB in {round(time.time() - start_t, 2)}s)")
                    return True
        except Exception as e:
            print(f"  ⚠️ Gemini Key #{key_num} failed: {e}")
            save_tracker_index("gemini_tts", actual_idx + 1, total_gemini)

    return False

# =========================================================================
# 🌟 ২. দ্বিতীয় প্রায়োরিটি: ElevenLabs API (eleven_v3)
# =========================================================================

def synthesize_with_elevenlabs(speech_text, output_audio_path):
    print("\n--- [AUDIO TIER 2] ElevenLabs API (eleven_v3) ---")
    raw_eleven = os.environ.get("ELEVENLABS_API_KEYS", os.environ.get("ELEVENLABS_API_KEY", "")).strip()
    eleven_order = get_keys_in_cyclic_order("elevenlabs", raw_eleven)
    total_eleven = len(parse_multiline_keys(raw_eleven))

    if not eleven_order:
        print("  ⚠️ No 'ELEVENLABS_API_KEYS' found. Moving to Tier 3...")
        return False

    voice_id = "JBFqnCBsd6RMkjVDRZzb" # George
    tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    payload = {
        "text": speech_text,
        "model_id": "eleven_v3",
        "language_code": "bn",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }

    print(f"🔑 Loaded {total_eleven} ElevenLabs Key(s). Resuming from Key #{eleven_order[0][0] + 1}...")

    for actual_idx, api_key in eleven_order:
        key_num = actual_idx + 1
        masked = mask_key(api_key)
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }

        start_t = time.time()
        try:
            print(f"  🚀 Synthesizing with ElevenLabs Key #{key_num}/{total_eleven} ({masked})...")
            resp = requests.post(tts_url, json=payload, headers=headers, timeout=90)
            if resp.status_code == 200 and len(resp.content) > 3000:
                with open(output_audio_path, "wb") as f:
                    f.write(resp.content)
                save_tracker_index("elevenlabs", actual_idx, total_eleven)
                audio_mb = round(len(resp.content) / (1024 * 1024), 2)
                print(f"  ✅ [SUCCESS] Generated via ElevenLabs Key #{key_num}! ({audio_mb} MB in {round(time.time() - start_t, 2)}s)")
                return True
            else:
                save_tracker_index("elevenlabs", actual_idx + 1, total_eleven)
        except Exception as e:
            print(f"  ⚠️ ElevenLabs Key #{key_num} error: {e}")
            save_tracker_index("elevenlabs", actual_idx + 1, total_eleven)

    return False

# =========================================================================
# 🌟 ৩. তৃতীয় ব্যাকআপ: Microsoft Edge Neural TTS
# =========================================================================

def synthesize_with_edge_fallback(speech_text, output_audio_path):
    print("\n--- [AUDIO TIER 3] Microsoft Edge Neural Backup (bn-BD-PradeepNeural) ---")
    try:
        import asyncio, edge_tts
        start_t = time.time()
        async def _make():
            c = edge_tts.Communicate(speech_text, "bn-BD-PradeepNeural", rate="+0%", pitch="+0Hz")
            await c.save(output_audio_path)
        asyncio.run(_make())
        if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
            audio_mb = round(os.path.getsize(output_audio_path) / (1024 * 1024), 2)
            print(f"  ✅ [SUCCESS] Generated via Microsoft Edge Backup! ({audio_mb} MB in {round(time.time() - start_t, 2)}s)")
            return True
    except Exception as e:
        print(f"  ⚠️ Edge fallback notice: {e}")
    return False

# =========================================================================
# 🌟 ৪. চতুর্থ চূড়ান্ত ফলব্যাক: লোকাল ব্যাকগ্রাউন্ড মিউজিক (Fail-Safe)
# =========================================================================

def synthesize_with_local_music(output_audio_path):
    print("\n--- [AUDIO TIER 4] Local Audio/Music Fail-Safe ---")
    candidates = [
        "Music/bg_music.mp3",
        "sample_voice.mp3",
        "sample_voice.wav",
        "Photos/sample_voice.mp3"
    ]
    for m in candidates:
        if os.path.exists(m) and os.path.getsize(m) > 2000:
            import shutil
            shutil.copyfile(m, output_audio_path)
            print(f"  ✅ [FAIL-SAFE] Using Local Audio File '{m}' as Voiceover Track!")
            return True
    return False

# =========================================================================
# 🌟 মাস্টার অডিও পাইপলাইন (Orchestrator)
# =========================================================================

def generate_voiceover_audio_pipeline(text, output_audio_path):
    speech_text = clean_script_for_speech(text)
    clean_chars = len(speech_text)
    words = len(speech_text.split())

    print("\n" + "="*65)
    print("🎙️ [AUDIO ENGINE] Multi-Tier Cascade Active")
    print("   1. Gemini 3.8 Flash TTS")
    print("   2. ElevenLabs API")
    print("   3. Microsoft Edge Backup")
    print("   4. Local Audio Fail-Safe")
    print(f"📊 [Text Stats] Chars: {clean_chars} | Words: {words}")
    print("="*65)

    # ১. Gemini 3.8 TTS
    if synthesize_with_gemini_tts(speech_text, output_audio_path):
        if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
            return True

    # ২. ElevenLabs
    if synthesize_with_elevenlabs(speech_text, output_audio_path):
        if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
            return True

    # ৩. Microsoft Edge Neural
    if synthesize_with_edge_fallback(speech_text, output_audio_path):
        if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
            return True

    # ৪. লোকাল মিউজিক
    if synthesize_with_local_music(output_audio_path):
        if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
            return True

    print("\n❌ [CRITICAL] All 4 audio tiers failed.")
    return False
