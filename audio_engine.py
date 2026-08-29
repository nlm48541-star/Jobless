# -*- coding: utf-8 -*-
import os, re, requests

# 🌟 আপনার টেস্ট করা সেরা 'Mark - Natural Conversations' ভয়েস আইডি
DEFAULT_VOICE_ID = "UgBBYS2sOqTuMpoF3BR0"

def clean_script_for_speech(raw_text):
    """স্ক্রিপ্ট থেকে সব মার্কডাউন ও অনাকাঙ্ক্ষিত চিহ্ন মুছে স্বাভাবিক বাচনে রূপান্তর করে"""
    if not raw_text:
        return ""
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

def generate_voiceover_audio_pipeline(text, output_audio_path):
    """
    🌟 ElevenLabs 'Eleven v3' এবং Mark ভয়েস দিয়ে ওয়েব ব্রাউজারের মতো নিখুঁত বাংলা অডিও তৈরি করে
    """
    eleven_keys = get_all_elevenlabs_keys()
    if not eleven_keys:
        print("❌ No ElevenLabs API keys provided in secrets. Audio generation aborted.")
        return False

    # স্পিচের জন্য টেক্সট ক্লিন করা
    speech_text = clean_script_for_speech(text)
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID).strip() or DEFAULT_VOICE_ID
    tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    payload = {
        "text": speech_text,
        "model_id": "eleven_v3",
        "language_code": "bn",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    for idx, api_key in enumerate(eleven_keys, start=1):
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }

        try:
            print(f"🎙️ Synthesizing with ElevenLabs Key #{idx}/{len(eleven_keys)} (Model: Eleven v3 | Voice: Mark)...")
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
