# -*- coding: utf-8 -*-
import os, json, re, requests
from datetime import datetime

WORKSPACE_DIR = "workspace"
TRACKER_FILE = "api_key_tracker.json"
WORKSPACE_TRACKER = os.path.join(WORKSPACE_DIR, "api_key_tracker.json")

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

def clean_script_for_speech(raw_text):
    if not raw_text: return ""
    text = re.sub(r'[\*\_\|\#\~]', '', str(raw_text))
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'https?://\S+|wa\.me/\S+', '', text)
    text = re.sub(r'[\<\>\{\}\(\)\@\$\^\&\+\=\_\\\/]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_multiline_keys(raw_text):
    if not raw_text: return []
    lines = re.split(r'[\r\n,;]+', str(raw_text))
    return [k.strip() for k in lines if k.strip() and not k.strip().startswith('#')]

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

def parse_json_safely(raw_text):
    try:
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match: return json.loads(json_match.group(0))
        return json.loads(raw_text)
    except Exception: return None

# =========================================================================
# 🌟 কেন্দ্রীয় এআই এক্সিকিউশন গেটওয়ে
# =========================================================================

def execute_ai_query(prompt, json_mode=True):
    # ১. OpenRouter (১ম প্রায়োরিটি)
    raw_openrouter = os.environ.get("OPENROUTER_API_KEYS", os.environ.get("OPENROUTER_API_KEY", "")).strip()
    or_order = get_keys_in_cyclic_order("openrouter", raw_openrouter)
    total_or = len(parse_multiline_keys(raw_openrouter))

    if or_order:
        for actual_idx, or_key in or_order:
            headers = {"Authorization": f"Bearer {or_key}", "Content-Type": "application/json", "HTTP-Referer": "https://github.com", "X-Title": "YouTube Automation"}
            for model_name in OPENROUTER_MODELS:
                payload = {"model": model_name, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}
                try:
                    resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=50)
                    if resp.status_code == 200:
                        content_txt = resp.json()['choices'][0]['message']['content']
                        save_tracker_index("openrouter", actual_idx, total_or)
                        return parse_json_safely(content_txt) if json_mode else content_txt
                    elif resp.status_code in [401, 402, 429]: break
                except Exception: pass
            save_tracker_index("openrouter", actual_idx + 1, total_or)

    # ২. Groq (২য় প্রায়োরিটি)
    raw_groq = os.environ.get("GROQ_API_KEYS", os.environ.get("GROQ_API", "")).strip()
    groq_order = get_keys_in_cyclic_order("groq", raw_groq)
    total_groq = len(parse_multiline_keys(raw_groq))

    if groq_order:
        for actual_idx, g_key in groq_order:
            headers = {"Authorization": f"Bearer {g_key}", "Content-Type": "application/json"}
            for g_model in GROQ_MODELS:
                payload = {
                    "model": g_model,
                    "messages": [{"role": "system", "content": "You are a professional Bengali job circular specialist. Output valid JSON only." if json_mode else "Be accurate."}, {"role": "user", "content": prompt}],
                    "temperature": 0.3, "max_tokens": 4000
                }
                if json_mode: payload["response_format"] = {"type": "json_object"}
                try:
                    resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=40)
                    if resp.status_code == 200:
                        content_txt = resp.json()['choices'][0]['message']['content']
                        save_tracker_index("groq", actual_idx, total_groq)
                        return parse_json_safely(content_txt) if json_mode else content_txt
                    elif resp.status_code in [401, 402, 429]: break
                except Exception: pass
            save_tracker_index("groq", actual_idx + 1, total_groq)

    # ৩. Cerebras (৩য় প্রায়োরিটি)
    raw_cerebras = os.environ.get("CEREBRAS_API_KEYS", os.environ.get("CEREBRAS_API_KEY", "")).strip()
    cerebras_order = get_keys_in_cyclic_order("cerebras", raw_cerebras)
    total_cerebras = len(parse_multiline_keys(raw_cerebras))

    if cerebras_order:
        for actual_idx, c_key in cerebras_order:
            headers = {"Authorization": f"Bearer {c_key}", "Content-Type": "application/json"}
            for c_model in CEREBRAS_MODELS:
                payload = {"model": c_model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3, "max_tokens": 4000}
                try:
                    resp = requests.post("https://api.cerebras.ai/v1/chat/completions", headers=headers, json=payload, timeout=40)
                    if resp.status_code == 200:
                        content_txt = resp.json()['choices'][0]['message']['content']
                        save_tracker_index("cerebras", actual_idx, total_cerebras)
                        return parse_json_safely(content_txt) if json_mode else content_txt
                    elif resp.status_code in [401, 402, 429]: break
                except Exception: pass
            save_tracker_index("cerebras", actual_idx + 1, total_cerebras)

    # ৪. Ollama (৪র্থ প্রায়োরিটি - Gemma First)
    raw_ollama = os.environ.get("OLLAMA_API_KEYS", os.environ.get("Ollama_API_Key", os.environ.get("OLLAMA_API_KEY", ""))).strip()
    ollama_order = get_keys_in_cyclic_order("ollama", raw_ollama)
    total_ollama = len(parse_multiline_keys(raw_ollama))

    if ollama_order:
        for actual_idx, o_key in ollama_order:
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {o_key}"}
            for model_name in OLLAMA_MODELS:
                payload = {"model": model_name, "messages": [{"role": "user", "content": prompt}], "stream": False, "options": {"temperature": 0.3}}
                try:
                    resp = requests.post("https://api.ollama.com/api/chat", headers=headers, json=payload, timeout=50)
                    if resp.status_code == 200:
                        content_txt = resp.json().get("message", {}).get("content", "").strip()
                        save_tracker_index("ollama", actual_idx, total_ollama)
                        return parse_json_safely(content_txt) if json_mode else content_txt
                    elif resp.status_code in [401, 402, 429]: break
                except Exception: pass
            save_tracker_index("ollama", actual_idx + 1, total_ollama)

    return None

# =========================================================================
# 🌟 ৪টি পৃথক মডুলার কল (আবেদন পদ্ধতি শনাক্ত ও রোবটিক শব্দ প্রতিরোধ)
# =========================================================================

def extract_verified_job_data(title, article_text):
    """
    【কল ১】টেক্সট পড়ে পদের সংখ্যা ও ডাকযোগ/কুরিয়ার/অনলাইন আবেদন পদ্ধতি নিশ্চিত করা
    """
    print("\n🔍 [STEP 1] Extracting accurate job facts & confirmed application method...")
    prompt = f"""You are a strict data extraction specialist.
Analyze this human-written Bengali job circular article text carefully:
---
TITLE: {title}
ARTICLE TEXT:
{article_text[:4000]}
---

CRITICAL INSTRUCTIONS:
1. Examine if application is through Courier (কুরিয়ার) or Postal Department / Post Office (ডাক বিভাগ / ডাকযোগে / রেজিস্টার্ড ডাক) or Direct Office Submission:
   - If applicants must fill a prescribed form (নির্ধারিত চাকরির আবেদন ফরম / নির্দিষ্ট ফরম পূরণ), set "application_method": "prescribed_form" and "hook_phrase": "ফর্ম পূরণ".
   - If applicants must write/draft a formal application letter on plain paper with CV (সাদা কাগজে স্বহস্তে লিখিত আবেদনপত্র / আবেদনপত্র তৈরি), set "application_method": "formal_letter" and "hook_phrase": "আবেদনপত্র তৈরি".
   - Otherwise, if application is via online link/teletalk/web portal, set "application_method": "online" and "hook_phrase": "অনলাইনে আবেদন".

2. Extract EXACT facts. DO NOT GUESS:
   - "organization": Official Bengali organization name.
   - "total_vacancies": Exact total vacancy count as stated (e.g. '০৫টি', '১২টি', '১টি').
   - "posts": Array of each job position:
     * "post_name": Exact post name.
     * "vacancy_count": Exact number of vacancies (e.g. '১টি', '০৫টি'). Never guess.
     * "salary_scale": Exact pay scale and grade.
     * "educational_qualification": Exact minimum degree and qualification.
     * "work_nature": Brief description of what work this post does.

Return strictly valid JSON:
{{
  "organization": "...",
  "total_vacancies": "...",
  "application_method": "prescribed_form" | "formal_letter" | "online",
  "hook_phrase": "ফর্ম পূরণ" | "আবেদনপত্র তৈরি" | "অনলাইনে আবেদন",
  "posts": [
    {{"post_name": "...", "vacancy_count": "...", "salary_scale": "...", "educational_qualification": "...", "work_nature": "..."}}
  ]
}}"""
    return execute_ai_query(prompt, json_mode=True)

def generate_script_from_verified_data(verified_data, title, article_text):
    """
    【কল ২】১০+ মিনিটের গভীর স্ক্রিপ্ট ('শূন্যপদ' পুনরাবৃত্তি মুক্ত ও নিশ্চিত CTA)
    """
    print("🎙️ [STEP 2] Generating in-depth 10+ minute script without repetitive 'শূন্যপদ'...")
    data_str = json.dumps(verified_data, ensure_ascii=False, indent=2)
    app_method = verified_data.get("application_method", "online")

    # 🌟 নিশ্চিত আবেদন কল-টু-অ্যাকশন
    if app_method == "prescribed_form":
        cta_instruction = 'Tell viewers: "এই নিয়োগে আবেদনের জন্য নির্ধারিত চাকরির আবেদন ফরমটি সঠিক নিয়মে পূরণ করতে এবং প্রয়োজনীয় কাগজপত্র প্রস্তুত করতে স্ক্রিনে দেওয়া অথবা ডেসক্রিপশনে থাকা হোয়াটসঅ্যাপ নম্বরে (জিরো ওয়ান ফাইভ ফোর জিরো ফাইভ জিরো থ্রি জিরো নাইন টু) আজই যোগাযোগ করুন। আমাদের অভিজ্ঞ টিম আপনার চাকরির ফর্ম পূরণ সফলভাবে সম্পন্ন করে দেবে।"'
    elif app_method == "formal_letter":
        cta_instruction = 'Tell viewers: "এই নিয়োগের জন্য সঠিক ফরম্যাটে আনুষ্ঠানিক আবেদনপত্র ও জীবনবৃত্তান্ত (CV) তৈরি করতে স্ক্রিনে দেওয়া অথবা ডেসক্রিপশনে থাকা হোয়াটসঅ্যাপ নম্বরে (জিরো ওয়ান ফাইভ ফোর জিরো ফাইভ জিরো থ্রি জিরো নাইন টু) আজই যোগাযোগ করুন। আমাদের অভিজ্ঞ টিম আপনার আবেদনপত্র তৈরি ও গুছিয়ে দেওয়ার সম্পূর্ণ দায়িত্ব নেবে।"'
    else:
        cta_instruction = 'Tell viewers: "এই নিয়োগে অনলাইনে শতভাগ নির্ভুলভাবে আবেদন সম্পন্ন করতে স্ক্রিনে দেওয়া অথবা ডেসক্রিপশনে থাকা হোয়াটসঅ্যাপ নম্বরে (জিরো ওয়ান ফাইভ ফোর জিরো ফাইভ জিরো থ্রি জিরো নাইন টু) আজই যোগাযোগ করুন। আমাদের অভিজ্ঞ টিম অত্যন্ত সতর্কতার সাথে আপনার আবেদন ফরম পূরণ করে দেবে।"'

    prompt = f"""You are a senior job documentary scriptwriter.
Title: "{title}"
VERIFIED JOB DATA:
{data_str}
REFERENCE ARTICLE CONTEXT:
{article_text[:2500]}

STRICT SCRIPT RULES (10+ MINUTE VIDEO DURATION):
1. LENGTH: 1350 to 1500 Bengali words total across 8 to 12 detailed segments.
2. 🚫 STRICT PROHIBITION ON 'শূন্যপদ':
   - Do NOT repetitively say 'অমুক পদে এতটি শূন্যপদ রয়েছে' or overuse the robotic word 'শূন্যপদ'.
   - Instead, use conversational, natural Bengali expressions like:
     * 'অমুক পদে [সংখ্যা] জন লোক নেওয়া হবে'
     * 'এই পদে [সংখ্যা] জন নিয়োগ পাবেন'
     * 'এই পদের জন্য মোট [সংখ্যা] জন কর্মী নেওয়া হবে'
3. IN-DEPTH DETAILS:
   - For every post, thoroughly explain daily responsibilities (কোন পদের কি কাজ ও দায়িত্ব), qualifications, GPA, salary scale, grade, and government benefits.
4. FORBIDDEN: Do NOT explain application website steps, SMS codes, or photo pixel sizes.
5. OUTRO & CONFIRMED CTA:
   {cta_instruction}
6. VISUAL TARGETS (For Video Synchronizer):
   Return as "script_segments" list:
   - "focus_region": One of ["header", "post_1", "post_2", "post_3", "post_4", "terms", "footer"]
   - "image_index": 1, 2, or 3
   - "text": Spoken Bengali text (120 to 160 words per segment). All numbers in Bengali words!

Return strictly valid JSON:
{{
  "script_segments": [
    {{"segment_id": 1, "focus_region": "header", "image_index": 1, "text": "..."}},
    {{"segment_id": 2, "focus_region": "post_1", "image_index": 1, "text": "..."}}
  ]
}}"""
    return execute_ai_query(prompt, json_mode=True)

def generate_seo_metadata(verified_data, title):
    """
    【কল ৩】এসইও ফ্রেন্ডলি টাইটেল, ডেসক্রিপশন ও ট্যাগস ('ফর্ম পূরণ' / 'আবেদনপত্র তৈরি' সহ)
    """
    print("📈 [STEP 3] Generating SEO Title, Description & Tags with Method Hook...")
    posts_summary = ", ".join([p.get("post_name", "") for p in verified_data.get("posts", [])[:4]])
    total_vac = verified_data.get("total_vacancies", "")
    org = verified_data.get("organization", title)
    hook_phrase = verified_data.get("hook_phrase", "অনলাইনে আবেদন")

    prompt = f"""Generate YouTube SEO metadata for this job circular:
Organization: "{org}"
Title: "{title}"
Key Posts: "{posts_summary}"
Total Vacancies: "{total_vac}"
Application Method Hook: "{hook_phrase}"

MANDATORY RULE:
- The YouTube Title, Description, and Tags MUST prominently mention "{hook_phrase}"!
  * If "{hook_phrase}" is "ফর্ম পূরণ": Title must include 'ফর্ম পূরণ' (e.g. "... | চাকরির ফর্ম পূরণ করার নিয়ম 🔥").
  * If "{hook_phrase}" is "আবেদনপত্র তৈরি": Title must include 'আবেদনপত্র তৈরি' (e.g. "... | চাকরির আবেদনপত্র তৈরি করার নিয়ম 📝").
  * If "{hook_phrase}" is "অনলাইনে আবেদন": Title must include 'অনলাইনে আবেদন'.

Return strictly valid JSON:
{{
  "optimized_title": "High CTR click-worthy Bengali YouTube Title under 95 chars with '{hook_phrase}' and symbols (🔥, 🚨, |)",
  "video_description": "Comprehensive description with post highlights, vacancy details, '{hook_phrase}' instructions, and WhatsApp contact: wa.me/8801540503092",
  "specific_tags": ["6 to 10 specific Bengali & English SEO tags including '{hook_phrase}', without commas"]
}}"""
    return execute_ai_query(prompt, json_mode=True)

def generate_thumbnail_metadata(verified_data, title):
    """
    【কল ৪】থাম্বনেইল টেক্সট ('ফর্ম পূরণ' / 'আবেদনপত্র তৈরি' সহ)
    """
    print("🎨 [STEP 4] Generating Dynamic Thumbnail Texts with Method Hook...")
    first_post = verified_data.get("posts", [{}])[0]
    post_name = first_post.get("post_name", "জরুরি নিয়োগ")
    total_vac = verified_data.get("total_vacancies", "")
    org = verified_data.get("organization", "সরকারি চাকরি")
    qual = first_post.get("educational_qualification", "যোগ্যতা ও নিয়ম")
    hook_phrase = verified_data.get("hook_phrase", "অনলাইনে আবেদন")

    prompt = f"""Generate 4 dynamic, distinct thumbnail texts for this job:
Organization: "{org}"
Main Post: "{post_name}"
Vacancies: "{total_vac}"
Qualification: "{qual}"
Application Method Hook: "{hook_phrase}"

MANDATORY RULE:
One of the thumbnail text lines (row1_text, sub_text, or bot_text) MUST specifically highlight "{hook_phrase}"!
- If "{hook_phrase}" is "ফর্ম পূরণ": use texts like "ফর্ম পূরণের নিয়ম" or "ফর্ম পূরণ করলেই চাকরি".
- If "{hook_phrase}" is "আবেদনপত্র তৈরি": use texts like "আবেদনপত্র তৈরির নিয়ম" or "আবেদনপত্র তৈরি".

Rules:
- "top_text": 2-3 words. Organization name or category.
- "row1_text": 2-3 words. Main eye-catching hook (e.g. "{post_name}").
- "row2_text": 2-3 words. Vacancy count in RED (e.g. "{total_vac if total_vac else 'বিশাল নিয়োগ'}").
- "sub_text": 2-3 words. Qualification or Hook (e.g. "{hook_phrase}", "SSC/HSC পাশ").
- "bot_text": 2-4 words. Bottom bar text featuring "{hook_phrase}" or circular details.

Return strictly valid JSON:
{{
  "top_text": "...",
  "row1_text": "...",
  "row2_text": "...",
  "sub_text": "...",
  "bot_text": "..."
}}"""
    return execute_ai_query(prompt, json_mode=True)

# =========================================================================
# 🌟 মূল মাস্টার ফাংশন
# =========================================================================

def generate_job_content(title, article_text, img_paths=None):
    clean_title = clean_title_for_display(title)

    # ১. কল ১: টেক্সট পড়ে সঠিক পদ ও আবেদন পদ্ধতি এক্সট্রাক্ট করা
    verified_data = extract_verified_job_data(clean_title, article_text)
    if not verified_data or not verified_data.get("posts"):
        verified_data = {
            "organization": clean_title.split("নিয়োগ")[0].strip(),
            "total_vacancies": "",
            "application_method": "online",
            "hook_phrase": "অনলাইনে আবেদন",
            "posts": [{"post_name": "বিভিন্ন পদে নিয়োগ", "vacancy_count": "", "salary_scale": "সরকারি স্কেল", "educational_qualification": "বিজ্ঞপ্তি অনুযায়ী", "work_nature": "দাপ্তরিক দায়িত্ব"}]
        }

    # ২. কল ২: ১০+ মিনিটের গভীর স্ক্রিপ্ট ('শূন্যপদ' মুক্ত)
    script_res = generate_script_from_verified_data(verified_data, clean_title, article_text)
    segments = script_res.get("script_segments", []) if script_res else []
    if not segments:
        segments = [{"segment_id": 1, "focus_region": "header", "image_index": 1, "text": "আসসালামু আলাইকুম। আজকের ভিডিওতে আপনাদের স্বাগতম।"}]

    full_text_list = []
    for seg in segments:
        clean_t = convert_all_numbers_in_script(seg.get("text", ""))
        seg["text"] = clean_t
        full_text_list.append(clean_t)
    voiceover_script = " ".join(full_text_list)

    # ৩. কল ৩: এসইও মেটাডাটা
    seo_res = generate_seo_metadata(verified_data, clean_title)
    opt_title = seo_res.get("optimized_title", clean_title)[:100] if seo_res else clean_title[:100]
    video_desc = seo_res.get("video_description", clean_title) if seo_res else clean_title
    raw_tags = seo_res.get("specific_tags", []) if seo_res else []
    video_tags = sanitize_youtube_tags(raw_tags + DEFAULT_BASE_TAGS)

    # ৪. কল ৪: থাম্বনেইল টেক্সট
    thumb_res = generate_thumbnail_metadata(verified_data, clean_title)
    if not thumb_res: thumb_res = {}
    
    hook = verified_data.get("hook_phrase", "অনলাইনে আবেদন")
    total_v = verified_data.get("total_vacancies", "বিশাল নিয়োগ")

    thumb_meta = {
        "top_text": strip_unwanted_chars(thumb_res.get("top_text", verified_data.get("organization", "সরকারি চাকরি"))),
        "row1_text": strip_unwanted_chars(thumb_res.get("row1_text", "জরুরি নিয়োগ")),
        "row2_text": strip_unwanted_chars(thumb_res.get("row2_text", total_v if total_v else "বিশাল নিয়োগ")),
        "sub_text": strip_unwanted_chars(thumb_res.get("sub_text", hook)),
        "bot_text": strip_unwanted_chars(thumb_res.get("bot_text", f"{hook} ও বিস্তারিত"))
    }

    print(f"✨ [ACCURACY GUARANTEED] 10+ Min Script Generated with Method Hook: '{hook}'!")
    return opt_title, voiceover_script, segments, thumb_meta, video_desc, video_tags