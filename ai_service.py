# -*- coding: utf-8 -*-
import base64
import io
import json
import os
import random
import re
import unicodedata
import requests
from datetime import datetime
from PIL import Image

WORKSPACE_DIR = "workspace"
TRACKER_FILE = "api_key_tracker.json"
WORKSPACE_TRACKER = os.path.join(WORKSPACE_DIR, "api_key_tracker.json")

# =========================================================================
# 🌟 সচল বড় মডেলসমূহ (Vision ও Text)
# =========================================================================

OPENROUTER_VISION_MODELS = [
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3.5-super-vl:free",
]

OPENROUTER_TEXT_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3.5-super-vl:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "openrouter/free",
]

OLLAMA_CHAT_URL = "https://ollama.com/api/chat"

OLLAMA_VISION_MODELS = [
    "kimi-k2.6",
    "mistral-large-3:675b",
    "deepseek-v4.1-flash",
    "glm-5.3-flash",
    "gemma4:31b",
]

OLLAMA_TEXT_MODELS = [
    "kimi-k2.6",
    "glm-5.2",
    "mistral-large-3:675b",
    "deepseek-v4.1-flash",
    "deepseek-v4-pro",
    "qwen3.5:397b",
    "minimax-m3",
    "glm-5.3-flash",
    "gpt-oss:120b",
    "nemotron-3-super",
    "gemma4:31b",
]

GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
]

CEREBRAS_MODELS = [
    "zai-glm-4.7",
    "qwen-3-235b-a22b-instruct-2507",
    "gpt-oss-120b",
]

GEMINI_TEXT_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash-lite",
]

LAYOUT_STYLES = [
    "poster_classic",
    "split_impact",
    "headline_first",
    "dark_bold",
    "stat_cards",
]

STANDARD_WHATSAPP_CTA = (
    "এই পদগুলোতে আবেদন করতে আগ্রহীরা আবেদন করার জন্য ভিডিওর স্ক্রিনে দেওয়া অথবা "
    "ডেসক্রিপশনে থাকা আমাদের হোয়াটসঅ্যাপ নম্বরে সরাসরি মেসেজ করুন। আমাদের অভিজ্ঞ টিম "
    "আপনার হয়ে সঠিক নিয়মে আবেদন সম্পন্ন করে দেবে। নিয়মিত চাকরির খবর পেতে চ্যানেলটি "
    "সাবস্ক্রাইব করে সাথেই থাকুন। ধন্যবাদ।"
)


def clean_script_for_speech(raw_text):
    if not raw_text:
        return ""
    text = unicodedata.normalize("NFC", str(raw_text))
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # অদৃশ্য ইউনিকোড ক্যারেক্টার রিমুভ (যা স্ক্রিনে □□□□ বক্স তৈরি করত)
    text = re.sub(r'[\u200b-\u200f\ufeff\u202a-\u202e\xa0]', ' ', text)
    text = re.sub(r'[\*\_\|\#\~`]', '', text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'https?://\S+|wa\.me/\S+', '', text)
    text = re.sub(r'[\<\>\{\}\(\)\@\$\^\&\+\=\_\\\/]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def parse_multiline_keys(raw_text):
    if not raw_text:
        return []
    lines = re.split(r'[\r\n,;]+', str(raw_text))
    return [k.strip() for k in lines if k.strip() and not k.strip().startswith('#')]


def mask_key(k):
    if not k or len(k) <= 8:
        return "****"
    return k[:4] + "..." + k[-4:]


def load_tracker():
    for p in [WORKSPACE_TRACKER, TRACKER_FILE]:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}


def save_tracker_index(service_name, index, total_keys):
    if total_keys == 0:
        return
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
        except Exception:
            pass


def get_keys_in_cyclic_order(service_name, raw_keys_str):
    keys = parse_multiline_keys(raw_keys_str)
    if not keys:
        return []
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

BN_ORDINALS = {
    "১ম": "প্রথম", "1st": "প্রথম",
    "২য়": "দ্বিতীয়", "২য়": "দ্বিতীয়", "2nd": "দ্বিতীয়",
    "৩য়": "তৃতীয়", "৩য়": "তৃতীয়", "3rd": "তৃতীয়",
    "৪র্থ": "চতুর্থ", "4th": "চতুর্থ",
    "৫ম": "পঞ্চম", "5th": "পঞ্চম",
    "৬ষ্ঠ": "ষষ্ঠ", "6th": "ষষ্ঠ",
    "৭ম": "সপ্তম", "7th": "সপ্তম",
    "৮ম": "অষ্টম", "8th": "অষ্টম",
    "৯ম": "নবম", "9th": "নবম",
    "১০ম": "দশম", "10th": "দশম",
}


def en_bn_to_int(s):
    trans = str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789')
    return int(str(s).translate(trans))


def number_to_bangla_words(n):
    if n == 0:
        return 'শূন্য'
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
        if shatok == 1:
            parts.append('একশত')
        else:
            parts.append(BN_NUMS.get(shatok, str(shatok)) + ' শত')
        n %= 100
    if n > 0:
        parts.append(BN_NUMS.get(n, str(n)))
    return ' '.join(parts)


def convert_all_numbers_in_script(text):
    """
    🌟 সংখ্যাকে নিখুঁত বাংলা কথায় রূপান্তর:
    - ১,৪২,৪০০ এর মতো একাধিক কমা-যুক্ত সংখ্যা সঠিকভাবে পড়ে
    - ১ম, ২য়, ৩য়, ৪র্থ, ১১তম ইত্যাদি ক্রমবাচক সংখ্যা সঠিকভাবে পড়ে (একম/চারর্থ বাগ ফিক্স)
    - ৫৮,০১০/- কে ৫৮ হাজার দশ টাকা পড়ে
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFC", str(text))
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'https?://\S+|wa\.me/\S+', '', text)
    text = re.sub(r'[\u200b-\u200f\ufeff\u202a-\u202e\xa0]', ' ', text)

    # টাকার পেছনের /- বা /= বা ৳ চিহ্ন দূর করা
    text = re.sub(r'([0-9০-৯,]+)\s*(?:/=|/-|৳)(?:\s*টাকা)?', r'\1 টাকা', text)
    text = re.sub(r'৳\s*([0-9০-৯,]+)', r'\1 টাকা', text)

    # সব কমা-যুক্ত সংখ্যা একত্র করা (যেমন ১,৪২,৪০০ -> ১৪২৪০০, ২৪,০০০ -> ২৪০০০)
    text = re.sub(r'(?<=[0-9০-৯]),(?=[0-9০-৯])', '', text)

    # হোয়াটসঅ্যাপ নম্বর সুরক্ষিত করা
    text = re.sub(r'(\+?(?:88|৮৮)?[\s\-]*0?1[0-9০-৯][\s\-0-9০-৯]{7,11})', ' আমাদের হোয়াটসঅ্যাপ নম্বর ', text)

    # শতাংশ ও প্লাস (+) রূপান্তর
    text = re.sub(r'([0-9০-৯]+(?:\.[0-9০-৯]+)?)\s*%', r'\1 শতাংশ', text)
    text = re.sub(r'([0-9০-৯]+)\s*\+', r'\1 প্লাস', text)

    # রেঞ্জ রূপান্তর (ক্রমবাচক এর আগেই করতে হবে, যেমন ১১-২০তম -> ১১ থেকে ২০তম)
    text = re.sub(r'([0-9০-৯]+)\s*[-–—]\s*([0-9০-৯]+)', r'\1 থেকে \2', text)

    # বাংলা ক্রমবাচক সংখ্যা (১ম -> প্রথম, ২য় -> দ্বিতীয়, ৪র্থ -> চতুর্থ ইত্যাদি)
    text = re.sub(
        r'(?<![0-9০-৯])(১ম|২য়|৩য়|৪র্থ|৫ম|৬ষ্ঠ|৭ম|৮ম|৯ম|১০ম)',
        lambda m: BN_ORDINALS.get(m.group(1), m.group(1)),
        text
    )
    text = re.sub(
        r'\b(1st|2nd|3rd|4th|5th|6th|7th|8th|9th|10th)\b',
        lambda m: BN_ORDINALS.get(m.group(1).lower(), m.group(1)),
        text,
        flags=re.I
    )

    # "৬ নং" -> "৬ নম্বর"
    text = re.sub(r'([0-9০-৯]+)\s*নং(?=\s|[।,!?\)]|$)', r'\1 নম্বর', text)

    # "১১তম" / "২০তম" -> "এগারোতম" / "বিশতম"
    def tomo_repl(m):
        try:
            val = en_bn_to_int(m.group(1))
            return f"{number_to_bangla_words(val)}তম"
        except Exception:
            return m.group(0)

    text = re.sub(r'([0-9০-৯]+)\s*তম', tomo_repl, text)

    # দশমিক সংখ্যা (যেমন ৩.৫০ -> তিন দশমিক পাঁচ শূন্য)
    def dec_repl(m):
        try:
            left = number_to_bangla_words(en_bn_to_int(m.group(1)))
            right = ' '.join(BN_NUMS.get(en_bn_to_int(ch), ch) for ch in m.group(2))
            return f"{left} দশমিক {right}"
        except Exception:
            return m.group(0)

    text = re.sub(r'([0-9০-৯]+)\.([0-9০-৯]+)', dec_repl, text)

    # পূর্ণসংখ্যাকে বাংলায় পড়া
    def num_repl(m):
        num_str = m.group(0)
        if len(num_str) > 9:
            return ""
        try:
            val = en_bn_to_int(num_str)
            return number_to_bangla_words(val)
        except Exception:
            return num_str

    text = re.sub(r'[0-9০-৯]+', num_repl, text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def sanitize_youtube_tags(raw_tags, max_total_chars=400):
    clean_tags = []
    current_length = 0
    for tag in raw_tags:
        if not tag or not isinstance(tag, str):
            continue
        cleaned = re.sub(r'[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\<\>\"\,\n\r]', '', tag)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        if not cleaned or len(cleaned) < 2:
            continue
        cleaned = cleaned[:50].strip()
        if cleaned not in clean_tags:
            tag_len = len(cleaned) + (1 if clean_tags else 0)
            if current_length + tag_len <= max_total_chars:
                clean_tags.append(cleaned)
                current_length += tag_len
            else:
                break
    return clean_tags


def clean_title_for_display(title):
    clean = title.split('|')[0].split('||')[0].strip()
    return re.sub(r'\s+', ' ', re.sub(r'[\r\n\t]+', ' ', clean))


def strip_unwanted_chars(text):
    s = unicodedata.normalize("NFC", str(text))
    s = re.sub(r'\s*৳', ' টাকা', s)
    cleaned = re.sub(r'[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|✪|★|☆|[\u200b-\u200f\ufeff\u202a-\u202e\xa0]', '', s)
    return re.sub(r'\s+', ' ', cleaned).strip()


def parse_json_safely(raw_text):
    if not raw_text:
        return None
    cleaned = re.sub(r'<think>.*?</think>', '', str(raw_text), flags=re.DOTALL).strip()
    cleaned = re.sub(r'```(?:json)?', '', cleaned, flags=re.I).replace('```', '').strip()

    for candidate in (cleaned,):
        try:
            return json.loads(candidate)
        except Exception:
            pass

    start_idx = cleaned.find('{')
    if start_idx != -1:
        depth = 0
        in_str = False
        esc = False
        end_idx = -1
        for i, ch in enumerate(cleaned[start_idx:], start=start_idx):
            if esc:
                esc = False
                continue
            if ch == '\\' and in_str:
                esc = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if not in_str:
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        end_idx = i
                        break
        sub = cleaned[start_idx:end_idx + 1] if end_idx != -1 else cleaned[start_idx:]
        for attempt in (sub, re.sub(r',\s*([}\]])', r'\1', sub)):
            try:
                return json.loads(attempt)
            except Exception:
                pass

    try:
        json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if json_match:
            fixed = re.sub(r',\s*([}\]])', r'\1', json_match.group(0))
            return json.loads(fixed)
    except Exception:
        pass
    return None


def _clean_text_response(raw_text):
    if not raw_text or not isinstance(raw_text, str):
        return ""
    cleaned = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL)
    cleaned = re.sub(r'```[\w]*', '', cleaned).replace('```', '')
    return cleaned.strip()


def _encode_images_base64(img_paths, max_images=3):
    b64_list = []
    if not img_paths:
        return b64_list
    for p in img_paths[:max_images]:
        if not p or not os.path.exists(p):
            continue
        try:
            with Image.open(p) as im:
                rgb = im.convert("RGB")
                if rgb.width > 2048:
                    new_h = int((2048 / rgb.width) * rgb.height)
                    rgb = rgb.resize((2048, new_h), Image.LANCZOS)
                buf = io.BytesIO()
                rgb.save(buf, format="JPEG", quality=92)
                b64_list.append(base64.b64encode(buf.getvalue()).decode("ascii"))
        except Exception:
            pass
    return b64_list


# =========================================================================
# 🌟 কেন্দ্রীয় এআই এক্সিকিউশন গেটওয়ে
# =========================================================================

def _call_openrouter(prompt, json_mode=True, b64_images=None, text_fallback=True):
    raw_openrouter = os.environ.get("OPENROUTER_API_KEYS", os.environ.get("OPENROUTER_API_KEY", "")).strip()
    or_order = get_keys_in_cyclic_order("openrouter", raw_openrouter)
    total_or = len(parse_multiline_keys(raw_openrouter))
    if not or_order:
        return None

    for actual_idx, or_key in or_order:
        headers = {
            "Authorization": f"Bearer {or_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com",
            "X-Title": "YouTube Automation",
        }

        if b64_images:
            vision_content = [{"type": "text", "text": prompt}]
            for b64 in b64_images:
                vision_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

            for v_model in OPENROUTER_VISION_MODELS:
                payload = {
                    "model": v_model,
                    "messages": [{"role": "user", "content": vision_content}],
                    "temperature": 0.25,
                    "max_tokens": 4500,
                }
                try:
                    resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=65)
                    if resp.status_code == 200:
                        content_txt = resp.json()['choices'][0]['message']['content']
                        save_tracker_index("openrouter", actual_idx, total_or)
                        res = parse_json_safely(content_txt) if json_mode else _clean_text_response(content_txt)
                        if res:
                            print(f"  ✨ [OpenRouter Vision] Success with Key #{actual_idx+1} ({v_model})")
                            return res
                    elif resp.status_code in [401, 402]:
                        break
                except Exception:
                    pass

        if text_fallback:
            for model_name in OPENROUTER_TEXT_MODELS:
                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.35 if json_mode else 0.4,
                    "max_tokens": 4500,
                }
                try:
                    resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=65)
                    if resp.status_code == 200:
                        content_txt = resp.json()['choices'][0]['message']['content']
                        save_tracker_index("openrouter", actual_idx, total_or)
                        res = parse_json_safely(content_txt) if json_mode else _clean_text_response(content_txt)
                        if res:
                            print(f"  ✨ [OpenRouter] Success with Key #{actual_idx+1} ({model_name})")
                            return res
                    elif resp.status_code in [401, 402]:
                        break
                except Exception:
                    pass
        save_tracker_index("openrouter", actual_idx + 1, total_or)
    return None


def _call_ollama_cloud(prompt, json_mode=True, b64_images=None, text_fallback=True):
    raw_ollama = os.environ.get("OLLAMA_API_KEYS", os.environ.get("Ollama_API_Key", os.environ.get("OLLAMA_API_KEY", ""))).strip()
    ollama_order = get_keys_in_cyclic_order("ollama", raw_ollama)
    total_ollama = len(parse_multiline_keys(raw_ollama))
    if not ollama_order:
        return None

    for actual_idx, o_key in ollama_order:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {o_key}"}
        consecutive_402 = 0

        if b64_images:
            for v_model in OLLAMA_VISION_MODELS:
                payload = {
                    "model": v_model,
                    "messages": [{"role": "user", "content": prompt, "images": b64_images}],
                    "stream": False,
                    "options": {"temperature": 0.25, "num_predict": 4500},
                }
                try:
                    resp = requests.post(OLLAMA_CHAT_URL, headers=headers, json=payload, timeout=65)
                    if resp.status_code == 200:
                        content_txt = resp.json().get("message", {}).get("content", "").strip()
                        save_tracker_index("ollama", actual_idx, total_ollama)
                        res = parse_json_safely(content_txt) if json_mode else _clean_text_response(content_txt)
                        if res:
                            print(f"  ✨ [Ollama Vision] Success with Key #{actual_idx+1} ({v_model})")
                            return res
                    elif resp.status_code in [401, 402]:
                        consecutive_402 += 1
                        if consecutive_402 >= 2:
                            break
                except Exception:
                    pass

        if text_fallback:
            for model_name in OLLAMA_TEXT_MODELS:
                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"temperature": 0.35 if json_mode else 0.4, "num_predict": 4500},
                }
                try:
                    resp = requests.post(OLLAMA_CHAT_URL, headers=headers, json=payload, timeout=65)
                    if resp.status_code == 200:
                        content_txt = resp.json().get("message", {}).get("content", "").strip()
                        save_tracker_index("ollama", actual_idx, total_ollama)
                        res = parse_json_safely(content_txt) if json_mode else _clean_text_response(content_txt)
                        if res:
                            print(f"  ✨ [Ollama Cloud] Success with Key #{actual_idx+1} ({model_name})")
                            return res
                    elif resp.status_code in [401, 402]:
                        consecutive_402 += 1
                        if consecutive_402 >= 2:
                            break
                except Exception:
                    pass
        save_tracker_index("ollama", actual_idx + 1, total_ollama)
    return None


def _call_groq(prompt, json_mode=True):
    raw_groq = os.environ.get("GROQ_API_KEYS", os.environ.get("GROQ_API", "")).strip()
    groq_order = get_keys_in_cyclic_order("groq", raw_groq)
    total_groq = len(parse_multiline_keys(raw_groq))
    if not groq_order:
        return None

    for actual_idx, g_key in groq_order:
        headers = {"Authorization": f"Bearer {g_key}", "Content-Type": "application/json"}
        for g_model in GROQ_MODELS:
            sys_msg = "You are a Bengali job circular specialist. Return strictly valid JSON." if json_mode else "You are a professional Bengali YouTube presenter."
            payload = {
                "model": g_model,
                "messages": [{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}],
                "temperature": 0.35 if json_mode else 0.4,
                "max_tokens": 4500,
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}
            try:
                resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=55)
                if resp.status_code == 200:
                    content_txt = resp.json()['choices'][0]['message']['content']
                    save_tracker_index("groq", actual_idx, total_groq)
                    res = parse_json_safely(content_txt) if json_mode else _clean_text_response(content_txt)
                    if res:
                        print(f"  ✨ [Groq] Success with Key #{actual_idx+1} ({g_model})")
                        return res
                elif "restricted" in resp.text.lower() or resp.status_code in [401, 403]:
                    break
            except Exception:
                pass
        save_tracker_index("groq", actual_idx + 1, total_groq)
    return None


def _call_cerebras(prompt, json_mode=True):
    raw_cerebras = os.environ.get("CEREBRAS_API_KEYS", os.environ.get("CEREBRAS_API_KEY", "")).strip()
    cerebras_order = get_keys_in_cyclic_order("cerebras", raw_cerebras)
    total_cerebras = len(parse_multiline_keys(raw_cerebras))
    if not cerebras_order:
        return None

    for actual_idx, c_key in cerebras_order:
        headers = {"Authorization": f"Bearer {c_key}", "Content-Type": "application/json"}
        for c_model in CEREBRAS_MODELS:
            payload = {
                "model": c_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.35 if json_mode else 0.4,
                "max_tokens": 4500,
            }
            try:
                resp = requests.post("https://api.cerebras.ai/v1/chat/completions", headers=headers, json=payload, timeout=50)
                if resp.status_code == 200:
                    content_txt = resp.json()['choices'][0]['message']['content']
                    save_tracker_index("cerebras", actual_idx, total_cerebras)
                    res = parse_json_safely(content_txt) if json_mode else _clean_text_response(content_txt)
                    if res:
                        print(f"  ✨ [Cerebras] Success with Key #{actual_idx+1} ({c_model})")
                        return res
            except Exception:
                pass
        save_tracker_index("cerebras", actual_idx + 1, total_cerebras)
    return None


def _call_gemini(prompt, json_mode=True, b64_images=None):
    raw_gemini = os.environ.get("GEMINI_API_KEYS", os.environ.get("GEMINI_API_KEY", "")).strip()
    gemini_order = get_keys_in_cyclic_order("gemini_text", raw_gemini)
    total_gemini = len(parse_multiline_keys(raw_gemini))
    if not gemini_order:
        return None

    parts = [{"text": prompt}]
    if b64_images:
        for b64 in b64_images:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})

    for actual_idx, g_key in gemini_order:
        for g_model in GEMINI_TEXT_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{g_model}:generateContent?key={g_key}"
            gen_cfg = {"temperature": 0.25 if b64_images else 0.35, "maxOutputTokens": 4500}
            if json_mode:
                gen_cfg["responseMimeType"] = "application/json"
            body = {
                "contents": [{"parts": parts}],
                "generationConfig": gen_cfg,
            }
            try:
                resp = requests.post(url, headers={"Content-Type": "application/json"}, json=body, timeout=60)
                if resp.status_code == 200:
                    text_res = resp.json()['candidates'][0]['content']['parts'][0]['text']
                    save_tracker_index("gemini_text", actual_idx, total_gemini)
                    res = parse_json_safely(text_res) if json_mode else _clean_text_response(text_res)
                    if res:
                        tag = "Vision" if len(parts) > 1 else "AI"
                        print(f"  ✨ [Gemini {tag}] Success with Key #{actual_idx+1} ({g_model})")
                        return res
            except Exception:
                pass
        save_tracker_index("gemini_text", actual_idx + 1, total_gemini)
    return None


def execute_ai_query(prompt, json_mode=True, img_paths=None):
    b64_images = _encode_images_base64(img_paths, max_images=3) if img_paths else None

    if b64_images:
        for fn in (
            lambda: _call_openrouter(prompt, json_mode=json_mode, b64_images=b64_images, text_fallback=False),
            lambda: _call_ollama_cloud(prompt, json_mode=json_mode, b64_images=b64_images, text_fallback=False),
            lambda: _call_gemini(prompt, json_mode=json_mode, b64_images=b64_images),
        ):
            res = fn()
            if res:
                return res

    for fn in (
        lambda: _call_openrouter(prompt, json_mode=json_mode, b64_images=None, text_fallback=True),
        lambda: _call_ollama_cloud(prompt, json_mode=json_mode, b64_images=None, text_fallback=True),
        lambda: _call_groq(prompt, json_mode=json_mode),
        lambda: _call_cerebras(prompt, json_mode=json_mode),
        lambda: _call_gemini(prompt, json_mode=json_mode, b64_images=None),
    ):
        res = fn()
        if res:
            return res

    return None


# =========================================================================
# 🌟 ডেটা ক্লিনআপ ও ডিটারমিনিস্টিক রিকভারি হেল্পার
# =========================================================================

def _clean_org_name(raw_org, fallback_title=""):
    s = strip_unwanted_chars(raw_org or fallback_title or "নিয়োগ বিজ্ঞপ্তি")
    s = re.sub(r'^[০-৯0-9]+\s*(?:টি|জন)?\s*পদে\s*', '', s)
    s = re.sub(r'\s*(?:নিয়োগ|নিয়োগ)\s*(?:বিজ্ঞপ্তি|সার্কুলার).*$', '', s)
    s = re.sub(r'\s*২০২[৩-৯]\s*$', '', s)
    s = re.sub(r'\s*[-–|,:]+\s*$', '', s).strip()
    return s or strip_unwanted_chars(fallback_title[:40])


def _clean_concise_field(val, max_len=48, drop_long_parens=True):
    s = strip_unwanted_chars(val or "")
    if drop_long_parens and len(s) > max_len:
        s = re.sub(r'\s*\([^)]{16,}\)', '', s).strip()
    if len(s) > max_len:
        s = re.split(r'\s+-\s+', s)[0].strip()
    return s


def _enrich_verified_data_from_text(vd, title, article_text):
    if not isinstance(vd, dict):
        vd = {}
    combined_text = f"{title}\n{article_text or ''}"

    vd["org_short"] = _clean_org_name(vd.get("org_short") or vd.get("organization"), title)
    if not vd.get("organization"):
        vd["organization"] = vd["org_short"]

    # শূন্যপদ রিকভারি
    tv = strip_unwanted_chars(vd.get("total_vacancies") or "")
    if not tv or tv in ("বিভিন্ন পদ", "নির্ধারিত", "বিজ্ঞপ্তি অনুযায়ী"):
        m_vac = re.search(r'(?:মোট|সর্বমোট)?\s*([০-৯0-9]+\s*(?:টি|জন))(?:\s*(?:শূন্য)?পদে|\s*লোক|\s*প্রার্থী)', combined_text)
        if not m_vac:
            m_vac = re.search(r'([০-৯0-9]+\s*(?:টি|জন)?)\s*পদে', title)
        if m_vac:
            tv = m_vac.group(1).strip()
    vd["total_vacancies"] = _clean_concise_field(tv, max_len=24)

    # আবেদনের শেষ সময় রিকভারি
    dl = strip_unwanted_chars(vd.get("deadline") or "")
    generic_dls = {"", "নির্ধারিত সময়সীমা", "নির্ধারিত সময়", "বিজ্ঞপ্তি অনুযায়ী", "চলমান"}
    if dl in generic_dls:
        m_dl = re.search(
            r'আবেদনের\s*শেষ\s*(?:তারিখ|সময়(?:সীমা)?)\s*(?:হলো|হচ্ছে|:|ঃ|-)?\s*([^\n।]{5,55})',
            combined_text
        )
        if not m_dl:
            m_dl = re.search(
                r'([০-৯0-9]{1,2}\s+(?:জানুয়ারি|ফেব্রুয়ারি|মার্চ|এপ্রিল|মে|জুন|জুলাই|আগস্ট|সেপ্টেম্বর|অক্টোবর|নভেম্বর|ডিসেম্বর)[,\s]*[০-৯0-9]{4}(?:\s*(?:বিকাল|রাত|সকাল)?\s*[০-৯0-9:]{1,5}\s*টা)?)',
                combined_text
            )
        if m_dl:
            dl = strip_unwanted_chars(m_dl.group(1))
    vd["deadline"] = _clean_concise_field(dl or "নির্ধারিত সময়সীমা", max_len=42)

    # প্রতিটি পদের ফিল্ড কনসাইজ ও পরিষ্কার রাখা যাতে ভিজুয়ালে ওভারফ্লো না হয়
    cleaned_posts = []
    for p in (vd.get("posts") or [])[:16]:
        if not isinstance(p, dict):
            continue
        p_copy = dict(p)
        p_copy["post_name"] = _clean_concise_field(p.get("post_name") or "বিভিন্ন পদে নিয়োগ", max_len=64)
        p_copy["vacancy_count"] = _clean_concise_field(p.get("vacancy_count") or vd["total_vacancies"] or "নির্ধারিত", max_len=18)
        p_copy["application_fee"] = _clean_concise_field(p.get("application_fee") or vd.get("application_fee_summary") or "বিজ্ঞপ্তি অনুযায়ী", max_len=42)
        p_copy["salary_scale"] = _clean_concise_field(p.get("salary_scale") or "নির্ধারিত স্কেল", max_len=64, drop_long_parens=False)
        p_copy["educational_qualification"] = strip_unwanted_chars(p.get("educational_qualification") or vd.get("eligibility_summary") or "বিজ্ঞপ্তি অনুযায়ী")
        p_copy["key_duties"] = strip_unwanted_chars(p.get("key_duties") or "সংশ্লিষ্ট প্রাতিষ্ঠানিক ও দাপ্তরিক দায়িত্ব পালন")
        cleaned_posts.append(p_copy)

    if cleaned_posts:
        vd["posts"] = cleaned_posts

    return vd


# =========================================================================
# 🌟 ফেইল-সেফ সেগমেন্টেড স্ক্রিপ্ট বিল্ডার
# =========================================================================

def _build_single_post_paragraph(idx, p):
    p_name = p.get("post_name", f"{idx} নম্বর পদ")
    p_vac = p.get("vacancy_count", "নির্ধারিত সংখ্যক")
    p_qual = p.get("educational_qualification", "বিজ্ঞপ্তি অনুযায়ী শিক্ষাগত যোগ্যতা")
    p_sal = p.get("salary_scale", "নির্ধারিত বেতন স্কেল")
    p_fee = p.get("application_fee", "বিজ্ঞপ্তিতে উল্লেখ নেই")
    p_duties = p.get("key_duties", "প্রতিষ্ঠানের সংশ্লিষ্ট দাপ্তরিক ও প্রাতিষ্ঠানিক দায়িত্ব পালন করা")

    fee_sentence = (
        "এই পদে আবেদন করতে কোনো আবেদন ফি লাগবে না।"
        if any(w in p_fee for w in ["নেই", "ফ্রি", "বিনামূল্যে", "লাগবে না"])
        else f"এই পদে আবেদন করতে আবেদন ফি লাগবে {p_fee}।"
    )

    return (
        f"{idx} নম্বর যে পদটি রয়েছে, সেটি হলো {p_name}। "
        f"এই পদে {p_vac} জনবল নেওয়া হবে। "
        f"পদটির জন্য বেতন স্কেল নির্ধারণ করা হয়েছে {p_sal}। "
        f"এই পদে চাকরি পেলে মূলত {p_duties}। "
        f"আবেদনের জন্য শিক্ষাগত যোগ্যতা ও অভিজ্ঞতা হিসেবে থাকতে হবে {p_qual} এবং {fee_sentence}"
    )


def build_segmented_script_from_verified_data(verified_data, title, article_text=""):
    org = verified_data.get("organization") or verified_data.get("org_short") or title
    total_vac = verified_data.get("total_vacancies", "")
    deadline = verified_data.get("deadline", "")
    district = verified_data.get("district_eligibility", "বাংলাদেশের সকল জেলা")
    age_limit = verified_data.get("age_limit", "১৮ থেকে ৩২ বছর")
    fee_sum = verified_data.get("application_fee_summary", "বিজ্ঞপ্তি অনুযায়ী")
    posts = verified_data.get("posts") or []

    vac_line = f"মোট {total_vac} শূন্যপদে" if total_vac else "বিভিন্ন পদে যোগ্য জনবল"
    dl_line = f"আবেদনের শেষ সময় নির্ধারিত হয়েছে {deadline}।" if deadline and deadline != "নির্ধারিত সময়সীমা" else ""

    segments = []
    segments.append({
        "id": "intro",
        "text": (
            f"আসসালামু আলাইকুম প্রিয় চাকরিপ্রার্থী ভাই ও বোনেরা। আজকের ভিডিওতে আপনাদের সবাইকে স্বাগতম। "
            f"সম্প্রতি {org} থেকে একটি গুরুত্বপূর্ণ নিয়োগ বিজ্ঞপ্তি প্রকাশিত হয়েছে, যেখানে {vac_line} নিয়োগ দেওয়া হবে।"
        )
    })

    segments.append({
        "id": "org_overview",
        "text": (
            f"{org} দেশের নিজস্ব কর্মক্ষেত্রে অত্যন্ত সুনাম ও মর্যাদার সাথে কাজ করে যাচ্ছে। "
            f"এই বিজ্ঞপ্তিতে {district} থেকে যোগ্য প্রার্থীরা আবেদন করতে পারবেন এবং আবেদন ফি নির্ধারিত হয়েছে {fee_sum}। "
            f"{dl_line} এখন চলুন বিজ্ঞপ্তিতে থাকা প্রতিটি পদের বিস্তারিত তথ্য জেনে নেওয়া যাক।"
        )
    })

    if len(posts) == 1:
        p = posts[0]
        p_name = p.get("post_name", "নিয়োগকৃত পদ")
        p_vac = p.get("vacancy_count", total_vac or "নির্ধারিত সংখ্যক")
        p_sal = p.get("salary_scale", "নির্ধারিত বেতন স্কেল")
        p_duties = p.get("key_duties", "প্রতিষ্ঠানের সংশ্লিষ্ট দাপ্তরিক দায়িত্ব পালন করা")
        p_qual = p.get("educational_qualification", "বিজ্ঞপ্তি অনুযায়ী শিক্ষাগত যোগ্যতা")
        p_fee = p.get("application_fee", fee_sum)
        fee_sentence = (
            "এই পদে আবেদন করতে কোনো আবেদন ফি লাগবে না।"
            if any(w in p_fee for w in ["নেই", "ফ্রি", "বিনামূল্যে", "লাগবে না"])
            else f"এই পদে আবেদন ফি নির্ধারিত হয়েছে {p_fee}।"
        )

        segments.append({
            "id": "post_0_part1",
            "text": (
                f"এই বিজ্ঞপ্তির আলোচ্য পদ হলো {p_name}। "
                f"এখানে মোট {p_vac} জনবল নিয়োগ দেওয়া হবে। "
                f"পদটির বেতন স্কেল নির্ধারণ করা হয়েছে {p_sal}। "
                f"এখানে দায়িত্ব হিসেবে মূলত {p_duties}।"
            )
        })
        segments.append({
            "id": "post_0_part2",
            "text": (
                f"এই পদে আবেদনের জন্য শিক্ষাগত যোগ্যতা ও অভিজ্ঞতা হিসেবে প্রয়োজন হবে {p_qual}। "
                f"{fee_sentence}"
            )
        })
    else:
        for idx, p in enumerate(posts[:16], 1):
            segments.append({
                "id": f"post_{idx - 1}",
                "text": _build_single_post_paragraph(idx, p)
            })

    segments.append({
        "id": "conditions",
        "text": (
            f"সাধারণ শর্তাবলী হিসেবে আবেদনকারীর বয়সসীমা নির্ধারিত হয়েছে {age_limit}। "
            f"{district} থেকে যোগ্য নারী ও পুরুষ প্রার্থীরা আবেদন করতে পারবেন এবং "
            f"নিয়োগপ্রাপ্তরা নির্ধারিত স্কেল অনুযায়ী বেতন, ভাতা ও অন্যান্য প্রাতিষ্ঠানিক সুযোগ-সুবিধা পাবেন।"
        )
    })

    segments.append({
        "id": "deadline",
        "text": (
            f"মনে রাখবেন আবেদনের শেষ সময়সীমা {deadline or 'নির্ধারিত তারিখের মধ্যে'}। "
            f"তাই শেষ দিনের ভিড় ও সার্ভার জটিলতা এড়াতে সময়মতো আপনার আবেদন সম্পন্ন করুন।"
        )
    })

    segments.append({
        "id": "whatsapp_cta",
        "text": STANDARD_WHATSAPP_CTA
    })

    cleaned_segments = []
    for seg in segments:
        spoken = clean_script_for_speech(convert_all_numbers_in_script(seg["text"]))
        cleaned_segments.append({"id": seg["id"], "text": spoken})
    return cleaned_segments


def build_script_from_verified_data(verified_data, title, article_text):
    segs = build_segmented_script_from_verified_data(verified_data, title, article_text)
    return "\n\n".join(s["text"] for s in segs)


# =========================================================================
# 🌟 ৪টি পৃথক মডুলার কল (সার্কুলার ছবি ও টেবিল থেকে ১০০% নির্ভুল ডেটা)
# =========================================================================

def extract_verified_job_data(title, article_text, img_paths=None):
    print("\n🔍 [STEP 1] Extracting accurate category, ALL posts, qualifications & fees (Image-First Truth)...")
    prompt = f"""Analyze BOTH the attached official job circular image(s) (if present) AND the cleaned article text below.
Extract EVERY SINGLE separate post and 100% factual data strictly in JSON.

CRITICAL GROUND TRUTH RULES (MUST OBEY):
1. THE OFFICIAL CIRCULAR IMAGE IS THE SUPREME TRUTH!
   Whenever blog text conflicts with circular image(s), ALWAYS copy EXACT numbers printed on the image(s) (salary, grade, vacancy, application fee, deadline).
2. DO NOT MERGE POSTS! If the circular or article lists multiple separate posts, extract EVERY SINGLE post separately into the "posts" array.
3. KEEP DISPLAY FIELDS SHORT & CLEAN:
   - "org_short": ONLY the clean organization name in 2-5 words (e.g. 'কর অঞ্চল-১৫, ঢাকা', 'বাংলাদেশ অভ্যন্তরীণ নৌপরিবহন কর্পোরেশন'). NEVER include vacancy numbers like '৪২ পদে' or 'নিয়োগ বিজ্ঞপ্তি' inside org_short!
   - "vacancy_count": Short count ONLY (e.g. '০১টি', '১৬টি', '৫৪ জন'). NO long parenthetical notes!
   - "post_name": Clean post name and grade ONLY (e.g. 'উপ-নৌ অধীক্ষক (গ্রেড-৪)'). NO long explanations in parentheses!
   - "application_fee": Concise fee ONLY (e.g. '১১২ টাকা', '১১২ ও ৫৬ টাকা', 'বিনামূল্যে', 'পূর্ণাঙ্গ বিজ্ঞপ্তিতে প্রকাশিত হবে').
   - "deadline": Exact last date & time from image/text in Bengali (e.g. '১৪ ডিসেম্বর ২০২৬, বিকাল ০৫:০০ টা').
---
TITLE: {title}
CLEANED ARTICLE TEXT:
{article_text[:11500]}
---

Return strictly valid JSON:
{{
  "organization": "Full Bengali organization/company/ministry name",
  "org_short": "Clean 2-5 word organization name without vacancy count",
  "job_category": "সরকারি চাকরি" | "স্বায়ত্তশাসিত প্রতিষ্ঠান" | "বেসরকারি চাকরি" | "ব্যাংক চাকরি",
  "total_vacancies": "e.g. ১০টি or ৪২টি or ৩৩টি",
  "eligibility_summary": "Short 2-4 word range e.g. ৮ম থেকে স্নাতক পাশ",
  "application_fee_summary": "e.g. ৫৬ থেকে ১১২ টাকা or আবেদন ফি নেই",
  "deadline": "Exact last date in Bengali",
  "age_limit": "e.g. ১৮ থেকে ৩০ বছর or ১৮ থেকে ৩২ বছর",
  "district_eligibility": "e.g. ৬৪ জেলা or নির্দিষ্ট জেলা",
  "posts": [
    {{
      "post_name": "Exact post name and grade",
      "vacancy_count": "Short exact count (e.g. ০১টি, ০২ জন)",
      "educational_qualification": "Exact qualification requirement for THIS post",
      "salary_scale": "Exact salary scale printed on official circular (e.g. ৮,২৫০-২০,০১০ টাকা)",
      "application_fee": "Exact concise fee for THIS post (e.g. ১১২ টাকা, ৫৬ টাকা, বিনামূল্যে)",
      "key_duties": "Brief 1-sentence realistic description of this post's responsibilities"
    }}
  ]
}}"""
    res = execute_ai_query(prompt, json_mode=True, img_paths=img_paths)
    if not res or not isinstance(res, dict) or not res.get("posts"):
        print("  🔄 Retrying Step 1 JSON extraction...")
        res = execute_ai_query(prompt, json_mode=True, img_paths=img_paths)
    if res and isinstance(res, dict):
        res = _enrich_verified_data_from_text(res, title, article_text)
    return res


def generate_segmented_script_from_verified_data(verified_data, title, article_text):
    """
    🌟 অডিও-ভিজুয়াল ১০০% সিঙ্ক নিশ্চিত করার জন্য প্রতিটি দৃশ্য অনুযায়ী আলাদা JSON সেগমেন্টে স্ক্রিপ্ট জেনারেট করে।
    """
    print("🎙️ [STEP 2] Generating scene-locked segmented Bengali voiceover script...")
    posts = (verified_data.get("posts") or [])[:16]
    data_str = json.dumps(verified_data, ensure_ascii=False, indent=2)

    if len(posts) == 1:
        expected_post_count = 2
        post_mapping_guide = (
            'Because there is 1 post entry, "post_scripts" MUST have EXACTLY 2 strings:\n'
            '  - post_scripts[0]: Discuss ONLY the post name/grade, vacancy count, salary scale, and key job duties (DO NOT mention qualification or fee here).\n'
            '  - post_scripts[1]: Discuss ONLY the educational qualification, experience, and application fee for this post.'
        )
    else:
        expected_post_count = len(posts)
        lines = [
            f'  - post_scripts[{i}]: Discuss ONLY Post #{i+1} ("{p.get("post_name", "")}"). '
            f'Speak in this exact order: (a) post name, grade & vacancy count, (b) salary scale, (c) job duties, (d) educational qualification & experience, (e) application fee. Do NOT talk about any other post in this item!'
            for i, p in enumerate(posts)
        ]
        post_mapping_guide = f'"post_scripts" MUST be a JSON array of EXACTLY {expected_post_count} strings matching posts 0..{expected_post_count - 1}:\n' + "\n".join(lines)

    prompt = f"""You are an expert Bangladeshi job circular YouTube presenter.
Write a crisp, natural, 100% factual spoken Bengali voiceover script divided into EXACT scene-aligned JSON fields so each spoken segment syncs 1-to-1 with its on-screen motion graphics scene.

Title: "{title}"
Verified Structured Job Data (SUPREME GROUND TRUTH — never contradict its facts or post count!):
{data_str}

Supporting Reference Text (for extra duties/allowances/dates context ONLY; never invent extra posts):
{article_text[:6500]}

STRICT JSON OUTPUT STRUCTURE:
1. "intro": Start with "আসসালামু আলাইকুম প্রিয় চাকরিপ্রার্থী ভাই ও বোনেরা।". Briefly welcome viewers, state the organization name, category, and total vacancies in 2-3 crisp sentences (~10 seconds).
2. "org_overview": Briefly explain what the organization/ministry does and its career value, eligible districts, application fee overview, and deadline summary in 3 sentences (~15 seconds). End with a short transition like "এখন চলুন প্রতিটি পদের বিস্তারিত তথ্য জেনে নেওয়া যাক।".
3. "post_scripts":
{post_mapping_guide}
4. "conditions": Discuss general conditions ONLY — age limit & calculation date, quota/district eligibility, and salary allowances/benefits (2-3 sentences). Do NOT mention deadline warning or WhatsApp CTA here.
5. "deadline": Clearly remind viewers of the application start & end date/time ({verified_data.get("deadline", "")}) and advise applying on time (2 short sentences).
6. "whatsapp_cta": Exact closing CTA telling interested candidates to message our WhatsApp number shown on screen or in description so our team completes their application properly, plus subscribe call.

NEGATIVE CONSTRAINTS:
- NEVER include application procedures (no postal/courier/email steps, no URLs, no pixel sizes).
- NEVER write phone number digits anywhere in any script text.
- Write pure spoken Bengali (no bullet points, no markdown, no brackets).

Return strictly valid JSON:
{{
  "intro": "...",
  "org_overview": "...",
  "post_scripts": ["..."],
  "conditions": "...",
  "deadline": "...",
  "whatsapp_cta": "..."
}}"""

    fallback_segments = build_segmented_script_from_verified_data(verified_data, title, article_text)
    fb_map = {s["id"]: s["text"] for s in fallback_segments}

    raw_res = execute_ai_query(prompt, json_mode=True)
    if not raw_res or not isinstance(raw_res, dict):
        print("⚠️ Segmented script JSON failed; using structured fallback segments.")
        return fallback_segments

    def _clean_seg(txt, fb_id):
        cleaned = clean_script_for_speech(convert_all_numbers_in_script(txt or ""))
        if len(cleaned) < 20:
            return fb_map.get(fb_id, "")
        return cleaned

    segments = [
        {"id": "intro", "text": _clean_seg(raw_res.get("intro"), "intro")},
        {"id": "org_overview", "text": _clean_seg(raw_res.get("org_overview"), "org_overview")},
    ]

    raw_posts = raw_res.get("post_scripts")
    if not isinstance(raw_posts, list):
        raw_posts = []

    if len(posts) == 1:
        if len(raw_posts) >= 2:
            segments.append({"id": "post_0_part1", "text": _clean_seg(raw_posts[0], "post_0_part1")})
            segments.append({"id": "post_0_part2", "text": _clean_seg(raw_posts[1], "post_0_part2")})
        else:
            segments.append({"id": "post_0_part1", "text": fb_map["post_0_part1"]})
            segments.append({"id": "post_0_part2", "text": fb_map["post_0_part2"]})
    else:
        # যদি AI সবগুলো পদকে ১-২টি স্ট্রিংয়ে মার্জ করে ফেলে, তাহলে ডুপ্লিকেট এড়াতে সম্পূর্ণ ফলব্যাক ব্যবহার
        if len(posts) >= 3 and len(raw_posts) < len(posts) - 1:
            print(f"⚠️ AI returned {len(raw_posts)} post segments for {len(posts)} posts; using exact 1-to-1 fallback posts.")
            for i in range(len(posts)):
                segments.append({"id": f"post_{i}", "text": fb_map[f"post_{i}"]})
        else:
            for i in range(len(posts)):
                txt = raw_posts[i] if i < len(raw_posts) else ""
                segments.append({"id": f"post_{i}", "text": _clean_seg(txt, f"post_{i}")})

    segments.append({"id": "conditions", "text": _clean_seg(raw_res.get("conditions"), "conditions")})
    segments.append({"id": "deadline", "text": _clean_seg(raw_res.get("deadline"), "deadline")})

    cta_clean = clean_script_for_speech(convert_all_numbers_in_script(raw_res.get("whatsapp_cta") or ""))
    if len(cta_clean) < 35 or "হোয়াটসঅ্যাপ" not in cta_clean:
        cta_clean = fb_map["whatsapp_cta"]
    segments.append({"id": "whatsapp_cta", "text": cta_clean})

    return segments


def generate_script_from_verified_data(verified_data, title, article_text):
    segs = generate_segmented_script_from_verified_data(verified_data, title, article_text)
    return "\n\n".join(s["text"] for s in segs if s.get("text"))


def generate_seo_metadata(verified_data, title):
    print("📈 [STEP 3] Generating SEO Title, Description & Tags...")
    posts_summary = ", ".join([p.get("post_name", "") for p in verified_data.get("posts", [])[:5]])
    total_vac = verified_data.get("total_vacancies", "")
    org = verified_data.get("organization", title)
    job_cat = verified_data.get("job_category", "চাকরির খবর")

    prompt = f"""Generate YouTube SEO metadata in JSON for this job circular:
Organization: "{org}"
Category: "{job_cat}"
Title: "{title}"
Key Posts: "{posts_summary}"
Total Vacancies: "{total_vac}"

Return strictly valid JSON:
{{
  "optimized_title": "High-CTR Bengali YouTube Title under 95 chars featuring organization and total vacancies (with 🔥 or 🚨)",
  "video_description": "Helpful Bengali description summarizing all posts, qualifications, fee info, deadline, and WhatsApp contact to apply: wa.me/8801540503092",
  "specific_tags": ["8 to 12 relevant Bengali & English SEO tags without commas"]
}}"""
    return execute_ai_query(prompt, json_mode=True)


def _normalize_thumb_meta(raw_res, verified_data, clean_title, fallback_layout):
    if not raw_res or not isinstance(raw_res, dict):
        raw_res = {}

    layout = str(raw_res.get("layout_style", "")).strip()
    if layout not in LAYOUT_STYLES:
        layout = fallback_layout

    org_short = strip_unwanted_chars(
        raw_res.get("org_short") or verified_data.get("org_short") or verified_data.get("organization") or clean_title[:35]
    )
    job_cat = strip_unwanted_chars(raw_res.get("job_category") or verified_data.get("job_category") or "সরকারি চাকরি")
    top_tag = strip_unwanted_chars(raw_res.get("top_tag") or job_cat)

    total_v = verified_data.get("total_vacancies", "")
    default_hero = f"{total_v} পদে বিশাল নিয়োগ" if total_v else "আকর্ষণীয় নিয়োগ বিজ্ঞপ্তি"
    default_sub = verified_data.get("eligibility_summary") or "যোগ্যতা, বেতন ও বিস্তারিত"

    hero_text = strip_unwanted_chars(raw_res.get("hero_text") or default_hero)
    sub_text = strip_unwanted_chars(raw_res.get("sub_text") or default_sub)
    bot_text = strip_unwanted_chars(raw_res.get("bot_text") or "প্রতিটি পদের যোগ্যতা, বেতন ও ফি")

    raw_hl = raw_res.get("highlights")
    highlights = []
    if isinstance(raw_hl, list):
        for item in raw_hl[:3]:
            if isinstance(item, dict):
                lbl = strip_unwanted_chars(item.get("label", ""))
                val = strip_unwanted_chars(item.get("value", ""))
                if val:
                    highlights.append({"label": lbl or "তথ্য", "value": val})
            elif isinstance(item, str) and item.strip():
                highlights.append({"label": "তথ্য", "value": strip_unwanted_chars(item)})

    if len(highlights) < 3:
        fallback_items = [
            {"label": "আবেদন যোগ্যতা", "value": strip_unwanted_chars(verified_data.get("eligibility_summary") or "বিজ্ঞপ্তি অনুযায়ী")},
            {"label": "আবেদন ফি", "value": strip_unwanted_chars(verified_data.get("application_fee_summary") or "বিজ্ঞপ্তি অনুযায়ী")},
            {"label": "সময়সীমা / জেলা", "value": strip_unwanted_chars(verified_data.get("deadline") or verified_data.get("district_eligibility") or "৬৪ জেলা")},
        ]
        for fb in fallback_items:
            if len(highlights) < 3 and fb["value"]:
                highlights.append(fb)

    return {
        "layout_style": layout,
        "job_category": job_cat,
        "top_tag": top_tag,
        "org_short": org_short,
        "hero_text": hero_text,
        "sub_text": sub_text,
        "highlights": highlights[:3],
        "bot_text": bot_text,
    }


def generate_thumbnail_metadata(verified_data, title):
    print("🎨 [STEP 4] Generating Creative Dynamic Thumbnail Concept...")
    posts = verified_data.get("posts") or [{}]
    posts_brief = ", ".join([
        f"{p.get('post_name', '')} ({p.get('vacancy_count', '')}, বেতন: {p.get('salary_scale', '')})"
        for p in posts[:4]
    ])
    total_vac = verified_data.get("total_vacancies", "")
    org_short = verified_data.get("org_short") or verified_data.get("organization", "নিয়োগ বিজ্ঞপ্তি")
    job_cat = verified_data.get("job_category", "সরকারি চাকরি")
    elig = verified_data.get("eligibility_summary") or posts[0].get("educational_qualification", "স্নাতক/HSC/SSC পাশ")
    fee_sum = verified_data.get("application_fee_summary", "")
    deadline = verified_data.get("deadline", "")
    district = verified_data.get("district_eligibility", "৬৪ জেলা")

    suggested_layout = random.choice(LAYOUT_STYLES)

    prompt = f"""You are a creative YouTube Thumbnail Copywriter for a Bangladeshi job channel.
Do NOT repeat the exact same boring wording every time! Vary the hook angle dynamically based on what is MOST attractive about THIS job!

Job Details:
- Organization: "{org_short}"
- Category: "{job_cat}"
- Total Vacancies: "{total_vac}"
- Key Posts & Salary: "{posts_brief}"
- Eligibility: "{elig}"
- Application Fee: "{fee_sum}"
- Deadline: "{deadline}"
- District: "{district}"

Suggested Layout Style: "{suggested_layout}"
Valid Layout Styles: "poster_classic", "split_impact", "headline_first", "dark_bold", "stat_cards"

CREATIVE RULES:
1. "top_tag": Creative 2-4 word top badge matching Category (NEVER write সরকারি if বেসরকারি!).
2. "org_short": Complete, clean, unmistakable Bengali name of the organization/ministry (3-5 words, NEVER cut mid-word!).
3. "hero_text": Most clickable 2-4 word hook for THIS job (mix angles: salary, low qualification, no fee, or post count).
4. "sub_text": Different complementary 2-4 word hook.
5. "highlights": Exactly 3 DIFFERENT factual label+value cards (write 'টাকা' instead of ৳, NO emojis!).
6. "bot_text": Creative 3-5 word CTA.

Return strictly valid JSON:
{{
  "layout_style": "{suggested_layout}",
  "job_category": "{job_cat}",
  "top_tag": "...",
  "org_short": "...",
  "hero_text": "...",
  "sub_text": "...",
  "highlights": [
    {{"label": "...", "value": "..."}},
    {{"label": "...", "value": "..."}},
    {{"label": "...", "value": "..."}}
  ],
  "bot_text": "..."
}}"""
    raw_res = execute_ai_query(prompt, json_mode=True)
    return _normalize_thumb_meta(raw_res, verified_data, title, suggested_layout)


# =========================================================================
# 🌟 মূল মাস্টার ফাংশন
# =========================================================================

def generate_job_content_with_data(title, article_text, img_paths=None):
    clean_title = clean_title_for_display(title)

    verified_data = extract_verified_job_data(clean_title, article_text, img_paths=img_paths)
    if not verified_data or not isinstance(verified_data, dict) or not verified_data.get("posts"):
        clean_org = _clean_org_name("", clean_title)
        is_priv = any(k in clean_title.lower() for k in ["লিমিটেড", "ফার্মা", "গ্রুপ", "কোম্পানি", "বেসরকারি", "বিকাশ", "ফাউন্ডেশন", "এনজিও", "ltd", "limited"])
        verified_data = _enrich_verified_data_from_text({
            "organization": clean_org,
            "org_short": " ".join(clean_org.split()[:5]),
            "job_category": "বেসরকারি চাকরি" if is_priv else "সরকারি চাকরি",
            "total_vacancies": "",
            "eligibility_summary": "বিজ্ঞপ্তি অনুযায়ী যোগ্যতা",
            "application_fee_summary": "বিজ্ঞপ্তি অনুযায়ী",
            "deadline": "",
            "age_limit": "১৮ থেকে ৩২ বছর",
            "district_eligibility": "সকল জেলা",
            "posts": [{
                "post_name": "বিভিন্ন পদে নিয়োগ",
                "vacancy_count": "নির্ধারিত সংখ্যক",
                "salary_scale": "নির্ধারিত স্কেল",
                "educational_qualification": "বিজ্ঞপ্তি অনুযায়ী",
                "application_fee": "বিজ্ঞপ্তি অনুযায়ী",
                "key_duties": "সংশ্লিষ্ট দাপ্তরিক দায়িত্ব পালন",
            }]
        }, clean_title, article_text)

    script_segments = generate_segmented_script_from_verified_data(verified_data, clean_title, article_text)
    voiceover_script = "\n\n".join(s["text"] for s in script_segments if s.get("text"))

    if not voiceover_script or len(voiceover_script.split()) < 80:
        print(f"⚠️ Generated script was short. Rebuilding structured segmented script...")
        script_segments = build_segmented_script_from_verified_data(verified_data, clean_title, article_text)
        voiceover_script = "\n\n".join(s["text"] for s in script_segments if s.get("text"))

    verified_data["script_segments"] = script_segments

    seo_res = generate_seo_metadata(verified_data, clean_title)
    opt_title = seo_res.get("optimized_title", clean_title)[:100] if seo_res and isinstance(seo_res, dict) else clean_title[:100]
    video_desc = seo_res.get("video_description", clean_title) if seo_res and isinstance(seo_res, dict) else clean_title
    raw_tags = seo_res.get("specific_tags", []) if seo_res and isinstance(seo_res, dict) else []
    video_tags = sanitize_youtube_tags(raw_tags + DEFAULT_BASE_TAGS)

    thumb_meta = generate_thumbnail_metadata(verified_data, clean_title)

    word_count = len(voiceover_script.split())
    print(f"✨ [SEGMENTED SYNC READY] {word_count}-word Script ({len(script_segments)} scenes) + Layout [{thumb_meta['layout_style']}]")
    return opt_title, voiceover_script, thumb_meta, video_desc, video_tags, verified_data


def generate_job_content(title, article_text, img_paths=None):
    opt_title, voiceover_script, thumb_meta, video_desc, video_tags, _ = generate_job_content_with_data(
        title, article_text, img_paths=img_paths
    )
    return opt_title, voiceover_script, thumb_meta, video_desc, video_tags
