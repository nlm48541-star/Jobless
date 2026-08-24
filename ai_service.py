# -*- coding: utf-8 -*-
import os, json, re, base64, requests
from PIL import Image

OLLAMA_API_KEY = os.environ.get("Ollama_API_Key", os.environ.get("OLLAMA_API_KEY", "")).strip()
OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "https://api.ollama.com").rstrip("/")
GROQ_API = os.environ.get("GROQ_API", "").strip()

# 🌟 মডেলের অগ্রাধিকার তালিকা (Best থেকে শুরু করে নিচের দিকে যাবে)
OLLAMA_PRIORITY_MODELS = [
    "kimi-k3",         # 🥇 ১ম সেরা
    "minimax-m3",      # 🥈 ২য় সেরা
    "kimi-k2.6",       # 🥉 ৩য় সেরা
    "mistral-large-3"  # ৪র্থ সেরা
]

DEFAULT_BASE_TAGS = [
    'চাকরির আবেদন', 'অনলাইন চাকরির আবেদন', 'সরকারি চাকরির আবেদন', 'বেসরকারি চাকরির আবেদন',
    'চাকরির সার্কুলার', 'চাকরির খবর', 'ঘরে বসে চাকরির আবেদন', 'চাকরির ফর্ম পূরণ',
    'চাকরির আবেদন করার নিয়ম', 'অনলাইনে ফর্ম পূরণ', 'সরকারি চাকরি ২০২৬', 'নতুন চাকরির খবর',
    'job circular', 'govt job circular', 'private job circular', 'job application bd',
    'online job application bangladesh', 'how to apply for jobs online', 'job application service',
    'online form fill up bd', 'government job apply', 'private job apply', 'job circular 2026'
]

def clean_title_for_display(title):
    clean = title.split('|')[0].split('||')[0].strip()
    return re.sub(r'\s+', ' ', re.sub(r'[\r\n\t]+', ' ', clean))

def strip_unwanted_chars(text):
    cleaned = re.sub(r'[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|✪|★|☆', '', str(text))
    return cleaned.strip()

def extract_vacancy_and_qual(title):
    vac_match = re.search(r'(\d+|[০-৯]+)\s*(টি\s*)?পদে', title)
    vac_str = vac_match.group(0) if vac_match else ""
    qual = ""
    if any(k in title.upper() for k in ["SSC", "এসএসসি"]): qual = "SSC পাশ"
    elif any(k in title.upper() for k in ["HSC", "এইচএসসি"]): qual = "HSC পাশ"
    elif any(k in title for k in ["৮ম", "অষ্টম"]): qual = "৮ম শ্রেণি পাশ"
    elif any(k in title for k in ["স্নাতক", "ডিগ্রী", "অনার্স", "Degree", "Honours"]): qual = "ডিগ্রী/অনার্স পাশ"
    return vac_str, qual

def encode_image_base64(image_path, max_dim=1024):
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            if max(img.size) > max_dim: img.thumbnail((max_dim, max_dim), Image.LANCZOS)
            from io import BytesIO
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception: return None

def generate_job_content(title, img_paths):
    """
    🌟 মডেল হায়ারার্কি অনুযায়ী ক্রমান্বয়ে চেষ্টা করবে:
       ১. kimi-k3 -> ২. minimax-m3 -> ৩. kimi-k2.6 -> ৪. mistral-large-3 -> ৫. Groq AI
    """
    clean_title = clean_title_for_display(title)
    words = clean_title.split()
    org_name = clean_title.split("নিয়োগ")[0].strip() if "নিয়োগ" in clean_title else " ".join(words[:min(3, len(words))])
    vac_str, qual_str = extract_vacancy_and_qual(clean_title)

    prompt = f"""You are the top Bengali YouTube SEO Manager and career news presenter.
Analyze the circular images and job title:
Job Title: "{clean_title}"
Organization: "{org_name}"

Output a strictly valid JSON object with the following fields:

1. "optimized_title": A UNIQUE, high-CTR, click-worthy YouTube Video Title under 95 characters (Use symbols like 🔥, 🚨, ⚡, 📢, |). Make it specific to this exact circular.

2. "voiceover_script": A comprehensive 5-minute continuous spoken Bengali voiceover script (750 to 850 words). Include formal announcement, job roles, salary/grade allowances, educational/age eligibility, and your WhatsApp application service call to action. (No bracketed dialogue, no [Host:], continuous spoken Bengali only).

3. "video_description": A tailored YouTube Description with circular summary, your official contact details, and hashtags:
---
[Circular Summary & Post Highlights here]

স্বাগতম আমাদের ইউটিউব চ্যানেলে! আমরা চাকরিপ্রার্থীদের জন্য সরকারি ও বেসরকারি সব ধরনের চাকরির আবেদন প্রক্রিয়াটি সহজ ও নিয়মতান্ত্রিক করতে কাজ করে থাকি।
প্রতিটি নতুন সার্কুলারে বারবার একই তথ্য দিয়ে ফরম পূরণ করা বেশ সময়সাপেক্ষ এবং ঝামেলার। আমাদের লক্ষ্য হলো এই জটিল প্রক্রিয়াটিকে আপনার জন্য সহজ করে দেওয়া। আমাদের এই সেবায় আপনাকে শুধুমাত্র প্রথমবার আপনার প্রয়োজনীয় তথ্য (যেমন: নাম, ঠিকানা, শিক্ষাগত যোগ্যতা ইত্যাদি) প্রদান করতে হবে। আপনার এই তথ্যগুলো আমরা আমাদের কাছে সুরক্ষিতভাবে সংরক্ষণ করে রাখব।
পরবর্তীতে আপনার হয়ে অত্যন্ত সতর্কতার সাথে এবং সঠিক নিয়মে আবেদনের বাকি সব কাজ সম্পন্ন করে দেব আমরাই।

আমাদের মাধ্যমে যেকোনো চাকরির আবেদন সম্পন্ন করতে আজই যোগাযোগ করুন:
💬 হোয়াটসঅ্যাপ (WhatsApp): wa.me/8801540503092
🌐 ফেসবুক পেজ (Facebook Page): https://www.facebook.com/profile.php?id=61583625958904

বারবার ফরম পূরণের চিন্তা আমাদের ওপর ছেড়ে দিয়ে আপনি নিশ্চিন্তে আপনার পরীক্ষার প্রস্তুতিতে মনোযোগ দিন। আমাদের চ্যানেলের সাথে থাকার জন্য ধন্যবাদ।

[3 to 5 targeted Bengali/English hashtags for this job]
---

4. "specific_tags": A list of 6 to 10 specific SEO tags/keywords in Bengali & English tailored specifically to this job circular (e.g. ["{org_name} নিয়োগ ২০২৬", "{org_name} job circular 2026", "চাকরির খবর"]).

5. "top_text": 2-3 clean Bengali words for Thumbnail Top Bar (e.g., "সরকারি চাকরি", "বাংলাদেশ নৌবাহিনী", "পানি উন্নয়ন বোর্ড"). DO NOT use any ✪ or star symbols.
6. "row1_text": 2-4 impactful words for Thumbnail Main Hook in RED (e.g., "নিজ জেলায়", "নাবিক পদে নিয়োগ", "অফিস সহায়ক", "বিশাল নিয়োগ প্রকাশ").
7. "row2_text": 2-4 bold words for Thumbnail Sub-line in BLACK (e.g., "DC অফিসে চাকরি", "নৌবাহিনীতে নিয়োগ", "(SSC পাশ/৬৪ জেলা)", "এডমিট কার্ড প্রকাশ").
8. "bot_text": Bottom Bar Bengali text (e.g., "({vac_str if vac_str else '১২৮০ পদে'}) নিয়োগ ২০২৬", "আবেদনের শেষ সময় ও নিয়ম").

Return strictly valid JSON only:
{{
  "optimized_title": "...",
  "voiceover_script": "...",
  "video_description": "...",
  "specific_tags": ["..."],
  "top_text": "...",
  "row1_text": "...",
  "row2_text": "...",
  "bot_text": "..."
}}"""

    base64_images = [encode_image_base64(p) for p in img_paths[:3] if encode_image_base64(p)]

    # ------------------ [ধাপ ১: Ollama ক্লাউডের মডেলগুলোতে ক্রমান্বয়ে চেষ্টা] ------------------
    if OLLAMA_API_KEY:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OLLAMA_API_KEY}"}
        for model_name in OLLAMA_PRIORITY_MODELS:
            print(f"🤖 Attempting Ollama Model: '{model_name}'...")
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt, "images": base64_images}],
                "stream": False, "options": {"temperature": 0.5}
            }
            try:
                resp = requests.post(f"{OLLAMA_API_URL}/api/chat", headers=headers, json=payload, timeout=60)
                if resp.status_code == 200:
                    raw_content = resp.json().get("message", {}).get("content", "").strip()
                    json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(0))
                        opt_title = data.get("optimized_title", "").strip()[:100]
                        script = re.sub(r'[\r\n]+', ' ', data.get("voiceover_script", "").strip())
                        description = data.get("video_description", "").strip()
                        specific_tags = data.get("specific_tags", [])
                        combined_tags = list(dict.fromkeys([str(t).strip() for t in specific_tags + DEFAULT_BASE_TAGS if str(t).strip()]))

                        top = strip_unwanted_chars(data.get("top_text", "সরকারি চাকরি"))
                        r1 = strip_unwanted_chars(data.get("row1_text", "জরুরি নিয়োগ"))
                        r2 = strip_unwanted_chars(data.get("row2_text", "(SSC পাশ/৬৪ জেলা)"))
                        bot = strip_unwanted_chars(data.get("bot_text", "নিয়োগ ২০২৬"))

                        if opt_title and len(script.split()) >= 150:
                            print(f"✨ Successfully Generated via Ollama '{model_name}'!")
                            thumb_meta = {"top_text": top, "row1_text": r1, "row2_text": r2, "bot_text": bot}
                            return opt_title, script, thumb_meta, description, combined_tags
                else:
                    print(f"⚠️ Model '{model_name}' returned {resp.status_code}. Trying next model...")
            except Exception: continue

    # ------------------ [ধাপ ২: সবশেষে Groq AI আলটিমেট ব্যাকআপ] ------------------
    if GROQ_API:
        print("🤖 Trying Ultimate Final Backup: Groq AI (llama-3.3-70b-versatile)...")
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {GROQ_API}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "system", "content": "You are an expert Bengali YouTube SEO and scriptwriter. Output strictly valid JSON."}, {"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.7, "max_tokens": 2500
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = json.loads(resp.json()['choices'][0]['message']['content'])
                opt_title = data.get("optimized_title", "").strip()[:100]
                script = re.sub(r'[\r\n]+', ' ', data.get("voiceover_script", "").strip())
                description = data.get("video_description", "").strip()
                specific_tags = data.get("specific_tags", [])
                combined_tags = list(dict.fromkeys([str(t).strip() for t in specific_tags + DEFAULT_BASE_TAGS if str(t).strip()]))

                top = strip_unwanted_chars(data.get("top_text", "সরকারি চাকরি"))
                r1 = strip_unwanted_chars(data.get("row1_text", "জরুরি নিয়োগ"))
                r2 = strip_unwanted_chars(data.get("row2_text", "(SSC পাশ/৬৪ জেলা)"))
                bot = strip_unwanted_chars(data.get("bot_text", "নিয়োগ ২০২৬"))

                if opt_title and len(script.split()) >= 150:
                    print(f"✨ Successfully Generated via Groq AI!")
                    thumb_meta = {"top_text": top, "row1_text": r1, "row2_text": r2, "bot_text": bot}
                    return opt_title, script, thumb_meta, description, combined_tags
        except Exception as ge:
            print(f"⚠️ Groq AI generation error: {ge}")

    # ❌ সব মডেল ফেইল করলেই কেবল ক্যানসেল হবে
    print(f"❌ All AI models (Ollama & Groq) failed for '{title}'. Process cancelled.")
    return None, None, None, None, None
