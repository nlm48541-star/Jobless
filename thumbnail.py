# -*- coding: utf-8 -*-
import os, re, random
from PIL import Image, ImageDraw, ImageFont
from ai_service import strip_unwanted_chars

FONTS_DIR = "Fonts"
PHOTOS_DIR = "Photos"

# 🌟 ১৮টি নির্দিষ্ট প্রতিষ্ঠান ও তাদের লোগো ফাইলের ম্যাপিং
ORG_LOGO_RULES = [
    (['সেনাবাহিনী', 'সেনা', 'army', 'সৈনিক', 'কমিশনড অফিসার'], ['Army.png', 'army.png']),
    (['নৌবাহিনী', 'নৌ', 'navy', 'নাবিক', 'sailor'], ['Navy.png', 'navy.png']),
    (['বিমান বাহিনী', 'বিমানবাহিনী', 'airforce', 'air force', 'এয়ারফোর্স'], ['AirForce.png', 'airforce.png']),
    (['বর্ডার গার্ড', 'বিজিবি', 'bgb', 'বিডিআর', 'bdr'], ['BGB.png', 'bgb.png']),
    (['পুলিশ', 'police', 'কনস্টেবল', 'এসআই', 'সার্জেন্ট'], ['Police.png', 'police.png']),
    (['আনসার', 'ansar', 'ভিডিপি', 'ব্যাটালিয়ন আনসার'], ['Ansar.png', 'ansar.png']),
    (['কোস্ট গার্ড', 'কোস্টগার্ড', 'coast guard', 'coastguard'], ['CoastGuard.png', 'coastguard.png']),
    (['র‍্যাব', 'র‌্যাব', 'rab'], ['RAB.png', 'rab.png']),
    (['ফায়ার সার্ভিস', 'ফায়ার সার্ভিস', 'fire service', 'ফায়ারম্যান'], ['FireService.png', 'fireservice.png']),
    (['রেলওয়ে', 'রেলওয়ে', 'railway', 'বাংলাদেশ রেলওয়ে'], ['Railway.png', 'railway.png']),
    (['বিসিএস', 'bcs', 'পিএসসি', 'bpsc', 'পাবলিক সার্ভিস'], ['BCS.png', 'bcs.png']),
    (['প্রাথমিক শিক্ষক', 'প্রাইমারি শিক্ষক', 'প্রাথমিক', 'প্রাইমারি', 'primary teacher', 'সহকারী শিক্ষক'], ['PrimaryTeacher.png', 'primaryteacher.png']),
    (['খাদ্য অধিদপ্তর', 'খাদ্য', 'food'], ['Food.png', 'food.png']),
    (['ডাক বিভাগ', 'ডাক', 'পোস্ট অফিস', 'পোস্টাল', 'post office'], ['PostOffice.png', 'postoffice.png']),
    (['কারা অধিদপ্তর', 'কারারক্ষী', 'কারাগার', 'jail', 'prison'], ['Jail.png', 'jail.png']),
    (['পাসপোর্ট অধিদপ্তর', 'পাসপোর্ট', 'passport', 'ইমিগ্রেশন'], ['Passport.png', 'passport.png']),
    (['পরিবার পরিকল্পনা', 'family planning'], ['FamilyPlanning.png', 'familyplanning.png']),
    (['গণপূর্ত', 'pwd', 'গণপূর্ত অধিদপ্তর'], ['PWD.jpeg', 'PWD.png', 'pwd.jpeg', 'pwd.png', 'PWD.jpg']),
]

# 🌟 ৬টি উজ্জ্বল ও হাই-কনট্রাস্ট প্রিমিয়াম কালার কম্বিনেশন
VIBRANT_PALETTES = [
    # ১. ক্লাসিক নেভি ব্লু ও ইলেকট্রিক ইয়োলো
    {"bar_bg": "#001275", "border": "#000a40", "bar_text": "#ffffff", "bot_text": "#ffffff", "sub_bg": "#ffe600", "sub_text": "#000000", "hook_text": "#d80000"},
    # ২. রয়েল ব্লু ও সান গোল্ড
    {"bar_bg": "#002fa7", "border": "#001c66", "bar_text": "#ffffff", "bot_text": "#ffe600", "sub_bg": "#ffd700", "sub_text": "#000000", "hook_text": "#d60000"},
    # ৩. এমারেল্ড ফরেস্ট গ্রিন ও নিওন ইয়োলো
    {"bar_bg": "#00521b", "border": "#003310", "bar_text": "#ffffff", "bot_text": "#ffe600", "sub_bg": "#ffea00", "sub_text": "#000000", "hook_text": "#d80000"},
    # ৪. ডিপ ক্রিমসন রেড ও ব্রাইট গোল্ড
    {"bar_bg": "#6b0014", "border": "#42000c", "bar_text": "#ffffff", "bot_text": "#ffffff", "sub_bg": "#ffea00", "sub_text": "#000000", "hook_text": "#d80000"},
    # ৫. ডিপ ভায়োলেট ও ইলেকট্রিক ইয়োলো
    {"bar_bg": "#38006b", "border": "#20003d", "bar_text": "#ffffff", "bot_text": "#ffe600", "sub_bg": "#ffe600", "sub_text": "#000000", "hook_text": "#d60000"},
    # ৬. ডিপ ডার্ক টিল ও গোল্ডেন ইয়োলো
    {"bar_bg": "#004754", "border": "#002a33", "bar_text": "#ffffff", "bot_text": "#ffffff", "sub_bg": "#ffea00", "sub_text": "#000000", "hook_text": "#d80000"}
]

def find_matched_org_logo(title_text):
    if not os.path.exists(PHOTOS_DIR): return None
    t_lower = str(title_text).lower()
    for keywords, filenames in ORG_LOGO_RULES:
        if any(k in t_lower for k in keywords):
            for fn in filenames:
                full_p = os.path.join(PHOTOS_DIR, fn)
                if os.path.exists(full_p): return full_p
    return None

def is_valid_bengali_font(font_path):
    try:
        test_font = ImageFont.truetype(font_path, 40)
        mask = test_font.getmask("বাংলাদেশ চাকরি")
        if mask.size[0] > 0 and mask.size[1] > 0: return True
    except Exception: pass
    return False

def get_verified_bengali_fonts():
    verified = []
    if os.path.exists(FONTS_DIR):
        for f in sorted(os.listdir(FONTS_DIR)):
            if f.lower().endswith(('.ttf', '.otf')):
                full_p = os.path.join(FONTS_DIR, f)
                if "akhand.ttf" == f.lower(): continue
                if is_valid_bengali_font(full_p): verified.append(full_p)
    return verified

def get_fixed_bar_font():
    valid_fonts = get_verified_bengali_fonts()
    for f in valid_fonts:
        if "kalpurush" in os.path.basename(f).lower(): return f
    return valid_fonts[0] if valid_fonts else "BengaliFont.ttf"

def get_two_distinct_middle_fonts():
    valid_fonts = get_verified_bengali_fonts()
    display_fonts = [f for f in valid_fonts if "kalpurush" not in os.path.basename(f).lower()]
    if len(display_fonts) >= 2: return random.sample(display_fonts, 2)
    elif len(display_fonts) == 1 and len(valid_fonts) >= 2:
        font1 = display_fonts[0]
        remaining = [f for f in valid_fonts if f != font1]
        return font1, random.choice(remaining)
    elif len(valid_fonts) >= 2: return random.sample(valid_fonts, 2)
    else: return get_fixed_bar_font(), get_fixed_bar_font()

def get_english_bold_font(font_size):
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
    tokens = re.split(r'([A-Za-z0-9/]+)', text)
    segments = []
    for t in tokens:
        if not t: continue
        is_eng = bool(re.match(r'^[A-Za-z0-9/]+$', t))
        segments.append((t, is_eng))
    return segments

def measure_mixed_text(text, bn_font_path, font_size):
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

def get_best_fitted_mixed_font_size(text, max_w, max_h, bn_font_path, start_size=340, min_size=60):
    for fs in range(start_size, min_size, -4):
        w, h = measure_mixed_text(text, bn_font_path, fs)
        if w <= max_w and h <= max_h: return fs, h
    return min_size, max_h

def draw_mixed_text_centered(draw, center_x, center_y, text, bn_font_path, font_size, fill_color):
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

    if not thumb_meta: thumb_meta = {}

    top_text = strip_unwanted_chars(thumb_meta.get("top_text", "সরকারি চাকরি"))
    row1_text = strip_unwanted_chars(thumb_meta.get("row1_text", "জরুরি নিয়োগ"))
    row2_text = strip_unwanted_chars(thumb_meta.get("row2_text", "(SSC পাশ/৬৪ জেলা)"))
    bot_text = strip_unwanted_chars(thumb_meta.get("bot_text", "আবেদনের নিয়ম ও বিস্তারিত"))

    bar_font = get_fixed_bar_font()
    font_line1, font_line2 = get_two_distinct_middle_fonts()

    # নির্দিষ্ট প্রতিষ্ঠান লোগো চেকিং
    matched_logo = find_matched_org_logo(title) or find_matched_org_logo(top_text)

    # =========================================================================
    # 🌟 ১. স্পেশাল অর্গানাইজেশন ডিজাইন (৩টি টেক্সট বক্স + ডানপাশে বড় লোগো)
    # =========================================================================
    if matched_logo and os.path.exists(matched_logo):
        theme = random.choice(VIBRANT_PALETTES)
        print(f"✨ [Special Org Thumbnail] Logo: {os.path.basename(matched_logo)} | Theme: {theme['bar_bg']}")

        # টপ বার (0 to 200px)
        draw.rectangle([0, 0, W, 200], fill=theme["bar_bg"])
        gov_logo_p = os.path.join(PHOTOS_DIR, "Govbd.png")
        if os.path.exists(gov_logo_p):
            try:
                g_logo = Image.open(gov_logo_p).convert("RGBA").resize((150, 150), Image.LANCZOS)
                img.paste(g_logo, (35, 25), g_logo)
                img.paste(g_logo, (W - 185, 25), g_logo)
                g_logo.close()
            except Exception: pass

        fs_top, _ = get_best_fitted_mixed_font_size(top_text, max_w=W - 420, max_h=160, bn_font_path=bar_font, start_size=170, min_size=80)
        draw_mixed_text_centered(draw, W // 2, 100, top_text, bar_font, fs_top, theme["bar_text"])

        split_x = 1260

        # ডানে লোগো বক্স (1260 to 1920px) — পিওর হোয়াইট ব্যাকগ্রাউন্ড
        draw.rectangle([split_x, 200, W, 880], fill="#ffffff")
        try:
            org_img = Image.open(matched_logo).convert("RGBA")
            org_img.thumbnail((560, 560), Image.LANCZOS)
            lw, lh = org_img.size
            pos_x = split_x + ((W - split_x - lw) // 2)
            pos_y = 200 + ((680 - lh) // 2)
            img.paste(org_img, (pos_x, pos_y), org_img)
            org_img.close()
        except Exception as e:
            print(f"⚠️ Logo paste notice: {e}")

        # বামে ৩টি স্ট্যাকড টেক্সট বক্স (0 to 1260px) — বিশালাকার ফন্ট সাইজ
        # বক্স ১: হলুদ সাব-হুক (200 to 380px, উচ্চতা ১৮০px)
        draw.rectangle([0, 200, split_x, 380], fill=theme["sub_bg"])
        fs_b1, _ = get_best_fitted_mixed_font_size(row1_text, max_w=split_x - 40, max_h=150, bn_font_path=font_line1, start_size=220, min_size=90)
        draw_mixed_text_centered(draw, split_x // 2, 290, row1_text, font_line1, fs_b1, theme["sub_text"])

        # বক্স ২: সাদা ব্যাকগ্রাউন্ডে বিশাল লাল মেইন হুক (380 to 700px, উচ্চতা ৩২০px)
        draw.rectangle([0, 380, split_x, 700], fill="#ffffff")
        fs_b2, _ = get_best_fitted_mixed_font_size(row2_text, max_w=split_x - 40, max_h=280, bn_font_path=font_line2, start_size=330, min_size=120)
        draw_mixed_text_centered(draw, split_x // 2, 540, row2_text, font_line2, fs_b2, theme["hook_text"])

        # বক্স ৩: হলুদ সাব-লাইন (700 to 880px, উচ্চতা ১৮০px)
        draw.rectangle([0, 700, split_x, 880], fill=theme["sub_bg"])
        b3_text = strip_unwanted_chars(thumb_meta.get("row2_text", "SSC/HSC পাশ"))
        if b3_text == row2_text: b3_text = "আবেদনের নিয়ম ও যোগ্যতা"
        fs_b3, _ = get_best_fitted_mixed_font_size(b3_text, max_w=split_x - 40, max_h=150, bn_font_path=font_line1, start_size=200, min_size=80)
        draw_mixed_text_centered(draw, split_x // 2, 790, b3_text, font_line1, fs_b3, theme["sub_text"])

        # বর্ডার ও সেপারেটর লাইন
        draw.line([(split_x, 200), (split_x, 880)], fill=theme["border"], width=7)
        draw.line([(0, 380), (split_x, 380)], fill=theme["border"], width=6)
        draw.line([(0, 700), (split_x, 700)], fill=theme["border"], width=6)

        # বটম বার (880 to 1080px)
        draw.rectangle([0, 880, W, H], fill=theme["bar_bg"])
        fs_bot, _ = get_best_fitted_mixed_font_size(bot_text, max_w=W - 80, max_h=160, bn_font_path=bar_font, start_size=170, min_size=80)
        draw_mixed_text_centered(draw, W // 2, 980, bot_text, bar_font, fs_bot, theme["bot_text"])

        draw.line([(0, 200), (W, 200)], fill=theme["border"], width=7)
        draw.line([(0, 880), (W, 880)], fill=theme["border"], width=7)

    # =========================================================================
    # 🌟 ২. রেগুলার ডিজাইন (আপনার আগের ক্লাসিক গ্রিন ডিজাইন ১০০% অক্ষুণ্ণ)
    # =========================================================================
    else:
        print(f"📄 [Classic Thumbnail] Regular layout for '{title[:35]}...'")
        green_bg = "#00521b"
        
        # টপ বার
        draw.rectangle([0, 0, W, 200], fill=green_bg)
        gov_logo_p = os.path.join(PHOTOS_DIR, "Govbd.png")
        if os.path.exists(gov_logo_p):
            try:
                g_logo = Image.open(gov_logo_p).convert("RGBA").resize((150, 150), Image.LANCZOS)
                img.paste(g_logo, (35, 25), g_logo)
                img.paste(g_logo, (W - 185, 25), g_logo)
                g_logo.close()
            except Exception: pass

        fs_top, _ = get_best_fitted_mixed_font_size(top_text, max_w=W - 420, max_h=160, bn_font_path=bar_font, start_size=170, min_size=80)
        draw_mixed_text_centered(draw, W // 2, 100, top_text, bar_font, fs_top, "#ffffff")

        # মিডল সেকশন (ফুল ওয়াইড্থ সাদা ব্যাকগ্রাউন্ডে বিশালাকার টেক্সট)
        draw.rectangle([0, 200, W, 880], fill="#ffffff")

        fs_l1, h1 = get_best_fitted_mixed_font_size(row1_text, max_w=W - 80, max_h=340, bn_font_path=font_line1, start_size=330, min_size=130)
        fs_l2, h2 = get_best_fitted_mixed_font_size(row2_text, max_w=W - 80, max_h=290, bn_font_path=font_line2, start_size=280, min_size=110)

        line_spacing = 15
        total_content_height = h1 + line_spacing + h2
        start_y = 540 - (total_content_height // 2)

        # লাল লাইন ১ (বিশাল লাল লেখা)
        draw_mixed_text_centered(draw, W // 2, start_y + (h1 // 2), row1_text, font_line1, fs_l1, "#d80000")

        # কালো লাইন ২ (বিশাল কালো লেখা)
        draw_mixed_text_centered(draw, W // 2, start_y + h1 + line_spacing + (h2 // 2), row2_text, font_line2, fs_l2, "#000000")

        # বটম বার
        draw.rectangle([0, 880, W, H], fill=green_bg)
        fs_bot, _ = get_best_fitted_mixed_font_size(bot_text, max_w=W - 80, max_h=160, bn_font_path=bar_font, start_size=170, min_size=80)
        draw_mixed_text_centered(draw, W // 2, 980, bot_text, bar_font, fs_bot, "#ffe600")

        draw.line([(0, 200), (W, 200)], fill="#003310", width=7)
        draw.line([(0, 880), (W, 880)], fill="#003310", width=7)

    img.save(output_path, "JPEG", quality=100, subsampling=0)
    print(f"✅ Generated Ultra-HD Dynamic Thumbnail: '{row1_text} | {row2_text}'")
