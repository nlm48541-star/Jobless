# -*- coding: utf-8 -*-
import os, re, time, shutil, requests, subprocess

LOCAL_MODELS_DIR = os.path.join("workspace", "local_tts_models")
MAX_SPACE_WAIT_SECONDS = 600  # প্রতিটি মডেলের জন্য সর্বোচ্চ ১০ মিনিট অপেক্ষা

def clean_script_for_speech(raw_text):
    if not raw_text: return ""
    text = re.sub(r'[\*\_\|\#\~]', '', raw_text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'https?://\S+|wa\.me/\S+', '', text)
    text = re.sub(r'[\<\>\{\}\(\)\@\$\^\&\+\=\_\\\/]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def create_gradio_client(space_name, hf_token=None):
    """
    🌟 gradio_client এর নতুন (token) ও পুরোনো (hf_token) সব ভার্সন সাপোর্ট করে
    """
    from gradio_client import Client
    if not hf_token:
        return Client(space_name)
    try:
        # নতুন gradio_client ভার্সনে 'token' ব্যবহৃত হয়
        return Client(space_name, token=hf_token)
    except TypeError:
        try:
            # পুরোনো ভার্সনে 'hf_token' ব্যবহৃত হতো
            return Client(space_name, hf_token=hf_token)
        except TypeError:
            return Client(space_name, headers={"Authorization": f"Bearer {hf_token}"})

# =========================================================================
# 🌟 ১০ মিনিট ওয়েট-লুপ হ্যান্ডলার (Generic Space Polling Runner)
# =========================================================================

def execute_space_with_10min_wait(space_name, predict_call, output_audio_path, hf_token=None):
    try:
        from gradio_client import Client
    except ImportError:
        print("  ⚠️ 'gradio_client' module not installed. Skipping Cloud Space...")
        return False

    print(f"\n  🚀 Connecting to Space: '{space_name}' (Max wait: 10m / {MAX_SPACE_WAIT_SECONDS}s)...")
    start_time = time.time()
    retry_count = 0

    while (time.time() - start_time) < MAX_SPACE_WAIT_SECONDS:
        elapsed = int(time.time() - start_time)
        retry_count += 1
        
        try:
            print(f"  ⏳ [Attempt #{retry_count}] Connecting/Checking Space (Elapsed: {elapsed}s/{MAX_SPACE_WAIT_SECONDS}s)...")
            client = create_gradio_client(space_name, hf_token)
            
            result = predict_call(client)
            
            if result and os.path.exists(result) and os.path.getsize(result) > 1000:
                shutil.copyfile(result, output_audio_path)
                total_time = round(time.time() - start_time, 2)
                audio_mb = round(os.path.getsize(output_audio_path) / (1024 * 1024), 2)
                print(f"  ✅ [SUCCESS] Synthesized via '{space_name}'! ({audio_mb} MB in {total_time}s)")
                return True

        except TypeError as te:
            # যদি কোনো আর্গুমেন্ট টাইপ এরর হয়, তবে বারবার ১০ মিনিট অপেক্ষা না করে সাথে সাথে ব্রেক করবে
            print(f"  ⚠️ Gradio Client Argument Error: {te}")
            break

        except Exception as e:
            err_msg = str(e).strip().replace('\n', ' ')
            print(f"  ℹ️ Space is booting/warming up: {err_msg[:90]}...")
            time.sleep(20)

    print(f"  ❌ [TIMEOUT] Space '{space_name}' did not complete within 10 minutes.")
    return False

# =========================================================================
# 🌟 শীর্ষ ৩টি Hugging Face ক্লাউড জিপিইউ স্পেস
# =========================================================================

def try_indic_parler_space(speech_text, output_audio_path, hf_token):
    """১. AI4Bharat Indic Parler-TTS Space"""
    desc_prompt = "A clear, professional Bengali male news anchor with confident tone and natural pace."
    def _call(client):
        return client.predict(text=speech_text, description=desc_prompt, api_name="/predict")
    return execute_space_with_10min_wait("ai4bharat/indic-parler-tts", _call, output_audio_path, hf_token)

def try_cosyvoice_space(speech_text, output_audio_path, hf_token):
    """২. BUET Bengali CosyVoice 3 Space"""
    def _call(client):
        return client.predict(text=speech_text, api_name="/predict")
    return execute_space_with_10min_wait("kawshikbuet17/bengali-cosyvoice3-tts-demo", _call, output_audio_path, hf_token)

def try_orpheus_space(speech_text, output_audio_path, hf_token):
    """৩. Orpheus Bangla Emotional TTS Space"""
    def _call(client):
        return client.predict(text=speech_text, emotion="normal", api_name="/predict")
    return execute_space_with_10min_wait("ehzawad/orpheus-bangla-emotional-tts-demo", _call, output_audio_path, hf_token)

# =========================================================================
# 🌟 অফলাইন / লোকাল ফলব্যাক ইঞ্জিনসমূহ
# =========================================================================

def synthesize_with_edge_fallback(speech_text, output_audio_path):
    try:
        import asyncio, edge_tts
        print("\n  🎙️ [FALLBACK] Synthesizing via Microsoft Neural Engine (bn-BD-PradeepNeural)...")
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

        print("  🎙️ [FALLBACK] Synthesizing via Piper Local ONNX Engine...")
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
    try:
        import torch, scipy.io.wavfile
        from transformers import AutoTokenizer, VitsModel
        print("\n  🎙️ [FALLBACK] Synthesizing via Meta MMS Local CPU Model...")
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
    print("🎙️ [AUDIO ENGINE] Multi-Space 10-Min Wait & Local Fallback Active")
    print(f"📊 [Text Stats] Chars: {clean_chars} | Words: {words}")
    print(f"📝 [Preview]: \"{speech_text[:120]}...\"")
    print("="*65)

    hf_token = os.environ.get("HF_TOKEN", os.environ.get("HUGGINGFACE_TOKEN", "")).strip()

    # ধাপ ১: Hugging Face শীর্ষ ৩টি জিপিইউ স্পেস পর্যায়ক্রমে ট্রাই করা
    space_runners = [
        try_indic_parler_space,
        try_cosyvoice_space,
        try_orpheus_space
    ]

    for runner in space_runners:
        if runner(speech_text, output_audio_path, hf_token):
            if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 1000:
                print("\n" + "="*65)
                print("🎉 [FINAL RESULT] Voiceover synthesized via Hugging Face Cloud GPU!")
                print("="*65 + "\n")
                return True

    # ধাপ ২: ফলব্যাক ইঞ্জিন এক্সিকিউশন
    print("\n⚠️ All Hugging Face Spaces unavailable or timed out. Engaging Fallback...")
    fallback_choice = os.environ.get("TTS_ENGINE", "edge").strip().lower()

    if "piper" in fallback_choice:
        if synthesize_with_piper_fallback(speech_text, output_audio_path): return True
        if synthesize_with_edge_fallback(speech_text, output_audio_path): return True
    elif "mms" in fallback_choice:
        if synthesize_with_local_mms_fallback(speech_text, output_audio_path): return True
        if synthesize_with_edge_fallback(speech_text, output_audio_path): return True
    else:
        if synthesize_with_edge_fallback(speech_text, output_audio_path): return True
        if synthesize_with_piper_fallback(speech_text, output_audio_path): return True

    print("\n❌ [CRITICAL] All TTS pipelines failed.")
    return False
