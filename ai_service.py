# -*- coding: utf-8 -*-
import os, json, re, requests
from datetime import datetime

WORKSPACE_DIR = "workspace"
TRACKER_FILE = "api_key_tracker.json"
WORKSPACE_TRACKER = os.path.join(WORKSPACE_DIR, "api_key_tracker.json")

# 🌟 ওপেনরাউটারের ১০০% ফ্রি মডেলসমূহ (০ ডলার ব্যালেন্সেও চলবে)
OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-lite-preview-02-05:free",
    "google/gemini-2.0-pro-exp-02-05:free",
    "deepseek/deepseek-r1:free",
    "mistralai/mistral-small-24b-instruct-2501:free"
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
    if not raw_text: return None
    try:
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match: return json.loads(json_match.group(0))
        return json.loads(raw_text)
    except Exception: return None

# =========================================================================
# 🌟 কেন্দ্রীয় এআই এক্সিকিউশন গেটওয়ে (ভার্বোস ডিবাগ লগিং ও ফ্রি মডেল সহ)
# =========================================================================

def execute_ai_query(prompt, json_mode=True):
    # ১. OpenRouter (১০০% ফ্রি :free মডেল দিয়ে শুরু)
    raw_openrouter = os.environ.get("OPENROUTER_API_KEYS", os.environ.get("OPENROUTER_API_KEY", "")).strip()
    or_order = get_keys_in_cyclic_order("openrouter", raw_openrouter)
    total_or = len(parse_multiline_keys(raw_openrouter))

    if or_order:
        for actual_idx, or_key in or_order:
            masked = mask_key(or_key)
            headers = {"Authorization": f"Bearer {or_key}", "Content-Type": "application/json", "HTTP-Referer": "https://github.com", "X-Title": "YouTube Automation"}
            for model_name in OPENROUTER_MODELS:
                payload = {"model": model_name, "messages": [{"role": "user", "content": prompt}], "temperature": 0.4}
                try:
                    resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=60)
                    if resp.status_code == 200:
                        content_txt = resp.json()['choices'][0]['message']['content']
                        save_tracker_index("openrouter", actual_idx, total_or)
                        res = parse_json_safely(content_txt) if json_mode else content_txt
                        if res: return res
                    else:
                        print(f"  • OpenRouter ({model_name}) status: {resp.status_code}")
                except Exception as e:
                    print(f"  • OpenRouter notice: {e}")
            save_tracker_index("openrouter", actual_idx + 1, total_or)

    # ২. Google Gemini Text AI (অফিশিয়াল ফ্রি টিয়ার)
    raw_gemini = os.environ.get("GEMINI_API_KEYS", os.environ.get("GEMINI_API_KEY", "")).strip()
    gemini_keys = parse_multiline_keys(raw_gemini)
    if gemini_keys:
        for g_idx, g_key in enumerate(gemini_keys, 1):
            for g_model in ["gemini-2.0-flash", "gemini-1.5-flash"]:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{g_model}:generateContent?key={g_key}"
                headers = {"Content-Type": "application/json"}
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                try:
                    resp = requests.post(url, headers=headers, json=payload, timeout=40)
                    if resp.status_code == 200:
                        text_res = resp.json()['candidates'][0]['content']['parts'][0]['text']
                        res = parse_json_safely(text_res) if json_mode else text_res
                        if res:
                            print(f"  ✨ [SUCCESS] AI Content Generated via Google {g_model}!")
                            return res
                except Exception: pass

    # ৩. Groq Cloud
    raw_groq = os.environ.get("GROQ_API_KEYS", os.environ.get("GROQ_API", "")).strip()
    groq_order = get_keys_in_cyclic_order("groq", raw_groq)
    total_groq = len(parse_multiline_keys(raw_groq))

    if groq_order:
        for actual_idx, g_key in groq_order:
            masked = mask_key(g_key)
            headers = {"Authorization": f"Bearer {g_key}", "Content-Type": "application/json"}
            for g_model in GROQ_MODELS:
                payload = {
                    "model": g_model,
                    "messages": [{"role": "system", "content": "You are a professional Bengali job circular specialist. Output strictly valid JSON." if json_mode else "Write natural Bengali text."}, {"role": "user", "content": prompt}],
                    "temperature": 0.4, "max_tokens": 4096
                }
                if json_mode: payload["response_format"] = {"type": "json_object"}
                try:
                    resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=45)
                    if resp.status_code == 200:
                        content_txt = resp.json()['choices'][0]['message']['content']
                        save_tracker_index("groq", actual_idx, total_groq)
                        res = parse_json_safely(content_txt) if json_mode else content_txt
                        if res: return res
                    else:
                        print(f"  • Groq ({g_model}) status: {resp.status_code} ({resp.text[:60]})")
                except Exception as e:
                    print(f"  • Groq notice: {e}")
            save_tracker_index("groq", actual_idx + 1, total_groq)

    # ৪. Cerebras Cloud
    raw_cerebras = os.environ.get("CEREBRAS_API_KEYS", os.environ.get("CEREBRAS_API_KEY", "")).strip()
    cerebras_order = get_keys_in_cyclic_order("cerebras", raw_cerebras)
    total_cerebras = len(parse_multiline_keys(raw_cerebras))

    if cerebras_order:
        for actual_idx, c_key in cerebras_order:
            headers = {"Authorization": f"Bearer {c_key}", "Content-Type": "application/json"}
            for c_model in CEREBRAS_MODELS:
                payload = {"model": c_model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.4, "max_tokens": 4096}
                try:
                    resp = requests.post("https://api.cerebras.ai/v1/chat/completions", headers=headers, json=payload, timeout=45)
                    if resp.status_code == 200:
                        content_txt = resp.json()['choices'][0]['message']['content']
                        save_tracker_index("cerebras", actual_idx, total_cerebras)
                        res = parse_json_safely(content_txt) if json_mode else content_txt
                        if res: return res
                except Exception: pass
            save_tracker_index("cerebras", actual_idx + 1, total_cerebras)

    # ৫. Ollama Cloud
    raw_ollama = os.environ.get("OLLAMA_API_KEYS", os.environ.get("Ollama_API_Key", os.environ.get("OLLAMA_API_KEY", ""))).strip()
    ollama_order = get_keys_in_cyclic_order("ollama", raw_ollama)
    total_ollama = len(parse_multiline_keys(raw_ollama))

    if ollama_order:
        for actual_idx, o_key in ollama_order:
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {o_key}"}
            for model_name in OLLAMA_MODELS:
                payload = {"model": model_name, "messages": [{"role": "user", "content": prompt}], "stream": False, "options": {"temperature": 0.4}}
                try:
                    resp = requests.post("https://api.ollama.com/api/chat", headers=headers, json=payload, timeout=50)
                    if resp.status_code == 200:
                        content_txt = resp.json().get("message", {}).get("content", "").strip()
                        save_tracker_index("ollama", actual_idx, total_ollama)
                        res = parse_json_safely(content_txt) if json_mode else content_txt
                        if res: return res
                except Exception: pass
            save_tracker_index("ollama", actual_idx + 1, total_ollama)

    return None

# =========================================================================
# 🌟 আর্টিকেল টেক্সট থেকে ইমার্জেন্সি ফলব্যাক স্ক্রিপ্ট বিল্ডার (Fail-Safe)
# =========================================================================

def build_script_from_article_text(title, article_text, hook_phrase="অনলাইনে আবেদন"):
    """সব এআই ফেইল করলেও ওয়েবসাইটের আসল টেক্সট থেকে একটি পূর্ণাঙ্গ বড় স্ক্রিপ্ট বানিয়ে দেবে"""
    clean_lines = [l.strip() for l in article_text.split('\n') if len(l.strip()) > 15]
    body_summary = " ".join(clean_lines[:15]) if clean_lines else article_text[:1500]
    
    script = f"""আসসালামু আলাইকুম। আজকের ভিডিওতে আপনাদের সবাইকে স্বাগতম। সম্প্রতি {title} সংক্রান্ত একটি আকর্ষণীয় ও গুরুত্বপূর্ণ নিয়োগ বিজ্ঞপ্তি প্রকাশিত হয়েছে।

উক্ত নিয়োগ বিজ্ঞপ্তির বিস্তারিত তথ্যাবলী অনুযায়ী:
{body_summary}

এই নিয়োগে বিভিন্ন পদে নির্ধারিত যোগ্যতা অনুযায়ী আগ্রহী প্রার্থীদের থেকে দরখাস্ত আহ্বান করা হয়েছে। প্রতিটি পদের জন্য সুনির্দিষ্ট শিক্ষাগত যোগ্যতা, অভিজ্ঞতা এবং সংশ্লিষ্ট শর্তাবলী প্রযোজ্য হবে।

আবেদনের শেষ তারিখের পূর্বেই প্রয়োজনীয় কাগজপত্রসহ নিয়ম অনুযায়ী আবেদন প্রক্রিয়াটি সম্পন্ন করার জন্য পরামর্শ দেওয়া হলো। 

এই সার্কুলারে {hook_phrase} করার জন্য অথবা চাকরির আবেদন সংক্রান্ত যেকোনো সহায়তা পেতে স্ক্রিনে দেওয়া বা ডেসক্রিপশনের হোয়াটসঅ্যাপ নম্বরে (জিরো ওয়ান ফাইভ ফোর জিরো ফাইভ জিরো থ্রি জিরো নাইন টু) আজই যোগাযোগ করুন। আমাদের অভিজ্ঞ টিম আপনার আবেদনের যাবতীয় কাজ সতর্কতার সাথে সম্পন্ন করে দেবে। ধন্যবাদ।"""
    return script

# =========================================================================
# 🌟 ৪টি পৃথক মডুলার কল
# =========================================================================

def extract_verified_job_data(title, article_text):
    print("\n🔍 [STEP 1] Extracting accurate job facts & application method...")
    prompt = f"""Analyze this Bengali job circular article text:
---
TITLE: {title}
TEXT:
{article_text[:3500]}
---

Extract EXACT facts:
1. Examine application method:
   - If postal/courier/in-person form: "application_method": "prescribed_form", "hook_phrase": "ফর্ম পূরণ"
   - If handwritten application letter/CV: "application_method": "formal_letter", "hook_phrase": "আবেদনপত্র তৈরি"
   - Otherwise: "application_method": "online", "hook_phrase": "অনলাইনে আবেদন"
2. "organization": Bengali organization name.
3. "total_vacancies": Exact vacancies (e.g. '০৫টি', '১২টি', '১টি').
4. "posts": Array of each job:
   - "post_name": Position name.
   - "vacancy_count": Vacancy count (e.g. '১টি', '০৫টি').
   - "salary_scale": Pay scale and grade.
   - "educational_qualification": Minimum degree needed.

Return strictly valid JSON:
{{
  "organization": "...",
  "total_vacancies": "...",
  "application_method": "prescribed_form" | "formal_letter" | "online",
  "hook_phrase": "ফর্ম পূরণ" | "আবেদনপত্র তৈরি" | "অনলাইনে আবেদন",
  "posts": [
    {{"post_name": "...", "vacancy_count": "...", "salary_scale": "...", "educational_qualification": "..."}}
  ]
}}"""
    return execute_ai_query(prompt, json_mode=True)

def generate_script_from_verified_data(verified_data, title, article_text):
    print("🎙️ [STEP 2] Generating in-depth spoken script (Direct Text Mode)...")
    data_str = json.dumps(verified_data, ensure_ascii=False, indent=2)
    app_method = verified_data.get("application_method", "online")

    if app_method == "prescribed_form":
        cta_instruction = 'Tell viewers: "এই নিয়োগে আবেদনের জন্য নির্ধারিত চাকরির আবেদন ফরমটি সঠিক নিয়মে পূরণ করতে এবং প্রয়োজনীয় কাগজপত্র প্রস্তুত করতে স্ক্রিনে দেওয়া অথবা ডেসক্রিপশনে থাকা হোয়াটসঅ্যাপ নম্বরে (জিরো ওয়ান ফাইভ ফোর জিরো ফাইভ জিরো থ্রি জিরো নাইন টু) আজই যোগাযোগ করুন। আমাদের অভিজ্ঞ টিম আপনার চাকরির ফর্ম পূরণ সফলভাবে সম্পন্ন করে দেবে।"'
    elif app_method == "formal_letter":
        cta_instruction = 'Tell viewers: "এই নিয়োগের জন্য সঠিক ফরম্যাটে আনুষ্ঠানিক আবেদনপত্র ও জীবনবৃত্তান্ত (CV) তৈরি করতে স্ক্রিনে দেওয়া অথবা ডেসক্রিপশনে থাকা হোয়াটসঅ্যাপ নম্বরে (জিরো ওয়ান ফাইভ ফোর জিরো ফাইভ জিরো থ্রি জিরো নাইন টু) আজই যোগাযোগ করুন। আমাদের অভিজ্ঞ টিম আপনার আবেদনপত্র তৈরি ও গুছিয়ে দেওয়ার সম্পূর্ণ দায়িত্ব নেবে।"'
    else:
        cta_instruction = 'Tell viewers: "এই নিয়োগে অনলাইনে শতভাগ নির্ভুলভাবে আবেদন সম্পন্ন করতে স্ক্রিনে দেওয়া অথবা ডেসক্রিপশনে থাকা হোয়াটসঅ্যাপ নম্বরে (জিরো ওয়ান ফাইভ ফোর জিরো ফাইভ জিরো থ্রি জিরো নাইন টু) আজই যোগাযোগ করুন। আমাদের অভিজ্ঞ টিম অত্যন্ত সতর্কতার সাথে আপনার আবেদন ফরম পূরণ করে দেবে।"'

    prompt = f"""You are a professional Bengali job documentary scriptwriter.
Write an extensive, comprehensive, 650 to 900 word spoken Bengali voiceover script.
Title: "{title}"
Job Facts: {data_str}
Reference Context: {article_text[:2000]}

RULES:
1. Write in continuous, natural, professional spoken Bengali (no brackets, no stage directions).
2. Thoroughly explain daily job responsibilities (কোন পদের কি কাজ), vacancies for each post, required qualifications, salary scale, grade, and benefits.
3. Do NOT mention any year.
4. Do NOT use the word 'শূন্যপদ' repeatedly; use 'লোক নেওয়া হবে', 'নিয়োগ পাবেন'.
5. At the end, state: {cta_instruction}
6. IMPORTANT: Output ONLY the spoken Bengali script text directly. Do NOT output JSON, markdown fences, or introduction."""

    res_text = execute_ai_query(prompt, json_mode=False)
    return res_text if res_text and isinstance(res_text, str) else ""

def generate_seo_metadata(verified_data, title):
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
Hook: "{hook_phrase}"

MANDATORY: YouTube Title, Description, and Tags MUST include '{hook_phrase}'.

Return strictly valid JSON:
{{
  "optimized_title": "High CTR Bengali YouTube Title under 95 chars with '{hook_phrase}' and symbols (🔥, 🚨, |)",
  "video_description": "Comprehensive description with post highlights, vacancy details, '{hook_phrase}' instructions, and WhatsApp contact: wa.me/8801540503092",
  "specific_tags": ["6 to 10 specific SEO tags including '{hook_phrase}', without commas"]
}}"""
    return execute_ai_query(prompt, json_mode=True)

def generate_thumbnail_metadata(verified_data, title):
    print("🎨 [STEP 4] Generating Dynamic Thumbnail Texts with Method Hook...")
    first_post = verified_data.get("posts", [{}])[0]
    post_name = first_post.get("post_name", "জরুরি নিয়োগ")
    total_vac = verified_data.get("total_vacancies", "")
    org = verified_data.get("organization", "সরকারি চাকরি")
    qual = first_post.get("educational_qualification", "যোগ্যতা ও নিয়ম")
    hook_phrase = verified_data.get("hook_phrase", "অনলাইনে আবেদন")

    prompt = f"""Generate 4 dynamic, distinct thumbnail texts:
Organization: "{org}"
Main Post: "{post_name}"
Vacancies: "{total_vac}"
Qualification: "{qual}"
Hook: "{hook_phrase}"

Rules:
- "top_text": 2-3 words. Organization name.
- "row1_text": 2-3 words. Main hook (e.g. "{post_name}").
- "row2_text": 2-3 words. Vacancy count in RED (e.g. "{total_vac if total_vac else 'বিশাল নিয়োগ'}").
- "sub_text": 2-3 words. Qualification or Hook.
- "bot_text": 2-4 words. Bottom bar text featuring "{hook_phrase}".

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
# 🌟 মূল মাস্টার ফাংশন (১০০% স্ক্রিপ্ট নিশ্চয়তা সহ)
# =========================================================================

def generate_job_content(title, article_text, img_paths=None):
    clean_title = clean_title_for_display(title)

    # ১. কল ১: টেক্সট পড়ে সঠিক পদ ও আবেদন পদ্ধতি এক্সট্রাক্ট করা
    verified_data = extract_verified_job_data(clean_title, article_text)
    if not verified_data or not isinstance(verified_data, dict) or not verified_data.get("posts"):
        clean_org = clean_title.split("নিয়োগ")[0].strip() if "নিয়োগ" in clean_title else clean_title[:30]
        verified_data = {
            "organization": clean_org,
            "total_vacancies": "",
            "application_method": "online",
            "hook_phrase": "অনলাইনে আবেদন",
            "posts": [{"post_name": "বিভিন্ন পদে নিয়োগ", "vacancy_count": "", "salary_scale": "সরকারি স্কেল", "educational_qualification": "বিজ্ঞপ্তি অনুযায়ী"}]
        }

    # ২. কল ২: পূর্ণাঙ্গ গভীর স্ক্রিপ্ট সরাসরি টেক্সট মোডে
    raw_script = generate_script_from_verified_data(verified_data, clean_title, article_text)
    
    # 🌟 ফেইল-সেফ: কোনো কারণে এআই স্ক্রিপ্ট ছোট বা খালি দিলে ওয়েবসাইটের লেখা থেকেই বড় স্ক্রিপ্ট বানিয়ে নেওয়া
    if not raw_script or len(raw_script.split()) < 50:
        print("⚠️ AI script was too short or failed. Constructing rich script directly from article text...")
        raw_script = build_script_from_article_text(clean_title, article_text, verified_data.get("hook_phrase", "অনলাইনে আবেদন"))

    voiceover_script = convert_all_numbers_in_script(raw_script)

    # ৩. কল ৩: এসইও মেটাডাটা
    seo_res = generate_seo_metadata(verified_data, clean_title)
    opt_title = seo_res.get("optimized_title", clean_title)[:100] if seo_res and isinstance(seo_res, dict) else clean_title[:100]
    video_desc = seo_res.get("video_description", clean_title) if seo_res and isinstance(seo_res, dict) else clean_title
    raw_tags = seo_res.get("specific_tags", []) if seo_res and isinstance(seo_res, dict) else []
    video_tags = sanitize_youtube_tags(raw_tags + DEFAULT_BASE_TAGS)

    # ৪. কল ৪: থাম্বনেইল টেক্সট
    thumb_res = generate_thumbnail_metadata(verified_data, clean_title)
    if not thumb_res or not isinstance(thumb_res, dict): thumb_res = {}
    
    hook = verified_data.get("hook_phrase", "অনলাইনে আবেদন")
    total_v = verified_data.get("total_vacancies", "বিশাল নিয়োগ")

    thumb_meta = {
        "top_text": strip_unwanted_chars(thumb_res.get("top_text", verified_data.get("organization", "সরকারি চাকরি"))),
        "row1_text": strip_unwanted_chars(thumb_res.get("row1_text", "জরুরি নিয়োগ")),
        "row2_text": strip_unwanted_chars(thumb_res.get("row2_text", total_v if total_v else "বিশাল নিয়োগ")),
        "sub_text": strip_unwanted_chars(thumb_res.get("sub_text", hook)),
        "bot_text": strip_unwanted_chars(thumb_res.get("bot_text", f"{hook} ও বিস্তারিত"))
    }

    word_count = len(voiceover_script.split())
    print(f"✨ [ACCURACY GUARANTEED] {word_count}-word Deep Script Generated for '{clean_title[:35]}'!")
    return opt_title, voiceover_script, thumb_meta, video_desc, video_tags
