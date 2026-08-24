# -*- coding: utf-8 -*-
import os, requests
from PIL import Image, ImageDraw, ImageFont
from ai_service import strip_emojis

FONT_PATH = "BengaliFont.ttf"

LOGO_MAPPING = {
    'পল্লী বিদ্যুৎ': 'PalliBidyut.png', 'সেনাবাহিনী': 'Army.png', 'নৌবাহিনী': 'Navy.png',
    'বিমান বাহিনী': 'AirForce.png', 'বর্ডার গার্ড': 'BGB.png', 'বিজিবি': 'BGB.png',
    'পুলিশ': 'Police.png', 'আনসার': 'Ansar.png', 'কোস্ট গার্ড': 'CoastGuard.png',
    'র‍্যাব': 'RAB.png', 'ফায়ার সার্ভিস': 'FireService.png', 'রেলওয়ে': 'Railway.png',
    'বিসিএস': 'BCS.png', 'প্রাথমিক শিক্ষক': 'PrimaryTeacher.png', 'বাংলাদেশ ব্যাংক': 'BangladeshBank.png',
    'ব্যাংক': 'BangladeshBank.png', 'খাদ্য অধিদপ্তর': 'Food.png', 'ডাক বিভাগ': 'PostOffice.png',
    'কারা অধিদপ্তর': 'Jail.png', 'পাসপোর্ট অধিদপ্তর': 'Passport.png', 'পরিবার পরিকল্পনা': 'FamilyPlanning.png'
}

COLOR_THEMES = [
    {'top_bot_bg': '#000839', 'top_bot_fg': '#ffffff', 'row1_bg': '#ffe600', 'row1_fg': '#000000', 'row2_bg': '#dc2626', 'row2_fg': '#ffffff', 'row3_bg': '#ffe600', 'row3_fg': '#000000'},
    {'top_bot_bg': '#013a1a', 'top_bot_fg': '#ffffff', 'row1_bg': '#ffffff', 'row1_fg': '#013a1a', 'row2_bg': '#dc2626', 'row2_fg': '#ffe600', 'row3_bg': '#ffe600', 'row3_fg': '#000000'},
    {'top_bot_bg': '#4a000d', 'top_bot_fg': '#ffffff', 'row1_bg': '#00f0ff', 'row1_fg': '#000000', 'row2_bg': '#dc2626', 'row2_fg': '#ffffff', 'row3_bg': '#ffe600', 'row3_fg': '#000000'}
]

def ensure_bengali_font():
    fonts_dir = "Fonts"
    if not os.path.exists(fonts_dir): os.makedirs(fonts_dir, exist_ok=True)
    if not any(f.lower().endswith(('.ttf', '.otf')) for f in os.listdir(fonts_dir)):
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
                    if r.status_code == 200:
                        with open(out_p, "wb") as f: f.write(r.content)
                except Exception: pass

def get_kalpurush_font():
    ensure_bengali_font()
    fonts_dir = "Fonts"
    if os.path.exists(fonts_dir):
        for f in os.listdir(fonts_dir):
            if "kalpurush" in f.lower(): return os.path.join(fonts_dir, f)
    return FONT_PATH if os.path.exists(FONT_PATH) else None

def get_distinct_fonts(count=4):
    ensure_bengali_font()
    fonts_dir = "Fonts"
    valid = [os.path.join(fonts_dir, f) for f in os.listdir(fonts_dir) if f.lower().endswith(('.ttf', '.otf')) and "kalpurush" not in f.lower()]
    if not valid: return [get_kalpurush_font()] * count
    pool = valid.copy()
    while len(pool) < count: pool.extend(valid)
    return pool[:count]

def get_specific_organization_logo(title):
    for kw, img_name in LOGO_MAPPING.items():
        if kw in title:
            path = os.path.join("Photos", img_name)
            if os.path.exists(path): return path
    return None

def draw_clean_text(draw, text, box, font_path, text_color, max_font_size=160, min_font_size=45):
    text = strip_emojis(text)
    x1, y1, x2, y2 = box
    cx, cy = x1 + (x2 - x1) / 2, y1 + (y2 - y1) / 2
    avail_w, avail_h = (x2 - x1) - 40, (y2 - y1) - 15

    if not font_path or not os.path.exists(font_path):
        draw.text((cx, cy), text, fill=text_color, anchor="mm")
        return

    best_size = min_font_size
    best_lines = [text]

    for fs in range(max_font_size, min_font_size, -3):
        try:
            f = ImageFont.truetype(font_path, fs)
            bbox = f.getbbox(text)
            if (bbox[2] - bbox[0]) <= avail_w and (bbox[3] - bbox[1]) <= avail_h:
                best_size = fs
                best_lines = [text]
                break
        except Exception: pass

    try: font = ImageFont.truetype(font_path, best_size)
    except Exception: font = ImageFont.load_default()
    draw.multiline_text((cx, cy), "\n".join(best_lines), fill=text_color, font=font, anchor="mm", align="center")

def generate_dynamic_thumbnail(title, output_path, thumb_meta=None):
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), "#ffffff")
    draw = ImageDraw.Draw(img)

    f_top, f_row1, f_row2, f_row3 = get_distinct_fonts(4)
    f_bot = get_kalpurush_font()

    if not thumb_meta:
        thumb_meta = {"top_text": "সরকারি চাকরি", "row1_text": "জরুরি নিয়োগ", "row2_text": "সরকারি চাকরি", "row3_text": "(SSC পাশ/৬৪ জেলা)", "bot_text": "(বিশাল পদে) নিয়োগ ২০২৬"}

    top_text = thumb_meta.get("top_text", "সরকারি চাকরি")
    row1_text = thumb_meta.get("row1_text", "জরুরি নিয়োগ")
    row2_text = thumb_meta.get("row2_text", "সরকারি চাকরি")
    row3_text = thumb_meta.get("row3_text", "(SSC পাশ/৬৪ জেলা)")
    bot_text = thumb_meta.get("bot_text", "(বিশাল পদে) নিয়োগ ২০২৬")

    specific_logo = get_specific_organization_logo(title)

    if specific_logo:
        theme = COLOR_THEMES[abs(hash(title)) % len(COLOR_THEMES)]
        draw.rectangle([0, 0, W, 180], fill=theme['top_bot_bg'])
        draw_clean_text(draw, f"✪ {top_text} ✪", (180, 0, W - 180, 180), f_top, theme['top_bot_fg'], max_font_size=95)

        draw.rectangle([0, 900, W, H], fill=theme['top_bot_bg'])
        draw_clean_text(draw, bot_text, (50, 900, W - 50, 1080), f_bot, theme['top_bot_fg'], max_font_size=90)

        draw.rectangle([1320, 180, W, 900], fill="#ffffff")
        try:
            org_logo = Image.open(specific_logo).convert("RGBA")
            scale = min(540 / org_logo.width, 540 / org_logo.height)
            org_logo = org_logo.resize((int(org_logo.width * scale), int(org_logo.height * scale)), Image.LANCZOS)
            img.paste(org_logo, (1320 + (600 - org_logo.width) // 2, 180 + (720 - org_logo.height) // 2), org_logo)
        except Exception: pass

        draw.rectangle([0, 180, 1320, 420], fill=theme['row1_bg'])
        draw_clean_text(draw, row1_text, (20, 180, 1300, 420), f_row1, theme['row1_fg'], max_font_size=130)

        draw.rectangle([0, 420, 1320, 660], fill=theme['row2_bg'])
        draw_clean_text(draw, row2_text, (20, 420, 1300, 660), f_row2, theme['row2_fg'], max_font_size=155)

        draw.rectangle([0, 660, 1320, 900], fill=theme['row3_bg'])
        draw_clean_text(draw, row3_text, (20, 660, 1300, 900), f_row3, theme['row3_fg'], max_font_size=120)

    else:
        # 🌟 গ্যাপবিহীন পারফেক্ট ৩-লেয়ার থাম্বনেইল
        green_bg = "#015a24"
        draw.rectangle([0, 0, W, 210], fill=green_bg)
        
        gov_logo_path = os.path.join("Photos", "Govbd.png")
        if os.path.exists(gov_logo_path):
            try:
                gov_logo = Image.open(gov_logo_path).convert("RGBA").resize((160, 160), Image.LANCZOS)
                img.paste(gov_logo, (40, 25), gov_logo)
                img.paste(gov_logo, (W - 200, 25), gov_logo)
            except Exception: pass

        draw_clean_text(draw, f"✪ {top_text} ✪", (210, 0, W - 210, 210), f_top, "#ffffff", max_font_size=115)

        # মাঝখানের অংশ টাইট ও সমন্বিত
        draw.rectangle([0, 210, W, 870], fill="#ffffff")
        draw_clean_text(draw, row1_text, (50, 240, W - 50, 560), f_row1, "#cc0000", max_font_size=180)
        draw_clean_text(draw, row3_text, (50, 570, W - 50, 850), f_row2, "#0f172a", max_font_size=125)

        draw.rectangle([0, 870, W, H], fill=green_bg)
        draw_clean_text(draw, bot_text, (40, 870, W - 40, 1080), f_bot, "#ffe600", max_font_size=125)

        draw.line([(0, 210), (W, 210)], fill="#003d16", width=5)
        draw.line([(0, 870), (W, 870)], fill="#003d16", width=5)

    img.save(output_path, "JPEG", quality=100, subsampling=0)
    print(f"Generated Dynamic 1080p Thumbnail: {title}")
