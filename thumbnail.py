# -*- coding: utf-8 -*-
import os, re, random
from PIL import Image, ImageDraw, ImageFont
from ai_service import strip_unwanted_chars

FONTS_DIR = "Fonts"
PHOTOS_DIR = "Photos"

# 🌟 ১৮টি নির্দিষ্ট প্রতিষ্ঠান ও তাদের লোগো ফাইলের ম্যাপিং
ORG_LOGO_RULES = [
    (['সেনাবাহিনী', 'সেনা', 'army', 'সৈনিক', 'কমিশনড অফিসার'], ['Army.png', 'army.png', 'ARMY.PNG', 'sena.png']),
    (['নৌবাহিনী', 'নৌ', 'navy', 'নাবিক', 'sailor'], ['Navy.png', 'navy.png', 'NAVY.PNG', 'nou.png']),
    (['বিমান বাহিনী', 'বিমানবাহিনী', 'airforce', 'air force', 'এয়ারফোর্স'], ['AirForce.png', 'airforce.png', 'biman.png']),
    (['বর্ডার গার্ড', 'বিজিবি', 'bgb', 'বিডিআর', 'bdr'], ['BGB.png', 'bgb.png', 'Bgb.png']),
    (['পুলিশ', 'police', 'কনস্টেবল', 'এসআই', 'সার্জেন্ট', 'পুলিশ সুপারের'], ['Police.png', 'police.png', 'POLICE.PNG', 'bd_police.png']),
    (['আনসার', 'ansar', 'ভিডিপি', 'ব্যাটালিয়ন আনসার'], ['Ansar.png', 'ansar.png']),
    (['কোস্ট গার্ড', 'কোস্টগার্ড', 'coast guard', 'coastguard'], ['CoastGuard.png', 'coastguard.png', 'coast_guard.png']),
    (['র‍্যাব', 'র‌্যাব', 'rab'], ['RAB.png', 'rab.png', 'Rab.png']),
    (['ফায়ার সার্ভিস', 'ফায়ার সার্ভিস', 'fire service', 'ফায়ারম্যান'], ['FireService.png', 'fireservice.png', 'fire.png', 'Fire.png']),
    (['রেলওয়ে', 'রেলওয়ে', 'railway', 'বাংলাদেশ রেলওয়ে'], ['Railway.png', 'railway.png', 'rail.png']),
    (['বিসিএস', 'bcs', 'পিএসসি', 'bpsc', 'পাবলিক সার্ভিস'], ['BCS.png', 'bcs.png']),
    (['প্রাথমিক শিক্ষক', 'প্রাইমারি শিক্ষক', 'প্রাথমিক', 'প্রাইমারি', 'primary teacher', 'সহকারী শিক্ষক'], ['PrimaryTeacher.png', 'primaryteacher.png', 'primary.png']),
    (['খাদ্য অধিদপ্তর', 'খাদ্য', 'food'], ['Food.png', 'food.png']),
    (['ডাক বিভাগ', 'ডাক', 'পোস্ট অফিস', 'পোস্টাল', 'post office'], ['PostOffice.png', 'postoffice.png', 'post.png']),
    (['কারা অধিদপ্তর', 'কারারক্ষী', 'কারাগার', 'jail', 'prison'], ['Jail.png', 'jail.png', 'prison.png']),
    (['পাসপোর্ট অধিদপ্তর', 'পাসপোর্ট', 'passport', 'ইমিগ্রেশন'], ['Passport.png', 'passport.png']),
    (['পরিবার পরিকল্পনা', 'family planning'], ['FamilyPlanning.png', 'familyplanning.png']),
    (['গণপূর্ত', 'pwd', 'গণপূর্ত অধিদপ্তর'], ['PWD.jpeg', 'PWD.png', 'pwd.jpeg', 'pwd.png', 'PWD.jpg', 'pwd.jpg']),
]

VIBRANT_PALETTES = [
    {"bar_bg": "#001275", "border": "#000a40", "bar_text": "#ffffff", "bot_text": "#ffffff", "sub_bg": "#ffe600", "sub_text": "#000000", "hook_text": "#d80000"},
    {"bar_bg": "#002fa7", "border": "#001c66", "bar_text": "#ffffff", "bot_text": "#ffe600", "sub_bg": "#ffd700", "sub_text": "#000000", "hook_text": "#d60000"},
    {"bar_bg": "#00521b", "border": "#003310", "bar_text": "#ffffff", "bot_text": "#ffe600", "sub_bg": "#ffea00", "sub_text": "#000000", "hook_text": "#d80000"},
    {"bar_bg": "#6b0014", "border": "#42000c", "bar_text": "#ffffff", "bot_text": "#ffffff", "sub_bg": "#ffea00", "sub_text": "#000000", "hook_text": "#d80000"},
    {"bar_bg": "#38006b", "border": "#20003d", "bar_text": "#ffffff", "bot_text": "#ffe600", "sub_bg": "#ffe600", "sub_text": "#000000", "hook_text": "#d60000"},
    {"bar_bg": "#004754", "border": "#002a33", "bar_text": "#ffffff", "bot_text": "#ffffff", "sub_bg": "#ffea00", "sub_text": "#000000", "hook_text": "#d80000"}
]

def find_matched_org_logo(title_text):
    if not os.path.exists(PHOTOS_DIR): return None
    disk_files = {f.lower(): os.path.join(PHOTOS_DIR, f) for f in os.listdir(PHOTOS_DIR)}
    t_lower = str(title_text).lower()

    for keywords, filenames in ORG_LOGO_RULES:
        if any(k in t_lower for k in keywords):
            for fn in filenames:
                if fn.lower() in disk_files:
                    return disk_files[fn.lower()]
    return None

def split_long_name_intelligently(name):
    """বড় প্রতিষ্ঠানের নামকে সুষম দুটি লাইনে ভাগ করে"""
    name = re.sub(r'\s+', ' ', str(name)).strip()
    if ',' in name:
        parts = [p.strip() for p in name.split(',', 1)]
        if parts[0] and parts[1]: return parts[0], parts[1]
    if ' ও ' in name:
        parts = name.split(' ও ', 1)
        if len(parts[0]) >= 6 and len(parts[1]) >= 6:
            return parts[0].strip() + ' ও', parts[1].strip()
    words = name.split()
    if len(words) <= 1: return name, ""
    mid = (len(words) + 1) // 2
    return " ".join(words[:mid]), " ".join(words[mid:])

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

def render_logo_to_box(img, logo_path, box_rect):
    try:
        x1, y1, x2, y2 = box_rect
        box_w, box_h = x2 - x1, y2 - y1
        with Image.open(logo_path) as raw_logo:
            logo_rgba = raw_logo.convert("RGBA")
            max_w, max_h = int(box_w * 0.88), int(box_h * 0.88)
            logo_rgba.thumbnail((max_w, max_h), Image.LANCZOS)
            lw, lh = logo_rgba.size
            box_patch = Image.new("RGBA", (box_w, box_h), (255, 255, 255, 255))
            px = (box_w - lw) // 2
            py = (box_h - lh) // 2
            box_patch.alpha_composite(logo_rgba, (px, py))
            img.paste(box_patch.convert("RGB"), (x1, y1))
            return True
    except Exception as e:
        print(f"⚠️ Logo render notice: {e}")
        return False

def generate_dynamic_thumbnail(title, output_path, thumb_meta=None):
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), "#ffffff")
    draw = ImageDraw.Draw(img)

    if not thumb_meta: thumb_meta = {}

    # মেটাডাটা এক্সট্রাকশন
    raw_top = strip_unwanted_chars(thumb_meta.get("top_text", ""))
    row1_hook = strip_unwanted_chars(thumb_meta.get("row1_text", "জরুরি নিয়োগ"))
    raw_sub = strip_unwanted_chars(thumb_meta.get("sub_text", "SSC/HSC পাশ"))
    bot_text = strip_unwanted_chars(thumb_meta.get("bot_text", "অনলাইনে আবেদন ও বিস্তারিত"))

    # যদি হুক ছাড়া অন্য কিছু না থাকে
    if not any(h in row1_hook for h in ["নিয়োগ", "সুযোগ"]):
        row1_hook = "জরুরি নিয়োগ"

    # প্রতিষ্ঠানের নাম নির্ধারণ
    org_candidate = raw_top
    if not org_candidate or org_candidate in ["সরকারি চাকরি", "বেসরকারি চাকরি", "জরুরি নিয়োগ"]:
        clean_t = title.split('|')[0].split('-')[0].strip()
        org_candidate = clean_t.split("নিয়োগ")[0].strip() if "নিয়োগ" in clean_t else clean_t[:35]

    org_words = org_candidate.split()
    is_name_long = len(org_candidate) > 22 or len(org_words) > 3

    # 🌟 আপনার নতুন রুল: ছোট নাম নাকি বড় নাম সে অনুযায়ী ২ লাইনের লেখা তৈরি
    if is_name_long:
        # বড় নাম: দুই লাইনে ভাগ হবে (অর্ধেক উপরে, অর্ধেক নিচে)
        middle_line1, middle_line2 = split_long_name_intelligently(org_candidate)
        top_bar_title = "সরকারি চাকরি" if "বেসরকারি" not in title else "বেসরকারি চাকরি"
    else:
        # ছোট নাম: ১ম লাইনে 'জরুরি নিয়োগ' / 'বিশাল নিয়োগ', ২য় লাইনে প্রতিষ্ঠানের নাম
        middle_line1 = row1_hook
        middle_line2 = org_candidate
        top_bar_title = "সরকারি চাকরি" if "বেসরকারি" not in title else "বেসরকারি চাকরি"

    bar_font = get_fixed_bar_font()
    font_line1, font_line2 = get_two_distinct_middle_fonts()

    # নির্দিষ্ট প্রতিষ্ঠান লোগো চেকিং
    matched_logo = find_matched_org_logo(title) or find_matched_org_logo(org_candidate)

    # =========================================================================
    # 🌟 ১. স্পেশাল অর্গানাইজেশন ডিজাইন (ডানপাশে লোগো সহ)
    # =========================================================================
    if matched_logo and os.path.exists(matched_logo):
        theme = random.choice(VIBRANT_PALETTES)
        print(f"✨ [Special Org Thumbnail] Logo: {os.path.basename(matched_logo)}")

        # টপ বার (0 to 200px)
        draw.rectangle([0, 0, W, 200], fill=theme["bar_bg"])
        gov_logo_p = os.path.join(PHOTOS_DIR, "Govbd.png")
        if os.path.exists(gov_logo_p):
            try:
                with Image.open(gov_logo_p) as gl:
                    gl_rgba = gl.convert("RGBA").resize((150, 150), Image.LANCZOS)
                    img.paste(gl_rgba, (35, 25), gl_rgba)
                    img.paste(gl_rgba, (W - 185, 25), gl_rgba)
            except Exception: pass

        fs_top, _ = get_best_fitted_mixed_font_size(org_candidate[:30], max_w=W - 420, max_h=160, bn_font_path=bar_font, start_size=170, min_size=80)
        draw_mixed_text_centered(draw, W // 2, 100, org_candidate[:30], bar_font, fs_top, theme["bar_text"])

        split_x = 1260

        # ডানে লোগো বক্স (1260 to 1920px)
        render_logo_to_box(img, matched_logo, (split_x, 200, W, 880))

        # বামে ৩টি স্ট্যাকড বক্স:
        # বক্স ১: হলুদ সাব-হুক
        draw.rectangle([0, 200, split_x, 380], fill=theme["sub_bg"])
        fs_b1, _ = get_best_fitted_mixed_font_size(row1_hook, max_w=split_x - 40, max_h=150, bn_font_path=font_line1, start_size=220, min_size=90)
        draw_mixed_text_centered(draw, split_x // 2, 290, row1_hook, font_line1, fs_b1, theme["sub_text"])

        # বক্স ২: সাদা ব্যাকগ্রাউন্ডে লাল হুক (পদ সংখ্যা / মূল বিষয়)
        draw.rectangle([0, 380, split_x, 700], fill="#ffffff")
        vac_text = strip_unwanted_chars(thumb_meta.get("row2_text", "বিশাল নিয়োগ"))
        fs_b2, _ = get_best_fitted_mixed_font_size(vac_text, max_w=split_x - 40, max_h=280, bn_font_path=font_line2, start_size=330, min_size=120)
        draw_mixed_text_centered(draw, split_x // 2, 540, vac_text, font_line2, fs_b2, theme["hook_text"])

        # বক্স ৩: হলুদ সাব-বক্স (যোগ্যতা / জেলা - কখনোই আবেদনের কথা রিপিট হবে না)
        draw.rectangle([0, 700, split_x, 880], fill=theme["sub_bg"])
        # আবেদনের কথা থাকলে ফিল্টার করে যোগ্যতা বসানো
        box3_text = raw_sub
        if any(term in box3_text for term in ["আবেদন", "ফরম", "পূরণ", "নিয়ম"]):
            box3_text = "SSC/HSC পাশ / ৬৪ জেলা"
        fs_b3, _ = get_best_fitted_mixed_font_size(box3_text, max_w=split_x - 40, max_h=150, bn_font_path=font_line1, start_size=200, min_size=80)
        draw_mixed_text_centered(draw, split_x // 2, 790, box3_text, font_line1, fs_b3, theme["sub_text"])

        draw.line([(split_x, 200), (split_x, 880)], fill=theme["border"], width=7)
        draw.line([(0, 380), (split_x, 380)], fill=theme["border"], width=6)
        draw.line([(0, 700), (split_x, 700)], fill=theme["border"], width=6)

        # বটম বার (আবেদনের পদ্ধতি ও নিয়ম এখানে একমাত্র থাকবে)
        draw.rectangle([0, 880, W, H], fill=theme["bar_bg"])
        fs_bot, _ = get_best_fitted_mixed_font_size(bot_text, max_w=W - 80, max_h=160, bn_font_path=bar_font, start_size=170, min_size=80)
        draw_mixed_text_centered(draw, W // 2, 980, bot_text, bar_font, fs_bot, theme["bot_text"])

        draw.line([(0, 200), (W, 200)], fill=theme["border"], width=7)
        draw.line([(0, 880), (W, 880)], fill=theme["border"], width=7)

    # =========================================================================
    # 🌟 ২. রেগুলার ক্লাসিক থাম্বনেইল (ফুল ওয়াইড্থ ২ লাইনের ডিজাইন)
    # =========================================================================
    else:
        print(f"📄 [Classic Thumbnail] Org: '{org_candidate}' | Long: {is_name_long}")
        green_bg = "#00521b"
        
        # টপ বার
        draw.rectangle([0, 0, W, 200], fill=green_bg)
        gov_logo_p = os.path.join(PHOTOS_DIR, "Govbd.png")
        if os.path.exists(gov_logo_p):
            try:
                with Image.open(gov_logo_p) as gl:
                    gl_rgba = gl.convert("RGBA").resize((150, 150), Image.LANCZOS)
                    img.paste(gl_rgba, (35, 25), gl_rgba)
                    img.paste(gl_rgba, (W - 185, 25), gl_rgba)
            except Exception: pass

        fs_top, _ = get_best_fitted_mixed_font_size(top_bar_title, max_w=W - 420, max_h=160, bn_font_path=bar_font, start_size=170, min_size=80)
        draw_mixed_text_centered(draw, W // 2, 100, top_bar_title, bar_font, fs_top, "#ffffff")

        # মিডল সেকশন (সাদা ব্যাকগ্রাউন্ডে বড় লেখা)
        draw.rectangle([0, 200, W, 880], fill="#ffffff")

        # 🌟 লাইন ১ (উজ্জ্বল লাল) ও লাইন ২ (গাঢ় কালো)
        fs_l1, h1 = get_best_fitted_mixed_font_size(middle_line1, max_w=W - 80, max_h=340, bn_font_path=font_line1, start_size=330, min_size=130)
        fs_l2, h2 = get_best_fitted_mixed_font_size(middle_line2, max_w=W - 80, max_h=290, bn_font_path=font_line2, start_size=290, min_size=110)

        line_spacing = 15
        total_content_height = h1 + line_spacing + h2
        start_y = 540 - (total_content_height // 2)

        # লাল লাইন ১
        draw_mixed_text_centered(draw, W // 2, start_y + (h1 // 2), middle_line1, font_line1, fs_l1, "#d80000")

        # কালো লাইন ২
        draw_mixed_text_centered(draw, W // 2, start_y + h1 + line_spacing + (h2 // 2), middle_line2, font_line2, fs_l2, "#000000")

        # বটম বার (অনলাইন আবেদন / ফরম পূরণ / আবেদনপত্র তৈরি একমাত্র এখানেই থাকবে)
        draw.rectangle([0, 880, W, H], fill=green_bg)
        fs_bot, _ = get_best_fitted_mixed_font_size(bot_text, max_w=W - 80, max_h=160, bn_font_path=bar_font, start_size=170, min_size=80)
        draw_mixed_text_centered(draw, W // 2, 980, bot_text, bar_font, fs_bot, "#ffe600")

        draw.line([(0, 200), (W, 200)], fill="#003310", width=7)
        draw.line([(0, 880), (W, 880)], fill="#003310", width=7)

    img.save(output_path, "JPEG", quality=100, subsampling=0)
    print(f"✅ Generated Smart Dynamic Thumbnail: '{middle_line1} | {middle_line2} | {bot_text}'")
