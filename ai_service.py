# -*- coding: utf-8 -*-
import os, json, re, base64, requests
from datetime import datetime
from PIL import Image

WORKSPACE_DIR = "workspace"
TRACKER_FILE = "api_key_tracker.json"
WORKSPACE_TRACKER = os.path.join(WORKSPACE_DIR, "api_key_tracker.json")

# 🌟 Ollama মডেলের অগ্রাধিকার (Gemma সবার প্রথমে)
OLLAMA_MODELS = [
    "gemma4:31b",
    "gemma4",
    "gpt-oss:120b",
    "gpt-oss:20b",
    "nemotron-3-nano:30b",
    "nemotron-3-super",
    "nemotron-3-ultra",
    "kimi-k3",
    "minimax-m3",
    "kimi-k2.6"
]

OPENROUTER_MODELS = [
    "google/gemini-2.0-flash-001",
    "meta-llama/llama-3.3-70b-instruct",
    "deepseek/deepseek-chat",
    "mistralai/mistral-large-2411"
]

GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
CEREBRAS_MODELS = ["llama-3.3-70b", "llama3.1-8b"]

# =========================================================================
# 🌟 মেমোরি ট্র্যাকার ও মাল্টিপল কী পার্সার (Enter / Newline Support)
# =========================================================================

def parse_multiline_keys(raw_text):
    if not raw_text: return []
    lines = re.split(r'[\r\n,;]+', str(raw_text))
    return [k.strip() for k in lines if k.strip() and not k.strip().startswith('#')]

def mask_key(k):
    if not k or len(k) <= 8: return "****"
    return k[:4] + "..." + k[-4:]

def load_tracker():
    for p in [WORKSPACE_TRACKER, TRACKER_FILE]:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception: pass
    return {}

def save_tracker_index(service_name, index, total_keys):
    if total_keys == 0: return
    data = load_tracker()
    if service_name not in data:
        data[service_name] = {}
    data[service_name]["current_index"] = index % total_keys
    data[service_name]["last_updated"] = datetime.now().isoformat()

    for p in [WORKSPACE_TRACKER, TRACKER_FILE]:
        try:
            os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception: pass

def get_keys_in_cyclic_order(service_name, raw_keys_str):
    keys = parse_multiline_keys(raw_keys_str)
    if not keys: return []
    total = len(keys)
    data = load_tracker()
    saved_idx = data.get(service_name, {}).get("current_index", 0) % total
    return [((saved_idx + i) % total, keys[(saved_idx + i) % total]) for i in range(total)]

# =========================================================================
# 🌟 টেক্সট ও সংখ্যা প্রসেসিং ফাংশনসমূহ
# =========================================================================

DEFAULT_BASE_TAGS = [
    'চাকরির সার্কুলার', 'চাকরির খবর', 'সরকারি চাকরি',
    'job circular', 'govt job circular', 'job application bd'
]

BN_NUMS = {
    0: 'শূন্য', 1: 'এক', 2: 'দুই', 3: 'তিন', 4: 'চার', 5: 'পাঁচ', 6: 'ছয়', 7: 'সাত', 8: 'আট', 9: 'নয়', 10: 'দশ',
    11: 'এগারো', 12: 'বারো', 13: 'তেরো', 14: 'চৌদ্দ', 15: 'পনেরো', 16: 'ষোলো', 17: 'সতেরো', 18: 'আঠারো', 19: 'উনিশ', 20: 'বিশ',
    21: 'একুশ', 22: 'বাইশ', 23: 'তেইশ', 24: 'চব্বিশ', 25: 'পঁচিশ', 26: 'ছাব্বিশ', 27: 'সাতাশ', 28: 'আঠাশ', 29: 'উনত্রিশ', 30: 'ত্রিশ',
    31: 'একত্রিশ', 32: 'বত্রিশ', 33: 'তেত্রিশ', 34: 'চৌত্রিশ', 35: 'পঁয়ত্রিশ', 36: 'ছত্রিশ', 37: 'সাঁইত্রিশ', 38: 'আটত্রিশ', 39: 'উনচল্লিশ', 40: 'চল্লিশ',
    41: 'একচল্লিশ', 42: 'বিয়াল্লিশ', 43: 'তেতাল্লিশ', 44: 'চুয়াল্লিশ', 45: 'পঁয়তাল্লিশ', 46: 'ছেচল্লিশ', 47: 'সাতচল্লিশ', 48: 'আটচল্লিশ', 49: 'উনপঞ্চাশ', 50: 'পঞ্চাশ',
    51: 'একান্ন', 52: 'বায়ান্ন', 53: 'তিপ্পান্ন', 54: 'চুয়ান্ন', 55: 'পঞ্চান্ন', 56: 'ছাপ্পান্ন', 57: 'সাতান্ন', 58: 'আটান্ন', 59: 'উনষাট', 60: 'ষাট',
    61: 'একষট্টি', 62: 'বাষট্টি', 63: 'তেষট্টি', 64: 'চৌষট্টি', 65: 'পঁয়ষট্টি', 66: 'ছেষট্টি', 67: 'সাতষট্টি', 68: 'আটষট্টি', 69: 'উনসত্তর', 70: 'সত্তর',
    71: 'একাত্তর', 72: 'বাহাত্তর', 73: 'তিয়াত্তর', 74: 'চৌহাত্তর', 75: 'পঁচাত্তর', 76: 'ছিয়াত্তর', 77: 'সাতাত্তর', 78: 'আটাত্তর', 79: 'উনআশি', 80: 'আশি',
    81: 'একাশি', 82: 'বিরাশি', 83: 'তিরাশি', 84: 'চুরাশি', 85: 'পঁচাশি', 86: 'ছিয়াশি', 87: 'সাতাশি', 88: 'অষ্টআশি', 89: 'ঊননব্বই', 90: 'নব্বই',
    91: 'একানব্বই', 92: 'বানব্বই', 93: 'তিরানব্বই', 94: 'চুরানব্বই', 95: 'পঁচানব্বই', 96: 'ছিয়ানব্বই', 97: 'সাতানব্বই', 98: 'আটানব্বই', 99: 'নিরানব্বই'
}

DIGIT_TO_ENG_BN = {
    '0': 'জিরো', '1': 'ওয়ান', '2': 'টু', '3': 'থ্রি', '4': 'ফোর',
    '5': 'ফাইভ', '6': 'সিক্স', '7': 'সেভেন', '8': 'এইট', '9': 'নাইন',
    '০': 'জিরো', '১': 'ওয়ান', '২': 'টু', '৩': 'থ্রি', '৪': 'ফোর',
    '৫': 'ফাইভ', '৬': 'সিক্স', '৭': 'সেভেন', '৮': 'এইট', '৯': 'নাইন'
}

def en_bn_to_int(s):
    trans = str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789')
    return int(str(s).translate(trans))

def number_to_bangla_words(n):
    if n == 0: return 'শূন্য'
    parts = []
    koti = n // 10000000
    if koti > 0:
        parts.append(number_to_bangla_words(koti) + ' কোটি')
        n %= 10000000
    lakh = n // 100000
    if lakh > 0:
        parts.append(BN_NUMS.get(lakh, str(lakh)) + ' লাখ')
        n %= 100000
    hajar = n // 1000
    if hajar > 0:
        parts.append(BN_NUMS.get(hajar, str(hajar)) + ' হাজার')
        n %= 1000
    shatok = n // 100
    if shatok > 0:
        if shatok == 1: parts.append('একশত')
        else: parts.append(BN_NUMS.get(shatok, str(shatok)) + ' শত')
        n %= 100
    if n > 0:
        parts.append(BN_NUMS.get(n, str(n)))
    return ' '.join(parts)

def convert_all_numbers_in_script(text):
    if not text: return ""
    text = re.sub(r'(\d+),(\d+)', r'\1\2', text)
    text = re.sub(r'([০-৯]+),([০-৯]+)', r'\1\2', text)

    def phone_repl(m):
        raw_phone = m.group(0)
        digits = re.findall(r'[0-9০-৯]', raw_phone)
        return ' '.join(DIGIT_TO_ENG_BN.get(d, d) for d in digits)

    text = re.sub(r'(\+?(?:88|৮৮)?\s*0?1[0-9০-৯]{8,10})', phone_repl, text)

    def num_repl(m):
        num_str = m.group(0)
        try:
            val = en_bn_to_int(num_str)
            return number_to_bangla_words(val)
        except Exception:
            return num_str

    text = re.sub(r'[0-9০-৯]+', num_repl, text)
    text = re.sub(r'ঘরে\s*বসে\s*', '', text)
    return text

def get_current_years():
    cur_year = datetime.now().year
    en_to_bn = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
    cur_year_bn = str(cur_year).translate(en_to_bn)
    return str(cur_year), cur_year_bn

def normalize_outdated_years(text):
    if not text: return text
    cur_en, cur_bn = get_current_years()
    text = re.sub(r'\b202[0-5]\b', cur_en, str(text))
    text = re.sub(r'২০২[০-৫]', cur_bn, text)
    text = re.sub(r'ঘরে\s*বসে\s*', '', text)
    return text

def sanitize_youtube_tags(raw_tags, max_total_chars=400):
    clean_tags = []
    current_length = 0
    for tag in raw_tags:
        if not tag or not isinstance(tag, str): continue
        cleaned = re.sub(r'[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\<\>\"\,\n\r]', '', tag)
        cleaned = normalize_outdated_years(re.sub(r'\s+', ' ', cleaned).strip())
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
    return normalize_outdated_years(cleaned.strip())

def extract_vacancy_and_qual(title):
    vac_match = re.search(r'(\d+|[০-৯]+)\s*(টি\s*)?পদে', title)
    vac_str = vac_match.group(0) if vac_match else ""
    qual = ""
    if any(k in title.upper() for k in ["SSC", "এসএসসি"]): qual = "SSC পাশ যোগ্যতা"
    elif any(k in title.upper() for k in ["HSC", "এইচএসসি"]): qual = "HSC পাশ যোগ্যতা"
    elif any(k in title for k in ["৮ম", "অষ্টম"]): qual = "৮ম শ্রেণি পাশ"
    elif any(k in title for k in ["স্নাতক", "ডিগ্রী", "অনার্স", "Degree", "Honours"]): qual = "স্নাতক পাশ যোগ্যতা"
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

# =========================================================================
# 🌟 মাস্টার টেক্সট ও ভিশন এআই পাইপলাইন (Ollama Gemma -> OpenRouter -> Groq -> Cerebras)
# =========================================================================

def generate_job_content(title, img_paths):
    cur_en, cur_bn = get_current_years()
    clean_title = clean_title_for_display(title)
    words = clean_title.split()
    org_name = clean_title.split("নিয়োগ")[0].strip() if "নিয়োগ" in clean_title else " ".join(words[:min(3, len(words))])
    vac_str, qual_str = extract_vacancy_and_qual(clean_title)

    prompt = f"""You are a professional Bengali YouTube SEO specialist, scriptwriter, and job circular inspector.
Context:
- Job Circular Title: "{clean_title}"
- Organization: "{org_name}"

CRITICAL STEP 1 - APPLICATION SUBMISSION INSPECTION:
Carefully inspect the official scanned notice images and text:
- Set "application_type": "offline" ONLY IF candidates are required to submit application papers via:
  1. Postal Mail (ডাকযোগে / রেজিস্টার্ড ডাকে / ডাক মারফত)
  2. Courier Service (কুরিয়ারের মাধ্যমে)
  3. Direct Physical In-Person submission by hand (সরাসরি অফিসে গিয়ে / হাতে হাতে জমা দেওয়া)
  And explain reason in "offline_reason" (e.g. "আবেদনপত্র ডাকযোগে পাঠাতে হবে").
- Set "application_type": "online" IF candidates can apply Online (e.g. teletalk.com.bd, web portal, online link, or email).
CAUTION: If circular states 'অনলাইনে আবেদন করতে হবে, ডাকযোগে কোনো আবেদন গ্রহণযোগ্য নয়', that is ONLINE, not offline!

CRITICAL STEP 2 - CONTENT GENERATION (ONLY IF ONLINE):
1. SCRIPT: Exactly 3 minutes (380 to 440 words). Continuous spoken Bengali. Do NOT mention any year in the script. All numbers in Bengali words. WhatsApp call to action at end (without 'ঘরে বসে').
2. THUMBNAIL TEXTS (MUST BE DYNAMIC & UNIQUE):
   - "top_text": 2-3 words. Organization name or Category.
   - "row1_text": 2-3 words. Main Eye-Catching Hook.
   - "row2_text": 2-3 words. Vacancy in RED (e.g. "{vac_str if vac_str else 'বিশাল শূন্যপদ'}").
   - "sub_text": 2-3 words. Specific Qualification / District (e.g. "{qual_str if qual_str else 'SSC/HSC পাশ'}").
   - "bot_text": 2-4 words. DYNAMIC & UNIQUE bottom bar text (e.g. "আবেদনের শেষ তারিখ ও নিয়ম", "({vac_str if vac_str else 'হাজারো পদে'}) মেগা সার্কুলার", "বেতন স্কেল ও সুযোগ-সুবিধা"). NEVER use the same phrase for all jobs!

Return strictly valid JSON:
{{
  "application_type": "online" or "offline",
  "offline_reason": "...",
  "optimized_title": "...",
  "voiceover_script": "...",
  "video_description": "...",
  "specific_tags": ["..."],
  "top_text": "...",
  "row1_text": "...",
  "row2_text": "...",
  "sub_text": "...",
  "bot_text": "..."
}}"""

    base64_images = [encode_image_base64(p) for p in img_paths[:3] if encode_image_base64(p)]

    def process_ai_result(data):
        app_type = data.get("application_type", "online").strip().lower()
        off_reason = data.get("offline_reason", "ডাকযোগে বা সরাসরি আবেদন").strip()

        if app_type == "offline":
            return None, None, None, None, None, "offline", off_reason

        opt_title = normalize_outdated_years(data.get("optimized_title").strip()[:100])
        raw_script = normalize_outdated_years(re.sub(r'[\r\n]+', ' ', data.get("voiceover_script", "").strip()))
        script = convert_all_numbers_in_script(raw_script)
        desc = normalize_outdated_years(data.get("video_description", "").strip())
        raw_tags = data.get("specific_tags", []) + DEFAULT_BASE_TAGS
        tags = sanitize_youtube_tags(raw_tags)

        gen_bot = data.get("bot_text", "").strip()
        if not gen_bot or "আবেদনের নিয়ম ও বিস্তারিত" in gen_bot:
            gen_bot = f"({vac_str}) বিশাল সার্কুলার" if vac_str else "আবেদনের শেষ তারিখ ও নিয়ম"

        thumb_meta = {
            "top_text": strip_unwanted_chars(data.get("top_text", org_name)),
            "row1_text": strip_unwanted_chars(data.get("row1_text", "জরুরি নিয়োগ")),
            "row2_text": strip_unwanted_chars(data.get("row2_text", vac_str if vac_str else "বিশাল নিয়োগ")),
            "sub_text": strip_unwanted_chars(data.get("sub_text", qual_str if qual_str else "SSC/HSC পাশ")),
            "bot_text": strip_unwanted_chars(gen_bot)
        }
        return opt_title, script, thumb_meta, desc, tags, "online", ""

    # =========================================================================
    # 🌟 ১. প্রথম প্রায়োরিটি: Ollama Cloud API (Gemma Model First)
    # =========================================================================
    raw_ollama = os.environ.get("OLLAMA_API_KEYS", os.environ.get("Ollama_API_Key", os.environ.get("OLLAMA_API_KEY", ""))).strip()
    ollama_order = get_keys_in_cyclic_order("ollama", raw_ollama)
    total_ollama = len(parse_multiline_keys(raw_ollama))

    if ollama_order:
        print("\n" + "="*65)
        print("🤖 [AI TIER 1] Priority 1: Ollama Cloud (Gemma Prioritized)")
        print(f"🔑 Total {total_ollama} Ollama Key(s). Resuming from Key #{ollama_order[0][0] + 1}...")
        print("="*65)

        for actual_idx, o_key in ollama_order:
            key_num = actual_idx + 1
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {o_key}"}

            for model_name in OLLAMA_MODELS:
                print(f"  • Trying Ollama Key #{key_num}/{total_ollama} (Model: '{model_name}')...")
                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt, "images": base64_images}],
                    "stream": False, "options": {"temperature": 0.4}
                }
                try:
                    resp = requests.post("https://api.ollama.com/api/chat", headers=headers, json=payload, timeout=45)
                    if resp.status_code == 200:
                        data = parse_json_safely(resp.json().get("message", {}).get("content", "").strip())
                        if data and data.get("optimized_title"):
                            save_tracker_index("ollama", actual_idx, total_ollama)
                            print(f"  ✨ [SUCCESS] AI Content Generated via Ollama Key #{key_num} ('{model_name}')!")
                            return process_ai_result(data)
                    elif resp.status_code in [401, 402, 429]:
                        print(f"  ⚠️ Key #{key_num} quota/auth issue ({resp.status_code}).")
                        break
                except Exception as e:
                    print(f"  ⚠️ Error with Ollama Key #{key_num} ('{model_name}'): {e}")

            save_tracker_index("ollama", actual_idx + 1, total_ollama)

    # =========================================================================
    # 🌟 ২. দ্বিতীয় প্রায়োরিটি: OpenRouter Cloud API
    # =========================================================================
    raw_openrouter = os.environ.get("OPENROUTER_API_KEYS", os.environ.get("OPENROUTER_API_KEY", "")).strip()
    openrouter_order = get_keys_in_cyclic_order("openrouter", raw_openrouter)
    total_openrouter = len(parse_multiline_keys(raw_openrouter))

    if openrouter_order:
        print("\n" + "="*65)
        print("🤖 [AI TIER 2] Priority 2: OpenRouter Cloud API")
        print(f"🔑 Total {total_openrouter} OpenRouter Key(s). Resuming from Key #{openrouter_order[0][0] + 1}...")
        print("="*65)

        for actual_idx, or_key in openrouter_order:
            key_num = actual_idx + 1
            headers = {
                "Authorization": f"Bearer {or_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com",
                "X-Title": "YouTube Job Automation"
            }

            # OpenRouter মাল্টিমোডাল পে-লোড গঠন
            content_list = [{"type": "text", "text": prompt}]
            for b64 in base64_images[:2]:
                content_list.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

            for model_name in OPENROUTER_MODELS:
                print(f"  • Trying OpenRouter Key #{key_num}/{total_openrouter} (Model: '{model_name}')...")
                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": content_list}],
                    "temperature": 0.4
                }
                try:
                    resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=40)
                    if resp.status_code == 200:
                        content_txt = resp.json()['choices'][0]['message']['content']
                        data = parse_json_safely(content_txt)
                        if data and data.get("optimized_title"):
                            save_tracker_index("openrouter", actual_idx, total_openrouter)
                            print(f"  ✨ [SUCCESS] AI Content Generated via OpenRouter Key #{key_num} ('{model_name}')!")
                            return process_ai_result(data)
                    elif resp.status_code in [401, 402, 429]:
                        print(f"  ⚠️ OpenRouter Key #{key_num} limit reached ({resp.status_code}).")
                        break
                except Exception as e:
                    print(f"  ⚠️ Error with OpenRouter Key #{key_num}: {e}")

            save_tracker_index("openrouter", actual_idx + 1, total_openrouter)

    # =========================================================================
    # 🌟 ৩. তৃতীয় প্রায়োরিটি: Groq Cloud API
    # =========================================================================
    raw_groq = os.environ.get("GROQ_API_KEYS", os.environ.get("GROQ_API", "")).strip()
    groq_order = get_keys_in_cyclic_order("groq", raw_groq)
    total_groq = len(parse_multiline_keys(raw_groq))

    if groq_order:
        print("\n" + "="*65)
        print("🤖 [AI TIER 3] Priority 3: Groq Cloud API")
        print(f"🔑 Total {total_groq} Groq Key(s). Resuming from Key #{groq_order[0][0] + 1}...")
        print("="*65)

        for actual_idx, g_key in groq_order:
            key_num = actual_idx + 1
            headers = {"Authorization": f"Bearer {g_key}", "Content-Type": "application/json"}

            for g_model in GROQ_MODELS:
                print(f"  • Trying Groq Key #{key_num}/{total_groq} (Model: '{g_model}')...")
                payload = {
                    "model": g_model,
                    "messages": [
                        {"role": "system", "content": "You are a professional Bengali YouTube SEO and scriptwriter. Output strictly valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.4,
                    "max_tokens": 2000
                }
                try:
                    resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
                    if resp.status_code == 200:
                        content_txt = resp.json()['choices'][0]['message']['content']
                        data = parse_json_safely(content_txt)
                        if data and data.get("optimized_title"):
                            save_tracker_index("groq", actual_idx, total_groq)
                            print(f"  ✨ [SUCCESS] AI Content Generated via Groq Key #{key_num} ('{g_model}')!")
                            return process_ai_result(data)
                    elif resp.status_code in [401, 402, 429]:
                        print(f"  ⚠️ Groq Key #{key_num} exhausted ({resp.status_code}).")
                        break
                except Exception as e:
                    print(f"  ⚠️ Error with Groq Key #{key_num}: {e}")

            save_tracker_index("groq", actual_idx + 1, total_groq)

    # =========================================================================
    # 🌟 ৪. চতুর্থ প্রায়োরিটি: Cerebras Cloud API
    # =========================================================================
    raw_cerebras = os.environ.get("CEREBRAS_API_KEYS", os.environ.get("CEREBRAS_API_KEY", "")).strip()
    cerebras_order = get_keys_in_cyclic_order("cerebras", raw_cerebras)
    total_cerebras = len(parse_multiline_keys(raw_cerebras))

    if cerebras_order:
        print("\n" + "="*65)
        print("🤖 [AI TIER 4] Priority 4: Cerebras Cloud API")
        print(f"🔑 Total {total_cerebras} Cerebras Key(s). Resuming from Key #{cerebras_order[0][0] + 1}...")
        print("="*65)

        for actual_idx, c_key in cerebras_order:
            key_num = actual_idx + 1
            headers = {"Authorization": f"Bearer {c_key}", "Content-Type": "application/json"}

            for c_model in CEREBRAS_MODELS:
                print(f"  • Trying Cerebras Key #{key_num}/{total_cerebras} (Model: '{c_model}')...")
                payload = {
                    "model": c_model,
                    "messages": [
                        {"role": "system", "content": "You are a professional Bengali YouTube SEO and scriptwriter. Output strictly valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.4,
                    "max_tokens": 2000
                }
                try:
                    resp = requests.post("https://api.cerebras.ai/v1/chat/completions", headers=headers, json=payload, timeout=30)
                    if resp.status_code == 200:
                        content_txt = resp.json()['choices'][0]['message']['content']
                        data = parse_json_safely(content_txt)
                        if data and data.get("optimized_title"):
                            save_tracker_index("cerebras", actual_idx, total_cerebras)
                            print(f"  ✨ [SUCCESS] AI Content Generated via Cerebras Key #{key_num} ('{c_model}')!")
                            return process_ai_result(data)
                    elif resp.status_code in [401, 402, 429]:
                        print(f"  ⚠️ Cerebras Key #{key_num} limit reached ({resp.status_code}).")
                        break
                except Exception as e:
                    print(f"  ⚠️ Error with Cerebras Key #{key_num}: {e}")

            save_tracker_index("cerebras", actual_idx + 1, total_cerebras)

    return None, None, None, None, None, "error", "All AI providers failed"
