# -*- coding: utf-8 -*-
import os, json, time, re, shutil, random
import requests, feedparser
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import numpy as np

try:
    from fontTools.ttLib import TTFont
    HAS_FONTTOOLS = True
except ImportError:
    HAS_FONTTOOLS = False

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from moviepy.editor import AudioFileClip, VideoClip, concatenate_videoclips, ImageClip, CompositeVideoClip

WORKSPACE_DIR = "workspace"      # Rclone Sync Location
LIVESTREAM_DIR = "workspace_live" # JobLive folder source
TMP_DIR = "temp_assets"          # Temp Files processing
FONT_PATH = "BengaliFont.ttf"    # Auto downloaded fallback Bengali Font

# 🌟 চটকদার হাই-কনট্রাস্ট কালার প্যালেট
COLOR_THEMES = [
    {
        'top_bot_bg': '#000839', 'top_bot_fg': '#ffffff',
        'row1_bg': '#ffea00', 'row1_fg': '#000000',
        'row2_bg': '#dc2626', 'row2_fg': '#ffffff',
        'row3_bg': '#ffea00', 'row3_fg': '#000000'
    },
    {
        'top_bot_bg': '#013a1a', 'top_bot_fg': '#ffffff',
        'row1_bg': '#ffffff', 'row1_fg': '#013a1a',
        'row2_bg': '#dc2626', 'row2_fg': '#ffea00',
        'row3_bg': '#ffea00', 'row3_fg': '#000000'
    },
    {
        'top_bot_bg': '#4a000d', 'top_bot_fg': '#ffffff',
        'row1_bg': '#00e5ff', 'row1_fg': '#000000',
        'row2_bg': '#ff0000', 'row2_fg': '#ffffff',
        'row3_bg': '#ffea00', 'row3_fg': '#000000'
    },
    {
        'top_bot_bg': '#1e1035', 'top_bot_fg': '#ffffff',
        'row1_bg': '#ffea00', 'row1_fg': '#000000',
        'row2_bg': '#ea580c', 'row2_fg': '#ffffff',
        'row3_bg': '#ffffff', 'row3_fg': '#000000'
    },
    {
        'top_bot_bg': '#0f172a', 'top_bot_fg': '#ffffff',
        'row1_bg': '#00ff66', 'row1_fg': '#000000',
        'row2_bg': '#dc2626', 'row2_fg': '#ffffff',
        'row3_bg': '#ffea00', 'row3_fg': '#000000'
    }
]

# 🌟 Photos/ ফোল্ডারের লোগো ম্যাচিং টেবিল
LOGO_MAPPING = {
    'পল্লী বিদ্যুৎ': 'PalliBidyut.png',
    'বিদ্যুৎ': 'PalliBidyut.png',
    'সেনাবাহিনী': 'Army.png',
    'নৌবাহিনী': 'Navy.png',
    'বিমান বাহিনী': 'AirForce.png',
    'বর্ডার গার্ড': 'BGB.png',
    'বিজিবি': 'BGB.png',
    'পুলিশ': 'Police.png',
    'আনসার': 'Ansar.png',
    'কোস্ট গার্ড': 'CoastGuard.png',
    'র‍্যাব': 'RAB.png',
    'ফায়ার সার্ভিস': 'FireService.png',
    'রেলওয়ে': 'Railway.png',
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

# ==================== [ 🌟 ১০০% ভেরিফাইড ইউনিকোড বাংলা ফন্ট ইঞ্জিন ] ====================
def is_valid_bengali_unicode_font(font_path):
    """যাচাই করে ফন্টটিতে আসলেই বাংলা ইউনিকোড গ্লিফ আছে কি না (ANSI ও বক্স গ্লিফ বাদ দেয়)"""
    try:
        if not os.path.exists(font_path):
            return False
            
        fname = os.path.basename(font_path).lower()
        # ANSI, Bijoy এবং Variable ফন্ট সরাসরি বাদ দেওয়া
        if any(bad in fname for bad in ['ansi', 'sutonny', 'mj', 'bijoy', 'durbar', '-vf', 'variable']):
            return False
            
        if HAS_FONTTOOLS:
            try:
                tt = TTFont(font_path)
                # বাংলা অক্ষরের কোড পয়েন্ট চেক: অ (0x0985), ক (0x0995), ব (0x09AC), া (0x09BE), ল (0x09B2)
                bengali_chars = [0x0985, 0x0995, 0x09AC, 0x09BE, 0x09B2]
                for table in tt['cmap'].tables:
                    if table.isUnicode():
                        matches = sum(1 for c in bengali_chars if c in table.cmap and table.cmap[c] != '.notdef')
                        if matches >= 4:
                            return True
                return False
            except Exception:
                pass
                
        # ফন্টটুলস না থাকলে সাধারণ যাচাই
        if any(good in fname for good in ['kalpurush', 'unicode', 'noto', 'siliguri', 'solaiman', 'bangla', 'bengali']):
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
        print("ভেরিফাইড ইউনিকোড বাংলা ফন্ট ডাউনলোড করা হচ্ছে...")
        urls = {
            "Kalpurush.ttf": "https://raw.githubusercontent.com/maateen/kalpurush/master/Kalpurush.ttf",
            "NotoSansBengali-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/notosansbengali/NotoSansBengali%5Bwdth%2Cwght%5D.ttf",
            "HindSiliguri-Bold.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/hindsiliguri/HindSiliguri-Bold.ttf"
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

def get_best_font():
    """একই থাম্বনেইলের সব লেখার জন্য একটি শতভাগ ভ্যালিড ইউনিকোড ফন্ট রিটার্ন করে"""
    ensure_bengali_font()
    fonts_dir = "Fonts"
    valid_fonts = []
    
    if os.path.exists(fonts_dir):
        for f in os.listdir(fonts_dir):
            if f.lower().endswith(('.ttf', '.otf')):
                full_p = os.path.join(fonts_dir, f)
                if is_valid_bengali_unicode_font(full_p):
                    valid_fonts.append(full_p)

    if valid_fonts:
        # বোল্ড এবং ক্লিয়ার ফন্টগুলোকে অগ্রাধিকার দেওয়া
        bold_fonts = [f for f in valid_fonts if any(k in os.path.basename(f).lower() for k in ['bold', 'shorif', 'kalpurush', 'siliguri', 'noto'])]
        return random.choice(bold_fonts) if bold_fonts else random.choice(valid_fonts)

    return FONT_PATH if os.path.exists(FONT_PATH) else None

def get_logo_for_title(title):
    t = title.strip()
    for kw, img_name in LOGO_MAPPING.items():
        if kw in t:
            path = os.path.join("Photos", img_name)
            if os.path.exists(path):
                return path
    default_path = os.path.join("Photos", "Govbd.png")
    return default_path if os.path.exists(default_path) else None

# ==================== [ 🌟 SMART UNIQUE TITLE PARSER ] ====================
def parse_title_for_thumbnail(title):
    clean_title = title.split('|')[0].split('||')[0].strip()
    words = clean_title.split()
    
    # 1. Top Text: Institutions / Organization name extraction
    top_text = ""
    if "নিয়োগ" in clean_title:
        before_niyog = clean_title.split("নিয়োগ")[0].strip()
        if "পদে" in before_niyog:
            try: before_niyog = before_niyog.split("পদে")[1].strip()
            except: pass
        if len(before_niyog) > 2:
            top_text = before_niyog
    
    if not top_text:
        top_text = " ".join(words[:min(3, len(words))]) if words else "সরকারি চাকরি নিয়োগ"
        
    if not any(top_text.endswith(w) for w in ["নিয়োগ", "বোর্ড", "অধিদপ্তর", "কার্যালয়", "বিশ্ববিদ্যালয়", "কর্তৃপক্ষ", "প্রোগ্রাম", "ব্যাংক", "সমিতি"]):
        top_text += " নিয়োগ"

    # 2. Row 1 Text
    if "বিশ্ববিদ্যালয়" in title or "University" in title:
        row1_text = "বিশ্ববিদ্যালয়ে চাকরি"
    elif "মেডিকেল" in title or "হাসপাতাল" in title:
        row1_text = "হাসপাতালে চাকরি"
    elif "স্কিলস" in title or "SICIP" in title:
        row1_text = "বিশেষ প্রজেক্টে নিয়োগ"
    elif "অফিস সহায়ক" in title:
        row1_text = "অফিস সহায়ক পদে"
    elif "ব্যাংক" in title or "Bank" in title:
        row1_text = "ব্যাংক খাতে চাকরি"
    elif "এনজিও" in title or "NGO" in title:
        row1_text = "এনজিও খাতে চাকরি"
    else:
        row1_text = "সরকারি চাকরি"

    # 3. Row 2 Text (Big Red Highlight)
    vac_match = re.search(r'(\d+|[০-৯]+)\s*পদে', title)
    if vac_match:
        row2_text = f"{vac_match.group(0)}"
    elif "এডমিট" in title or "কার্ড" in title:
        row2_text = "এডমিট কার্ড প্রকাশ"
    elif "ফলাফল" in title or "রেজাল্ট" in title:
        row2_text = "চূড়ান্ত ফলাফল প্রকাশ"
    elif "অফিসার" in title or "ক্যাডেট" in title:
        row2_text = "অফিসার পদে সুযোগ"
    else:
        hooks = ["জরুরি নিয়োগ ২০২৬", "বিশাল নিয়োগ বিজ্ঞপ্তি", "বড় নিয়োগ প্রকাশ", "নতুন সার্কুলার ২০২৬"]
        row2_text = hooks[abs(hash(title)) % len(hooks)]

    # 4. Row 3 Text
    if "SSC" in title or "এসএসসি" in title or "এইচএসসি" in title or "HSC" in title or "৮ম" in title:
        row3_text = "৮ম/SSC/HSC পাশে আবেদন"
    elif "ডিগ্রী" in title or "অনার্স" in title or "বিএসসি" in title:
        row3_text = "ডিগ্রী/অনার্স পাশে আবেদন"
    else:
        elig_options = ["ছেলে/মেয়ে/৬৪ জেলা", "৬৪ জেলা থেকে আবেদনযোগ্য", "সকল জেলার জন্য প্রযোজ্য", "নারী ও পুরুষ আবেদনযোগ্য"]
        row3_text = elig_options[abs(hash(title)) % len(elig_options)]

    # 5. Bottom Text
    bot_options = ["আবেদনের সময় ও নিয়ম দেখুন", "বিজ্ঞপ্তি প্রকাশ ২০২৬", "আজই আবেদন সম্পন্ন করুন", "বিস্তারিত দেখে আবেদন করুন"]
    bot_text = bot_options[abs(hash(title)) % len(bot_options)]

    return top_text, row1_text, row2_text, row3_text, bot_text

# ==================== [ 🌟 ডায়নামিক বড় ও বোল্ড টেক্সট রেন্ডারার ] ====================
def draw_auto_sized_text(draw, text, box, font_path, text_color, max_font_size=115, min_font_size=40):
    x1, y1, x2, y2 = box
    w_box = x2 - x1
    h_box = y2 - y1
    cx = x1 + w_box / 2
    cy = y1 + h_box / 2
    
    pad_x = 40
    pad_y = 20
    avail_w = w_box - pad_x * 2
    avail_h = h_box - pad_y * 2
    
    if not font_path or not os.path.exists(font_path):
        draw.text((cx, cy), text, fill=text_color, anchor="mm")
        return
        
    words = text.split()
    best_font_size = None
    best_lines = [text]
    
    # প্রথমে ১ লাইনে বড় ফন্টে ট্রাই করা
    for fs in range(max_font_size, int(max_font_size * 0.70), -2):
        f = ImageFont.truetype(font_path, fs)
        bbox = f.getbbox(text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        if tw <= avail_w and th <= avail_h:
            best_font_size = fs
            best_lines = [text]
            break
            
    # ১ লাইনে না ধরলে ব্যালান্সড ২ লাইনে ট্রাই করা (যাতে লেখা সবসময় বড় সাইজে থাকে)
    if best_font_size is None and len(words) >= 2:
        splits = []
        for i in range(1, len(words)):
            splits.append((" ".join(words[:i]), " ".join(words[i:])))
            
        for fs in range(max_font_size, min_font_size, -2):
            f = ImageFont.truetype(font_path, fs)
            found = False
            for l1, l2 in splits:
                bb1, bb2 = f.getbbox(l1), f.getbbox(l2)
                w1, w2 = bb1[2] - bb1[0], bb2[2] - bb2[0]
                h1, h2 = bb1[3] - bb1[1], bb2[3] - bb2[1]
                total_h = h1 + h2 + fs * 0.20
                if max(w1, w2) <= avail_w and total_h <= avail_h:
                    best_font_size = fs
                    best_lines = [l1, l2]
                    found = True
                    break
            if found:
                break
                
    if best_font_size is None:
        best_font_size = min_font_size
        best_lines = [text]
        
    font = ImageFont.truetype(font_path, best_font_size)
    full_text = "\n".join(best_lines)
    
    # আল্ট্রা-শার্প সেন্টারিং
    draw.multiline_text(
        (cx, cy), full_text, fill=text_color, font=font,
        anchor="mm", align="center", spacing=int(best_font_size * 0.15)
    )

# ==================== [ 🌟 FULL HD 1080P ডায়নামিক থাম্বনেইল জেনারেটর ] ====================
def generate_dynamic_thumbnail(title, output_path):
    print(f"Generating Ultra-HD 1080p Thumbnail for: {title}")
    
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), "#ffffff")
    draw = ImageDraw.Draw(img)

    theme_index = abs(hash(title)) % len(COLOR_THEMES)
    theme = COLOR_THEMES[theme_index]
    
    # এই থাম্বনেইলের সব লেখার জন্য একটি একক ইউনিকোড ফন্ট সিলেক্ট করা
    font_path = get_best_font()

    top_text, row1_text, row2_text, row3_text, bot_text = parse_title_for_thumbnail(title)

    # ১. টপ বার (Y: 0..180)
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

    draw_auto_sized_text(draw, top_text, (180, 0, W - 180, 180), font_path, theme['top_bot_fg'], max_font_size=85, min_font_size=40)

    # ২. বটম বার (Y: 900..1080)
    draw.rectangle([0, 900, W, H], fill=theme['top_bot_bg'])
    draw_auto_sized_text(draw, bot_text, (50, 900, W - 50, 1080), font_path, theme['top_bot_fg'], max_font_size=80, min_font_size=40)

    # ৩. ডানপাশের লোগো কার্ড (X: 1320..1920, Y: 180..900)
    draw.rectangle([1320, 180, W, 900], fill="#ffffff")
    logo_path = get_logo_for_title(title)
    if logo_path and os.path.exists(logo_path):
        try:
            org_logo = Image.open(logo_path).convert("RGBA")
            scale = min(500 / org_logo.width, 500 / org_logo.height)
            new_lw = int(org_logo.width * scale)
            new_lh = int(org_logo.height * scale)
            org_logo = org_logo.resize((new_lw, new_lh), Image.LANCZOS)
            
            lx = 1320 + (600 - new_lw) // 2
            ly = 180 + (720 - new_lh) // 2
            img.paste(org_logo, (lx, ly), org_logo)
        except Exception as e:
            print(f"Error pasting org logo ({logo_path}): {e}")

    # ৪. বামপাশের ৩টি টেক্সট রো (X: 0..1320, Y: 180..900)
    # Row 1 (ক্যাটাগরি)
    draw.rectangle([0, 180, 1320, 420], fill=theme['row1_bg'])
    draw_auto_sized_text(draw, row1_text, (0, 180, 1320, 420), font_path, theme['row1_fg'], max_font_size=110, min_font_size=45)

    # Row 2 (মেইন হাইলাইট - লাল ব্যাকগ্রাউন্ড ও সবচেয়ে বড় লেখা)
    draw.rectangle([0, 420, 1320, 660], fill=theme['row2_bg'])
    draw_auto_sized_text(draw, row2_text, (0, 420, 1320, 660), font_path, theme['row2_fg'], max_font_size=130, min_font_size=55)

    # Row 3 (যোগ্যতা / জেলা)
    draw.rectangle([0, 660, 1320, 900], fill=theme['row3_bg'])
    draw_auto_sized_text(draw, row3_text, (0, 660, 1320, 900), font_path, theme['row3_fg'], max_font_size=100, min_font_size=40)

    # ৫. হাই-ডেফিনিশন বর্ডার সেপারেটর
    draw.line([(0, 180), (W, 180)], fill="#ffffff", width=4)
    draw.line([(0, 900), (W, 900)], fill="#ffffff", width=4)
    draw.line([(1320, 180), (1320, 900)], fill="#e2e8f0", width=4)
    draw.line([(0, 420), (1320, 420)], fill="#ffffff", width=3)
    draw.line([(0, 660), (1320, 660)], fill="#ffffff", width=3)

    # আল্ট্রা-শার্প কোয়ালিটিতে সেভ করা
    img.save(output_path, "JPEG", quality=98, subsampling=0)
    print(f"Generated 1080p Dynamic Thumbnail successfully for: {title}")

# ==================== [ 1. FEED PARSING ] ====================
def check_new_articles_and_prepare_folders():
    print("Checking for new RSS items (Last 24 Hours)...")
    if not os.path.exists(WORKSPACE_DIR): os.makedirs(WORKSPACE_DIR)

    if not os.path.exists('config.json'):
        print("config.json not found!")
        return

    with open('config.json', 'r', encoding='utf-8') as f:
        rss_links = json.load(f).get('rss_links', [])

    time_limit = datetime.now() - timedelta(hours=24)
    existing_folders = [f for f in os.listdir(WORKSPACE_DIR) if os.path.isdir(os.path.join(WORKSPACE_DIR, f))]
    
    history_file = os.path.join(WORKSPACE_DIR, "history.txt")
    history_logs = []
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as hf:
            history_logs = f.read().splitlines()

    for feed_url in rss_links:
        print(f"Parsing Feed: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
        except: continue
        
        for entry in feed.entries:
            try: published_time = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            except: continue

            if published_time >= time_limit:
                folder_title = clean_filename(entry.title).strip()
                if folder_title.lower() == "shorts":
                    continue
                if not folder_title or folder_title in existing_folders or folder_title in history_logs: 
                    continue 

                print(f"New Article Found: {folder_title}. Generating folder...")
                folder_path = os.path.join(WORKSPACE_DIR, folder_title)
                os.makedirs(folder_path, exist_ok=True)
                existing_folders.append(folder_title)
                
                history_logs.append(folder_title)
                with open(history_file, 'a', encoding='utf-8') as hf:
                    hf.write(f"{folder_title}\n")

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
            if new_h < target_h:
                new_h = target_h
                
            resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
            img_np = np.array(resized)
            
            def make_frame(t):
                progress = t / duration if duration > 0 else 0
                y = int(progress * (new_h - target_h)) if (new_h - target_h) > 0 else 0 
                x = 0
                return img_np[y:y+target_h, x:x+target_w]
            
            return VideoClip(make_frame, duration=duration)
            
        elif (9.0 / 16.0) - 0.01 <= ratio < (16.0 / 9.0) - 0.01:
            scale_w = target_w / w
            scale_h = target_h / h
            scale = min(scale_w, scale_h)
            
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
            
            canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
            offset_x = (target_w - new_w) // 2
            offset_y = (target_h - new_h) // 2
            canvas.paste(resized, (offset_x, offset_y))
            
            img_np = np.array(canvas)
            return VideoClip(lambda t: img_np, duration=duration)
            
        else:
            new_h = target_h
            new_w = int((target_h / h) * w)
            if new_w < target_w:
                new_w = target_w
                
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

# ==================== [ FRONT OVERLAY ENGINE ] ====================
def apply_front_overlay(main_clip, target_w, target_h):
    front_path = "front.png"
    if os.path.exists(front_path):
        try:
            pil_front = Image.open(front_path).convert("RGBA")
            scaled_w = int(target_w * 0.40)
            scaled_h = int((scaled_w / pil_front.width) * pil_front.height)
            pil_front_resized = pil_front.resize((scaled_w, scaled_h), Image.LANCZOS)
            
            front_np = np.array(pil_front_resized)
            rgb_np = front_np[:, :, :3]
            alpha_np = front_np[:, :, 3] / 255.0 
            
            front_clip = ImageClip(rgb_np).set_duration(main_clip.duration)
            mask_clip = ImageClip(alpha_np, ismask=True).set_duration(main_clip.duration)
            front_clip = front_clip.set_mask(mask_clip)
            
            margin = int(target_h * 0.05)
            y_pos = target_h - scaled_h - margin
            front_clip = front_clip.set_position(("center", y_pos))
            
            main_clip = CompositeVideoClip([main_clip, front_clip]).set_audio(main_clip.audio)
        except Exception as e:
            print(f"Error applying front.png: {e}")
    return main_clip

# ==================== [ 3. MOVIEPY PROCESS & DRIVE CLEANUP ] ====================
def process_ready_videos(yt):
    print("\nScanning Drive folders for Audios...")
    if not os.path.exists(WORKSPACE_DIR): return
    if not os.path.exists(TMP_DIR): os.makedirs(TMP_DIR, exist_ok=True)
    
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
                    
            if not audio_file: 
                continue
                
            print(f"\n========== Process started: {folder_name} ==========")
            audio_path = os.path.join(folder_path, audio_file)
            
            video_title = folder_name
            if txt_path and os.path.exists(txt_path):
                with open(txt_path, 'r', encoding='utf-8') as tf:
                    video_title = tf.read().strip()

            if not img_files:
                print("No images found inside folder, skipping...")
                continue
                
            thumbnail_path = os.path.join(TMP_DIR, "thumbnail.jpg")
            if os.path.exists(thumbnail_path): os.remove(thumbnail_path)
            
            out_video_file = os.path.join(TMP_DIR, "final_out.mp4")
            if os.path.exists(out_video_file): os.remove(out_video_file)

            # 🌟 ডায়নামিক থাম্বনেইল তৈরি
            generate_dynamic_thumbnail(video_title, thumbnail_path)
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
            
            # ভিডিও আপলোড করা
            upload_success = upload_to_youtube(
                yt, out_video_file, video_title, 
                thumbnail_path if os.path.exists(thumbnail_path) else None
            )
            
            # মেমরি এবং ফাইল হ্যান্ডেল রিলিজ করা
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

                # 🌟 প্রসেস হওয়া ফোল্ডারটি লোকালি ডিলিট করা (যা পরবর্তীতে rclone গুগল ড্রাইভ থেকে ডিলিট করবে)
                print(f"🗑️ Deleting completed local folder: {folder_path}")
                shutil.rmtree(folder_path, ignore_errors=True)
                print(f"✅ Folder '{folder_name}' successfully queued for Google Drive deletion.\n")
            else:
                print("❌ YouTube upload failed! Skipping deletion to prevent data loss.")

        except Exception as folder_error:
            print(f"\n❌ Error occurred while processing folder '{folder_name}': {folder_error}")

# ==================== [ 4. DEDICATED SHORTS LOADER ] ====================
def process_shorts_folder(yt):
    print("\nScanning for pre-made Shorts in 'Shorts' folder...")
    shorts_dir = None
    if os.path.exists(WORKSPACE_DIR):
        for f in os.listdir(WORKSPACE_DIR):
            if f.lower() == "shorts" and os.path.isdir(os.path.join(WORKSPACE_DIR, f)):
                shorts_dir = os.path.join(WORKSPACE_DIR, f)
                break
                
    if not shorts_dir:
        return
        
    keep_file = os.path.join(shorts_dir, ".keep")
    if not os.path.exists(keep_file):
        try:
            with open(keep_file, 'w') as kf:
                kf.write("keep")
        except Exception: pass
                
    for file in os.listdir(shorts_dir):
        if file == ".keep": 
            continue
            
        file_path = os.path.join(shorts_dir, file)
        if os.path.isdir(file_path): continue 
        
        ext = file.lower().split('.')[-1]
        if ext in ['mp4', 'mov', 'mkv', 'avi']:
            video_title = os.path.splitext(file)[0]
            print(f"\n========== Processing Short Video: {video_title} ==========")
            
            upload_success = upload_to_youtube(yt, file_path, video_title, thumbnail_path=None)
            
            if upload_success:
                print(f"Deleting uploaded Short locally: {file}")
                try: os.remove(file_path)
                except Exception as r_e: print("File delete error:", r_e)

# ==================== [ 5. YOUTUBE API ] ====================
def upload_to_youtube(yt, video_file, title, thumbnail_path):
    print(f"Now Uploading: '{title}'")
    try:
        body = {
            'snippet': { 
                'title': title[:100], 
                'description': "", 
                'tags': ['Job Circular BD', 'Today Govt Jobs', 'Niyog Biggopti'] 
            },
            'status': { 'privacyStatus': 'public' } 
        }
        media_vid = MediaFileUpload(video_file, chunksize=1024*1024, resumable=True)
        res = yt.videos().insert(part="snippet,status", body=body, media_body=media_vid).execute()
        video_id = res['id']
        print(f"» Successfully Uploaded! Video Link: https://youtu.be/{video_id}")
        
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
    print("\n====== [ Google Drive Bot Active | Process Start ] ======\n")
    try:
        yt_service = get_youtube_service()
        check_new_articles_and_prepare_folders()
        process_ready_videos(yt_service)
        process_shorts_folder(yt_service) 
    except Exception as critical:
        print("\nFATAL ERROR DETECTED: ", critical)
    finally:
        if os.path.exists(TMP_DIR): shutil.rmtree(TMP_DIR, ignore_errors=True)
        print("\nAll Tasks Finalized Perfectly.\n======================================")
