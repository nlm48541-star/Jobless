# -*- coding: utf-8 -*-
import os, re, time, shutil, requests, subprocess
from gradio_client import Client, handle_file

LOCAL_MODELS_DIR = os.path.join("workspace", "local_tts_models")
MAX_SPACE_WAIT_SECONDS = 180  # স্পেস চালু হওয়ার জন্য সর্বোচ্চ ৩ মিনিট অপেক্ষা

def clean_script_for_speech(raw_text):
    if not raw_text: return ""
    text = re.sub(r'[\*\_\|\#\~]', '', raw_text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'https?://\S+|wa\.me/\S+', '', text)
    text = re.sub(r'[\<\>\{\}\(\)\@\$\^\&\+\=\_\\\/]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def create_gradio_client(space_name, hf_token=None):
    from gradio_client import Client
    if not hf_token:
        return Client(space_name)
    try:
        return Client(space_name, token=hf_token)
    except TypeError:
        try:
            return Client(space_name, hf_token=hf_token)
        except TypeError:
            return Client(space_name, headers={"Authorization": f"Bearer {hf_token}"})

def execute_space_smart(space_name, predict_call, output_audio_path, hf_token=None):
    try:
        from gradio_client import Client
    except ImportError:
        return False

    print(f"\n  🚀 Connecting to Space: '{space_name}'...")
    start_time = time.time()
    retry_count = 0

    while (time.time() - start_time) < MAX_REAL_WAIT_SECONDS:
        elapsed = int(time.time() - start_time)
        retry_count += 1
        
        try:
            client = create_gradio_client(space_name, hf_token)
            result = predict_call(client)
            
            # অডিও রেজাল্ট হ্যান্ডলিং
            out_file = result
            if isinstance(result, (list, tuple)) and len(result) > 0:
                out_file = result[0]
            if isinstance(out_file, dict) and 'name' in out_file:
                out_file = out_file['name']

            if out_file and os.path.exists(out_file) and os.path.getsize(out_file) > 1000:
                shutil.copyfile(out_file, output_audio_path)
                total_time = round(time.time() - start_time, 2)
                audio_mb = round(os.path.getsize(output_audio_path) / (1024 * 1024), 2)
                print(f"  ✅ [SUCCESS] Synthesized via '{space_name}'! ({audio_mb} MB in {total_time}s)")
                return True

        except Exception as e:
            err_str = str(e).lower()
            if any(term in err_str for term in ['404', 'not found', 'entrynotfound', 'could not find', 'does not exist']):
                print(f"  ❌ Space '{space_name}' not found (404). Skipping in 0.1s!")
                return False
                
            if any(term in err_str for term in ['401', 'unauthorized', 'permission', 'gated']):
                print(f"  ❌ Space '{space_name}' access restricted (401). Skipping!")
                return False

            print(f"  ⏳ Space is booting/generating (Elapsed: {elapsed}s/{MAX_REAL_WAIT_SECONDS}s)...")
            time.sleep(15)

    print(f"  ⚠️ Space '{space_name}' did not complete within {MAX_REAL_WAIT_SECONDS}s. Moving to next...")
    return False

# =========================================================================
# 🌟 ১. প্রায়োরিটি ১: AI4Bharat Indic Parler-TTS Space (আপনার ডুপ্লিকেট স্পেস)
# =========================================================================

def try_indic_parler_space(speech_text, output_audio_path, hf_token):
    # ব্যবহারকারীর ডুপ্লিকেট স্পেস থাকলে সেটি ব্যবহার করবে, না থাকলে পাবলিক ডেমো
    user_space = os.environ.get("MY_PARLER_SPACE", "KAGUNOSID/indic-parler-tts-demo").strip()
    desc_prompt = "A clear, professional Bengali male news anchor with confident tone and natural pace."

    def _call(client):
        try:
            # বাংলা স্ক্রিপ্ট ও প্রম্পট পাস করা
            return client.predict(
                text=speech_text, 
                description=desc_prompt, 
                api_name="/predict"
            )
        except Exception:
            # অল্টারনেট এপিআই এন্ডপয়েন্ট সাপোর্ট
            return client.predict(
                "Bengali (বাংলা)",
                speech_text,
                desc_prompt,
                api_name="/synthesize"
            )

    return execute_space_smart(user_space, _call, output_audio_path, hf_token)

# =========================================================================
# 🌟 ২. প্রায়োরিটি ২ (দ্বিতীয় ফলব্যাক): BUET Bengali CosyVoice 3 Space
# =========================================================================

def try_cosyvoice_space(speech_text, output_audio_path, hf_token):
    print("\n  🌟 [2nd Fallback] Connecting to High-Quality Bengali CosyVoice 3 Space...")
    
    def _call(client):
        # CosyVoice3 ক্রস-লিঙ্গুয়াল ক্লোনিং এপিআই
        try:
            return client.predict(
                tts_text=speech_text,
                prompt_wav=None,
                speed=1.0,
                seed=0,
                api_name="/predict"
            )
        except Exception:
            return client.predict(
                speech_text,
                api_name="/predict"
            )

    return execute_space_smart("kawshikbuet17/bengali-cosyvoice3-tts-demo", _call, output_audio_path, hf_token)

# =========================================================================
# 🌟 ৩. জরুরি ব্যাকআপ ইঞ্জিনসমূহ (Edge / Piper / MMS - মাত্র ১০ সেকেন্ড)
# =========================================================================

def synthesize_with_edge_fallback(speech_text, output_audio_path):
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
        print(f"  ⚠️ Edge fallback notice: {e}")
    return False

def synthesize_with_piper_fallback(speech_text, output_audio_path):
    try:
        os.makedirs(LOCAL_MODELS_DIR, exist_ok=True)
        model_path = os.path.join(LOCAL_MODELS_DIR, "bn_IN-biswas-medium.onnx")
        json_path = os.path.join(LOCAL_MODELS_DIR, "bn_IN-biswas-medium.onnx.json")
        base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/bn/bn_IN/biswas/medium/"

        if not os.path.exists(model_path):
            r = requests.get(base_url + "bn_IN-biswas-medium.onnx", timeout=60)
            if r.status_code == 200:
                with open(model_path, "wb") as f: f.write(r.content)
            r2 = requests.get(base_url + "bn_IN-biswas-medium.onnx.json", timeout=30)
            if r2.status_code == 200:
                with open(json_path, "wb") as f: f.write(r2.content)

        cmd = ["piper", "--model", model_path, "--output_file", output_audio_path]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        proc.communicate(input=speech_text, timeout=120)

        if proc.returncode == 0 and os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 2000:
            return True
    except Exception: pass
    return False

# =========================================================================
# 🌟 মূল অডিও পাইপলাইন (Main Orchestrator)
# =========================================================================

def generate_voiceover_audio_pipeline(text, output_audio_path):
    speech_text = clean_script_for_speech(text)
    clean_chars = len(speech_text)
    words = len(speech_text.split())

    print("\n" + "="*65)
    print("🎙️ [AUDIO ENGINE] Parler-TTS ➔ CosyVoice3 ➔ Emergency Backup Active")
    print(f"📊 [Text Stats] Chars: {clean_chars} | Words: {words}")
    print(f"📝 [Preview]: \"{speech_text[:120]}...\"")
    print("="*65)

    hf_token = os.environ.get("HF_TOKEN", os.environ.get("HUGGINGFACE_TOKEN", "")).strip()

    # 🌟 ধাপ ১: AI4Bharat Indic Parler-TTS Space ট্রাই করা
    if try_indic_parler_space(speech_text, output_audio_path, hf_token):
        if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
            return True

    # 🌟 ধাপ ২: দ্বিতীয় ফলব্যাক - BUET Bengali CosyVoice 3 ট্রাই করা (উচ্চমানের কোয়ালিটি)
    if try_cosyvoice_space(speech_text, output_audio_path, hf_token):
        if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
            return True

    # 🌟 ধাপ ৩: জরুরি দ্রুততম ব্যাকআপ (মাত্র ১০ সেকেন্ডে তৈরি করবে)
    print("\n⚠️ Cloud Spaces busy or slow. Engaging Instant Emergency Backup...")
    fallback_choice = os.environ.get("TTS_ENGINE", "edge").strip().lower()

    if "piper" in fallback_choice:
        if synthesize_with_piper_fallback(speech_text, output_audio_path): return True
        if synthesize_with_edge_fallback(speech_text, output_audio_path): return True
    else:
        if synthesize_with_edge_fallback(speech_text, output_audio_path): return True
        if synthesize_with_piper_fallback(speech_text, output_audio_path): return True

    print("\n❌ [CRITICAL] All TTS pipelines failed.")
    return False
