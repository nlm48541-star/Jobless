# -*- coding: utf-8 -*-
import os, re, requests

FALLBACK_FREE_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"

def get_all_elevenlabs_keys():
    raw_keys = os.environ.get("ELEVENLABS_API_KEYS", os.environ.get("ELEVENLABS_API_KEY", "")).strip()
    if not raw_keys: return []
    return [k.strip() for k in re.split(r'[\r\n,;]+', raw_keys) if k.strip()]

def get_available_voice_id(api_key):
    """
    অ্যাকাউন্টে থাকা যেকোনো সক্রিয় ভয়েস আইডি ডাইনামিকভাবে খুঁজে বের করে।
    """
    try:
        url = "https://api.elevenlabs.io/v1/voices"
        headers = {"xi-api-key": api_key}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            voices = resp.json().get("voices", [])
            for v in voices:
                if v.get("category") in ["premade", "generated"]:
                    return v.get("voice_id")
    except Exception:
        pass
    return FALLBACK_FREE_VOICE_ID

def generate_voiceover_audio_pipeline(text, output_audio_path):
    """
    🌟 ElevenLabs 'Eleven v3' মডেল ব্যবহার করে খাঁটি ও স্পষ্ট বাংলা অডিও তৈরি করে।
    """
    eleven_keys = get_all_elevenlabs_keys()
    
    if not eleven_keys:
        print("❌ No ElevenLabs API keys provided in secrets. Audio generation aborted.")
        return False

    for idx, api_key in enumerate(eleven_keys, start=1):
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        
        voice_id = get_available_voice_id(api_key)
        tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        # 🌟 Eleven v3 মডেল কনফিগারেশন
        payload = {
            "text": text,
            "model_id": "eleven_v3",
            "voice_settings": {
                "stability": 0.5
            }
        }

        try:
            print(f"🎙️ Synthesizing with ElevenLabs Key #{idx}/{len(eleven_keys)} (Model: Eleven v3 | Voice: {voice_id})...")
            resp = requests.post(tts_url, json=payload, headers=headers, timeout=90)
            
            if resp.status_code == 200:
                with open(output_audio_path, "wb") as f:
                    f.write(resp.content)
                print(f"✅ Successfully generated Eleven v3 Bengali audio using Key #{idx}!")
                return True
            elif resp.status_code in [401, 402, 429] or "quota" in resp.text.lower() or "credit" in resp.text.lower():
                print(f"⚠️ Key #{idx} failed ({resp.status_code}): {resp.text[:100]}. Trying next key...")
                continue
            else:
                print(f"⚠️ Key #{idx} returned {resp.status_code}: {resp.text[:100]}. Trying next key...")
                continue
        except Exception as e:
            print(f"⚠️ Network error with Key #{idx}: {e}. Trying next...")
            continue

    print("❌ All ElevenLabs API keys failed. Audio generation cancelled.")
    return False
