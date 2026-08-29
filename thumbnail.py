# -*- coding: utf-8 -*-
import os, re, random
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
        font1 = display_fonts[0]
        remaining = [f for f in valid_fonts if f != font1]
        return font1, random.choice(remaining)
    elif len(valid_fonts) >= 2:
        return random.sample(valid_fonts, 2)
    else:
        bar_f = get_fixed_bar_font()
        return bar_f, bar_f

def get_english_bold_font(font_size):
    """ইংরেজি শব্দের জন্য লিনাক্স/উবুন্টু সিস্টেমের বোল্ড ইংরেজি ফন্ট লোড করে"""
    eng_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
    ]
    for p in eng_paths:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, font_size)
            except Exception: pass
    try: return ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
    except Exception: return ImageFont.load_default()

def split_text_by_script(text):
    """বাক্যটিকে বাংলা অংশ এবং ইংরেজি অংশে ভাগ করে"""
    tokens = re.split(r'([A-Za-z0-9]+)', text)
    segments = []
    for t in tokens:
        if not t: continue
        is_eng = bool(re.match(r'^[A-Za-z0-9]+$', t))
        segments.append((t, is_eng))
    return segments

def measure_mixed_text(text, bn_font_path, font_size):
    """বাংলা ও ইংরেজি মিশ্রিত লাইনের মোট প্রস্থ ও উচ্চতা পরিমাপ করে"""
    try: bn_font = ImageFont.truetype(bn_font_path, font_size)
    except Exception: bn_font = ImageFont.load_default()
    eng_font = get_english_bold_font(font_size)

    segments = split_text_by_script(text)
    total_w, max_h = 0, 0

    for seg_text, is_eng in segments:
        f = eng_font if is_eng else bn_font
        bbox = f.getbbox(seg_text)
        total_w += (bbox[2] - bbox[0])
        h = bbox[3] - bbox[1]
        if h > max_h: max_h = h

    return total_w, max_h

def get_best_fitted_mixed_font_size(text, max_w, max_h, bn_font_path, start_size=320, min_size=80):
    """টেক্সট যেন সীমানার বাইরে না যায় সেজন্য পারফেক্ট ফন্ট সাইজ বের করে"""
    for fs in range(start_size, min_size, -4):
        w, h = measure_mixed_text(text, bn_font_path, fs)
        if w <= max_w and h <= max_h:
            return fs, h
    return min_size, max_h

def draw_mixed_text_centered(draw, center_x, center_y, text, bn_font_path, font_size, fill_color):
    """বাংলা ও ইংরেজি ফন্ট আলাদা করে নিখুঁতভাবে লাইনের মাঝখানে ড্র করে"""
    try: bn_font = ImageFont.truetype(bn_font_path, font_size)
    except Exception: bn_font = ImageFont.load_default()
    eng_font = get_english_bold_font(font_size)

    segments = split_text_by_script(text)
    total_w = 0
    seg_widths = []

    for seg_text, is_eng in segments:
        f = eng_font if is_eng else bn_font
        bbox = f.getbbox(seg_text)
        w = bbox[2] - bbox[0]
        seg_widths.append(w)
        total_w += w

    cur_x = center_x - (total_w // 2)

    for (seg_text, is_eng), w in zip(segments, seg_widths):
        f = eng_font if is_eng else bn_font
        draw.text((cur_x, center_y), seg_text, font=f, fill=fill_color, anchor="lm")
        cur_x += w

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

    print(f"🎨 [Thumbnail Fonts Applied] Top/Bottom Bar: {os.path.basename(str(bar_font))}")
    print(f"   ├─ Middle Line 1 (Red)  : {os.path.basename(str(font_line1))}")
    print(f"   └─ Middle Line 2 (Black): {os.path.basename(str(font_line2))}")

    # ১. টপ বার (0 to 200px)
    green_bg = "#00531b"
    draw.rectangle([0, 0, W, 200], fill=green_bg)
    
    gov_logo_path = os.path.join("Photos", "Govbd.png")
    if os.path.exists(gov_logo_path):
        try:
            gov_logo = Image.open(gov_logo_path).convert("RGBA").resize((150, 150), Image.LANCZOS)
            img.paste(gov_logo, (35, 25), gov_logo)
            img.paste(gov_logo, (W - 185, 25), gov_logo)
        except Exception: pass

    fs_top, _ = get_best_fitted_mixed_font_size(top_text, max_w=W - 420, max_h=150, bn_font_path=bar_font, start_size=155, min_size=80)
    draw_mixed_text_centered(draw, W // 2, 100, top_text, bar_font, fs_top, "#ffffff")

    # ২. মিডল সেকশন (200 to 880px) — মাঝের দুটি লাইনে দুটি আলাদা ফন্ট ও বাংলা+ইংরেজি মিক্সড রেন্ডারিং
    draw.rectangle([0, 200, W, 880], fill="#ffffff")

    fs_l1, h1 = get_best_fitted_mixed_font_size(row1_text, max_w=W - 100, max_h=340, bn_font_path=font_line1, start_size=310, min_size=130)
    fs_l2, h2 = get_best_fitted_mixed_font_size(row2_text, max_w=W - 100, max_h=290, bn_font_path=font_line2, start_size=260, min_size=110)

    line_spacing = 20
    total_content_height = h1 + line_spacing + h2
    start_y = 540 - (total_content_height // 2)

    # লাল লাইন ১ (মাঝের ১ম লাইন)
    draw_mixed_text_centered(draw, W // 2, start_y + (h1 // 2), row1_text, font_line1, fs_l1, "#d60000")

    # কালো লাইন ২ (মাঝের ২য় লাইন - SSC/HSC সহ যেকোনো ইংরেজি শব্দ ক্রিস্প বোল্ড ফন্টে আসবে)
    draw_mixed_text_centered(draw, W // 2, start_y + h1 + line_spacing + (h2 // 2), row2_text, font_line2, fs_l2, "#000000")

    # ৩. বটম বার (880 to 1080px)
    draw.rectangle([0, 880, W, H], fill=green_bg)
    fs_bot, _ = get_best_fitted_mixed_font_size(bot_text, max_w=W - 80, max_h=150, bn_font_path=bar_font, start_size=155, min_size=80)
    draw_mixed_text_centered(draw, W // 2, 980, bot_text, bar_font, fs_bot, "#ffe600")

    draw.line([(0, 200), (W, 200)], fill="#003d14", width=6)
    draw.line([(0, 880), (W, 880)], fill="#003d14", width=6)

    img.save(output_path, "JPEG", quality=100, subsampling=0)
    print(f"✅ Generated Ultra-HD Dynamic Thumbnail: '{row1_text} | {row2_text}'")
