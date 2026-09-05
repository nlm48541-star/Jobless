# -*- coding: utf-8 -*-
import os, re, time, shutil, requests, subprocess

LOCAL_MODELS_DIR = os.path.join("workspace", "local_tts_models")
MAX_REAL_WAIT_SECONDS = 150  # 🌟 আসল স্পেস চালু হওয়ার জন্য সর্বোচ্চ ২.৫ মিনিট অপেক্ষা

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

# =========================================================================
# 🌟 স্মার্ট স্পেস রানার (404 / 401 পেলে অবিলম্বে স্কিপ করবে)
# =========================================================================

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
            
            if result and os.path.exists(result) and os.path.getsize(result) > 1000:
                shutil.copyfile(result, output_audio_path)
                total_time = round(time.time() - start_time, 2)
                audio_mb = round(os.path.getsize(output_audio_path) / (1024 * 1024), 2)
                print(f"  ✅ [SUCCESS] Synthesized via '{space_name}'! ({audio_mb} MB in {total_time}s)")
                return True

        except Exception as e:
            err_str = str(e).lower()
            
            # 🌟 [ম্যাজিক ফিক্স]: 404 (ফাইল নেই) বা 401 (লক) পেলে সাথে সাথে স্কিপ করবে, ০ সেকেন্ডও অপেক্ষা করবে না
            if any(term in err_str for term in ['404', 'not found', 'entrynotfound', 'could not find', 'does not exist']):
                print(f"  ❌ Space '{space_name}' does not exist (404 Not Found). Skipping instantly in 0.1s!")
                return False
                
            if any(term in err_str for term in ['401', 'unauthorized', 'permission', 'gated']):
                print(f"  ❌ Space '{space_name}' access restricted (401). Skipping instantly!")
                return False

            # শুধুমাত্র আসল লোডিং এরর হলে অপেক্ষা করবে
            print(f"  ⏳ Space is booting (Elapsed: {elapsed}s/{MAX_REAL_WAIT_SECONDS}s)...")
            time.sleep(15)

    print(f"  ⚠️ Space '{space_name}' did not respond within {MAX_REAL_WAIT_SECONDS}s. Moving forward...")
    return False

# =========================================================================
# 🌟 Hugging Face ক্লাউড জিপিইউ স্পেস চেইন
# =========================================================================

def try_indic_parler_space(speech_text, output_audio_path, hf_token):
    """১. AI4Bharat Indic Parler-TTS Space"""
    desc_prompt = "A clear, professional Bengali male news anchor with confident tone and natural pace."
    def _call(client):
        return client.predict(text=speech_text, description=desc_prompt, api_name="/predict")
    return execute_space_smart("ai4bharat/indic-parler-tts", _call, output_audio_path, hf_token)

def try_cosyvoice_space(speech_text, output_audio_path, hf_token):
    """২. BUET Bengali CosyVoice 3 Space"""
    def _call(client):
        return client.predict(text=speech_text, api_name="/predict")
    return execute_space_smart("kawshikbuet17/bengali-cosyvoice3-tts-demo", _call, output_audio_path, hf_token)

def try_orpheus_space(speech_text, output_audio_path, hf_token):
    """৩. Orpheus Bangla Emotional TTS Space"""
    def _call(client):
        return client.predict(text=speech_text, emotion="normal", api_name="/predict")
    return execute_space_smart("ehzawad/orpheus-bangla-emotional-tts-demo", _call, output_audio_path, hf_token)

# =========================================================================
# 🌟 অফলাইন / লোকাল ফলব্যাক ইঞ্জিনসমূহ (যা মাত্র ১০–১৫ সেকেন্ডে অডিও তৈরি করে)
# =========================================================================

def synthesize_with_edge_fallback(speech_text, output_audio_path):
    """মাইক্রোসফট ফাস্ট নিউরাল ইঞ্জিন (bn-BD-PradeepNeural)"""
    try:
        import asyncio, edge_tts
        print("\n  🎙️ [LOCAL FALLBACK] Synthesizing via Microsoft Neural Engine (bn-BD-PradeepNeural)...")
        start_t = time.time()
        async def _make():
            c = edge_tts.Communicate(speech_text, "bn-BD-PradeepNeural", rate="+0%", pitch="+0Hz")
            await c.save(output_audio_path)
        asyncio.run(_make())
        if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
            elapsed = round(time.time() - start_t, 2)
            audio_mb = round(os.path.getsize(output_audio_path) / (1024 * 1024), 2)
            print(f"  ✅ [SUCCESS] Generated via Microsoft Neural Backup! ({audio_mb} MB in {elapsed}s)")
            return True
    except Exception as e:
        print(f"  ⚠️ Edge fallback notice: {e}")
    return False

def synthesize_with_piper_fallback(speech_text, output_audio_path):
    """Piper লোকাল ONNX ইঞ্জিন"""
    try:
        os.makedirs(LOCAL_MODELS_DIR, exist_ok=True)
        model_path = os.path.join(LOCAL_MODELS_DIR, "bn_IN-biswas-medium.onnx")
        json_path = os.path.join(LOCAL_MODELS_DIR, "bn_IN-biswas-medium.onnx.json")
        base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/bn/bn_IN/biswas/medium/"

        if not os.path.exists(model_path):
            print("  ⏳ Downloading Piper Bengali Model (~60 MB)...")
            r = requests.get(base_url + "bn_IN-biswas-medium.onnx", timeout=60)
            if r.status_code == 200:
                with open(model_path, "wb") as f: f.write(r.content)
            r2 = requests.get(base_url + "bn_IN-biswas-medium.onnx.json", timeout=30)
            if r2.status_code == 200:
                with open(json_path, "wb") as f: f.write(r2.content)

        print("  🎙️ [LOCAL FALLBACK] Synthesizing via Piper Local ONNX Engine...")
        start_t = time.time()
        cmd = ["piper", "--model", model_path, "--output_file", output_audio_path]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        proc.communicate(input=speech_text, timeout=120)

        if proc.returncode == 0 and os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 2000:
            elapsed = round(time.time() - start_t, 2)
            audio_mb = round(os.path.getsize(output_audio_path) / (1024 * 1024), 2)
            print(f"  ✅ [SUCCESS] Generated via Piper Local Engine! ({audio_mb} MB in {elapsed}s)")
            return True
    except Exception as e:
        print(f"  ⚠️ Piper fallback notice: {e}")
    return False

def synthesize_with_local_mms_fallback(speech_text, output_audio_path):
    """Meta MMS-TTS লোকাল CPU ইঞ্জিন"""
    try:
        import torch, scipy.io.wavfile
        from transformers import AutoTokenizer, VitsModel
        print("\n  🎙️ [LOCAL FALLBACK] Synthesizing via Meta MMS Local CPU Model...")
        start_t = time.time()

        tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-ben")
        model = VitsModel.from_pretrained("facebook/mms-tts-ben")

        raw_sentences = re.split(r'([।\?\!\n]+)', speech_text)
        chunks = []
        current = ""
        for p in raw_sentences:
            current += p
            if any(sym in p for sym in ['।', '?', '!', '\n']) or len(current) >= 180:
                if current.strip(): chunks.append(current.strip())
                current = ""
        if current.strip(): chunks.append(current.strip())

        audio_arrays = []
        sampling_rate = model.config.sampling_rate
        pause_samples = np.zeros(int(sampling_rate * 0.2), dtype=np.float32)

        for s in chunks:
            if not s.strip(): continue
            inputs = tokenizer(s, return_tensors="pt")
            with torch.no_grad():
                output = model(**inputs).waveform
            audio_arrays.append(output.squeeze().cpu().numpy().astype(np.float32))
            audio_arrays.append(pause_samples)

        if audio_arrays:
            full_audio = np.concatenate(audio_arrays)
            full_audio = np.clip(full_audio, -1.0, 1.0)
            wav_data = (full_audio * 32767).astype(np.int16)
            scipy.io.wavfile.write(output_audio_path, rate=sampling_rate, data=wav_data)
            elapsed = round(time.time() - start_t, 2)
            audio_mb = round(os.path.getsize(output_audio_path) / (1024 * 1024), 2)
            print(f"  ✅ [SUCCESS] Generated via Meta MMS Local Model! ({audio_mb} MB in {elapsed}s)")
            return True
    except Exception as e:
        print(f"  ⚠️ Meta MMS fallback notice: {e}")
    return False

# =========================================================================
# 🌟 মূল অডিও পাইপলাইন
# =========================================================================

def generate_voiceover_audio_pipeline(text, output_audio_path):
    speech_text = clean_script_for_speech(text)
    clean_chars = len(speech_text)
    words = len(speech_text.split())

    print("\n" + "="*65)
    print("🎙️ [AUDIO ENGINE] High-Speed Smart Space & Fallback Active")
    print(f"📊 [Text Stats] Chars: {clean_chars} | Words: {words}")
    print(f"📝 [Preview]: \"{speech_text[:120]}...\"")
    print("="*65)

    hf_token = os.environ.get("HF_TOKEN", os.environ.get("HUGGINGFACE_TOKEN", "")).strip()

    # ধাপ ১: স্পেসগুলো স্মার্টলি চেক করা (অনুপস্থিত স্পেস ০.১ সেকেন্ডে স্কিপ হবে)
    space_runners = [
        try_indic_parler_space,
        try_cosyvoice_space,
        try_orpheus_space
    ]

    for runner in space_runners:
        if runner(speech_text, output_audio_path, hf_token):
            if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
                print("\n" + "="*65)
                print("🎉 [FINAL RESULT] Voiceover synthesized via Cloud Space!")
                print("="*65 + "\n")
                return True

    # ধাপ ২: সুপারফাস্ট ফলব্যাক ইঞ্জিন (মাত্র ১০–১৫ সেকেন্ডে কাজ শেষ করে)
    print("\n⚠️ Cloud Spaces unavailable. Engaging Fast Local Fallback Engine...")
    fallback_choice = os.environ.get("TTS_ENGINE", "edge").strip().lower()

    if "piper" in fallback_choice:
        if synthesize_with_piper_fallback(speech_text, output_audio_path): return True
        if synthesize_with_edge_fallback(speech_text, output_audio_path): return True
    elif "mms" in fallback_choice:
        if synthesize_with_local_mms_fallback(speech_text, output_audio_path): return True
        if synthesize_with_edge_fallback(speech_text, output_audio_path): return True
    else:
        # ডিফল্ট ফাস্টেস্ট ইঞ্জিন (মাত্র ১১ সেকেন্ড!)
        if synthesize_with_edge_fallback(speech_text, output_audio_path): return True
        if synthesize_with_piper_fallback(speech_text, output_audio_path): return True

    print("\n❌ [CRITICAL] All TTS pipelines failed.")
    return False
