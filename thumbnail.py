# -*- coding: utf-8 -*-
import os, random
from PIL import Image, ImageDraw, ImageFont
from ai_service import strip_unwanted_chars

FONTS_DIR = "Fonts"

def is_valid_bengali_font(font_path):
    """চেক করে ফন্টটি আসলেই বাংলা ইউনিকোড অক্ষর সাপোর্ট করে কিনা"""
    try:
        test_font = ImageFont.truetype(font_path, 40)
        mask = test_font.getmask("বাংলাদেশ চাকরি")
        if mask.size[0] > 0 and mask.size[1] > 0:
            return True
    except Exception:
        pass
    return False

def get_verified_bengali_fonts():
    """Fonts ফোল্ডার থেকে শুধুমাত্র টেস্টেড ও ভ্যালিড বাংলা ফন্টগুলো রিটার্ন করে"""
    verified = []
    if os.path.exists(FONTS_DIR):
        for f in sorted(os.listdir(FONTS_DIR)):
            if f.lower().endswith(('.ttf', '.otf')):
                full_p = os.path.join(FONTS_DIR, f)
                if "akhand.ttf" == f.lower():
                    continue
                if is_valid_bengali_font(full_p):
                    verified.append(full_p)
    return verified

def get_fixed_bar_font():
    """টপ ও বটমের জন্য Kalpurush বা নিশ্চিত বাংলা ফন্ট"""
    valid_fonts = get_verified_bengali_fonts()
    for f in valid_fonts:
        if "kalpurush" in os.path.basename(f).lower():
            return f
    return valid_fonts[0] if valid_fonts else "BengaliFont.ttf"

def get_two_distinct_middle_fonts():
    """মাঝখানের দুটি লাইনের জন্য আলাদা দুটি ভিন্ন ১০০% ইউনিকোড বাংলা ফন্ট বেছে নেয়"""
    valid_fonts = get_verified_bengali_fonts()
    display_fonts = [f for f in valid_fonts if "kalpurush" not in os.path.basename(f).lower()]
    
    if len(display_fonts) >= 2:
        return random.sample(display_fonts, 2)
    elif len(display_fonts) == 1 and len(valid_fonts) >= 2:
        other = [f for f in valid_fonts if f != display_fonts[0]][0]
        return display_fonts[0], other
    elif len(valid_fonts) >= 2:
        return random.sample(valid_fonts, 2)
    elif len(valid_fonts) == 1:
        return valid_fonts[0], valid_fonts[0]
    else:
        bar_f = get_fixed_bar_font()
        return bar_f, bar_f

def get_fitted_font(text, max_w, max_h, font_file=None, start_size=320, min_size=80):
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
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), "#ffffff")
    draw = ImageDraw.Draw(img)

    if not thumb_meta:
        thumb_meta = {}

    top_text = strip_unwanted_chars(thumb_meta.get("top_text", "সরকারি চাকরি"))
    row1_text = strip_unwanted_chars(thumb_meta.get("row1_text", "জরুরি নিয়োগ"))
    row2_text = strip_unwanted_chars(thumb_meta.get("row2_text", "(SSC পাশ/৬৪ জেলা)"))
    bot_text = strip_unwanted_chars(thumb_meta.get("bot_text", "আবেদনের নিয়ম ও বিস্তারিত"))

    # ফন্ট নির্ধারণ
    bar_font = get_fixed_bar_font()
    font_line1, font_line2 = get_two_distinct_middle_fonts()

    # ১. টপ বার
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

    f_top, _ = get_fitted_font(top_text, max_w=W - 420, max_h=150, font_file=bar_font, start_size=155, min_size=80)
    draw.text((W // 2, 100), top_text, fill="#ffffff", font=f_top, anchor="mm")

    # ২. মিডল সেকশন (মাঝের দুটি লাইনে দুটি আলাদা ফন্ট)
    draw.rectangle([0, 200, W, 880], fill="#ffffff")

    f_l1, _ = get_fitted_font(row1_text, max_w=W - 100, max_h=340, font_file=font_line1, start_size=310, min_size=130)
    f_l2, _ = get_fitted_font(row2_text, max_w=W - 100, max_h=290, font_file=font_line2, start_size=260, min_size=110)

    bb1 = f_l1.getbbox(row1_text)
    h1 = bb1[3] - bb1[1]
    bb2 = f_l2.getbbox(row2_text)
    h2 = bb2[3] - bb2[1]

    line_spacing = 15
    total_content_height = h1 + line_spacing + h2
    start_y = 540 - (total_content_height // 2)

    # লাইন ১: উজ্জ্বল লাল
    draw.text((W // 2, start_y + (h1 // 2)), row1_text, fill="#d60000", font=f_l1, anchor="mm")

    # লাইন ২: গাঢ় কালো
    draw.text((W // 2, start_y + h1 + line_spacing + (h2 // 2)), row2_text, fill="#000000", font=f_l2, anchor="mm")

    # ৩. বটম বার
    draw.rectangle([0, 880, W, H], fill=green_bg)
    f_bot, _ = get_fitted_font(bot_text, max_w=W - 80, max_h=150, font_file=bar_font, start_size=155, min_size=80)
    draw.text((W // 2, 980), bot_text, fill="#ffe600", font=f_bot, anchor="mm")

    draw.line([(0, 200), (W, 200)], fill="#003d14", width=6)
    draw.line([(0, 880), (W, 880)], fill="#003d14", width=6)

    img.save(output_path, "JPEG", quality=100, subsampling=0)
    print(f"✅ Generated Ultra-HD Dynamic Thumbnail: '{row1_text} | {row2_text}'")
