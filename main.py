# -*- coding: utf-8 -*-
import os, json, time, re, shutil, random, traceback, base64, asyncio
import requests, feedparser
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import numpy as np

try:
    from fontTools.ttLib import TTFont
    HAS_FONTTOOLS = True
except ImportError:
    HAS_FONTTOOLS = False

import edge_tts
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from moviepy.editor import AudioFileClip, VideoClip, concatenate_videoclips, ImageClip, CompositeVideoClip

# ==================== [ ডিরেক্টরি ও গ্লোবাল ভেরিয়েবল ] ====================
WORKSPACE_DIR = "workspace"        # Rclone Sync Location
LIVESTREAM_DIR = "workspace_live"  # JobLive folder source
TMP_DIR = "temp_assets"            # Temp Files processing
FONT_PATH = "BengaliFont.ttf"      # Fallback Bengali Font
SCHEDULE_TRACKER_FILE = "schedule_tracker.txt"

# 🌟 GitHub Secrets থেকে API Keys ও মডেল নেওয়া
GROQ_API = os.environ.get("GROQ_API", "").strip()
OLLAMA_API_KEY = os.environ.get("Ollama_API_Key", os.environ.get("OLLAMA_API_KEY", "")).strip()
OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "https://api.ollama.com").rstrip("/")
OLLAMA_MODEL = "qwen3.5"

# ElevenLabs মাল্টিপল কী এবং ভয়েস আইডি
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "RWLFUuahyI6QdILs8AI5").strip()

def get_all_elevenlabs_keys():
    """🌟 সিক্রেটস থেকে এন্টার বা কমা দিয়ে রাখা অসংখ্য ElevenLabs API Key লিস্ট আকারে নিয়ে আসে"""
    raw_keys = os.environ.get("ELEVENLABS_API_KEYS", os.environ.get("ELEVENLABS_API_KEY", "")).strip()
    if not raw_keys:
        return []
    # এন্টার (\n), কমা (,), বা সেমিকোলন দিয়ে আলাদা করা কি-গুলো ফিল্টার করা
    keys = [k.strip() for k in re.split(r'[\r\n,;]+', raw_keys) if k.strip()]
    return keys

# 🌟 হাই-কনট্রাস্ট কালার প্যালেট
COLOR_THEMES = [
    {
        'top_bot_bg': '#000839', 'top_bot_fg': '#ffffff',
        'row1_bg': '#ffe600', 'row1_fg': '#000000',
        'row2_bg': '#dc2626', 'row2_fg': '#ffffff',
        'row3_bg': '#ffe600', 'row3_fg': '#000000'
    },
    {
        'top_bot_bg': '#013a1a', 'top_bot_fg': '#ffffff',
        'row1_bg': '#ffffff', 'row1_fg': '#013a1a',
        'row2_bg': '#dc2626', 'row2_fg': '#ffe600',
        'row3_bg': '#ffe600', 'row3_fg': '#000000'
    },
    {
        'top_bot_bg': '#4a000d', 'top_bot_fg': '#ffffff',
        'row1_bg': '#00f0ff', 'row1_fg': '#000000',
        'row2_bg': '#dc2626', 'row2_fg': '#ffffff',
        'row3_bg': '#ffe600', 'row3_fg': '#000000'
    },
    {
        'top_bot_bg': '#1e1035', 'top_bot_fg': '#ffffff',
        'row1_bg': '#ffe600', 'row1_fg': '#000000',
        'row2_bg': '#ea580c', 'row2_fg': '#ffffff',
        'row3_bg': '#ffffff', 'row3_fg': '#000000'
    },
    {
        'top_bot_bg': '#0f172a', 'top_bot_fg': '#ffffff',
        'row1_bg': '#00ff66', 'row1_fg': '#000000',
        'row2_bg': '#dc2626', 'row2_fg': '#ffffff',
        'row3_bg': '#ffe600', 'row3_fg': '#000000'
    }
]

LOGO_MAPPING = {
    'পল্লী বিদ্যুৎ': 'PalliBidyut.png',
    'বিদ্যুৎ': 'PalliBidyut.png',
    'সেনাবাহিনী': 'Army.png',
    'নৌবাহিনী': 'Navy.png',
    'বিমান বাহিনী': 'AirForce.png',
    'বিমানবাহিনী': 'AirForce.png',
    'বর্ডার গার্ড': 'BGB.png',
    'বিজিবি': 'BGB.png',
    'পুলিশ': 'Police.png',
    'আনসার': 'Ansar.png',
    'কোস্ট গার্ড': 'CoastGuard.png',
    'কোস্টগার্ড': 'CoastGuard.png',
    'র‍্যাব': 'RAB.png',
    'র‌্যাব': 'RAB.png',
    'ফায়ার সার্ভিস': 'FireService.png',
    'ফায়ার সার্ভিস': 'FireService.png',
    'রেলওয়ে': 'Railway.png',
    'রেলওয়ে': 'Railway.png',
    'বিসিএস': 'BCS.png',
    'প্রাথমিক শিক্ষক': 'PrimaryTeacher.png',
    'প্রাথমিক': 'PrimaryTeacher.png',
    'বাংলাদেশ ব্যাংক': 'BangladeshBank.png',
    'ব্যাংক': 'BangladeshBank.png',
    'খাদ্য অধিদপ্তর': 'Food.png',
    'খাদ্য': 'Food.png',
    'ডাক বিভাগ': 'PostOffice.png',
    'পোস্ট': 'PostOffice.png',
    'কারা অধিদপ্তর': 'Jail.png',
    'কারাগার': 'Jail.png',
    'জেল': 'Jail.png',
    'পাসপোর্ট অধিদপ্তর': 'Passport.png',
    'পাসপোর্ট': 'Passport.png',
    'পরিবার পরিকল্পনা': 'FamilyPlanning.png'
}

def get_youtube_service():
    creds = Credentials(
        None,
        refresh_token=os.environ['REFRESH_TOKEN'],
        client_id=os.environ['CLIENT_ID'],
        client_secret=os.environ['CLIENT_SECRET'],
        token_uri="https://oauth2.googleapis.com/token"
    )
    return build('youtube', 'v3', credentials=creds)

def clean_filename(text):
    return re.sub(r'[\\/*?:"<>|]', "", text)

def download_image(url, output_path):
    try:
        req = requests.get(url, timeout=10)
        if req.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(req.content)
            return True
    except: pass
    return False

# ==================== [ 🌟 ইউনিকোড বাংলা ফন্ট ইঞ্জিন ] ====================
def is_valid_bengali_unicode_font(font_path):
    try:
        if not os.path.exists(font_path):
            return False
            
        fname = os.path.basename(font_path).lower()
        if any(bad in fname for bad in ['ansi', 'sutonny', 'mj', 'bijoy', 'durbar', '-vf', 'variable']):
            return False
            
        if HAS_FONTTOOLS:
            try:
                tt = TTFont(font_path)
                bengali_chars = [0x0985, 0x0995, 0x09AC, 0x09BE, 0x09B2]
                for table in tt['cmap'].tables:
                    if table.isUnicode():
                        matches = sum(1 for c in bengali_chars if c in table.cmap and table.cmap[c] != '.notdef')
                        if matches >= 4:
                            return True
                return False
            except Exception:
                pass
                
        if any(good in fname for good in ['kalpurush', 'unicode', 'noto', 'siliguri', 'solaiman', 'bangla', 'bengali', 'akhand', 'shorif', 'shokuntola', 'ador']):
            return True
            
        return False
    except Exception:
        return False

def ensure_bengali_font():
    fonts_dir = "Fonts"
    if not os.path.exists(fonts_dir):
        os.makedirs(fonts_dir, exist_ok=True)

    verified_fonts = [
        os.path.join(fonts_dir, f) for f in os.listdir(fonts_dir)
        if f.lower().endswith(('.ttf', '.otf')) and is_valid_bengali_unicode_font(os.path.join(fonts_dir, f))
    ]

    if not verified_fonts:
        print("Downloading verified Unicode Bengali fonts...")
        urls = {
            "Kalpurush.ttf": "https://raw.githubusercontent.com/maateen/kalpurush/master/Kalpurush.ttf",
            "HindSiliguri-Bold.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/hindsiliguri/HindSiliguri-Bold.ttf",
            "NotoSansBengali-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/notosansbengali/NotoSansBengali%5Bwdth%2Cwght%5D.ttf"
        }
        for fname, url in urls.items():
            out_p = os.path.join(fonts_dir, fname)
            if not os.path.exists(out_p):
                try:
                    r = requests.get(url, timeout=12)
                    if r.status_code == 200 and len(r.content) > 10000:
                        with open(out_p, "wb") as f:
                            f.write(r.content)
                        print(f"Downloaded: {fname}")
                except Exception as e:
                    print(f"Failed to download {fname}: {e}")

def get_kalpurush_font():
    ensure_bengali_font()
    fonts_dir = "Fonts"
    if os.path.exists(fonts_dir):
        for f in os.listdir(fonts_dir):
            if "kalpurush" in f.lower() and f.lower().endswith(('.ttf', '.otf')):
                return os.path.join(fonts_dir, f)
    return FONT_PATH if os.path.exists(FONT_PATH) else None

def get_distinct_fonts_for_top_rows(count=4):
    ensure_bengali_font()
    fonts_dir = "Fonts"
    valid_fonts = []
    
    if os.path.exists(fonts_dir):
        for f in os.listdir(fonts_dir):
            if f.lower().endswith(('.ttf', '.otf')):
                if "kalpurush" in f.lower():
                    continue
                full_p = os.path.join(fonts_dir, f)
                if is_valid_bengali_unicode_font(full_p):
                    valid_fonts.append(full_p)

    if not valid_fonts:
        kp = get_kalpurush_font()
        return [kp] * count
        
    pool = valid_fonts.copy()
    random.shuffle(pool)
    while len(pool) < count:
        pool.extend(valid_fonts)
        
    return pool[:count]

def get_specific_organization_logo(title):
    t = title.strip()
    for kw, img_name in LOGO_MAPPING.items():
        if kw in t:
            path = os.path.join("Photos", img_name)
            if os.path.exists(path):
                return path
    return None

# ==================== [ 🌟 OLLAMA CLOUD QWEN3.5 SCRIPT & TTS ENGINE ] ====================
def encode_image_base64(image_path, max_dim=1024):
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            if max(img.size) > max_dim:
                img.thumbnail((max_dim, max_dim), Image.LANCZOS)
            from io import BytesIO
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"Image base64 encoding error for {image_path}: {e}")
        return None

def generate_voiceover_script_with_ollama(title, img_paths):
    """🌟 Ollama Cloud (qwen3.5) দিয়ে সার্কুলার ইমেজ ও টাইটেল পড়ে স্ক্রিপ্ট তৈরি করে"""
    print(f"🤖 Generating AI Voiceover Script with Ollama Cloud ({OLLAMA_MODEL})...")
    
    prompt_text = f"""জব টাইটেল: "{title}"

এই জব নিয়োগটির উপর ভিত্তি করে আমাকে একটি ইউটিউব ভিডিওর স্ক্রিপ্ট লিখে দাও যেখানে আমি এই নিয়োগটি বিস্তারিতভাবে মানুষদের বোঝাবো। আবেদন করার প্রক্রিয়া বা বাড়তি বিষয়গুলো উল্লেখ করার দরকার নেই শুধু নিয়োগটি সম্পর্কে অর্থাৎ পদ কয়টি, ওই পদে কি কাজ, বেতন স্কেল কেমন, শিক্ষাগত যোগ্যতা কেমন লাগে ইত্যাদি। আর ভিডিওর শেষে যারা যারা আবেদন করতে আগ্রহী তাদেরকে আমার হোয়াটসঅ্যাপ নাম্বারে মেসেজ দেওয়ার জন্য বলবে যা আমার ডেসক্রিপশনে এবং চ্যানেলের বায়োতে থাকবে। আমাদের কাছে বিশ্বস্ততার সাথে সার্ভিস নিতে পারবে। আমরা যত্ন সহকারে এবং নির্ভুলভাবে আবেদনটি করে দেই। আমাদেরকে মূলত একবার নিজের তথ্যগুলো যেমন নাম ঠিকানা ইত্যাদি এগুলো দিলেই হবে। পরবর্তী যেকোনো আবেদনের সময় এগুলো আর দেওয়া লাগবে না। এখন তুমি স্ক্রিপটি লিখে দাও। সম্পূর্ণ স্ক্রিপটি একটিমাত্র প্যারাগ্রাফ আকারে হবে। কোনো অতিরিক্ত কথা, শিরোনাম বা ব্র্যাকেটের ডায়ালগ রাখবে না, শুধুমাত্র মুখে বলার কথাগুলো একটি প্যারাগ্রাফে দিবে।"""

    base64_images = []
    for p in img_paths[:4]:
        b64 = encode_image_base64(p)
        if b64:
            base64_images.append(b64)

    headers = {"Content-Type": "application/json"}
    if OLLAMA_API_KEY:
        headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"

    url = f"{OLLAMA_API_URL}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt_text,
                "images": base64_images
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0.4
        }
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            script_text = data.get("message", {}).get("content", "").strip()
            script_text = re.sub(r'[\r\n]+', ' ', script_text).strip()
            if len(script_text) > 40:
                print(f"✅ Generated Script:\n{script_text[:150]}...\n")
                return script_text
        else:
            print(f"⚠️ Ollama API Error {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"⚠️ Ollama script generation error ({e}). Using smart rule-based fallback.")

    # ফলব্যাক স্ক্রিপ্ট
    clean = clean_title_for_display(title)
    return f"আসসালামু আলাইকুম। {clean} এর নতুন নিয়োগ বিজ্ঞপ্তি প্রকাশিত হয়েছে। এই সার্কুলারে বেশ কয়েকটি পদে আকর্ষণীয় বেতন স্কেলে আবেদনের সুযোগ রয়েছে। শিক্ষাগত যোগ্যতা পদভেদে ৮ম শ্রেণি, এসএসসি, এইচএসসি এবং স্নাতক পাস নির্ধারণ করা হয়েছে। আগ্রহী সকল প্রার্থী নিয়ম অনুযায়ী নির্ধারিত সময়ের মধ্যে আবেদন সম্পন্ন করতে পারবেন। যারা যারা আবেদন করতে আগ্রহী তারা আমাদের ডেসক্রিপশন এবং চ্যানেলের বায়োতে দেওয়া হোয়াটসঅ্যাপ নম্বরে সরাসরি মেসেজ দিন। আমাদের মাধ্যমে শতভাগ নির্ভুল ও বিশ্বস্ততার সাথে আবেদন করে নিতে পারবেন। আমাদের একবার তথ্য দিয়ে রাখলে পরবর্তীতে আর কোনো তথ্য দিতে হবে না। ধন্যবাদ।"

async def text_to_speech_edge_async(text, output_audio_path, voice="bn-BD-PradeepNeural"):
    communicate = edge_tts.Communicate(text, voice, rate="+4%")
    await communicate.save(output_audio_path)

def generate_bengali_edge_tts(text, output_audio_path):
    asyncio.run(text_to_speech_edge_async(text, output_audio_path, voice="bn-BD-PradeepNeural"))
    print(f"✅ Edge-TTS Voiceover Audio generated: {output_audio_path}")

def generate_voiceover_audio_pipeline(text, output_audio_path):
    """🌟 ElevenLabs-এর একাধিক API Key ঘুরিয়ে ব্যবহার করে, শেষ হলে Edge-TTS ব্যাকআপ হিসেবে চালায়"""
    eleven_keys = get_all_elevenlabs_keys()
    
    if eleven_keys:
        print(f"🔑 Found {len(eleven_keys)} ElevenLabs API key(s). Attempting synthesis...")
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        for idx, api_key in enumerate(eleven_keys, start=1):
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": api_key
            }
            try:
                print(f"🎙️ Synthesizing with ElevenLabs Key #{idx}/{len(eleven_keys)}...")
                resp = requests.post(url, json=payload, headers=headers, timeout=35)
                
                if resp.status_code == 200:
                    with open(output_audio_path, "wb") as f:
                        f.write(resp.content)
                    print(f"✅ Successfully generated ElevenLabs audio using Key #{idx}!")
                    return
                elif resp.status_code in [401, 429] or any(err in resp.text.lower() for err in ["quota", "credit", "character", "unauthorized"]):
                    print(f"⚠️ ElevenLabs Key #{idx} quota exhausted or invalid. Switching to next key...")
                    continue
                else:
                    print(f"⚠️ Key #{idx} returned {resp.status_code}: {resp.text[:100]}. Trying next...")
                    continue
            except Exception as e:
                print(f"⚠️ Network error with ElevenLabs Key #{idx}: {e}. Trying next key...")
                continue

    # সব কি শেষ হলে বা না থাকলে Edge-TTS চালানো
    print("🎙️ Using Edge-TTS (bn-BD-PradeepNeural) as reliable audio engine...")
    generate_bengali_edge_tts(text, output_audio_path)

# ==================== [ 🌟 AI & ALGORITHMIC METADATA GENERATOR ] ====================
def clean_title_for_display(title):
    clean = title.split('|')[0].split('||')[0].strip()
    clean = re.sub(r'[\r\n\t]+', ' ', clean)
    return re.sub(r'\s+', ' ', clean)

def extract_vacancy_and_qual(title):
    vac_match = re.search(r'(\d+|[০-৯]+)\s*(টি\s*)?পদে', title)
    vac_str = vac_match.group(0) if vac_match else ""
    
    qual = ""
    if any(k in title.upper() for k in ["SSC", "এসএসসি"]):
        qual = "SSC পাশ"
    elif any(k in title.upper() for k in ["HSC", "এইচএসসি"]):
        qual = "HSC পাশ"
    elif any(k in title for k in ["৮ম", "অষ্টম"]):
        qual = "৮ম শ্রেণি পাশ"
    elif any(k in title for k in ["স্নাতক", "ডিগ্রী", "অনার্স", "Degree", "Honours"]):
        qual = "স্নাতক/ডিগ্রী পাশ"
    return vac_str, qual

def parse_title_with_groq_ai(title):
    clean_title = clean_title_for_display(title)
    words = clean_title.split()
    
    org_name = ""
    if "নিয়োগ" in clean_title:
        before_niyog = clean_title.split("নিয়োগ")[0].strip()
        if "পদে" in before_niyog:
            try: before_niyog = before_niyog.split("পদে")[1].strip()
            except: pass
        if len(before_niyog) >= 2:
            org_name = before_niyog
            
    if not org_name:
        org_name = " ".join(words[:min(3, len(words))]) if words else "সরকারি চাকরি"

    vac_str, qual_str = extract_vacancy_and_qual(clean_title)

    if GROQ_API:
        try:
            prompt = f"""You are an expert YouTube SEO Title & Bengali Thumbnail copywriter for Bangladeshi Job Circulars (চাকরির খবর ও নিয়োগ বিজ্ঞপ্তি ২০২৬).
Job Title: "{clean_title}"
Organization: "{org_name}"

Create high-CTR click-worthy metadata:
1. "optimized_title": Catchy YouTube Video Title strictly under 95 characters. Use fire emoji "🔥", pipe separator "|", high-ranking keywords (e.g. "🔥 নিজ জেলা DC অফিসে নিয়োগ ২০২৬ | জেলা প্রশাসকের কার্যালয়ে বিশাল নিয়োগ | Govt Job Circular 2026" or "🔥 {org_name} বিশাল নিয়োগ ২০২৬ | সরকারি জব সার্কুলার ২০২৬ | Govt Job Circular 2026").
2. "top_text": Short top bar header (2-3 words in Bengali, e.g. "সরকারি চাকরি", "সরকারি নিয়োগ", "গণপ্রজাতন্ত্রী বাংলাদেশ সরকার").
3. "row1_text": Very large main hook (2-4 words in Bengali, e.g. "নিজ উপজেলায়", "জেলা প্রশাসকের কার্যালয়", "জরুরি নিয়োগ", "এপ্রিল মাসের", "অফিসার পদে বিশাল নিয়োগ").
4. "row2_text": Core organization name (e.g. "{org_name}").
5. "row3_text": Eligibility / qualification badge (e.g. "(জরুরি নিয়োগ) SSC পাশ", "(SSC পাশ/৬৪ জেলা)", "চলমান সেরা সার্কুলার", "(নারী ও পুরুষ আবেদনযোগ্য)").
6. "bot_text": Bottom bar highlight (e.g. "({vac_str if vac_str else 'বিশাল পদে'}) নিয়োগ ২০২৬", "({vac_str if vac_str else '২৬৫৩ পদে'}) নিয়োগ ২০২৬", "অনলাইনে দ্রুত আবেদন করুন").

Return strictly valid JSON only:
{{
  "optimized_title": "...",
  "top_text": "...",
  "row1_text": "...",
  "row2_text": "...",
  "row3_text": "...",
  "bot_text": "..."
}}"""
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {GROQ_API}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": "You are a professional Bengali YouTube SEO and Thumbnail copywriter. Output strictly valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.7,
                "max_tokens": 250
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=7)
            if resp.status_code == 200:
                data = resp.json()
                content = data['choices'][0]['message']['content']
                parsed = json.loads(content)
                opt_title = parsed.get("optimized_title", "").strip()
                top = parsed.get("top_text", "").strip()
                r1 = parsed.get("row1_text", "").strip()
                r2 = parsed.get("row2_text", org_name).strip()
                r3 = parsed.get("row3_text", "").strip()
                bot = parsed.get("bot_text", "").strip()
                if opt_title and top and r1 and r3 and bot:
                    if len(opt_title) > 100: opt_title = opt_title[:100]
                    return opt_title, top, r1, r2, r3, bot
        except Exception as e:
            print(f"⚠️ Groq AI text generation warning ({e}). Using smart rule-based fallback.")

    clean_no_year = re.sub(r'(২০২\d|202\d)', '', clean_title).strip()
    
    if "dc" in clean_title.lower() or "জেলা প্রশাসক" in clean_title:
        opt_title = "🔥 নিজ জেলা DC অফিসে নিয়োগ ২০২৬ | জেলা প্রশাসকের কার্যালয়ে বিশাল নিয়োগ | Govt Job Circular 2026"
        top_text = "সরকারি চাকরি"
        r1_text = "নিজ উপজেলায়"
        r2_text = "জেলা প্রশাসকের কার্যালয়"
        r3_text = f"(জরুরি নিয়োগ) {qual_str if qual_str else 'SSC পাশ'}"
        bot_text = f"({vac_str if vac_str else '২৬৫৩ পদে'}) নিয়োগ ২০২৬"
    elif "উপজেলা" in clean_title:
        opt_title = f"🔥 নিজ উপজেলায় সরকারি চাকরি ২০২৬ | {clean_no_year[:30]} বিশাল নিয়োগ | Govt Job Circular 2026"
        top_text = "সরকারি চাকরি"
        r1_text = "নিজ উপজেলায়"
        r2_text = org_name
        r3_text = f"(জরুরি নিয়োগ) {qual_str if qual_str else '৬৪ জেলা'}"
        bot_text = f"({vac_str if vac_str else 'বিশাল পদে'}) নিয়োগ ২০২৬"
    else:
        months = ["জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"]
        found_month = next((m for m in months if m in clean_title), "")
        
        if found_month:
            opt_title = f"{found_month} মাসের সরকারি নিয়োগ ২০২৬ 🔥 {found_month} মাসের জব সার্কুলার ২০২৬ | Govt Job Circular 2026"
            top_text = "সরকারি নিয়োগ"
            r1_text = f"{found_month} মাসের"
            r2_text = "চলমান সেরা সার্কুলার"
            r3_text = f"({qual_str if qual_str else 'SSC পাশ/৬৪ জেলা'})"
            bot_text = f"({vac_str if vac_str else '২৩৫৮০ পদে'}) নিয়োগ ২০২৬"
        else:
            opt_title = f"🔥 {clean_no_year[:38]} বিশাল নিয়োগ ২০২৬ | সরকারি জব সার্কুলার ২০২৬ | Govt Job Circular 2026"
            top_text = "সরকারি চাকরি"
            r1_text = "জরুরি নিয়োগ"
            r2_text = org_name
            r3_text = f"({qual_str if qual_str else 'SSC পাশ/৬৪ জেলা'})"
            bot_text = f"({vac_str if vac_str else 'বিশাল পদে'}) নিয়োগ ২০২৬"

    if len(opt_title) > 100:
        opt_title = opt_title[:100]

    return opt_title, top_text, r1_text, r2_text, r3_text, bot_text

# ==================== [ 🌟 ক্লিন বড় টেক্সট রেন্ডারার ] ====================
def draw_clean_text(draw, text, box, font_path, text_color, max_font_size=160, min_font_size=45):
    x1, y1, x2, y2 = box
    w_box = x2 - x1
    h_box = y2 - y1
    cx = x1 + w_box / 2
    cy = y1 + h_box / 2
    
    pad_x = 25
    pad_y = 10
    avail_w = w_box - pad_x * 2
    avail_h = h_box - pad_y * 2
    
    if not font_path or not os.path.exists(font_path):
        draw.text((cx, cy), text, fill=text_color, anchor="mm")
        return
        
    words = text.split()
    best_font_size = None
    best_lines = [text]
    
    for fs in range(max_font_size, int(max_font_size * 0.65), -2):
        try:
            f = ImageFont.truetype(font_path, fs)
            bbox = f.getbbox(text)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            if tw <= avail_w and th <= avail_h:
                best_font_size = fs
                best_lines = [text]
                break
        except Exception: pass
            
    if best_font_size is None and len(words) >= 2:
        splits = []
        for i in range(1, len(words)):
            splits.append((" ".join(words[:i]), " ".join(words[i:])))
            
        for fs in range(max_font_size, min_font_size, -2):
            try:
                f = ImageFont.truetype(font_path, fs)
                found = False
                for l1, l2 in splits:
                    bb1, bb2 = f.getbbox(l1), f.getbbox(l2)
                    w1, w2 = bb1[2] - bb1[0], bb2[2] - bb2[0]
                    h1, h2 = bb1[3] - bb1[1], bb2[3] - bb2[1]
                    total_h = h1 + h2 + fs * 0.15
                    if max(w1, w2) <= avail_w and total_h <= avail_h:
                        best_font_size = fs
                        best_lines = [l1, l2]
                        found = True
                        break
                if found: break
            except Exception: pass
                
    if best_font_size is None:
        best_font_size = min_font_size
        best_lines = [text]
        
    try:
        font = ImageFont.truetype(font_path, best_font_size)
    except Exception:
        font = ImageFont.load_default()
        
    full_text = "\n".join(best_lines)
    
    draw.multiline_text(
        (cx, cy), full_text, fill=text_color, font=font,
        anchor="mm", align="center", spacing=int(best_font_size * 0.12)
    )

# ==================== [ 🌟 FULL HD 1080P ডায়নামিক থাম্বনেইল জেনারেটর ] ====================
def generate_dynamic_thumbnail(title, output_path):
    print(f"Generating Ultra-HD 1080p AI Thumbnail for: {title}")
    
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), "#ffffff")
    draw = ImageDraw.Draw(img)

    f_top, f_row1, f_row2, f_row3 = get_distinct_fonts_for_top_rows(4)
    f_bot = get_kalpurush_font()

    opt_title, top_text, row1_text, row2_text, row3_text, bot_text = parse_title_with_groq_ai(title)

    specific_logo_path = get_specific_organization_logo(title)

    if specific_logo_path and os.path.exists(specific_logo_path):
        theme_index = abs(hash(title)) % len(COLOR_THEMES)
        theme = COLOR_THEMES[theme_index]

        draw.rectangle([0, 0, W, 180], fill=theme['top_bot_bg'])
        gov_logo_path = os.path.join("Photos", "Govbd.png")
        if os.path.exists(gov_logo_path):
            try:
                gov_logo = Image.open(gov_logo_path).convert("RGBA")
                gov_logo = gov_logo.resize((140, 140), Image.LANCZOS)
                img.paste(gov_logo, (25, 20), gov_logo)
                img.paste(gov_logo, (W - 165, 20), gov_logo)
            except Exception as e:
                print(f"Error pasting Govbd.png: {e}")

        draw_clean_text(draw, f"✪ {top_text} ✪", (180, 0, W - 180, 180), f_top, theme['top_bot_fg'], max_font_size=95, min_font_size=50)
        draw.rectangle([0, 900, W, H], fill=theme['top_bot_bg'])
        draw_clean_text(draw, bot_text, (50, 900, W - 50, 1080), f_bot, theme['top_bot_fg'], max_font_size=90, min_font_size=45)

        draw.rectangle([1320, 180, W, 900], fill="#ffffff")
        try:
            org_logo = Image.open(specific_logo_path).convert("RGBA")
            scale = min(540 / org_logo.width, 540 / org_logo.height)
            new_lw = int(org_logo.width * scale)
            new_lh = int(org_logo.height * scale)
            org_logo = org_logo.resize((new_lw, new_lh), Image.LANCZOS)
            lx = 1320 + (600 - new_lw) // 2
            ly = 180 + (720 - new_lh) // 2
            img.paste(org_logo, (lx, ly), org_logo)
        except Exception as e:
            print(f"Error pasting org logo: {e}")

        draw.rectangle([0, 180, 1320, 420], fill=theme['row1_bg'])
        draw_clean_text(draw, row1_text, (20, 180, 1300, 420), f_row1, theme['row1_fg'], max_font_size=130, min_font_size=55)

        draw.rectangle([0, 420, 1320, 660], fill=theme['row2_bg'])
        draw_clean_text(draw, row2_text, (20, 420, 1300, 660), f_row2, theme['row2_fg'], max_font_size=160, min_font_size=60)

        draw.rectangle([0, 660, 1320, 900], fill=theme['row3_bg'])
        draw_clean_text(draw, row3_text, (20, 660, 1300, 900), f_row3, theme['row3_fg'], max_font_size=120, min_font_size=50)

        draw.line([(0, 180), (W, 180)], fill="#ffffff", width=4)
        draw.line([(0, 900), (W, 900)], fill="#ffffff", width=4)
        draw.line([(1320, 180), (1320, 900)], fill="#cbd5e1", width=4)
        draw.line([(0, 420), (1320, 420)], fill="#ffffff", width=3)
        draw.line([(0, 660), (1320, 660)], fill="#ffffff", width=3)

    else:
        # 🌟 স্ক্রিনশটের ৩-লেয়ার ফুল-উইডথ থাম্বনেইল
        green_bg = "#015a24"
        red_fg = "#cc0000"
        dark_fg = "#0f172a"
        yellow_fg = "#ffe600"
        white_fg = "#ffffff"

        draw.rectangle([0, 0, W, 220], fill=green_bg)
        gov_logo_path = os.path.join("Photos", "Govbd.png")
        if os.path.exists(gov_logo_path):
            try:
                gov_logo = Image.open(gov_logo_path).convert("RGBA")
                gov_logo = gov_logo.resize((170, 170), Image.LANCZOS)
                img.paste(gov_logo, (35, 25), gov_logo)
                img.paste(gov_logo, (W - 205, 25), gov_logo)
            except Exception as e:
                print(f"Error pasting Govbd.png: {e}")

        top_header = f"✪ {top_text} ✪"
        draw_clean_text(draw, top_header, (220, 0, W - 220, 220), f_top, white_fg, max_font_size=120, min_font_size=60)

        draw.rectangle([0, 220, W, 870], fill="#ffffff")
        draw_clean_text(draw, row1_text, (40, 230, W - 40, 580), f_row1, red_fg, max_font_size=200, min_font_size=80)
        draw_clean_text(draw, row3_text, (40, 590, W - 40, 860), f_row2, dark_fg, max_font_size=130, min_font_size=55)

        draw.rectangle([0, 870, W, H], fill=green_bg)
        draw_clean_text(draw, bot_text, (40, 870, W - 40, 1080), f_bot, yellow_fg, max_font_size=130, min_font_size=55)

        draw.line([(0, 220), (W, 220)], fill="#003d16", width=5)
        draw.line([(0, 870), (W, 870)], fill="#003d16", width=5)

    img.save(output_path, "JPEG", quality=100, subsampling=0)
    print(f"Generated AI Dynamic 1080p Thumbnail successfully for: {title}")
    return opt_title

# ==================== [ 1. FEED PARSING ] ====================
def check_new_articles_and_prepare_folders():
    print("Checking for new RSS items (Last 24 Hours)...")
    if not os.path.exists(WORKSPACE_DIR): os.makedirs(WORKSPACE_DIR)

    if not os.path.exists('config.json'):
        print("config.json not found!")
        return

    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            rss_links = config_data.get('rss_links', [])
    except Exception as ce:
        print(f"Error reading config.json: {ce}")
        return

    time_limit = datetime.now() - timedelta(hours=24)
    existing_folders = [f for f in os.listdir(WORKSPACE_DIR) if os.path.isdir(os.path.join(WORKSPACE_DIR, f))]
    
    history_file = os.path.join(WORKSPACE_DIR, "history.txt")
    history_logs = []
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as hf:
                history_logs = [line.strip() for line in hf if line.strip()]
        except Exception: pass

    req_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }

    for feed_url in rss_links:
        print(f"Parsing Feed: {feed_url}")
        try:
            resp = requests.get(feed_url, headers=req_headers, timeout=15)
            if resp.status_code == 200:
                feed = feedparser.parse(resp.content)
            else:
                feed = feedparser.parse(feed_url)
        except Exception as fe:
            print(f"Feed fetch error for {feed_url}: {fe}")
            continue
        
        for entry in feed.entries:
            try:
                published_time = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            except: continue

            if published_time >= time_limit:
                folder_title = clean_filename(entry.title).strip()
                if folder_title.lower() == "shorts": continue
                if not folder_title or folder_title in existing_folders or folder_title in history_logs: 
                    continue 

                print(f"New Article Found: {folder_title}. Generating folder...")
                folder_path = os.path.join(WORKSPACE_DIR, folder_title)
                os.makedirs(folder_path, exist_ok=True)
                existing_folders.append(folder_title)
                
                history_logs.append(folder_title)
                try:
                    with open(history_file, 'a', encoding='utf-8') as hf:
                        hf.write(f"{folder_title}\n")
                except Exception: pass

                with open(os.path.join(folder_path, "title.txt"), "w", encoding="utf-8") as text_file:
                    text_file.write(entry.title)

                content = entry.content[0].value if hasattr(entry, 'content') else getattr(entry, 'summary', "")
                images = BeautifulSoup(content, 'html.parser').find_all('img')
                
                img_count = 1
                for img in images:
                    src = img.get('src')
                    if src and src.startswith("http"):
                        img_path = os.path.join(folder_path, f"{img_count}.jpg")
                        if download_image(src, img_path):
                            img_count += 1

# ==================== [ 2. DYNAMIC FRAME ENGINE ] ====================
def make_video_frame(img_path, duration, target_w=1920, target_h=1080):
    pil_img = Image.open(img_path).convert("RGB")
    w, h = pil_img.size
    ratio = w / h
    target_ratio = target_w / target_h

    is_vertical = target_w < target_h 

    if is_vertical:
        if ratio < (9.0 / 16.0) - 0.01:
            new_w = target_w
            new_h = int((target_w / w) * h)
            if new_h < target_h: new_h = target_h
                
            resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
            img_np = np.array(resized)
            
            def make_frame(t):
                progress = t / duration if duration > 0 else 0
                y = int(progress * (new_h - target_h)) if (new_h - target_h) > 0 else 0 
                x = 0
                return img_np[y:y+target_h, x:x+target_w]
            
            return VideoClip(make_frame, duration=duration)
            
        elif (9.0 / 16.0) - 0.01 <= ratio < (16.0 / 9.0) - 0.01:
            scale = min(target_w / w, target_h / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
            
            canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
            canvas.paste(resized, ((target_w - new_w) // 2, (target_h - new_h) // 2))
            img_np = np.array(canvas)
            return VideoClip(lambda t: img_np, duration=duration)
            
        else:
            new_h = target_h
            new_w = int((target_h / h) * w)
            if new_w < target_w: new_w = target_w
                
            resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
            img_np = np.array(resized)
            
            def make_frame(t):
                progress = t / duration if duration > 0 else 0
                y = 0
                x = int(progress * (new_w - target_w)) if (new_w - target_w) > 0 else 0 
                return img_np[y:y+target_h, x:x+target_w]
                
            return VideoClip(make_frame, duration=duration)
            
    else:
        if ratio >= target_ratio: 
            new_h = target_h
            new_w = int((target_h / h) * w)
        else:
            new_w = target_w
            new_h = int((target_w / w) * h)
            
        if new_w < target_w:
            new_w = target_w
            new_h = int((new_w / w) * h)
        if new_h < target_h:
            new_h = target_h
            new_w = int((new_h / h) * w)

        resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
        img_np = np.array(resized)
        
        def make_frame(t):
            progress = t / duration if duration > 0 else 0
            y = int(progress * (new_h - target_h)) if (new_h - target_h) > 0 else 0 
            x = int(progress * (new_w - target_w)) if (new_w - target_w) > 0 else 0 
            return img_np[y:y+target_h, x:x+target_w]
            
        return VideoClip(make_frame, duration=duration)

# ==================== [ 🌟 ফ্লোটিং FRONT.PNG ওভারলে ইঞ্জিন ] ====================
def find_front_overlay_file():
    candidates = ["Front.png", "front.png", "FRONT.PNG"]
    for c in candidates:
        if os.path.exists(c): return c
    for f in os.listdir("."):
        if f.lower() == "front.png": return f
    return None

def apply_front_overlay(main_clip, target_w, target_h):
    front_path = find_front_overlay_file()
    if front_path and os.path.exists(front_path):
        try:
            print(f"Applying Smooth Slow-Floating Animation for '{front_path}'...")
            pil_front = Image.open(front_path).convert("RGBA")
            
            scale_ratio = 0.28 if target_w >= target_h else 0.38
            scaled_w = int(target_w * scale_ratio)
            scaled_h = int((scaled_w / pil_front.width) * pil_front.height)
            pil_front_resized = pil_front.resize((scaled_w, scaled_h), Image.LANCZOS)
            
            front_np = np.array(pil_front_resized)
            rgb_np = front_np[:, :, :3]
            alpha_np = front_np[:, :, 3] / 255.0 
            
            front_clip = ImageClip(rgb_np).set_duration(main_clip.duration)
            mask_clip = ImageClip(alpha_np, ismask=True).set_duration(main_clip.duration)
            front_clip = front_clip.set_mask(mask_clip)
            
            pad = 25
            avail_w = max(1, target_w - scaled_w - 2 * pad)
            avail_h = max(1, target_h - scaled_h - 2 * pad)
            
            # ধীরগতির মোশন (৪৫ ও ৩২ সেকেন্ড সাইকেল)
            vx = avail_w / 45.0
            vy = avail_h / 32.0
            
            def floating_pos(t):
                x_val = (t * vx) % (2 * avail_w)
                x = x_val if x_val <= avail_w else (2 * avail_w - x_val)
                y_val = (t * vy) % (2 * avail_h)
                y = y_val if y_val <= avail_h else (2 * avail_h - y_val)
                return (pad + int(x), pad + int(y))
            
            front_clip = front_clip.set_position(floating_pos)
            main_clip = CompositeVideoClip([main_clip, front_clip]).set_audio(main_clip.audio)
            print("Successfully attached Smooth Slow-Floating Front.png overlay!")
        except Exception as e:
            print(f"Error applying floating Front.png: {e}")
    return main_clip

# ==================== [ 🌟 YOUTUBE DESCRIPTION, TAGS & 1-HOUR SCHEDULER ] ====================
def get_video_description(video_title, config_data=None):
    for desc_filename in ["description.txt", "default_description.txt"]:
        if os.path.exists(desc_filename):
            try:
                with open(desc_filename, "r", encoding="utf-8") as df:
                    custom_text = df.read().strip()
                    if custom_text:
                        return custom_text.replace("{title}", video_title)
            except Exception: pass
                
    if config_data and isinstance(config_data, dict):
        desc_from_cfg = config_data.get("default_description", "").strip()
        if desc_from_cfg:
            return desc_from_cfg.replace("{title}", video_title)

    return f"""{video_title}

সকল চাকরির আবেদন করতে ও সেবা পেতে নিচের যেকোন একটা গ্রুপে জয়েন করে ফেলুনঃ
1. Telegram জয়েন করুন 👇: https://t.me/jobcircularbd
2. Facebook পেজ ফলো করুন 👇: https://facebook.com/allnewsonlinebd

#job_circular #job_news #bd_jobs #govt_jobs #চাকরির_খবর"""

def get_video_tags(config_data=None):
    if os.path.exists("tags.txt"):
        try:
            with open("tags.txt", "r", encoding="utf-8") as tf:
                content = tf.read().strip()
                if content:
                    return [t.strip() for t in content.split(",") if t.strip()]
        except Exception: pass
            
    if config_data and isinstance(config_data, dict):
        tags_from_cfg = config_data.get("default_tags", [])
        if isinstance(tags_from_cfg, list) and len(tags_from_cfg) > 0:
            return tags_from_cfg

    return [
        'Job Circular BD', 'Today Govt Jobs', 'Niyog Biggopti', 
        'Govt Job Circular 2026', 'সরকারি চাকরির খবর', 'নিয়োগ বিজ্ঞপ্তি ২০২৬', 
        'bd jobs', 'job news bd', 'চাকরির নিয়োগ বিজ্ঞপ্তি', 
        'সরকারি জব সার্কুলার ২০২৬', 'bd govt job circular', 'DC Office Job Circular'
    ]

def get_next_schedule_time_iso():
    """🌟 প্রতি ১ ঘণ্টা পর পর ভিডিও শিডিউল করার ISO টাইমস্ট্যাম্প তৈরি করে"""
    now_utc = datetime.now(timezone.utc)
    base_time = now_utc + timedelta(hours=1)

    if os.path.exists(SCHEDULE_TRACKER_FILE):
        try:
            with open(SCHEDULE_TRACKER_FILE, "r", encoding="utf-8") as sf:
                last_time_str = sf.read().strip()
                last_time = datetime.fromisoformat(last_time_str)
                if last_time > now_utc:
                    base_time = last_time + timedelta(hours=1)
        except Exception: pass

    next_schedule_str = base_time.isoformat()
    try:
        with open(SCHEDULE_TRACKER_FILE, "w", encoding="utf-8") as sf:
            sf.write(next_schedule_str)
    except Exception: pass

    yt_iso_str = base_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    return yt_iso_str

# ==================== [ 3. MOVIEPY PROCESS & DRIVE CLEANUP ] ====================
def process_ready_videos(yt):
    print("\nScanning Drive folders for Audios / AI Scripting...")
    if not os.path.exists(WORKSPACE_DIR): return
    if not os.path.exists(TMP_DIR): os.makedirs(TMP_DIR, exist_ok=True)
    
    config_data = {}
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except Exception: pass

    folders = [f for f in os.listdir(WORKSPACE_DIR) if os.path.isdir(os.path.join(WORKSPACE_DIR, f)) and f.lower() != "shorts"]
    
    for folder_name in folders:
        folder_path = os.path.join(WORKSPACE_DIR, folder_name)
        
        try:
            audio_file, txt_path = None, None
            img_files = []
            for file in sorted(os.listdir(folder_path)):
                ext = file.lower().split('.')[-1]
                if ext in ['mp3', 'wav', 'm4a', 'aac']: 
                    audio_file = file
                elif ext in ['txt']: 
                    txt_path = os.path.join(folder_path, file)
                elif ext in ['jpg', 'jpeg', 'png', 'webp']: 
                    img_files.append(os.path.join(folder_path, file))
                    
            raw_title = folder_name
            if txt_path and os.path.exists(txt_path):
                try:
                    with open(txt_path, 'r', encoding='utf-8') as tf:
                        raw_title = tf.read().strip()
                except Exception: pass

            if not img_files:
                print(f"No images found inside folder '{folder_name}', skipping...")
                continue
                
            print(f"\n========== Process started: {folder_name} ==========")

            # 🌟 অডিও না থাকলে AI স্ক্রিপ্ট (Qwen3.5) ও ভয়েসওভার তৈরি
            if not audio_file:
                print("No audio found in folder. Generating AI Voiceover script & Audio...")
                voiceover_script = generate_voiceover_script_with_ollama(raw_title, img_files)
                gen_audio_path = os.path.join(folder_path, "voiceover.mp3")
                generate_voiceover_audio_pipeline(voiceover_script, gen_audio_path)
                audio_path = gen_audio_path
            else:
                audio_path = os.path.join(folder_path, audio_file)

            thumbnail_path = os.path.join(TMP_DIR, "thumbnail.jpg")
            if os.path.exists(thumbnail_path): os.remove(thumbnail_path)
            
            out_video_file = os.path.join(TMP_DIR, "final_out.mp4")
            if os.path.exists(out_video_file): os.remove(out_video_file)

            # AI থাম্বনেইল তৈরি এবং হাই-CTR অপ্টিমাইজড টাইটেল নেওয়া
            opt_title = generate_dynamic_thumbnail(raw_title, thumbnail_path)
            video_title = opt_title if opt_title else raw_title
            video_imgs = img_files

            # ------------------ [১ম কাজ: ১৬:৯ ল্যান্ডস্কেপ ভিডিও (YouTube)] ------------------
            print("Rendering 16:9 Landscape slideshow for YouTube upload...")
            audio_clip_yt = AudioFileClip(audio_path)
            per_img_duration = audio_clip_yt.duration / len(video_imgs)

            yt_clips = [make_video_frame(v, per_img_duration, target_w=1920, target_h=1080) for v in video_imgs]
            youtube_video = concatenate_videoclips(yt_clips).set_audio(audio_clip_yt)
            youtube_video = apply_front_overlay(youtube_video, target_w=1920, target_h=1080)
            
            youtube_video.write_videofile(
                out_video_file, fps=30, codec="libx264", 
                audio_codec="aac", threads=4, preset="ultrafast",
                ffmpeg_params=["-g", "60", "-keyint_min", "60", "-sc_threshold", "0", "-pix_fmt", "yuv420p"],
                logger=None
            )
            
            # ভিডিও ১ ঘণ্টা পর পর শিডিউল করে আপলোড
            upload_success = upload_to_youtube(
                yt, out_video_file, video_title, 
                thumbnail_path if os.path.exists(thumbnail_path) else None,
                config_data=config_data,
                schedule_upload=True
            )
            
            youtube_video.close()
            audio_clip_yt.close()
            for c in yt_clips: c.close()
            
            # ------------------ [২য় কাজ: ৯:১৬ পোর্ট্রেট ভিডিও (JobLive)] ------------------
            if upload_success:
                try:
                    if not os.path.exists(LIVESTREAM_DIR):
                        os.makedirs(LIVESTREAM_DIR, exist_ok=True)
                        
                    safe_video_title = clean_filename(video_title)
                    live_video_file = os.path.join(LIVESTREAM_DIR, f"{safe_video_title}.mp4")
                    
                    print(f"Rendering 9:16 Vertical slideshow for JobLive: {live_video_file}")
                    audio_clip_live = AudioFileClip(audio_path)
                    
                    live_clips = [make_video_frame(v, audio_clip_live.duration / len(video_imgs), target_w=1080, target_h=1920) for v in video_imgs]
                    live_video = concatenate_videoclips(live_clips).set_audio(audio_clip_live)
                    live_video = apply_front_overlay(live_video, target_w=1080, target_h=1920)
                    
                    live_video.write_videofile(
                        live_video_file, fps=30, codec="libx264", 
                        audio_codec="aac", threads=4, preset="ultrafast",
                        ffmpeg_params=["-g", "60", "-keyint_min", "60", "-sc_threshold", "0", "-pix_fmt", "yuv420p"],
                        logger=None
                    )
                    
                    live_video.close()
                    audio_clip_live.close()
                    for c in live_clips: c.close()
                except Exception as live_err:
                    print(f"⚠️ JobLive generation warning: {live_err}")

                print(f"🗑️ Deleting completed local folder: {folder_path}")
                shutil.rmtree(folder_path, ignore_errors=True)
                print(f"✅ Folder '{folder_name}' successfully processed and removed.\n")
            else:
                print("❌ YouTube upload failed! Skipping deletion to prevent data loss.")

        except Exception as folder_error:
            print(f"\n❌ Error occurred while processing folder '{folder_name}': {folder_error}")
            traceback.print_exc()

# ==================== [ 4. DEDICATED SHORTS LOADER ] ====================
def process_shorts_folder(yt):
    print("\nScanning for pre-made Shorts in 'Shorts' folder...")
    shorts_dir = None
    if os.path.exists(WORKSPACE_DIR):
        for f in os.listdir(WORKSPACE_DIR):
            if f.lower() == "shorts" and os.path.isdir(os.path.join(WORKSPACE_DIR, f)):
                shorts_dir = os.path.join(WORKSPACE_DIR, f)
                break
                
    if not shorts_dir: return
        
    config_data = {}
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except Exception: pass

    keep_file = os.path.join(shorts_dir, ".keep")
    if not os.path.exists(keep_file):
        try:
            with open(keep_file, 'w') as kf:
                kf.write("keep")
        except Exception: pass
                
    for file in os.listdir(shorts_dir):
        if file == ".keep": continue
            
        file_path = os.path.join(shorts_dir, file)
        if os.path.isdir(file_path): continue 
        
        ext = file.lower().split('.')[-1]
        if ext in ['mp4', 'mov', 'mkv', 'avi']:
            video_title = os.path.splitext(file)[0]
            print(f"\n========== Processing Short Video: {video_title} ==========")
            
            upload_success = upload_to_youtube(
                yt, file_path, video_title, thumbnail_path=None, 
                config_data=config_data, schedule_upload=True
            )
            
            if upload_success:
                print(f"Deleting uploaded Short locally: {file}")
                try: os.remove(file_path)
                except Exception as r_e: print("File delete error:", r_e)

# ==================== [ 5. YOUTUBE API (SCHEDULED UPLOAD) ] ====================
def upload_to_youtube(yt, video_file, title, thumbnail_path, config_data=None, schedule_upload=True):
    print(f"Now Uploading: '{title}'")
    try:
        final_description = get_video_description(title, config_data)
        final_tags = get_video_tags(config_data)
        
        status_dict = {}
        if schedule_upload:
            schedule_iso = get_next_schedule_time_iso()
            print(f"⏰ Scheduling video for 1-hour interval release: {schedule_iso}")
            status_dict = {
                'privacyStatus': 'private',
                'publishAt': schedule_iso
            }
        else:
            status_dict = {'privacyStatus': 'public'}

        body = {
            'snippet': { 
                'title': title[:100], 
                'description': final_description, 
                'tags': final_tags
            },
            'status': status_dict 
        }
        media_vid = MediaFileUpload(video_file, chunksize=1024*1024, resumable=True)
        res = yt.videos().insert(part="snippet,status", body=body, media_body=media_vid).execute()
        video_id = res['id']
        print(f"» Successfully Uploaded & Scheduled! Video Link: https://youtu.be/{video_id}")
        
        if thumbnail_path and os.path.exists(thumbnail_path):
            try: 
                media_thmb = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
                yt.thumbnails().set(videoId=video_id, media_body=media_thmb).execute()
                print("» Attached perfect Custom Thumbnail!")
            except Exception as e: 
                print(f"\n⚠️ Custom Thumbnail Add Failed: {e}\n")
        return True
    except Exception as e:
        print("\n❌ Upload failed! Error:", e)
        return False

if __name__ == "__main__":
    print("\n====== [ Google Drive Bot Active | AI Script & Schedule System ] ======\n")
    try:
        yt_service = get_youtube_service()
        
        try:
            check_new_articles_and_prepare_folders()
        except Exception as rss_err:
            print("⚠️ RSS check warning:", rss_err)
            traceback.print_exc()

        try:
            process_ready_videos(yt_service)
        except Exception as vid_err:
            print("⚠️ Video processing warning:", vid_err)
            traceback.print_exc()

        try:
            process_shorts_folder(yt_service)
        except Exception as sh_err:
            print("⚠️ Shorts processing warning:", sh_err)
            traceback.print_exc()

    except Exception as critical:
        print("\nFATAL ERROR DETECTED: ", critical)
        traceback.print_exc()
    finally:
        if os.path.exists(TMP_DIR): shutil.rmtree(TMP_DIR, ignore_errors=True)
        print("\nAll Tasks Finalized Perfectly.\n======================================")
