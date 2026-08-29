# -*- coding: utf-8 -*-
import os, re, requests

# 🌟 আপনার টেস্ট করা চমৎকার 'Mark - Natural Conversations' ভয়েস আইডি
MARK_VOICE_ID = "UgBBYS2sOqTuMpoF3BR0"

def get_all_elevenlabs_keys():
    raw_keys = os.environ.get("ELEVENLABS_API_KEYS", os.environ.get("ELEVENLABS_API_KEY", "")).strip()
    if not raw_keys: return []
    return [k.strip() for k in re.split(r'[\r\n,;]+', raw_keys) if k.strip()]

def get_available_voice_id(api_key):
    """
    অ্যাকাউন্টে Mark ভয়েস থাকলে সেটি অগ্রাধিকার দেবে, না থাকলে সক্রিয় যেকোনো ফ্রি ভয়েস নেবে।
    """
    # ব্যবহারকারী যদি গিটহাব সিক্রেটসে ELEVENLABS_VOICE_ID দিয়ে থাকে তবে সেটি নেবে
    env_voice = os.environ.get("ELEVENLABS_VOICE_ID", "").strip()
    if env_voice:
        return env_voice

    try:
        url = "https://api.elevenlabs.io/v1/voices"
        headers = {"xi-api-key": api_key}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            voices = resp.json().get("voices", [])
            
            # ১. প্রথমে 'Mark' ভয়েস খুঁজবে
            for v in voices:
                if "mark" in v.get("name", "").lower():
                    return v.get("voice_id")
            
            # ২. না পেলে ব্যবহারকারীর কাস্টম তৈরি করা কোনো ভয়েস খুঁজবে
            for v in voices:
                if v.get("category") == "generated":
                    return v.get("voice_id")
                    
            # ৩. অন্যথায় প্রথম সক্রিয় ফ্রি ভয়েস
            for v in voices:
                if v.get("category") == "premade":
                    return v.get("voice_id")
    except Exception:
        pass
        
    return MARK_VOICE_ID

def generate_voiceover_audio_pipeline(text, output_audio_path):
    """
    🌟 ElevenLabs 'Eleven v3' মডেল এবং 'language_code: bn' ব্যবহার করে 
    ওয়েবসাইটের মতো খাঁটি ও নিখুঁত বাংলা অডিও তৈরি করে।
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
        
        # 🌟 Eleven v3 + বাংলা ভাষা বাধ্যতামূলক কনফিগারেশন
        payload = {
            "text": text,
            "model_id": "eleven_v3",
            "language_code": "bn",  # 🔥 এটিই ব্রাউজারের মতো ১০০% স্বাভাবিক বাংলা উচ্চারণ নিশ্চিত করে
            "voice_settings": {
                "stability": 0.5
            }
        }

        try:
            print(f"🎙️ Synthesizing with ElevenLabs Key #{idx}/{len(eleven_keys)} (Model: Eleven v3 | Lang: Bengali | Voice: {voice_id})...")
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
