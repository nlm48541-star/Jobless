# -*- coding: utf-8 -*-
import os, re, time, requests

# 🌟 ফ্রি এপিআই-এর জন্য অনুমোদিত সবচেয়ে সেরা পুরুষ কণ্ঠ (George - News Anchor Tone)
FREE_PERMITTED_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"

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
    raw_keys = os.environ.get("ELEVENLABS_API_KEYS", os.environ.get("ELEVENLABS_API_KEY", "")).strip()
    if not raw_keys: return []
    return [k.strip() for k in re.split(r'[\r\n,;]+', raw_keys) if k.strip()]

def get_best_free_voice(api_key):
    """
    অ্যাকাউন্ট স্ক্যান করে শুধুমাত্র ফ্রি-অনুমোদিত (premade বা generated) ভয়েস সিলেক্ট করে।
    লাইব্রেরি/প্রফেশনাল ভয়েস এড়িয়ে চলে যাতে 402 এরর না আসে।
    """
    try:
        url = "https://api.elevenlabs.io/v1/voices"
        headers = {"xi-api-key": api_key}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            voices = resp.json().get("voices", [])
            
            # ১. ব্যবহারকারীর তৈরি কাস্টম ভয়েস
            for v in voices:
                if v.get("category") == "generated":
                    return v.get("voice_id"), f"'{v.get('name')}' (Custom Generated)"
            
            # ২. ডিফল্ট সেরা ফ্রি পুরুষ ভয়েস (George / Adam)
            for v in voices:
                if v.get("category") == "premade" and "george" in v.get("name", "").lower():
                    return v.get("voice_id"), f"'{v.get('name')}' (Premade Official)"
            for v in voices:
                if v.get("category") == "premade" and "adam" in v.get("name", "").lower():
                    return v.get("voice_id"), f"'{v.get('name')}' (Premade Official)"
                    
            # ৩. যেকোনো সক্রিয় premade ভয়েস
            for v in voices:
                if v.get("category") == "premade":
                    return v.get("voice_id"), f"'{v.get('name')}' (Premade Official)"
    except Exception:
        pass
        
    return FREE_PERMITTED_VOICE_ID, "'George' (Default Premade Official)"

def generate_voiceover_audio_pipeline(text, output_audio_path):
    print("\n" + "="*65)
    print("🎙️ [AUDIO ENGINE] Starting ElevenLabs Eleven v3 Voiceover Pipeline")
    print("="*65)

    speech_text = clean_script_for_speech(text)
    raw_chars = len(text) if text else 0
    clean_chars = len(speech_text)
    words = len(speech_text.split())

    print(f"📊 [Text Analysis] Raw: {raw_chars} chars ➔ Clean: {clean_chars} chars | Words: {words}")
    print(f"📝 [Script Preview]: \"{speech_text[:140]}...\"\n")

    eleven_keys = get_all_elevenlabs_keys()
    if not eleven_keys:
        print("❌ [CRITICAL ERROR] No ElevenLabs API keys found in secrets!")
        print("="*65 + "\n")
        return False

    print(f"🔑 [API Key Pool] Total {len(eleven_keys)} ElevenLabs key(s) loaded.")

    for idx, api_key in enumerate(eleven_keys, start=1):
        masked = mask_key(api_key)
        voice_id, voice_name = get_best_free_voice(api_key)
        tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

        print(f"\n--- [Attempting Key #{idx}/{len(eleven_keys)}] ---")
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

                print(f"  ✅ [SUCCESS] Eleven v3 Bengali Voiceover Generated Successfully!")
                print(f"  📁 Saved Path  : {output_audio_path} ({audio_mb} MB / {audio_bytes:,} bytes)")
                print("="*65 + "\n")
                return True

            else:
                print(f"  ⚠️ [FAILED] Server returned status code: {resp.status_code}")
                print(f"  📄 Error Body  : {resp.text[:300]}")
                
                if resp.status_code in [401, 402, 429] or "quota" in resp.text.lower() or "credit" in resp.text.lower():
                    print("  🔄 Reason      : Quota exhausted or invalid key. Trying next key...")
                else:
                    print("  🔄 Reason      : API error. Trying next key...")
                continue

        except requests.exceptions.Timeout:
            print(f"  ❌ [TIMEOUT] Request timed out after 120s with Key #{idx}.")
            continue
        except Exception as e:
            print(f"  ❌ [ERROR] Network exception with Key #{idx}: {e}")
            continue

    print("\n" + "="*65)
    print("❌ [ALL KEYS EXHAUSTED] Audio generation failed across all keys.")
    print("="*65 + "\n")
    return False
