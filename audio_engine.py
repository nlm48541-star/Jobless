# -*- coding: utf-8 -*-
import os, re, time, requests

# 🌟 আপনার টেস্ট করা সেরা 'Mark - Natural Conversations' ভয়েস আইডি
DEFAULT_VOICE_ID = "UgBBYS2sOqTuMpoF3BR0"

def mask_key(k):
    """লগে এপিআই কী নিরাপদভাবে প্রদর্শন করে (যেমন: sk_1...a8f9)"""
    if not k or len(k) <= 8: return "****"
    return k[:4] + "..." + k[-4:]

def clean_script_for_speech(raw_text):
    """স্ক্রিপ্ট থেকে সব মার্কডাউন ও অনাকাঙ্ক্ষিত চিহ্ন মুছে স্বাভাবিক উচ্চারণে রূপান্তর করে"""
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
    return [k.strip() for k in re.split(r'[\r\n,;]+', raw_keys) if k.strip()]

def get_voice_info(api_key, voice_id):
    """ভয়েসের নাম এবং ক্যাটাগরি ডিটেলস বের করে লগে দেখানোর জন্য"""
    try:
        url = "https://api.elevenlabs.io/v1/voices"
        headers = {"xi-api-key": api_key}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            voices = resp.json().get("voices", [])
            for v in voices:
                if v.get("voice_id") == voice_id:
                    return f"'{v.get('name')}' (Category: {v.get('category')}, ID: {voice_id})"
    except Exception:
        pass
    return f"ID: {voice_id}"

def generate_voiceover_audio_pipeline(text, output_audio_path):
    """
    🌟 ElevenLabs Eleven v3 মডেল দিয়ে অডিও তৈরি এবং অত্যন্ত স্পষ্ট ও বিস্তারিত লগ প্রিন্ট করে
    """
    print("\n" + "="*65)
    print("🎙️ [AUDIO ENGINE] Starting ElevenLabs Voiceover Pipeline")
    print("="*65)

    # ১. স্ক্রিপ্ট প্রসেসিং ও প্রিভিউ
    raw_chars = len(text) if text else 0
    speech_text = clean_script_for_speech(text)
    clean_chars = len(speech_text)
    words = len(speech_text.split())

    print(f"📊 [Text Analysis] Raw: {raw_chars} chars ➔ Clean: {clean_chars} chars | Words: {words}")
    print(f"📝 [Script Preview]: \"{speech_text[:140]}...\"\n")

    # ২. এপিআই কী চেক
    eleven_keys = get_all_elevenlabs_keys()
    if not eleven_keys:
        print("❌ [CRITICAL ERROR] No ElevenLabs API keys found in environment secrets!")
        print("="*65 + "\n")
        return False

    print(f"🔑 [API Key Pool] Total {len(eleven_keys)} ElevenLabs key(s) loaded.")

    target_voice_id = os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID).strip() or DEFAULT_VOICE_ID
    tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{target_voice_id}"

    payload = {
        "text": speech_text,
        "model_id": "eleven_v3",
        "language_code": "bn",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    # ৩. কী-ভিত্তিক রিকোয়েস্ট লুপ
    for idx, api_key in enumerate(eleven_keys, start=1):
        masked = mask_key(api_key)
        voice_desc = get_voice_info(api_key, target_voice_id)

        print(f"\n--- [Attempting Key #{idx}/{len(eleven_keys)}] ---")
        print(f"  • Active Key    : {masked}")
        print(f"  • Target Voice  : {voice_desc}")
        print(f"  • AI Model      : eleven_v3 (Language: 'bn' - Bengali)")
        print(f"  • Voice Tuning  : Stability=0.5, SimilarityBoost=0.75")
        print(f"  • Endpoint URL  : {tts_url}")

        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }

        start_time = time.time()
        try:
            print("  ⏳ Sending synthesis request to ElevenLabs API...")
            resp = requests.post(tts_url, json=payload, headers=headers, timeout=120)
            elapsed = round(time.time() - start_time, 2)

            print(f"  📥 Server Response: HTTP {resp.status_code} (Response Time: {elapsed}s)")

            if resp.status_code == 200:
                audio_bytes = len(resp.content)
                audio_mb = round(audio_bytes / (1024 * 1024), 2)
                
                with open(output_audio_path, "wb") as f:
                    f.write(resp.content)

                print(f"  ✅ [SUCCESS] Bengali Voiceover Generated Successfully!")
                print(f"  📁 Saved Path  : {output_audio_path} ({audio_mb} MB / {audio_bytes:,} bytes)")
                print("="*65 + "\n")
                return True

            else:
                print(f"  ⚠️ [FAILED] Server returned status code: {resp.status_code}")
                print(f"  📄 Error Body  : {resp.text[:400]}")
                
                if resp.status_code in [401, 402, 429] or "quota" in resp.text.lower() or "credit" in resp.text.lower():
                    print("  🔄 Reason      : Quota/Credit limit reached or invalid key. Switching to next key...")
                else:
                    print("  🔄 Reason      : Unexpected API error. Switching to next key...")
                continue

        except requests.exceptions.Timeout:
            print(f"  ❌ [TIMEOUT] Request timed out after 120 seconds with Key #{idx}.")
            continue
        except Exception as e:
            print(f"  ❌ [ERROR] Network/Connection error with Key #{idx}: {e}")
            continue

    print("\n" + "="*65)
    print("❌ [ALL KEYS EXHAUSTED] Audio generation failed across all available keys.")
    print("="*65 + "\n")
    return False
