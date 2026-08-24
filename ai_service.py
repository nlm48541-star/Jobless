# -*- coding: utf-8 -*-
import os, json, re, base64, requests
from PIL import Image

OLLAMA_API_KEY = os.environ.get("Ollama_API_Key", os.environ.get("OLLAMA_API_KEY", "")).strip()
OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "https://api.ollama.com").rstrip("/")
OLLAMA_MODEL = "qwen3.5"

def clean_title_for_display(title):
    clean = title.split('|')[0].split('||')[0].strip()
    return re.sub(r'\s+', ' ', re.sub(r'[\r\n\t]+', ' ', clean))

def strip_unwanted_chars(text):
    """ইমোজি এবং '✪' সহ সব অপ্রয়োজনীয় প্রতীক ফিল্টার করে"""
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
    🌟 শীর্ষস্থানীয় ভাইরাল ইউটিউব থাম্বনেইলের কি-ওয়ার্ড প্যাটার্ন মেনে টাইটেল, ৫ মিনিটের স্ক্রিপ্ট 
    এবং পারফেক্ট থাম্বনেইল টেক্সট তৈরি করে।
    """
    clean_title = clean_title_for_display(title)
    words = clean_title.split()
    org_name = clean_title.split("নিয়োগ")[0].strip() if "নিয়োগ" in clean_title else " ".join(words[:min(3, len(words))])
    vac_str, qual_str = extract_vacancy_and_qual(clean_title)

    print(f"🤖 Ollama is analyzing Job Circular: '{clean_title}'")

    if not OLLAMA_API_KEY:
        print("❌ Ollama_API_Key is missing in Secrets! Aborting generation.")
        return None, None, None

    prompt = f"""You are the top YouTube Job Circular Content & Thumbnail Expert in Bangladesh.
Analyze this job circular:
Job Title: "{clean_title}"
Organization: "{org_name}"

CRITICAL INSTRUCTIONS FOR THUMBNAIL KEYWORDS (Study these exact viral patterns):
1. IF Organization/Department (e.g. সমাজসেবা, পানি উন্নয়ন বোর্ড, ব্যাংক, খাদ্য, ইসলামিক ফাউন্ডেশন, গণপূর্ত, মহিলা বিষয়ক):
   - "top_text": Name of Organization (e.g. "সমাজসেবা অধিদপ্তর", "পানি উন্নয়ন বোর্ড", "বাংলাদেশ ব্যাংক", "ইসলামিক ফাউন্ডেশন")
   - "row1_text": Exact Post or Big Hook in RED (e.g. "অফিস সহায়ক", "ইউনিয়ন সমাজকর্মী কাজ কি?", "অফিসার পদে", "{vac_str if vac_str else 'বিশাল নিয়োগ'}")
   - "row2_text": Benefit/Eligibility in BLACK (e.g. "বেতন/পেনশন/সুযোগ-সুবিধা", "৮ম/SSC/HSC/পাশে", "এডমিট কার্ড প্রকাশ", "({qual_str if qual_str else 'SSC পাশ/৬৪ জেলা'})")
   - "bot_text": ("({vac_str if vac_str else 'বিশাল পদে'}) নিয়োগ ২০২৬" or "নিয়োগ বিজ্ঞপ্তি ২০২৬ প্রকাশ" or "বেতনঃ ১৯,২৪০ টাকা")

2. IF Defense/Forces (সেনাবাহিনী, পুলিশ, নৌবাহিনী, বিজিবি, আনসার):
   - "top_text": ("সেনাবাহিনী সৈনিক পদে" or "পুলিশ কনস্টেবল" or "বাংলাদেশ নৌবাহিনী")
   - "row1_text": ("SSC পাশে বিশাল" or "মাঠে কি কি কাগজ লাগবে" or "নাবিক পদে নিয়োগ" or "লিখিত পরীক্ষার প্রশ্ন")
   - "row2_text": ("(সকল জেলা থেকে)" or "আবেদন পদ্ধতি ২০২৬" or "(SSC পাশে আবেদন)")
   - "bot_text": ("নিয়োগ প্রকাশ ২০২৬" or "(সারাদেশে সবাই পারবে)")

3. IF Primary/Teacher/NTRCA (প্রাইমারি শিক্ষক, শিক্ষক নিবন্ধন):
   - "top_text": ("প্রাইমারি শিক্ষক নিয়োগ" or "NTRCA শিক্ষক নিবন্ধন" or "প্রাইমারি সহকারী শিক্ষক")
   - "row1_text": ("সহকারী শিক্ষক" or "প্রধান শিক্ষক" or "শিক্ষক পদে {vac_str if vac_str else 'বিশাল'}")
   - "row2_text": ("ছেলে/মেয়ে/৬৪ জেলা" or "১ম/২য় ধাপ" or "আবেদন পদ্ধতি ২০২৬")
   - "bot_text": ("নতুন নিয়োগ প্রকাশ ২০২৬" or "({vac_str if vac_str else '১০,২১৯ পদে'}) নিয়োগ ২০২৬")

4. IF General/Monthly/Other Govt Circular:
   - "top_text": ("সরকারি চাকরি" or "সরকারি নিয়োগ")
   - "row1_text": Month name (e.g. "আগস্ট মাসের" or "মার্চ মাসের" or "জরুরি নিয়োগ" or "নিজ উপজেলায়")
   - "row2_text": ("চলমান সেরা সার্কুলার" or "(SSC পাশ/৬৪ জেলা)" or "(জরুরি নিয়োগ) SSC পাশ")
   - "bot_text": "({vac_str if vac_str else '১২৮০ পদে'}) নিয়োগ ২০২৬"

STRICT RULES:
- DO NOT use any ✪ or star symbols in any field.
- "optimized_title": A UNIQUE, high-CTR YouTube title under 95 characters with symbols like 🔥, 🚨, ⚡, 📢, | .
- "voiceover_script": A comprehensive, high-retention 5-minute continuous spoken Bengali voiceover script (750 to 850 words) with full circular breakdown, job roles, salary scale, eligibility, and WhatsApp application service call to action.

Output strictly valid JSON only:
{{
  "optimized_title": "...",
  "voiceover_script": "...",
  "top_text": "...",
  "row1_text": "...",
  "row2_text": "...",
  "bot_text": "..."
}}"""

    base64_images = [encode_image_base64(p) for p in img_paths[:3] if encode_image_base64(p)]
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OLLAMA_API_KEY}"}
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt, "images": base64_images}],
        "stream": False,
        "options": {"temperature": 0.5}
    }

    try:
        resp = requests.post(f"{OLLAMA_API_URL}/api/chat", headers=headers, json=payload, timeout=90)
        if resp.status_code == 200:
            raw_content = resp.json().get("message", {}).get("content", "").strip()
            json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                opt_title = data.get("optimized_title", "").strip()[:100]
                script = re.sub(r'[\r\n]+', ' ', data.get("voiceover_script", "").strip())
                
                top = strip_unwanted_chars(data.get("top_text", "সরকারি চাকরি"))
                r1 = strip_unwanted_chars(data.get("row1_text", "জরুরি নিয়োগ"))
                r2 = strip_unwanted_chars(data.get("row2_text", "(SSC পাশ/৬৪ জেলা)"))
                bot = strip_unwanted_chars(data.get("bot_text", "নিয়োগ ২০২৬"))

                if opt_title and len(script.split()) >= 150:
                    print(f"✨ Ollama Generated Unique SEO Title: {opt_title}")
                    print(f"✅ Generated Script Word Count: {len(script.split())} words")
                    print(f"🎨 High-CTR Thumbnail Text: Top='{top}', Line1='{r1}', Line2='{r2}', Bot='{bot}'")
                    thumb_meta = {"top_text": top, "row1_text": r1, "row2_text": r2, "bot_text": bot}
                    return opt_title, script, thumb_meta
        else:
            print(f"⚠️ Ollama API Error {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"⚠️ Ollama Generation Exception: {e}")

    print(f"❌ Ollama generation failed for '{title}'. Process cancelled.")
    return None, None, None
