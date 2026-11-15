# -*- coding: utf-8 -*-
import hashlib
import os
import re
import random
from PIL import Image, ImageDraw, ImageFont
from ai_service import strip_unwanted_chars

FONTS_DIR = "Fonts"
PHOTOS_DIR = "Photos"

# ১৮টি নির্দিষ্ট প্রতিষ্ঠান ও তাদের লোগো ফাইলের ম্যাপিং
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

# ৫টি মার্জিত, প্রফেশনাল ও হাই-কনট্রাস্ট কালার থিম
PRO_THEMES = [
    {
        "bar_bg": "#064E3B", "accent": "#FACC15", "canvas": "#F8FAFC", "grid": "#E2E8F0",
        "org_pill": "#0F172A", "org_text": "#FACC15", "red": "#D90429", "dark": "#0F172A",
        "chip_bg": "#ECFDF5", "chip_border": "#059669", "chip_text": "#064E3B", "bot_text": "#FACC15",
    },
    {
        "bar_bg": "#0F172A", "accent": "#F59E0B", "canvas": "#F8FAFC", "grid": "#E2E8F0",
        "org_pill": "#B91C1C", "org_text": "#FFFFFF", "red": "#DC2626", "dark": "#0F172A",
        "chip_bg": "#FEF3C7", "chip_border": "#D97706", "chip_text": "#78350F", "bot_text": "#FDE047",
    },
    {
        "bar_bg": "#7F1D1D", "accent": "#FDE047", "canvas": "#FFFDF9", "grid": "#F3E8E2",
        "org_pill": "#0F172A", "org_text": "#FFFFFF", "red": "#B91C1C", "dark": "#1E293B",
        "chip_bg": "#FEF2F2", "chip_border": "#DC2626", "chip_text": "#7F1D1D", "bot_text": "#FDE047",
    },
    {
        "bar_bg": "#115E59", "accent": "#FACC15", "canvas": "#F8FAFC", "grid": "#E2E8F0",
        "org_pill": "#1E293B", "org_text": "#FDE047", "red": "#D90429", "dark": "#0F172A",
        "chip_bg": "#F0FDFA", "chip_border": "#0D9488", "chip_text": "#115E59", "bot_text": "#FACC15",
    },
    {
        "bar_bg": "#1E1B4B", "accent": "#FBBF24", "canvas": "#F8FAFC", "grid": "#E2E8F0",
        "org_pill": "#DC2626", "org_text": "#FFFFFF", "red": "#DC2626", "dark": "#0F172A",
        "chip_bg": "#EEF2FF", "chip_border": "#4F46E5", "chip_text": "#1E1B4B", "bot_text": "#FDE047",
    },
]


def find_matched_org_logo(title_text):
    if not os.path.exists(PHOTOS_DIR):
        return None
    disk_files = {f.lower(): os.path.join(PHOTOS_DIR, f) for f in os.listdir(PHOTOS_DIR)}
    t_lower = str(title_text).lower()
    for keywords, filenames in ORG_LOGO_RULES:
        if any(k in t_lower for k in keywords):
            for fn in filenames:
                if fn.lower() in disk_files:
                    return disk_files[fn.lower()]
    return None


def is_valid_bengali_font(font_path):
    try:
        test_font = ImageFont.truetype(font_path, 40)
        mask = test_font.getmask("বাংলাদেশ চাকরি")
        if mask.size[0] > 0 and mask.size[1] > 0:
            return True
    except Exception:
        pass
    return False


def get_verified_bengali_fonts():
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
    valid_fonts = get_verified_bengali_fonts()
    for f in valid_fonts:
        if "kalpurush" in os.path.basename(f).lower():
            return f
    return valid_fonts[0] if valid_fonts else "BengaliFont.ttf"


def get_two_distinct_middle_fonts():
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
        return get_fixed_bar_font(), get_fixed_bar_font()


def get_english_bold_font(font_size):
    eng_size = max(16, int(font_size * 0.85))
    eng_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    ]
    for p in eng_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, eng_size)
            except Exception:
                pass
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", eng_size)
    except Exception:
        return ImageFont.load_default()


def split_text_by_script(text):
    tokens = re.split(r'([A-Za-z0-9/.\-]+)', str(text))
    segments = []
    for t in tokens:
        if not t:
            continue
        is_eng = bool(re.match(r'^[A-Za-z0-9/.\-]+$', t))
        segments.append((t, is_eng))
    return segments


def measure_mixed_text(text, bn_font_path, font_size):
    try:
        bn_font = ImageFont.truetype(bn_font_path, font_size)
    except Exception:
        bn_font = ImageFont.load_default()
    eng_font = get_english_bold_font(font_size)

    segments = split_text_by_script(text)
    total_w, max_h = 0, 0
    for seg_text, is_eng in segments:
        f = eng_font if is_eng else bn_font
        bbox = f.getbbox(seg_text)
        total_w += (bbox[2] - bbox[0])
        h = bbox[3] - bbox[1]
        if h > max_h:
            max_h = h
    return total_w, max_h


def get_best_fitted_mixed_font_size(text, max_w, max_h, bn_font_path, start_size=260, min_size=40):
    for fs in range(start_size, min_size - 1, -4):
        w, h = measure_mixed_text(text, bn_font_path, fs)
        if w <= max_w and h <= max_h:
            return fs, w, h
    w, h = measure_mixed_text(text, bn_font_path, min_size)
    return min_size, w, h


def draw_mixed_text_centered(draw, center_x, center_y, text, bn_font_path, font_size, fill_color, shadow_color=None, shadow_offset=4):
    try:
        bn_font = ImageFont.truetype(bn_font_path, font_size)
    except Exception:
        bn_font = ImageFont.load_default()
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

    start_x = center_x - (total_w // 2)

    if shadow_color:
        cur_x = start_x + shadow_offset
        for (seg_text, is_eng), w in zip(segments, seg_widths):
            f = eng_font if is_eng else bn_font
            draw.text((cur_x, center_y + shadow_offset), seg_text, font=f, fill=shadow_color, anchor="lm")
            cur_x += w

    cur_x = start_x
    for (seg_text, is_eng), w in zip(segments, seg_widths):
        f = eng_font if is_eng else bn_font
        draw.text((cur_x, center_y), seg_text, font=f, fill=fill_color, anchor="lm")
        cur_x += w


def draw_subtle_grid_background(draw, W, H, y_start, y_end, canvas_color, grid_color):
    draw.rectangle([0, y_start, W, y_end], fill=canvas_color)
    step = 60
    for x in range(0, W, step):
        draw.line([(x, y_start), (x, y_end)], fill=grid_color, width=1)
    for y in range(y_start, y_end, step):
        draw.line([(0, y), (W, y)], fill=grid_color, width=1)


def draw_pill(draw, cx, cy, text, font_path, max_w, max_h, bg_color, text_color, border_color=None, border_w=0, pad_x=44, pad_y=20, start_fs=76, min_fs=34, shadow=False):
    fs, tw, th = get_best_fitted_mixed_font_size(text, max_w=max_w - 2 * pad_x, max_h=max_h - 2 * pad_y, bn_font_path=font_path, start_size=start_fs, min_size=min_fs)
    pw = min(max_w, tw + 2 * pad_x)
    ph = max(th + 2 * pad_y, int(fs * 1.45))
    x1, y1 = int(cx - pw // 2), int(cy - ph // 2)
    x2, y2 = int(cx + pw // 2), int(cy + ph // 2)
    radius = ph // 2

    if shadow:
        draw.rounded_rectangle([x1 + 5, y1 + 6, x2 + 5, y2 + 6], radius=radius, fill="#CBD5E1")
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=bg_color, outline=border_color, width=border_w)
    draw_mixed_text_centered(draw, cx, cy, text, font_path, fs, text_color)
    return pw, ph


def render_logo_card(img, draw, logo_path, rect, border_color):
    x1, y1, x2, y2 = rect
    draw.rounded_rectangle([x1 + 6, y1 + 8, x2 + 6, y2 + 8], radius=28, fill="#CBD5E1")
    draw.rounded_rectangle([x1, y1, x2, y2], radius=28, fill="#FFFFFF", outline=border_color, width=5)

    box_w, box_h = x2 - x1, y2 - y1
    try:
        with Image.open(logo_path) as raw_logo:
            logo_rgba = raw_logo.convert("RGBA")
            max_w, max_h = int(box_w * 0.80), int(box_h * 0.80)
            logo_rgba.thumbnail((max_w, max_h), Image.LANCZOS)
            lw, lh = logo_rgba.size
            px = x1 + (box_w - lw) // 2
            py = y1 + (box_h - lh) // 2
            img.paste(logo_rgba, (px, py), logo_rgba)
            return True
    except Exception as e:
        print(f"⚠️ Logo render notice: {e}")
        return False


def _detect_is_private(title_text, job_cat):
    combined = f"{title_text} {job_cat}".lower()
    if any(k in combined for k in ["বেসরকারি", "প্রাইভেট", "লিমিটেড", "ফার্মা", "গ্রুপ", "ফাউন্ডেশন", "বিকাশ কেন্দ্র", "এনজিও", "ltd"]):
        return True
    return False


def generate_dynamic_thumbnail(title, output_path, thumb_meta=None):
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), "#F8FAFC")
    draw = ImageDraw.Draw(img)

    if not thumb_meta:
        thumb_meta = {}

    job_cat = strip_unwanted_chars(thumb_meta.get("job_category", ""))
    is_private = _detect_is_private(title, job_cat)

    if is_private:
        header_title = "বেসরকারি চাকরির নিয়োগ"
    elif "স্বায়ত্তশাসিত" in job_cat:
        header_title = "স্বায়ত্তশাসিত চাকরির নিয়োগ"
    else:
        header_title = "সরকারি চাকরির নিয়োগ"

    org_short = strip_unwanted_chars(thumb_meta.get("org_short") or thumb_meta.get("top_text") or "")
    if not org_short:
        clean_t = title.split('|')[0].split('-')[0].strip()
        org_short = " ".join((clean_t.split("নিয়োগ")[0].strip() if "নিয়োগ" in clean_t else clean_t).split()[:4])

    main_red = strip_unwanted_chars(thumb_meta.get("main_red") or thumb_meta.get("row1_text") or "জরুরি নিয়োগ বিজ্ঞপ্তি")
    main_dark = strip_unwanted_chars(thumb_meta.get("main_dark") or thumb_meta.get("row2_text") or "যোগ্যতা ও বিস্তারিত")
    bot_text = strip_unwanted_chars(thumb_meta.get("bot_text") or "প্রতিটি পদের যোগ্যতা, বেতন ও ফি")

    chips = []
    for k in ("pill_1", "pill_2", "pill_3"):
        val = strip_unwanted_chars(thumb_meta.get(k, ""))
        if val and val not in chips:
            chips.append(val)
    if not chips:
        chips = ["৬৪ জেলা", "সব পদের তথ্য", "বিস্তারিত বেতন ও ফি"]

    # টাইটেল অনুযায়ী কনসিস্টেন্ট কিন্তু বৈচিত্র্যময় প্রফেশনাল থিম নির্বাচন
    theme_idx = int(hashlib.md5(title.encode("utf-8")).hexdigest(), 16) % len(PRO_THEMES)
    theme = PRO_THEMES[theme_idx]

    bar_font = get_fixed_bar_font()
    font_line1, font_line2 = get_two_distinct_middle_fonts()
    matched_logo = find_matched_org_logo(title) or find_matched_org_logo(org_short)

    # ---------------- ১. টপ হেডার বার (0 .. 170px) ----------------
    draw.rectangle([0, 0, W, 170], fill=theme["bar_bg"])
    draw.rectangle([0, 170, W, 180], fill=theme["accent"])

    if not is_private:
        gov_logo_p = os.path.join(PHOTOS_DIR, "Govbd.png")
        if os.path.exists(gov_logo_p):
            try:
                with Image.open(gov_logo_p) as gl:
                    gl_rgba = gl.convert("RGBA").resize((124, 124), Image.LANCZOS)
                    img.paste(gl_rgba, (44, 23), gl_rgba)
                    img.paste(gl_rgba, (W - 168, 23), gl_rgba)
            except Exception:
                pass
    else:
        # বেসরকারি চাকরিতে ডেকোরেটিভ গোল্ডেন ডায়মন্ড ব্যাজ
        for cx in (106, W - 106):
            cy = 85
            r = 26
            draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=theme["accent"])

    fs_top, _, _ = get_best_fitted_mixed_font_size(header_title, max_w=W - 460, max_h=125, bn_font_path=bar_font, start_size=120, min_size=56)
    draw_mixed_text_centered(draw, W // 2, 85, header_title, bar_font, fs_top, "#FFFFFF")

    # ---------------- ২. মাঝের প্রফেশনাল ক্যানভাস (180 .. 905px) ----------------
    draw_subtle_grid_background(draw, W, H, 180, 905, theme["canvas"], theme["grid"])
    # বামে ও ডানে হালকা ব্র্যান্ড অ্যাকসেন্ট স্ট্রিপ
    draw.rectangle([0, 180, 18, 905], fill=theme["bar_bg"])
    draw.rectangle([W - 18, 180, W, 905], fill=theme["bar_bg"])

    if matched_logo and os.path.exists(matched_logo):
        # স্পেশাল অর্গানাইজেশন লোগো মোড (ডানে প্রিমিয়াম কার্ড)
        left_cx = 635
        render_logo_card(img, draw, matched_logo, (1270, 215, 1865, 870), theme["bar_bg"])

        draw_pill(
            draw, left_cx, 265, org_short, bar_font,
            max_w=1140, max_h=95, bg_color=theme["org_pill"], text_color=theme["org_text"],
            start_fs=66, min_fs=36, shadow=True,
        )

        fs1, _, _ = get_best_fitted_mixed_font_size(main_red, max_w=1160, max_h=190, bn_font_path=font_line1, start_size=210, min_size=75)
        draw_mixed_text_centered(draw, left_cx, 440, main_red, font_line1, fs1, theme["red"], shadow_color="#E2E8F0", shadow_offset=5)

        fs2, _, _ = get_best_fitted_mixed_font_size(main_dark, max_w=1160, max_h=150, bn_font_path=font_line2, start_size=155, min_size=62)
        draw_mixed_text_centered(draw, left_cx, 625, main_dark, font_line2, fs2, theme["dark"])

        # নিচে ২টি ইনফো চিপ
        show_chips = chips[:2]
        chip_w = 530
        gap = 36
        start_cx = left_cx - ((len(show_chips) - 1) * (chip_w + gap)) // 2
        for idx, ch_txt in enumerate(show_chips):
            draw_pill(
                draw, start_cx + idx * (chip_w + gap), 805, ch_txt, bar_font,
                max_w=chip_w, max_h=88, bg_color=theme["chip_bg"], text_color=theme["chip_text"],
                border_color=theme["chip_border"], border_w=4, pad_x=28, pad_y=14, start_fs=48, min_fs=28,
            )
    else:
        # স্ট্যান্ডার্ড ফুল-ওয়াইড্থ প্রো ডিজাইন
        draw_pill(
            draw, W // 2, 265, org_short, bar_font,
            max_w=1460, max_h=102, bg_color=theme["org_pill"], text_color=theme["org_text"],
            start_fs=74, min_fs=40, shadow=True,
        )

        fs1, _, _ = get_best_fitted_mixed_font_size(main_red, max_w=1720, max_h=210, bn_font_path=font_line1, start_size=240, min_size=85)
        draw_mixed_text_centered(draw, W // 2, 445, main_red, font_line1, fs1, theme["red"], shadow_color="#E2E8F0", shadow_offset=5)

        fs2, _, _ = get_best_fitted_mixed_font_size(main_dark, max_w=1700, max_h=160, bn_font_path=font_line2, start_size=170, min_size=65)
        draw_mixed_text_centered(draw, W // 2, 645, main_dark, font_line2, fs2, theme["dark"])

        # নিচে ৩টি ইনফো চিপ পিল
        show_chips = chips[:3]
        chip_w = 520
        gap = 38
        total_span = len(show_chips) * chip_w + (len(show_chips) - 1) * gap
        first_cx = (W - total_span) // 2 + chip_w // 2
        for idx, ch_txt in enumerate(show_chips):
            draw_pill(
                draw, first_cx + idx * (chip_w + gap), 815, ch_txt, bar_font,
                max_w=chip_w, max_h=90, bg_color=theme["chip_bg"], text_color=theme["chip_text"],
                border_color=theme["chip_border"], border_w=4, pad_x=28, pad_y=14, start_fs=50, min_fs=28,
            )

    # ---------------- ৩. বটম বার (905 .. 1080px — YouTube টাইমস্ট্যাম্প সেফ) ----------------
    draw.rectangle([0, 905, W, 915], fill=theme["accent"])
    draw.rectangle([0, 915, W, H], fill=theme["bar_bg"])

    # ডানদিকের ৩২০ পিক্সেল (YouTube-এর 3:35 টাইমস্ট্যাম্প জোন) নিরাপদ রেখে বামে/মাঝে লেখা বসানো
    safe_bot_cx = 840
    fs_bot, _, _ = get_best_fitted_mixed_font_size(bot_text, max_w=1420, max_h=120, bn_font_path=bar_font, start_size=110, min_size=50)
    draw_mixed_text_centered(draw, safe_bot_cx, 998, bot_text, bar_font, fs_bot, theme["bot_text"])

    img.save(output_path, "JPEG", quality=100, subsampling=0)
    print(f"✅ Pro Thumbnail Ready: [{header_title}] '{org_short}' -> '{main_red} | {main_dark}'")
