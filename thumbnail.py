# -*- coding: utf-8 -*-
import os, requests
from PIL import Image, ImageDraw, ImageFont
from ai_service import strip_unwanted_chars

FONT_PATH = "BengaliFont.ttf"

def ensure_bengali_font():
    fonts_dir = "Fonts"
    if not os.path.exists(fonts_dir): os.makedirs(fonts_dir, exist_ok=True)
    urls = {
        "HindSiliguri-Bold.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/hindsiliguri/HindSiliguri-Bold.ttf",
        "Kalpurush.ttf": "https://raw.githubusercontent.com/maateen/kalpurush/master/Kalpurush.ttf"
    }
    for fname, url in urls.items():
        out_p = os.path.join(fonts_dir, fname)
        if not os.path.exists(out_p):
            try:
                r = requests.get(url, timeout=12)
                if r.status_code == 200:
                    with open(out_p, "wb") as f: f.write(r.content)
            except Exception: pass

def get_best_font():
    ensure_bengali_font()
    fonts_dir = "Fonts"
    if os.path.exists(fonts_dir):
        for f in os.listdir(fonts_dir):
            if "hindsiliguri" in f.lower() or "kalpurush" in f.lower():
                return os.path.join(fonts_dir, f)
    return FONT_PATH if os.path.exists(FONT_PATH) else None

def get_fitted_font(text, max_w, max_h, start_size=220, min_size=60):
    font_file = get_best_font()
    if not font_file:
        return ImageFont.load_default(), start_size
    for fs in range(start_size, min_size, -4):
        try:
            f = ImageFont.truetype(font_file, fs)
            bbox = f.getbbox(text)
            if (bbox[2] - bbox[0]) <= max_w and (bbox[3] - bbox[1]) <= max_h:
                return f, fs
        except Exception: pass
    try: return ImageFont.truetype(font_file, min_size), min_size
    except Exception: return ImageFont.load_default(), min_size

def generate_dynamic_thumbnail(title, output_path, thumb_meta=None):
    """
    🌟 Ollama-এর দেওয়া ইউনিক টেক্সট দিয়ে কোনো '✪' ছাড়া রেফারেন্সের মতো বিশালাকার ও গ্যাপবিহীন থাম্বনেইল তৈরি করে
    """
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), "#ffffff")
    draw = ImageDraw.Draw(img)

    if not thumb_meta:
        thumb_meta = {}

    top_text = strip_unwanted_chars(thumb_meta.get("top_text", "সরকারি চাকরি"))
    row1_text = strip_unwanted_chars(thumb_meta.get("row1_text", "জরুরি নিয়োগ"))
    row2_text = strip_unwanted_chars(thumb_meta.get("row2_text", "(SSC পাশ/৬৪ জেলা)"))
    bot_text = strip_unwanted_chars(thumb_meta.get("bot_text", "নিয়োগ ২০২৬"))

    # 🌟 ১. টপ বার (0 to 220px) — কোনো ✪ প্রতীক ছাড়া
    green_bg = "#005a1e"
    draw.rectangle([0, 0, W, 220], fill=green_bg)
    
    gov_logo_path = os.path.join("Photos", "Govbd.png")
    if os.path.exists(gov_logo_path):
        try:
            gov_logo = Image.open(gov_logo_path).convert("RGBA").resize((165, 165), Image.LANCZOS)
            img.paste(gov_logo, (35, 27), gov_logo)
            img.paste(gov_logo, (W - 200, 27), gov_logo)
        except Exception: pass

    f_top, _ = get_fitted_font(top_text, max_w=W - 440, max_h=160, start_size=130, min_size=70)
    draw.text((W // 2, 110), top_text, fill="#ffffff", font=f_top, anchor="mm")

    # 🌟 ২. মিডল সেকশন (220 to 860px, উচ্চতা = 640px)
    # লাইন-১ (লাল) এবং লাইন-২ (কালো) টাইট স্পেসিংয়ে মাঝখানে সেন্টারিং
    draw.rectangle([0, 220, W, 860], fill="#ffffff")

    f_l1, _ = get_fitted_font(row1_text, max_w=W - 120, max_h=270, start_size=220, min_size=80)
    f_l2, _ = get_fitted_font(row2_text, max_w=W - 120, max_h=230, start_size=190, min_size=70)

    bb1 = f_l1.getbbox(row1_text)
    h1 = bb1[3] - bb1[1]
    bb2 = f_l2.getbbox(row2_text)
    h2 = bb2[3] - bb2[1]

    line_spacing = 25  # টাইট স্পেসিং (কোনো গ্যাপ থাকবে না)
    total_content_height = h1 + line_spacing + h2
    
    middle_center_y = 220 + (640 // 2)  # 540
    start_y = middle_center_y - (total_content_height // 2)

    # লাইন ১: উজ্জ্বল লাল টেক্সট
    draw.text((W // 2, start_y + (h1 // 2)), row1_text, fill="#d60000", font=f_l1, anchor="mm")

    # লাইন ২: গাঢ় কালো টেক্সট
    draw.text((W // 2, start_y + h1 + line_spacing + (h2 // 2)), row2_text, fill="#000000", font=f_l2, anchor="mm")

    # 🌟 ৩. বটম বার (860 to 1080px)
    draw.rectangle([0, 860, W, H], fill=green_bg)
    f_bot, _ = get_fitted_font(bot_text, max_w=W - 100, max_h=160, start_size=135, min_size=70)
    draw.text((W // 2, 970), bot_text, fill="#ffe600", font=f_bot, anchor="mm")

    # বর্ডার সেপারেটর
    draw.line([(0, 220), (W, 220)], fill="#003d14", width=5)
    draw.line([(0, 860), (W, 860)], fill="#003d14", width=5)

    img.save(output_path, "JPEG", quality=100, subsampling=0)
    print(f"Generated Ultra-HD Dynamic Thumbnail: '{row1_text} | {row2_text}' for {title}")
