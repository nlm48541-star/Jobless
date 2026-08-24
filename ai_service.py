# -*- coding: utf-8 -*-
import os, json, re, base64, requests
from PIL import Image

GROQ_API = os.environ.get("GROQ_API", "").strip()
OLLAMA_API_KEY = os.environ.get("Ollama_API_Key", os.environ.get("OLLAMA_API_KEY", "")).strip()
OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "https://api.ollama.com").rstrip("/")
OLLAMA_MODEL = "qwen3.5"

def clean_title_for_display(title):
    clean = title.split('|')[0].split('||')[0].strip()
    return re.sub(r'\s+', ' ', re.sub(r'[\r\n\t]+', ' ', clean))

def strip_emojis(text):
    return re.sub(r'[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]', '', str(text)).strip()

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
    🌟 এআই এর মাধ্যমে SEO টাইটেল, ৫ মিনিটের স্ক্রিপ্ট ও থাম্বনেইল টেক্সট তৈরি করে।
    ব্যর্থ হলে কোনো ফলব্যাক স্ক্রিপ্ট তৈরি করবে না, সরাসরি None রিটার্ন করবে।
    """
    clean_title = clean_title_for_display(title)
    words = clean_title.split()
    org_name = clean_title.split("নিয়োগ")[0].strip() if "নিয়োগ" in clean_title else " ".join(words[:min(3, len(words))])
    vac_str, qual_str = extract_vacancy_and_qual(clean_title)

    print(f"🤖 Requesting AI for SEO Title & 5-Min Script: '{clean_title}'")

    prompt = f"""Job Circular Title: "{clean_title}"
Organization: "{org_name}"

You are a top-tier Bengali YouTube SEO expert and career news presenter.
Generate a complete JSON package for this job circular:

1. "optimized_title": A UNIQUE, high-CTR, click-worthy YouTube Title strictly under 95 chars with creative hooks and symbols (🔥, 🚨, ⚡, 📢, |). Tailored specifically to this job.
2. "voiceover_script": A comprehensive, 5-minute long (750 to 850 words) detailed narration script in spoken natural Bengali.
Structure:
  - Salutation & Formal Circular Announcement (institution, job type, vacancy count).
  - Detailed Position Breakdown (job titles, responsibilities, pay scale & allowances).
  - Educational Qualification & Skills (8th/SSC/HSC/Degree).
  - Age limits & quotas.
  - Eligible districts and deadline reminder.
  - WhatsApp Application Service promotion (Message WhatsApp in description/bio for 100% accurate application; save info once for all future jobs).
  - Outro & subscribe call to action.
(No bracketed dialogue, no [Host:], continuous natural speaking Bengali only).

3. "top_text": 2-3 words for Top bar (e.g. "সরকারি চাকরি", "জরুরি নিয়োগ", "গণপ্রজাতন্ত্রী বাংলাদেশ সরকার").
4. "row1_text": 2-4 impactful words for Main Hook (e.g. "নিজ উপজেলায়", "জেলা প্রশাসকের কার্যালয়", "অফিসার পদে বিশাল নিয়োগ").
5. "row2_text": Core organization name (e.g. "{org_name}").
6. "row3_text": Eligibility badge (e.g. "(জরুরি নিয়োগ) {qual_str if qual_str else 'SSC পাশ'}", "(SSC পাশ/৬৪ জেলা)", "চলমান সেরা সার্কুলার").
7. "bot_text": Bottom bar info (e.g. "({vac_str if vac_str else 'বিশাল পদে'}) নিয়োগ ২০২৬", "আবেদনের শেষ সময় ও নিয়ম").

Return strictly valid JSON only:
{{
  "optimized_title": "...",
  "voiceover_script": "...",
  "top_text": "...",
  "row1_text": "...",
  "row2_text": "...",
  "row3_text": "...",
  "bot_text": "..."
}}"""

    # ১. Groq AI জেনারেশন চেষ্টা
    if GROQ_API:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {GROQ_API}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": "You are a professional Bengali YouTube SEO copywriter and scriptwriter. Output strictly valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.7, "max_tokens": 2500
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = json.loads(resp.json()['choices'][0]['message']['content'])
                opt_title = data.get("optimized_title", "").strip()[:100]
                script = re.sub(r'[\r\n]+', ' ', data.get("voiceover_script", "").strip())
                
                if opt_title and len(script.split()) >= 200:
                    print(f"✨ AI Generated SEO Title: {opt_title}")
                    print(f"✅ Generated Script Length: {len(script.split())} words")
                    thumb_meta = {
                        "top_text": strip_emojis(data.get("top_text", "সরকারি চাকরি")),
                        "row1_text": strip_emojis(data.get("row1_text", "জরুরি নিয়োগ")),
                        "row2_text": strip_emojis(data.get("row2_text", org_name)),
                        "row3_text": strip_emojis(data.get("row3_text", "(SSC পাশ/৬৪ জেলা)")),
                        "bot_text": strip_emojis(data.get("bot_text", "নিয়োগ ২০২৬"))
                    }
                    return opt_title, script, thumb_meta
            else:
                print(f"⚠️ Groq API Error {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"⚠️ Groq Generation Exception: {e}")

    # ২. Ollama Vision জেনারেশন চেষ্টা
    if OLLAMA_API_KEY:
        try:
            base64_images = [encode_image_base64(p) for p in img_paths[:3] if encode_image_base64(p)]
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OLLAMA_API_KEY}"}
            payload = {
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt, "images": base64_images}],
                "stream": False, "options": {"temperature": 0.5}
            }
            resp = requests.post(f"{OLLAMA_API_URL}/api/chat", headers=headers, json=payload, timeout=75)
            if resp.status_code == 200:
                raw_content = resp.json().get("message", {}).get("content", "").strip()
                json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                    opt_title = data.get("optimized_title", "").strip()[:100]
                    script = re.sub(r'[\r\n]+', ' ', data.get("voiceover_script", "").strip())
                    if opt_title and len(script.split()) >= 150:
                        thumb_meta = {
                            "top_text": strip_emojis(data.get("top_text", "সরকারি চাকরি")),
                            "row1_text": strip_emojis(data.get("row1_text", "জরুরি নিয়োগ")),
                            "row2_text": strip_emojis(data.get("row2_text", org_name)),
                            "row3_text": strip_emojis(data.get("row3_text", "(SSC পাশ/৬৪ জেলা)")),
                            "bot_text": strip_emojis(data.get("bot_text", "নিয়োগ ২০২৬"))
                        }
                        return opt_title, script, thumb_meta
            else:
                print(f"⚠️ Ollama API Error {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"⚠️ Ollama Generation Exception: {e}")

    # ❌ কোনো ফলব্যাক স্ক্রিপ্ট তৈরি হবে না, ব্যর্থ হলে সরাসরি ক্যানসেল
    print(f"❌ AI content generation completely failed for '{title}'. No fallback script will be generated.")
    return None, None, None
