# -*- coding: utf-8 -*-
import os, json, re, base64, requests
from PIL import Image

OLLAMA_API_KEY = os.environ.get("Ollama_API_Key", os.environ.get("OLLAMA_API_KEY", "")).strip()
OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "https://api.ollama.com").rstrip("/")
GROQ_API = os.environ.get("GROQ_API", "").strip()

OLLAMA_MODELS = ["kimi-k3", "minimax-m3", "gemma4", "kimi-k2.6"]
GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

DEFAULT_BASE_TAGS = [
    'চাকরির সার্কুলার', 'চাকরির খবর', 'সরকারি চাকরি ২০২৬',
    'job circular', 'govt job circular', 'job application bd'
]

def fix_years_to_2026(text):
    """২০২৪ বা ২০২৫ থাকলে সেটিকে স্বয়ংক্রিয়ভাবে ২০২৬ বানিয়ে দেবে"""
    if not text:
        return text
    text = re.sub(r'\b202[0-5]\b', '2026', str(text))
    text = re.sub(r'২০২[০-৫]', '২০২৬', text)
    return text

def sanitize_youtube_tags(raw_tags, max_total_chars=400):
    clean_tags = []
    current_length = 0
    for tag in raw_tags:
        if not tag or not isinstance(tag, str): continue
        cleaned = re.sub(r'[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\<\>\"\,\n\r]', '', tag)
        cleaned = fix_years_to_2026(re.sub(r'\s+', ' ', cleaned).strip())
        if not cleaned or len(cleaned) < 2: continue
        cleaned = cleaned[:50].strip()
        if cleaned not in clean_tags:
            tag_len = len(cleaned) + (1 if clean_tags else 0)
            if current_length + tag_len <= max_total_chars:
                clean_tags.append(cleaned)
                current_length += tag_len
            else: break
    return clean_tags

def clean_title_for_display(title):
    clean = title.split('|')[0].split('||')[0].strip()
    return re.sub(r'\s+', ' ', re.sub(r'[\r\n\t]+', ' ', clean))

def strip_unwanted_chars(text):
    cleaned = re.sub(r'[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|✪|★|☆', '', str(text))
    return fix_years_to_2026(cleaned.strip())

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

def parse_json_safely(raw_text):
    try:
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return json.loads(raw_text)
    except Exception:
        return None

def generate_job_content(title, img_paths):
    clean_title = clean_title_for_display(title)
    words = clean_title.split()
    org_name = clean_title.split("নিয়োগ")[0].strip() if "নিয়োগ" in clean_title else " ".join(words[:min(3, len(words))])
    vac_str, qual_str = extract_vacancy_and_qual(clean_title)

    prompt = f"""You are the top Bengali YouTube SEO Content & Script Specialist.
CRITICAL MANDATORY RULE: The current year is strictly ২০২৬ (2026). NEVER EVER use 2024 or 2025. Always write ২০২৬ or 2026.

Analyze this job circular:
Job Title: "{clean_title}"
Organization: "{org_name}"

Return a strictly valid JSON object:
1. "optimized_title": A UNIQUE, high-CTR, click-worthy YouTube Video Title under 95 characters (Must include year ২০২৬ and emojis like 🔥, 🚨, ⚡, 📢, |).
2. "voiceover_script": A comprehensive continuous spoken Bengali voiceover script (750 to 850 words) referencing circular ۲۰২৬.
3. "video_description": A tailored YouTube Description referencing year 2026/২০২৬ with circular summary and contact details:
---
[Circular Summary & Post Highlights here]

স্বাগতম আমাদের ইউটিউব চ্যানেলে! আমরা চাকরিপ্রার্থীদের জন্য সরকারি ও বেসরকারি সব ধরনের চাকরির আবেদন প্রক্রিয়াটি সহজ ও নিয়মতান্ত্রিক করতে কাজ করে থাকি।
আমাদের মাধ্যমে যেকোনো চাকরির আবেদন সম্পন্ন করতে আজই যোগাযোগ করুন:
💬 হোয়াটসঅ্যাপ (WhatsApp): wa.me/8801540503092
🌐 ফেসবুক পেজ (Facebook Page): https://www.facebook.com/profile.php?id=61583625958904

[3 to 5 targeted Bengali/English hashtags for this job circular 2026]
---
4. "specific_tags": A list of 4 to 6 specific SEO tags without emojis or commas.
5. "top_text": 2-3 clean Bengali words for Thumbnail Top Bar (e.g., "সরকারি চাকরি", "পানি উন্নয়ন বোর্ড"). DO NOT use any ✪ or star symbols.
6. "row1_text": 2-3 short, massive impact words for Thumbnail Hook in RED (e.g., "নিজ জেলায়", "অফিস সহায়ক", "জরুরি নিয়োগ", "আগস্ট মাসের").
7. "row2_text": 2-4 short words for Thumbnail Sub-line in BLACK (e.g., "DC অফিসে চাকরি", "এডমিট কার্ড প্রকাশ", "(SSC পাশ/৬৪ জেলা)").
8. "bot_text": Bottom Bar Bengali text (e.g., "({vac_str if vac_str else '১২৮০ পদে'}) নিয়োগ ২০২৬", "আবেদনের শেষ সময় ও নিয়ম"). MUST USE ২০২৬!

Return strictly valid JSON:
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

    # ------------------ [১ম ধাপ: Ollama ক্লাউড] ------------------
    if OLLAMA_API_KEY:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OLLAMA_API_KEY}"}
        for model_name in OLLAMA_MODELS:
            print(f"🤖 Attempting Ollama Model '{model_name}' for '{clean_title}'...")
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt, "images": base64_images}],
                "stream": False, "options": {"temperature": 0.5}
            }
            try:
                resp = requests.post(f"{OLLAMA_API_URL}/api/chat", headers=headers, json=payload, timeout=45)
                if resp.status_code == 200:
                    raw_content = resp.json().get("message", {}).get("content", "").strip()
                    data = parse_json_safely(raw_content)
                    if data and data.get("optimized_title") and data.get("voiceover_script"):
                        opt_title = fix_years_to_2026(data.get("optimized_title").strip()[:100])
                        script = fix_years_to_2026(re.sub(r'[\r\n]+', ' ', data.get("voiceover_script").strip()))
                        desc = fix_years_to_2026(data.get("video_description", "").strip())
                        raw_tags = data.get("specific_tags", []) + DEFAULT_BASE_TAGS
                        tags = sanitize_youtube_tags(raw_tags)
                        
                        thumb_meta = {
                            "top_text": strip_unwanted_chars(data.get("top_text", "সরকারি চাকরি")),
                            "row1_text": strip_unwanted_chars(data.get("row1_text", "জরুরি নিয়োগ")),
                            "row2_text": strip_unwanted_chars(data.get("row2_text", "(SSC পাশ/৬৪ জেলা)")),
                            "bot_text": strip_unwanted_chars(data.get("bot_text", "নিয়োগ ২০২৬"))
                        }
                        print(f"✨ Successfully Generated via Ollama '{model_name}'!")
                        return opt_title, script, thumb_meta, desc, tags
            except Exception: pass

    # ------------------ [২য় ধাপ: Groq AI] ------------------
    if GROQ_API:
        headers = {"Authorization": f"Bearer {GROQ_API}", "Content-Type": "application/json"}
        for g_model in GROQ_MODELS:
            print(f"🤖 Attempting Groq AI Model '{g_model}'...")
            payload = {
                "model": g_model,
                "messages": [
                    {"role": "system", "content": "You are a professional Bengali YouTube SEO specialist. The year is STRICTLY 2026/২০২৬. Output JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.5,
                "max_tokens": 2500
            }
            try:
                resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
                if resp.status_code == 200:
                    raw_content = resp.json()['choices'][0]['message']['content']
                    data = parse_json_safely(raw_content)
                    if data and data.get("optimized_title") and data.get("voiceover_script"):
                        opt_title = fix_years_to_2026(data.get("optimized_title").strip()[:100])
                        script = fix_years_to_2026(re.sub(r'[\r\n]+', ' ', data.get("voiceover_script").strip()))
                        desc = fix_years_to_2026(data.get("video_description", "").strip())
                        raw_tags = data.get("specific_tags", []) + DEFAULT_BASE_TAGS
                        tags = sanitize_youtube_tags(raw_tags)

                        thumb_meta = {
                            "top_text": strip_unwanted_chars(data.get("top_text", "সরকারি চাকরি")),
                            "row1_text": strip_unwanted_chars(data.get("row1_text", "জরুরি নিয়োগ")),
                            "row2_text": strip_unwanted_chars(data.get("row2_text", "(SSC পাশ/৬৪ জেলা)")),
                            "bot_text": strip_unwanted_chars(data.get("bot_text", "নিয়োগ ২০২৬"))
                        }
                        print(f"✨ Successfully Generated via Groq AI ({g_model})!")
                        return opt_title, script, thumb_meta, desc, tags
            except Exception: pass

    return None, None, None, None, None
