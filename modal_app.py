# -*- coding: utf-8 -*-
import modal
from fastapi import Response

app = modal.App("bengali-tts-service")
volume = modal.Volume.from_name("bengali-tts-cache", create_if_missing=True)

# কন্টেইনার ইমেজ কনফিগারেশন
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
    import torch, io, soundfile as sf
    from transformers import AutoTokenizer

    text = data.get("text", "").strip()
    model_choice = data.get("model", "bharat").strip().lower()
    hf_token = data.get("hf_token", "").strip()

    if not text:
        return Response(content="Empty text", status_code=400)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🎙️ Generating Audio on {device} (Model: {model_choice.upper()})...")

    # 🌟 ১. AI4Bharat Indic Parler-TTS (টোকেন ফিক্সড)
    if "bharat" in model_choice or "parler" in model_choice:
        from parler_tts import ParlerTTSForConditionalGeneration
        model_id = "ai4bharat/indic-parler-tts"
        
        token_arg = hf_token if hf_token else None
        tokenizer = AutoTokenizer.from_pretrained(model_id, cache_dir=CACHE_DIR, token=token_arg)
        model = ParlerTTSForConditionalGeneration.from_pretrained(model_id, cache_dir=CACHE_DIR, token=token_arg).to(device)

        desc = "A clear, professional Bengali male news anchor with confident tone and natural pace."
        desc_inputs = tokenizer(desc, return_tensors="pt").to(device)
        prompt_inputs = tokenizer(text, return_tensors="pt").to(device)

        with torch.no_grad():
            generation = model.generate(input_ids=desc_inputs.input_ids, prompt_input_ids=prompt_inputs.input_ids)

        audio_arr = generation.squeeze().cpu().numpy()
        sampling_rate = model.config.sampling_rate

    # 🌟 ২. Meta MMS-TTS
    else:
        from transformers import VitsModel
        model_id = "facebook/mms-tts-ben"
        
        tokenizer = AutoTokenizer.from_pretrained(model_id, cache_dir=CACHE_DIR)
        model = VitsModel.from_pretrained(model_id, cache_dir=CACHE_DIR).to(device)

        inputs = tokenizer(text, return_tensors="pt").to(device)
        with torch.no_grad():
            output = model(**inputs).waveform

        audio_arr = output.squeeze().cpu().numpy()
        sampling_rate = model.config.sampling_rate

    buffer = io.BytesIO()
    sf.write(buffer, audio_arr, sampling_rate, format="WAV")
    volume.commit()
    
    return Response(content=buffer.getvalue(), media_type="audio/wav")
