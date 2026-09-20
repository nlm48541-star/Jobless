# -*- coding: utf-8 -*-
import os, re, time, base64, requests

MODAL_TRACKER_FILE = os.path.join("workspace", "modal_key_tracker.txt")

def clean_script_for_speech(raw_text):
    if not raw_text: return ""
    text = re.sub(r'[\*\_\|\#\~]', '', raw_text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'https?://\S+|wa\.me/\S+', '', text)
    text = re.sub(r'[\<\>\{\}\(\)\@\$\^\&\+\=\_\\\/]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_sample_voice_b64():
    """রিপোজিটরি থেকে sample_voice.mp3 লোড করে base64 এ রূপান্তর করে"""
    candidates = ["sample_voice.mp3", "sample_voice.wav", "Photos/sample_voice.mp3", "Photos/sample_voice.wav"]
    for fname in candidates:
        if os.path.exists(fname) and os.path.getsize(fname) > 1000:
            try:
                with open(fname, "rb") as f:
                    return base64.b64encode(f.read()).decode('utf-8')
            except Exception: pass
    return None

def get_all_modal_endpoints():
    """এন্টার (Newline) বা কমা দিয়ে সাজানো সব Modal অ্যাকাউন্টের URL লোড করে"""
    raw_urls = os.environ.get("MODAL_ENDPOINTS", os.environ.get("MODAL_URLS", "")).strip()
    if not raw_urls: return []
    lines = re.split(r'[\r\n,;]+', raw_urls)
    return [u.strip() for u in lines if u.strip() and u.strip().startswith("http")]

def get_saved_modal_index(total_endpoints):
    if total_endpoints == 0: return 0
    if os.path.exists(MODAL_TRACKER_FILE):
        try:
            with open(MODAL_TRACKER_FILE, "r", encoding="utf-8") as f:
                return int(f.read().strip()) % total_endpoints
        except Exception: pass
    return 0

def save_modal_index(idx, total_endpoints):
    if total_endpoints == 0: return
    try:
        os.makedirs(os.path.dirname(MODAL_TRACKER_FILE), exist_ok=True)
        with open(MODAL_TRACKER_FILE, "w", encoding="utf-8") as f:
            f.write(str(idx % total_endpoints))
    except Exception: pass

def synthesize_with_modal_cyclic(speech_text, output_audio_path):
    """
    🌟 সিক্রেটে উল্লেখিত মডেল (cosyvoice/bharat/mms) নিয়ে Modal অ্যাকাউন্টে সাইক্লিক রোটেশন চালায়
    """
    endpoints = get_all_modal_endpoints()
    total_acc = len(endpoints)
    if total_acc == 0:
        print("  ⚠️ No Modal endpoints configured in MODAL_ENDPOINTS secret.")
        return False

    start_idx = get_saved_modal_index(total_acc)
    
    # 🌟 সিক্রেট থেকে ব্যবহারকারীর পছন্দের মডেল রিড করা (cosyvoice, bharat, mms ইত্যাদি)
    chosen_model = os.environ.get("TTS_MODEL", os.environ.get("TTS_ENGINE", "bharat")).strip().lower()
    sample_b64 = get_sample_voice_b64()

    print(f"\n--- [ENGINE: Modal Cloud GPU Multi-Account Pool] ---")
    print(f"🎯 Target Model Selected: '{chosen_model.upper()}'")
    print(f"🔑 Total {total_acc} Modal Account(s) loaded. Resuming from Account #{start_idx + 1}...")

    # সাইক্লিক লুপ
    for offset in range(total_acc):
        current_idx = (start_idx + offset) % total_acc
        endpoint_url = endpoints[current_idx]
        acc_num = current_idx + 1

        print(f"\n  🚀 [Attempting Modal Account #{acc_num}/{total_acc}]")
        print(f"  • Endpoint: {endpoint_url[:45]}...")
        print(f"  • Model   : {chosen_model.upper()}")

        payload = {
            "text": speech_text,
            "model": chosen_model,
            "sample_voice_b64": sample_b64
        }

        start_time = time.time()
        try:
            print(f"  ⏳ Synthesizing with Modal GPU via {chosen_model.upper()}...")
            resp = requests.post(endpoint_url, json=payload, timeout=150)
            elapsed = round(time.time() - start_time, 2)

            if resp.status_code == 200 and len(resp.content) > 3000:
                with open(output_audio_path, "wb") as f:
                    f.write(resp.content)
                
                # সফল হলে ইনডেক্স মেমোরিতে সেভ থাকবে
                save_modal_index(current_idx, total_acc)
                audio_mb = round(os.path.getsize(output_audio_path) / (1024 * 1024), 2)
                print(f"  ✅ [SUCCESS] Generated via Modal Account #{acc_num}! ({audio_mb} MB in {elapsed}s)")
                return True
            else:
                print(f"  ⚠️ Modal Account #{acc_num} failed ({resp.status_code}): {resp.text[:100]}")
                save_modal_index(current_idx + 1, total_acc)
                continue

        except Exception as e:
            print(f"  ⚠️ Error with Modal Account #{acc_num}: {e}")
            save_modal_index(current_idx + 1, total_acc)
            continue

    print("⚠️ All Modal accounts exhausted or unreachable.")
    return False

# =========================================================================
# 🌟 জরুরি অফলাইন ব্যাকআপ ইঞ্জিন (Edge-TTS)
# =========================================================================
def synthesize_with_emergency_backup(speech_text, output_audio_path):
    try:
        import asyncio, edge_tts
        print("\n  🎙️ [EMERGENCY BACKUP] Synthesizing via Microsoft Neural Engine (bn-BD-PradeepNeural)...")
        start_t = time.time()
        async def _make():
            c = edge_tts.Communicate(speech_text, "bn-BD-PradeepNeural", rate="+0%", pitch="+0Hz")
            await c.save(output_audio_path)
        asyncio.run(_make())
        if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
            elapsed = round(time.time() - start_t, 2)
            audio_mb = round(os.path.getsize(output_audio_path) / (1024 * 1024), 2)
            print(f"  ✅ [SUCCESS] Generated via Emergency Neural Backup! ({audio_mb} MB in {elapsed}s)")
            return True
    except Exception as e:
        print(f"  ⚠️ Emergency backup notice: {e}")
    return False

# =========================================================================
# 🌟 মূল অডিও পাইপলাইন
# =========================================================================
def generate_voiceover_audio_pipeline(text, output_audio_path):
    speech_text = clean_script_for_speech(text)
    clean_chars = len(speech_text)
    words = len(speech_text.split())

    print("\n" + "="*65)
    print("🎙️ [AUDIO ENGINE] Dynamic Model Selection & Modal Pool Active")
    print(f"📊 [Text Stats] Chars: {clean_chars} | Words: {words}")
    print(f"📝 [Preview]: \"{speech_text[:120]}...\"")
    print("="*65)

    # ১. প্রথমে Modal ক্লাউড জিপিইউতে ব্যবহারকারীর পছন্দের মডেলে অডিও তৈরি
    if synthesize_with_modal_cyclic(speech_text, output_audio_path):
        if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
            print("\n" + "="*65)
            print("🎉 [FINAL RESULT] Voiceover successfully synthesized via Modal Cloud GPU!")
            print("="*65 + "\n")
            return True

    # ২. যদি সব Modal অ্যাকাউন্টের ক্রেডিট ফুরিয়ে যায়, তবে তাৎক্ষণিক ব্যাকআপ ইঞ্জিন
    print("\n⚠️ Modal pool exhausted. Engaging Instant Emergency Backup...")
    if synthesize_with_emergency_backup(speech_text, output_audio_path):
        return True

    print("\n❌ [CRITICAL] All audio engines failed.")
    return False
