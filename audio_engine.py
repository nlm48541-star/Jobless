# -*- coding: utf-8 -*-
import os, re, time, requests

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

def get_all_elevenlabs_keys():
    """এন্টার (Newline) বা কমা দিয়ে সাজানো সব ElevenLabs এপিআই কি লোড করে"""
    raw_keys = os.environ.get("ELEVENLABS_API_KEYS", os.environ.get("ELEVENLABS_API_KEY", "")).strip()
    if not raw_keys: return []
    # এন্টার (\n), কমা, সেমিকোলন দিয়ে ক্লিন পার্সিং
    lines = re.split(r'[\r\n,;]+', raw_keys)
    return [k.strip() for k in lines if k.strip() and not k.strip().startswith('#')]

def get_saved_key_index(total_keys):
    """ড্রাইভ/ওয়ার্কস্পেস থেকে সর্বশেষ সফল বা সক্রিয় কি ইনডেক্স পড়ে নেয়"""
    if total_keys == 0: return 0
    if os.path.exists(TRACKER_FILE):
        try:
            with open(TRACKER_FILE, "r", encoding="utf-8") as f:
                saved = int(f.read().strip())
                return saved % total_keys
        except Exception: pass
    return 0

def save_key_index(idx, total_keys):
    """পরবর্তী রান বা পরবর্তী ভিডিওর জন্য কি ইনডেক্স মনে রাখে"""
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

def generate_voiceover_audio_pipeline(text, output_audio_path):
    print("\n" + "="*65)
    print("🎙️ [AUDIO ENGINE] Starting ElevenLabs Voiceover (Smart Cyclic Pool)")
    print("="*65)

    speech_text = clean_script_for_speech(text)
    raw_chars = len(text) if text else 0
    clean_chars = len(speech_text)
    words = len(speech_text.split())

    print(f"📊 [Text Analysis] Raw: {raw_chars} chars ➔ Clean: {clean_chars} chars | Words: {words}")
    print(f"📝 [Script Preview]: \"{speech_text[:140]}...\"\n")

    eleven_keys = get_all_elevenlabs_keys()
    total_keys = len(eleven_keys)
    if total_keys == 0:
        print("❌ [CRITICAL ERROR] No ElevenLabs API keys found in secrets!")
        print("="*65 + "\n")
        return False

    start_idx = get_saved_key_index(total_keys)
    print(f"🔑 [API Key Pool] Total {total_keys} key(s) loaded. Resuming from Key #{start_idx + 1}...")

    # 🌟 সাইক্লিক রোটেশন: শেষ যেখানে হয়েছিল সেখান থেকে শুরু হয়ে পুরো লুপ ঘুরবে
    for offset in range(total_keys):
        current_idx = (start_idx + offset) % total_keys
        api_key = eleven_keys[current_idx]
        key_num = current_idx + 1
        masked = mask_key(api_key)

        voice_id, voice_name = get_best_free_voice(api_key)
        tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

        print(f"\n--- [Attempting Key #{key_num}/{total_keys}] ---")
        print(f"  • Active Key    : {masked}")
        print(f"  • Selected Voice: {voice_name} [ID: {voice_id}]")
        print(f"  • Model         : eleven_v3 (Language: 'bn' - Bengali)")
        print(f"  • Endpoint URL  : {tts_url}")

        payload = {
            "text": speech_text,
            "model_id": "eleven_v3",
            "language_code": "bn",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }

        start_time = time.time()
        try:
            print("  ⏳ Sending synthesis request to ElevenLabs...")
            resp = requests.post(tts_url, json=payload, headers=headers, timeout=120)
            elapsed = round(time.time() - start_time, 2)

            print(f"  📥 Server Response: HTTP {resp.status_code} (Response Time: {elapsed}s)")

            if resp.status_code == 200:
                audio_bytes = len(resp.content)
                audio_mb = round(audio_bytes / (1024 * 1024), 2)
                
                with open(output_audio_path, "wb") as f:
                    f.write(resp.content)

                # 🌟 সফল হলে এই কি-টিই মেমোরিতে সেভ করে রাখবে
                save_key_index(current_idx, total_keys)

                print(f"  ✅ [SUCCESS] Eleven v3 Bengali Voiceover Generated Successfully via Key #{key_num}!")
                print(f"  📁 Saved Path  : {output_audio_path} ({audio_mb} MB / {audio_bytes:,} bytes)")
                print("="*65 + "\n")
                return True

            else:
                print(f"  ⚠️ [FAILED] Key #{key_num} returned: {resp.status_code}")
                print(f"  📄 Error Body  : {resp.text[:300]}")
                
                # কোটা শেষ হলে পরবর্তী কী-কে পয়েন্টার হিসেবে সেভ করে দেবে
                save_key_index(current_idx + 1, total_keys)
                print(f"  🔄 Moving pointer to next Key #{((current_idx + 1) % total_keys) + 1}...")
                continue

        except requests.exceptions.Timeout:
            print(f"  ❌ [TIMEOUT] Request timed out after 120s with Key #{key_num}.")
            save_key_index(current_idx + 1, total_keys)
            continue
        except Exception as e:
            print(f"  ❌ [ERROR] Network exception with Key #{key_num}: {e}")
            save_key_index(current_idx + 1, total_keys)
            continue

    print("\n" + "="*65)
    print("❌ [ALL KEYS EXHAUSTED] Audio generation failed across all keys.")
    print("="*65 + "\n")
    return False
