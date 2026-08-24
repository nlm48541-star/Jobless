# -*- coding: utf-8 -*-
import os, re, requests

DEFAULT_BENGALI_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"

def get_all_elevenlabs_keys():
    raw_keys = os.environ.get("ELEVENLABS_API_KEYS", os.environ.get("ELEVENLABS_API_KEY", "")).strip()
    if not raw_keys: return []
    return [k.strip() for k in re.split(r'[\r\n,;]+', raw_keys) if k.strip()]

def generate_voiceover_audio_pipeline(text, output_audio_path):
    """
    🌟 শুধুমাত্র ElevenLabs এপিআই কি-গুলো ঘুরিয়ে অডিও তৈরি করে।
    ব্যর্থ হলে কোনো ফলব্যাক ছাড়া সরাসরি False রিটার্ন করবে।
    """
    eleven_keys = get_all_elevenlabs_keys()
    
    if not eleven_keys:
        print("❌ No ElevenLabs API keys provided in secrets. Audio generation aborted.")
        return False

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{DEFAULT_BENGALI_VOICE_ID}"
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }

    for idx, api_key in enumerate(eleven_keys, start=1):
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        try:
            print(f"🎙️ Synthesizing with ElevenLabs Key #{idx}/{len(eleven_keys)}...")
            resp = requests.post(url, json=payload, headers=headers, timeout=45)
            
            if resp.status_code == 200:
                with open(output_audio_path, "wb") as f:
                    f.write(resp.content)
                print(f"✅ Successfully generated ElevenLabs audio using Key #{idx}!")
                return True
            elif resp.status_code in [401, 429] or "quota" in resp.text.lower() or "credit" in resp.text.lower():
                print(f"⚠️ ElevenLabs Key #{idx} quota exhausted or invalid. Trying next key...")
                continue
            else:
                print(f"⚠️ Key #{idx} returned {resp.status_code}: {resp.text[:100]}. Trying next...")
                continue
        except Exception as e:
            print(f"⚠️ Network error with Key #{idx}: {e}. Trying next...")
            continue

    print("❌ All ElevenLabs API keys failed. Audio generation cancelled.")
    return False
