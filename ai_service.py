# -*- coding: utf-8 -*-
import os, json, re, base64, requests
from datetime import datetime
from PIL import Image

WORKSPACE_DIR = "workspace"
TRACKER_FILE = "api_key_tracker.json"
WORKSPACE_TRACKER = os.path.join(WORKSPACE_DIR, "api_key_tracker.json")

# 🌟 নতুন মডেল তালিকা
OPENROUTER_MODELS = [
    "google/gemini-2.0-flash-001",
    "meta-llama/llama-3.3-70b-instruct",
    "deepseek/deepseek-chat",
    "mistralai/mistral-large-2411"
]
GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
CEREBRAS_MODELS = ["llama-3.3-70b", "llama3.1-8b"]
OLLAMA_MODELS = [
    "gemma4:31b", "gemma4", "gpt-oss:120b", "gpt-oss:20b",
    "nemotron-3-nano:30b", "kimi-k3", "minimax-m3", "kimi-k2.6"
]

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
                with open(p, "r", encoding="utf-8") as f: return json.load(f)
            except Exception: pass
    return {}

def save_tracker_index(service_name, index, total_keys):
    if total_keys == 0: return
    data = load_tracker()
    if service_name not in data: data[service_name] = {}
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
# 🌟 বাংলা সংখ্যা ও ফরম্যাটিং ইঞ্জিন
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
        except Exception: return num_str
    text = re.sub(r'[0-9০-৯]+', num_repl, text)
    text = re.sub(r'ঘরে\s*বসে\s*', '', text)
    return text

def sanitize_youtube_tags(raw_tags, max_total_chars=400):
    clean_tags = []
    current_length = 0
    for tag in raw_tags:
        if not tag or not isinstance(tag, str): continue
        cleaned = re.sub(r'[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\<\>\"\,\n\r]', '', tag)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
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
    return cleaned.strip()

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
        if json_match: return json.loads(json_match.group(0))
        return json.loads(raw_text)
    except Exception: return None

# =========================================================================
# 🌟 মাস্টার প্রম্পট ও এআই এক্সিকিউশন ইঞ্জিন (১০+ মিনিটের সেগমেন্টেড স্ক্রিপ্ট)
# =========================================================================

def generate_job_content(title, img_paths):
    clean_title = clean_title_for_display(title)
    words = clean_title.split()
    org_name = clean_title.split("নিয়োগ")[0].strip() if "নিয়োগ" in clean_title else " ".join(words[:min(3, len(words))])
    vac_str, qual_str = extract_vacancy_and_qual(clean_title)

    prompt = f"""You are a senior job analyst and YouTube documentary scriptwriter.
Job Circular: "{clean_title}"
Organization: "{org_name}"

CRITICAL SCRIPT REQUIREMENTS (MUST PRODUCE A 10+ MINUTE VIDEO):
1. LENGTH: 1350 to 1500 Bengali words total across all segments.
2. CONTENT FOCUS:
   - For every single position/post in this circular, thoroughly explain:
     * Exact name of the post and how many people will be hired.
     * Job responsibilities: what kind of work and duties the employee will perform day-to-day.
     * Educational qualifications, required GPA/division, and technical skills needed.
     * Salary scale, pay grade, and government/institutional benefits.
   - Outline age limit requirements and eligible district criteria.
3. FORBIDDEN CONTENT:
   - Do NOT explain application submission procedures (do not mention website links, application portal forms, or SMS fee submission rules).
4. OUTRO & CALL TO ACTION (CTA):
   - At the end, state:
     "এই নিয়োগে আবেদন করার জন্য যদি আবেদন ফরম পূরণ করতে হয় অথবা ফরমাল আবেদনপত্র ও জীবনবৃত্তান্ত প্রস্তুত করতে হয়, তবে স্ক্রিনে দেওয়া অথবা ডেসক্রিপশনে থাকা হোয়াটসঅ্যাপ নম্বরে (জিরো ওয়ান ফাইভ ফোর জিরো ফাইভ জিরো থ্রি জিরো নাইন টু) আজই যোগাযোগ করুন। আমাদের অভিজ্ঞ টিম অত্যন্ত সতর্কতার সাথে আপনার হয়ে আবেদনের যাবতীয় কাজ সম্পন্ন করে দেবে।"
5. SCRIPT STRUCTURE (For Video Synchronizer):
   Return the script in "script_segments" list (8 to 12 detailed segments). Each segment must specify its visual target on the circular:
   - "focus_region": One of ["header", "post_1", "post_2", "post_3", "post_4", "terms", "footer"]
   - "image_index": 1, 2, or 3 (indicating which circular image page this corresponds to)
   - "text": Spoken Bengali text (120 to 160 words per segment).
6. NUMBERS IN WORDS: Every single number in the spoken text MUST be written in full Bengali words (কথায় লেখা, যেমন 'দুইশত একুশ', 'একশত পঞ্চাশ', 'পঁচিশ আগস্ট').

Return strictly valid JSON:
{{
  "optimized_title": "Unique high-CTR title under 95 chars",
  "video_description": "Tailored description with post highlights and WhatsApp contact wa.me/8801540503092",
  "specific_tags": ["..."],
  "top_text": "2-3 words for thumbnail top bar",
  "row1_text": "2-3 words for thumbnail red hook",
  "row2_text": "2-3 words for thumbnail vacancy hook",
  "sub_text": "2-3 words for thumbnail qualification",
  "bot_text": "Unique dynamic 2-4 words for thumbnail bottom bar",
  "script_segments": [
    {{"segment_id": 1, "focus_region": "header", "image_index": 1, "text": "..."}},
    {{"segment_id": 2, "focus_region": "post_1", "image_index": 1, "text": "..."}}
  ]
}}"""

    base64_images = [encode_image_base64(p) for p in img_paths[:3] if encode_image_base64(p)]

    def format_output(data):
        opt_title = data.get("optimized_title", clean_title)[:100]
        desc = data.get("video_description", "")
        tags = sanitize_youtube_tags(data.get("specific_tags", []) + DEFAULT_BASE_TAGS)

        segments = data.get("script_segments", [])
        if not segments:
            # ফলব্যাক সেগমেন্ট
            segments = [{"segment_id": 1, "focus_region": "header", "image_index": 1, "text": "আসসালামু আলাইকুম। আজকের ভিডিওতে আপনাদের স্বাগতম।"}]

        # প্রতিটি সেগমেন্টের টেক্সটের সংখ্যাকে কথায় রূপান্তর
        full_text_list = []
        for seg in segments:
            clean_t = convert_all_numbers_in_script(seg.get("text", ""))
            seg["text"] = clean_t
            full_text_list.append(clean_t)

        voiceover_script = " ".join(full_text_list)

        gen_bot = data.get("bot_text", "").strip()
        if not gen_bot or "আবেদনের নিয়ম ও বিস্তারিত" in gen_bot:
            gen_bot = f"({vac_str}) মেগা সার্কুলার" if vac_str else "আবেদনের শেষ তারিখ ও নিয়ম"

        thumb_meta = {
            "top_text": strip_unwanted_chars(data.get("top_text", org_name)),
            "row1_text": strip_unwanted_chars(data.get("row1_text", "জরুরি নিয়োগ")),
            "row2_text": strip_unwanted_chars(data.get("row2_text", vac_str if vac_str else "বিশাল নিয়োগ")),
            "sub_text": strip_unwanted_chars(data.get("sub_text", qual_str if qual_str else "যোগ্যতা ও বিস্তারিত")),
            "bot_text": strip_unwanted_chars(gen_bot)
        }
        return opt_title, voiceover_script, segments, thumb_meta, desc, tags

    # =========================================================================
    # 🌟 ১. প্রথম প্রায়োরিটি: OpenRouter Cloud API (Priority 1)
    # =========================================================================
    raw_openrouter = os.environ.get("OPENROUTER_API_KEYS", os.environ.get("OPENROUTER_API_KEY", "")).strip()
    openrouter_order = get_keys_in_cyclic_order("openrouter", raw_openrouter)
    total_openrouter = len(parse_multiline_keys(raw_openrouter))

    if openrouter_order:
        print("\n" + "="*65)
        print("🤖 [AI PRIORITY 1] OpenRouter Cloud API (10-Min In-Depth Script)")
        print(f"🔑 Total {total_openrouter} Key(s). Resuming from Key #{openrouter_order[0][0] + 1}...")
        print("="*65)

        for actual_idx, or_key in openrouter_order:
            key_num = actual_idx + 1
            headers = {
                "Authorization": f"Bearer {or_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com",
                "X-Title": "YouTube Job Automation"
            }
            content_list = [{"type": "text", "text": prompt}]
            for b64 in base64_images[:2]:
                content_list.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

            for model_name in OPENROUTER_MODELS:
                print(f"  • Trying OpenRouter Key #{key_num}/{total_openrouter} (Model: '{model_name}')...")
                payload = {"model": model_name, "messages": [{"role": "user", "content": content_list}], "temperature": 0.4}
                try:
                    resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=60)
                    if resp.status_code == 200:
                        content_txt = resp.json()['choices'][0]['message']['content']
                        data = parse_json_safely(content_txt)
                        if data and data.get("optimized_title"):
                            save_tracker_index("openrouter", actual_idx, total_openrouter)
                            print(f"  ✨ [SUCCESS] Generated via OpenRouter Key #{key_num} ('{model_name}')!")
                            return format_output(data)
                    elif resp.status_code in [401, 402, 429]:
                        break
                except Exception as e:
                    print(f"  ⚠️ Error with OpenRouter Key #{key_num}: {e}")

            save_tracker_index("openrouter", actual_idx + 1, total_openrouter)

    # =========================================================================
    # 🌟 ২. দ্বিতীয় প্রায়োরিটি: Groq Cloud API (Priority 2)
    # =========================================================================
    raw_groq = os.environ.get("GROQ_API_KEYS", os.environ.get("GROQ_API", "")).strip()
    groq_order = get_keys_in_cyclic_order("groq", raw_groq)
    total_groq = len(parse_multiline_keys(raw_groq))

    if groq_order:
        print("\n" + "="*65)
        print("🤖 [AI PRIORITY 2] Groq Cloud API")
        print("="*65)
        for actual_idx, g_key in groq_order:
            key_num = actual_idx + 1
            headers = {"Authorization": f"Bearer {g_key}", "Content-Type": "application/json"}
            for g_model in GROQ_MODELS:
                print(f"  • Trying Groq Key #{key_num}/{total_groq} (Model: '{g_model}')...")
                payload = {
                    "model": g_model,
                    "messages": [{"role": "system", "content": "You are an expert Bengali job scriptwriter. Output valid JSON only."}, {"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.4,
                    "max_tokens": 4000
                }
                try:
                    resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=40)
                    if resp.status_code == 200:
                        data = parse_json_safely(resp.json()['choices'][0]['message']['content'])
                        if data and data.get("optimized_title"):
                            save_tracker_index("groq", actual_idx, total_groq)
                            print(f"  ✨ [SUCCESS] Generated via Groq Key #{key_num} ('{g_model}')!")
                            return format_output(data)
                    elif resp.status_code in [401, 402, 429]:
                        break
                except Exception as e:
                    print(f"  ⚠️ Error with Groq: {e}")
            save_tracker_index("groq", actual_idx + 1, total_groq)

    # =========================================================================
    # 🌟 ৩. তৃতীয় প্রায়োরিটি: Cerebras Cloud API (Priority 3)
    # =========================================================================
    raw_cerebras = os.environ.get("CEREBRAS_API_KEYS", os.environ.get("CEREBRAS_API_KEY", "")).strip()
    cerebras_order = get_keys_in_cyclic_order("cerebras", raw_cerebras)
    total_cerebras = len(parse_multiline_keys(raw_cerebras))

    if cerebras_order:
        print("\n" + "="*65)
        print("🤖 [AI PRIORITY 3] Cerebras Cloud API")
        print("="*65)
        for actual_idx, c_key in cerebras_order:
            key_num = actual_idx + 1
            headers = {"Authorization": f"Bearer {c_key}", "Content-Type": "application/json"}
            for c_model in CEREBRAS_MODELS:
                print(f"  • Trying Cerebras Key #{key_num}/{total_cerebras} (Model: '{c_model}')...")
                payload = {
                    "model": c_model,
                    "messages": [{"role": "system", "content": "Output valid JSON only."}, {"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.4,
                    "max_tokens": 4000
                }
                try:
                    resp = requests.post("https://api.cerebras.ai/v1/chat/completions", headers=headers, json=payload, timeout=40)
                    if resp.status_code == 200:
                        data = parse_json_safely(resp.json()['choices'][0]['message']['content'])
                        if data and data.get("optimized_title"):
                            save_tracker_index("cerebras", actual_idx, total_cerebras)
                            print(f"  ✨ [SUCCESS] Generated via Cerebras Key #{key_num} ('{c_model}')!")
                            return format_output(data)
                    elif resp.status_code in [401, 402, 429]:
                        break
                except Exception as e:
                    print(f"  ⚠️ Error with Cerebras: {e}")
            save_tracker_index("cerebras", actual_idx + 1, total_cerebras)

    # =========================================================================
    # 🌟 ৪. চতুর্থ (সর্বশেষ) প্রায়োরিটি: Ollama Cloud API (Gemma First)
    # =========================================================================
    raw_ollama = os.environ.get("OLLAMA_API_KEYS", os.environ.get("Ollama_API_Key", os.environ.get("OLLAMA_API_KEY", ""))).strip()
    ollama_order = get_keys_in_cyclic_order("ollama", raw_ollama)
    total_ollama = len(parse_multiline_keys(raw_ollama))

    if ollama_order:
        print("\n" + "="*65)
        print("🤖 [AI PRIORITY 4 - LAST] Ollama Cloud (Gemma Prioritized)")
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
                    resp = requests.post("https://api.ollama.com/api/chat", headers=headers, json=payload, timeout=50)
                    if resp.status_code == 200:
                        data = parse_json_safely(resp.json().get("message", {}).get("content", "").strip())
                        if data and data.get("optimized_title"):
                            save_tracker_index("ollama", actual_idx, total_ollama)
                            print(f"  ✨ [SUCCESS] Generated via Ollama Key #{key_num} ('{model_name}')!")
                            return format_output(data)
                    elif resp.status_code in [401, 402, 429]:
                        break
                except Exception as e:
                    print(f"  ⚠️ Error with Ollama: {e}")
            save_tracker_index("ollama", actual_idx + 1, total_ollama)

    return None, None, None, None, None, None
