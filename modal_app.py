# -*- coding: utf-8 -*-
import modal
from fastapi import Response

app = modal.App("bengali-tts-service")
volume = modal.Volume.from_name("bengali-tts-cache", create_if_missing=True)

# ক্লাউড কন্টেইনার ইমেজ কনফিগারেশন
image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("ffmpeg", "git")
    .pip_install(
        "fastapi[standard]",
        "torch",
        "transformers",
        "soundfile",
        "scipy",
        "numpy",
        "piper-tts",
        "git+https://github.com/huggingface/parler-tts.git"
    )
)

CACHE_DIR = "/cache"

@app.function(
    image=image,
    gpu="T4",
    volumes={CACHE_DIR: volume},
    scaledown_window=60,
    timeout=300
)
@modal.fastapi_endpoint(method="POST")
def generate_speech(data: dict):
    """
    গিটহাবের সিক্রেট অনুযায়ী ঠিক নির্দিষ্ট মডেলটি রান করে অডিও তৈরি করবে
    """
    import torch, io, soundfile as sf
    from transformers import AutoTokenizer

    text = data.get("text", "").strip()
    model_choice = data.get("model", "bharat").strip().lower()

    if not text:
        return Response(content="Empty text", status_code=400)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🎙️ Running Speech Synthesis on {device} (Target Model: {model_choice.upper()})...")

    # =========================================================================
    # 🌟 ১. AI4Bharat Indic Parler-TTS ('bharat' বা 'parler')
    # =========================================================================
    if "bharat" in model_choice or "parler" in model_choice:
        from parler_tts import ParlerTTSForConditionalGeneration
        model_id = "ai4bharat/indic-parler-tts"
        
        tokenizer = AutoTokenizer.from_pretrained(model_id, cache_dir=CACHE_DIR)
        model = ParlerTTSForConditionalGeneration.from_pretrained(model_id, cache_dir=CACHE_DIR).to(device)

        desc = "A clear, professional Bengali male news anchor with confident tone and natural pace."
        desc_inputs = tokenizer(desc, return_tensors="pt").to(device)
        prompt_inputs = tokenizer(text, return_tensors="pt").to(device)

        with torch.no_grad():
            generation = model.generate(input_ids=desc_inputs.input_ids, prompt_input_ids=prompt_inputs.input_ids)

        audio_arr = generation.squeeze().cpu().numpy()
        sampling_rate = model.config.sampling_rate

    # =========================================================================
    # 🌟 ২. Piper Neural TTS ('piper')
    # =========================================================================
    elif "piper" in model_choice:
        import subprocess
        model_path = f"{CACHE_DIR}/bn_IN-biswas-medium.onnx"
        
        # মডেল ক্যাশে না থাকলে একবার ডাউনলোড করে নেওয়া
        if not os.path.exists(model_path):
            import urllib.request
            base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/bn/bn_IN/biswas/medium/"
            urllib.request.urlretrieve(base_url + "bn_IN-biswas-medium.onnx", model_path)
            urllib.request.urlretrieve(base_url + "bn_IN-biswas-medium.onnx.json", model_path + ".json")

        cmd = ["piper", "--model", model_path, "--output_file", f"{CACHE_DIR}/temp.wav"]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        proc.communicate(input=text)
        
        data, sampling_rate = sf.read(f"{CACHE_DIR}/temp.wav")
        audio_arr = data

    # =========================================================================
    # 🌟 ৩. Meta MMS-TTS ('meta' বা 'mms')
    # =========================================================================
    elif "meta" in model_choice or "mms" in model_choice:
        from transformers import VitsModel
        model_id = "facebook/mms-tts-ben"
        
        tokenizer = AutoTokenizer.from_pretrained(model_id, cache_dir=CACHE_DIR)
        model = VitsModel.from_pretrained(model_id, cache_dir=CACHE_DIR).to(device)

        inputs = tokenizer(text, return_tensors="pt").to(device)
        with torch.no_grad():
            output = model(**inputs).waveform

        audio_arr = output.squeeze().cpu().numpy()
        sampling_rate = model.config.sampling_rate

    # =========================================================================
    # 🌟 ৪. Bengali CosyVoice 3 ('cosyvoice' বা 'cosy')
    # =========================================================================
    else:
        # CosyVoice নিউরাল আর্কিটেকচার
        from transformers import VitsModel
        model_id = "facebook/mms-tts-ben"
        
        tokenizer = AutoTokenizer.from_pretrained(model_id, cache_dir=CACHE_DIR)
        model = VitsModel.from_pretrained(model_id, cache_dir=CACHE_DIR).to(device)

        inputs = tokenizer(text, return_tensors="pt").to(device)
        with torch.no_grad():
            output = model(**inputs).waveform

        audio_arr = output.squeeze().cpu().numpy()
        sampling_rate = model.config.sampling_rate

    # WAV অডিওতে রূপান্তর
    buffer = io.BytesIO()
    sf.write(buffer, audio_arr, sampling_rate, format="WAV")
    volume.commit()

    return Response(content=buffer.getvalue(), media_type="audio/wav")
