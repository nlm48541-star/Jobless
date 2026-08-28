# -*- coding: utf-8 -*-
import os, random, requests
from PIL import Image, ImageDraw, ImageFont
from ai_service import strip_unwanted_chars

FONTS_DIR = "Fonts"

def get_fixed_bar_font():
    """টপ এবং বটম বারের জন্য নির্দিষ্ট ফিক্সড ফন্ট (Kalpurush) রিটার্ন করে"""
    if os.path.exists(FONTS_DIR):
        for f in os.listdir(FONTS_DIR):
            if "kalpurush" in f.lower():
                return os.path.join(FONTS_DIR, f)
        # kalpurush না থাকলে ফোল্ডারের ১ম ফন্টটি নেবে
        all_fonts = [os.path.join(FONTS_DIR, f) for f in os.listdir(FONTS_DIR) if f.lower().endswith(('.ttf', '.otf'))]
        if all_fonts:
            return all_fonts[0]
    return "BengaliFont.ttf" if os.path.exists("BengaliFont.ttf") else None

def get_random_middle_font():
    """মাঝখানের হুকের জন্য ফোল্ডার থেকে র‍্যান্ডমলি যেকোনো একটি বোল্ড/স্টাইলিশ ফন্ট বেছে নেয়"""
    if os.path.exists(FONTS_DIR):
        all_fonts = [
            os.path.join(FONTS_DIR, f) for f in os.listdir(FONTS_DIR) 
            if f.lower().endswith(('.ttf', '.otf'))
        ]
        # মাঝখানের জন্য স্টাইলিশ ফন্টগুলোকে প্রাধান্য দেওয়া (kalpurush বাদে)
        display_fonts = [f for f in all_fonts if "kalpurush" not in os.path.basename(f).lower()]
        
        if display_fonts:
            chosen = random.choice(display_fonts)
            return chosen
        elif all_fonts:
            return random.choice(all_fonts)
            
    return get_fixed_bar_font()

def get_fitted_font(text, max_w, max_h, font_file=None, start_size=320, min_size=80):
    """নির্দিষ্ট ফন্ট ফাইল দিয়ে টেক্সটের সাইজ নিখুঁতভাবে ফিট করায়"""
    if not font_file or not os.path.exists(font_file):
        font_file = get_fixed_bar_font()
        
    if not font_file or not os.path.exists(font_file):
        return ImageFont.load_default(), start_size

    for fs in range(start_size, min_size, -4):
        try:
            f = ImageFont.truetype(font_file, fs)
            bbox = f.getbbox(text)
            if (bbox[2] - bbox[0]) <= max_w and (bbox[3] - bbox[1]) <= max_h:
                return f, fs
        except Exception:
            pass
            
    try:
        return ImageFont.truetype(font_file, min_size), min_size
    except Exception:
        return ImageFont.load_default(), min_size

def generate_dynamic_thumbnail(title, output_path, thumb_meta=None):
    """
    🌟 টপ/বটমে ফিক্সড ফন্ট এবং মাঝখানে র‍্যান্ডম স্টাইলিশ ফন্ট দিয়ে বিশালাকার থাম্বনেইল তৈরি করে
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

    # ১. ফন্ট নির্ধারণ
    bar_font_file = get_fixed_bar_font()         # টপ ও বটমের নির্দিষ্ট ফন্ট
    middle_font_file = get_random_middle_font()   # মাঝখানের র‍্যান্ডম ডিসপ্লে ফন্ট
    
    print(f"🎨 Thumbnail Fonts Selected -> Bar: {os.path.basename(str(bar_font_file))} | Middle: {os.path.basename(str(middle_font_file))}")

    # 🌟 ২. টপ বার (0 to 200px)
    green_bg = "#00531b"
    draw.rectangle([0, 0, W, 200], fill=green_bg)
    
    gov_logo_path = os.path.join("Photos", "Govbd.png")
    if os.path.exists(gov_logo_path):
        try:
            gov_logo = Image.open(gov_logo_path).convert("RGBA").resize((150, 150), Image.LANCZOS)
            img.paste(gov_logo, (35, 25), gov_logo)
            img.paste(gov_logo, (W - 185, 25), gov_logo)
        except Exception:
            pass

    f_top, _ = get_fitted_font(top_text, max_w=W - 420, max_h=150, font_file=bar_font_file, start_size=155, min_size=80)
    draw.text((W // 2, 100), top_text, fill="#ffffff", font=f_top, anchor="mm")

    # 🌟 ৩. মিডল সেকশন (200 to 880px) — মাঝখানের র‍্যান্ডম ফন্টে বিশাল লেখা
    draw.rectangle([0, 200, W, 880], fill="#ffffff")

    # লাল লাইন ১ (বিশাল সাইজ)
    f_l1, _ = get_fitted_font(row1_text, max_w=W - 100, max_h=340, font_file=middle_font_file, start_size=310, min_size=130)
    # কালো লাইন ২ (বিশাল সাইজ)
    f_l2, _ = get_fitted_font(row2_text, max_w=W - 100, max_h=290, font_file=middle_font_file, start_size=260, min_size=110)

    bb1 = f_l1.getbbox(row1_text)
    h1 = bb1[3] - bb1[1]
    bb2 = f_l2.getbbox(row2_text)
    h2 = bb2[3] - bb2[1]

    line_spacing = 15
    total_content_height = h1 + line_spacing + h2
    
    middle_center_y = 200 + (680 // 2)  # 540
    start_y = middle_center_y - (total_content_height // 2)

    # লাইন ১: উজ্জ্বল লাল টেক্সট
    draw.text((W // 2, start_y + (h1 // 2)), row1_text, fill="#d60000", font=f_l1, anchor="mm")

    # লাইন ২: গাঢ় কালো টেক্সট
    draw.text((W // 2, start_y + h1 + line_spacing + (h2 // 2)), row2_text, fill="#000000", font=f_l2, anchor="mm")

    # 🌟 ৪. বটম বার (880 to 1080px)
    draw.rectangle([0, 880, W, H], fill=green_bg)
    f_bot, _ = get_fitted_font(bot_text, max_w=W - 80, max_h=150, font_file=bar_font_file, start_size=155, min_size=80)
    draw.text((W // 2, 980), bot_text, fill="#ffe600", font=f_bot, anchor="mm")

    # বর্ডার সেপারেটর
    draw.line([(0, 200), (W, 200)], fill="#003d14", width=6)
    draw.line([(0, 880), (W, 880)], fill="#003d14", width=6)

    img.save(output_path, "JPEG", quality=100, subsampling=0)
    print(f"✅ Generated Ultra-HD Dynamic Thumbnail: '{row1_text} | {row2_text}'")
