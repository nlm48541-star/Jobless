# -*- coding: utf-8 -*-
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

# ১০টি ভিন্ন ভিন্ন প্রফেশনাল কালার থিম (৭টি লাইট + ৩টি ডার্ক — প্রতিটিতে ব্যাকগ্রাউন্ড ও লেখার রঙ আলাদা)
LIGHT_THEMES = [
    {
        "is_dark": False, "bar_bg": "#064E3B", "bar_text": "#FFFFFF", "bot_bg": "#064E3B", "bot_text": "#FACC15",
        "accent": "#FACC15", "canvas": "#F8FAFC", "grid": "#E2E8F0", "shadow": "#CBD5E1",
        "org_pill": "#0F172A", "org_text": "#FACC15", "hero_color": "#D90429", "sub_color": "#0F172A",
        "chip_bg": "#ECFDF5", "chip_border": "#059669", "chip_text": "#064E3B",
    },
    {
        "is_dark": False, "bar_bg": "#0F172A", "bar_text": "#FFFFFF", "bot_bg": "#1E293B", "bot_text": "#FDE047",
        "accent": "#F59E0B", "canvas": "#F8FAFC", "grid": "#E2E8F0", "shadow": "#CBD5E1",
        "org_pill": "#DC2626", "org_text": "#FFFFFF", "hero_color": "#1D4ED8", "sub_color": "#111827",
        "chip_bg": "#FEF3C7", "chip_border": "#D97706", "chip_text": "#78350F",
    },
    {
        "is_dark": False, "bar_bg": "#7F1D1D", "bar_text": "#FFFFFF", "bot_bg": "#7F1D1D", "bot_text": "#FDE047",
        "accent": "#FDE047", "canvas": "#FFFDF7", "grid": "#F3E8E2", "shadow": "#E2D5CE",
        "org_pill": "#0F172A", "org_text": "#FFFFFF", "hero_color": "#B91C1C", "sub_color": "#1E293B",
        "chip_bg": "#FEF2F2", "chip_border": "#DC2626", "chip_text": "#7F1D1D",
    },
    {
        "is_dark": False, "bar_bg": "#115E59", "bar_text": "#FFFFFF", "bot_bg": "#0F766E", "bot_text": "#FEF08A",
        "accent": "#FACC15", "canvas": "#F4FBF9", "grid": "#D7EFEA", "shadow": "#C4E2DC",
        "org_pill": "#1E293B", "org_text": "#FDE047", "hero_color": "#EA580C", "sub_color": "#0F172A",
        "chip_bg": "#F0FDFA", "chip_border": "#0D9488", "chip_text": "#115E59",
    },
    {
        "is_dark": False, "bar_bg": "#1E1B4B", "bar_text": "#FFFFFF", "bot_bg": "#312E81", "bot_text": "#FDE047",
        "accent": "#FBBF24", "canvas": "#F5F7FF", "grid": "#E0E7FF", "shadow": "#C7D2FE",
        "org_pill": "#BE123C", "org_text": "#FFFFFF", "hero_color": "#4338CA", "sub_color": "#0F172A",
        "chip_bg": "#EEF2FF", "chip_border": "#4F46E5", "chip_text": "#1E1B4B",
    },
    {
        "is_dark": False, "bar_bg": "#4C1D95", "bar_text": "#FFFFFF", "bot_bg": "#5B21B6", "bot_text": "#FDE047",
        "accent": "#F59E0B", "canvas": "#FAF7FF", "grid": "#EDE9FE", "shadow": "#DDD6FE",
        "org_pill": "#0F172A", "org_text": "#FDE047", "hero_color": "#9D174D", "sub_color": "#1E1B4B",
        "chip_bg": "#FDF2F8", "chip_border": "#DB2777", "chip_text": "#831843",
    },
    {
        "is_dark": False, "bar_bg": "#14532D", "bar_text": "#FEF9C3", "bot_bg": "#0F172A", "bot_text": "#4ADE80",
        "accent": "#22C55E", "canvas": "#F9FAFB", "grid": "#E5E7EB", "shadow": "#D1D5DB",
        "org_pill": "#EA580C", "org_text": "#FFFFFF", "hero_color": "#15803D", "sub_color": "#0F172A",
        "chip_bg": "#FFF7ED", "chip_border": "#EA580C", "chip_text": "#9A3412",
    },
]

DARK_THEMES = [
    {
        "is_dark": True, "bar_bg": "#020617", "bar_text": "#FACC15", "bot_bg": "#1D4ED8", "bot_text": "#FFFFFF",
        "accent": "#38BDF8", "canvas": "#0F172A", "grid": "#1E293B", "shadow": "#020617",
        "org_pill": "#DC2626", "org_text": "#FFFFFF", "hero_color": "#FACC15", "sub_color": "#E2E8F0",
        "chip_bg": "#1E293B", "chip_border": "#38BDF8", "chip_text": "#F8FAFC",
    },
    {
        "is_dark": True, "bar_bg": "#18181B", "bar_text": "#FFFFFF", "bot_bg": "#B91C1C", "bot_text": "#FEF08A",
        "accent": "#10B981", "canvas": "#111827", "grid": "#1F2937", "shadow": "#030712",
        "org_pill": "#FACC15", "org_text": "#0F172A", "hero_color": "#34D399", "sub_color": "#F8FAFC",
        "chip_bg": "#1F2937", "chip_border": "#10B981", "chip_text": "#ECFDF5",
    },
    {
        "is_dark": True, "bar_bg": "#450A0A", "bar_text": "#FDE047", "bot_bg": "#0F172A", "bot_text": "#38BDF8",
        "accent": "#F59E0B", "canvas": "#1C0F13", "grid": "#331820", "shadow": "#090406",
        "org_pill": "#FDE047", "org_text": "#111827", "hero_color": "#FB7185", "sub_color": "#F1F5F9",
        "chip_bg": "#2D151C", "chip_border": "#F59E0B", "chip_text": "#FEF3C7",
    },
]

ALL_THEMES = LIGHT_THEMES + DARK_THEMES
VALID_LAYOUTS = ["poster_classic", "split_impact", "headline_first", "dark_bold", "stat_cards"]


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


def get_best_fitted_mixed_font_size(text, max_w, max_h, bn_font_path, start_size=260, min_size=36):
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


def wrap_two_lines(text):
    words = str(text).split()
    if len(words) <= 2:
        return text, ""
    mid = (len(words) + 1) // 2
    return " ".join(words[:mid]), " ".join(words[mid:])


def draw_subtle_grid_background(draw, x1, y1, x2, y2, canvas_color, grid_color):
    draw.rectangle([x1, y1, x2, y2], fill=canvas_color)
    step = 60
    for x in range(x1, x2, step):
        draw.line([(x, y1), (x, y2)], fill=grid_color, width=1)
    for y in range(y1, y2, step):
        draw.line([(x1, y), (x2, y)], fill=grid_color, width=1)


def draw_pill(draw, cx, cy, text, font_path, max_w, max_h, bg_color, text_color, border_color=None, border_w=0, pad_x=48, pad_y=14, start_fs=112, min_fs=34, shadow_color=None):
    fs, tw, th = get_best_fitted_mixed_font_size(
        text,
        max_w=max_w - 2 * pad_x,
        max_h=max_h - 2 * pad_y,
        bn_font_path=font_path,
        start_size=start_fs,
        min_size=min_fs,
    )
    pw = min(max_w, tw + 2 * pad_x)
    ph = min(max_h, max(th + 2 * pad_y, int(fs * 1.38)))
    x1, y1 = int(cx - pw // 2), int(cy - ph // 2)
    x2, y2 = int(cx + pw // 2), int(cy + ph // 2)
    radius = ph // 2

    if shadow_color:
        draw.rounded_rectangle([x1 + 5, y1 + 6, x2 + 5, y2 + 6], radius=radius, fill=shadow_color)
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=bg_color, outline=border_color, width=border_w)
    draw_mixed_text_centered(draw, cx, cy, text, font_path, fs, text_color)
    return pw, ph


def render_logo_card(img, draw, logo_path, rect, border_color, shadow_color="#CBD5E1"):
    x1, y1, x2, y2 = rect
    draw.rounded_rectangle([x1 + 6, y1 + 8, x2 + 6, y2 + 8], radius=28, fill=shadow_color)
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


def draw_header_emblems(img, draw, W, center_y, size, is_private, accent_color):
    if not is_private:
        gov_logo_p = os.path.join(PHOTOS_DIR, "Govbd.png")
        if os.path.exists(gov_logo_p):
            try:
                with Image.open(gov_logo_p) as gl:
                    gl_rgba = gl.convert("RGBA").resize((size, size), Image.LANCZOS)
                    img.paste(gl_rgba, (44, center_y - size // 2), gl_rgba)
                    img.paste(gl_rgba, (W - 44 - size, center_y - size // 2), gl_rgba)
                    return
            except Exception:
                pass
    for cx in (96, W - 96):
        r = 24
        draw.polygon([(cx, center_y - r), (cx + r, center_y), (cx, center_y + r), (cx - r, center_y)], fill=accent_color)


def _detect_is_private(title_text, job_cat):
    combined = f"{title_text} {job_cat}".lower()
    if any(k in combined for k in ["বেসরকারি", "প্রাইভেট", "লিমিটেড", "ফার্মা", "গ্রুপ", "ফাউন্ডেশন", "বিকাশ কেন্দ্র", "এনজিও", "ltd"]):
        return True
    return False


def _extract_highlights(thumb_meta):
    hl = thumb_meta.get("highlights")
    out = []
    if isinstance(hl, list):
        for item in hl[:3]:
            if isinstance(item, dict):
                lbl = strip_unwanted_chars(item.get("label", ""))
                val = strip_unwanted_chars(item.get("value", ""))
                if val:
                    out.append({"label": lbl or "তথ্য", "value": val})
            elif isinstance(item, str) and item.strip():
                out.append({"label": "তথ্য", "value": strip_unwanted_chars(item)})
    if not out:
        for k in ("pill_1", "pill_2", "pill_3"):
            v = strip_unwanted_chars(thumb_meta.get(k, ""))
            if v:
                out.append({"label": "তথ্য", "value": v})
    while len(out) < 3:
        defaults = [
            {"label": "যোগ্যতা", "value": "বিজ্ঞপ্তি অনুযায়ী"},
            {"label": "আবেদন", "value": "সকল জেলা"},
            {"label": "বিস্তারিত", "value": "বেতন ও ফি"},
        ]
        out.append(defaults[len(out)])
    return out[:3]


def _chip_text(h):
    lbl, val = h["label"], h["value"]
    if lbl in ("তথ্য", "") or lbl in val:
        return val
    return f"{lbl}: {val}" if len(f"{lbl}: {val}") <= 24 else val


# =========================================================================
# 🌟 ৫টি ডাইনামিক লেআউট ইঞ্জিন
# =========================================================================

def _render_poster_classic(img, draw, W, H, theme, data, fonts, matched_logo, is_private):
    bar_font, font1, font2 = fonts
    draw.rectangle([0, 0, W, 145], fill=theme["bar_bg"])
    draw.rectangle([0, 145, W, 154], fill=theme["accent"])
    draw_header_emblems(img, draw, W, 72, 110, is_private, theme["accent"])

    fs_top, _, _ = get_best_fitted_mixed_font_size(data["top_tag"], max_w=W - 440, max_h=108, bn_font_path=bar_font, start_size=108, min_size=50)
    draw_mixed_text_centered(draw, W // 2, 72, data["top_tag"], bar_font, fs_top, theme["bar_text"])

    draw_subtle_grid_background(draw, 0, 154, W, 900, theme["canvas"], theme["grid"])
    draw.rectangle([0, 154, 18, 900], fill=theme["bar_bg"])
    draw.rectangle([W - 18, 154, W, 900], fill=theme["bar_bg"])

    cx = 635 if matched_logo else W // 2
    max_w = 1160 if matched_logo else 1740

    if matched_logo:
        render_logo_card(img, draw, matched_logo, (1270, 185, 1865, 875), theme["bar_bg"], shadow_color=theme["shadow"])

    draw_pill(
        draw, cx, 246, data["org_short"], bar_font,
        max_w=max_w, max_h=148, bg_color=theme["org_pill"], text_color=theme["org_text"],
        pad_x=52, pad_y=14, start_fs=112, min_fs=50, shadow_color=theme["shadow"],
    )

    fs1, _, _ = get_best_fitted_mixed_font_size(data["hero_text"], max_w=max_w, max_h=205, bn_font_path=font1, start_size=230, min_size=80)
    draw_mixed_text_centered(draw, cx, 445, data["hero_text"], font1, fs1, theme["hero_color"], shadow_color=theme["shadow"], shadow_offset=5)

    fs2, _, _ = get_best_fitted_mixed_font_size(data["sub_text"], max_w=max_w, max_h=155, bn_font_path=font2, start_size=165, min_size=62)
    draw_mixed_text_centered(draw, cx, 635, data["sub_text"], font2, fs2, theme["sub_color"])

    chips = [_chip_text(h) for h in data["highlights"][: (2 if matched_logo else 3)]]
    chip_w = 545 if matched_logo else 550
    gap = 34
    total_span = len(chips) * chip_w + (len(chips) - 1) * gap
    first_cx = cx - total_span // 2 + chip_w // 2
    for idx, ch_txt in enumerate(chips):
        draw_pill(
            draw, first_cx + idx * (chip_w + gap), 815, ch_txt, bar_font,
            max_w=chip_w, max_h=108, bg_color=theme["chip_bg"], text_color=theme["chip_text"],
            border_color=theme["chip_border"], border_w=4, pad_x=24, pad_y=12, start_fs=62, min_fs=32,
        )

    draw.rectangle([0, 900, W, 910], fill=theme["accent"])
    draw.rectangle([0, 910, W, H], fill=theme["bot_bg"])
    fs_bot, _, _ = get_best_fitted_mixed_font_size(data["bot_text"], max_w=1440, max_h=125, bn_font_path=bar_font, start_size=112, min_size=50)
    draw_mixed_text_centered(draw, 840, 995, data["bot_text"], bar_font, fs_bot, theme["bot_text"])


def _render_split_impact(img, draw, W, H, theme, data, fonts, matched_logo, is_private):
    bar_font, font1, font2 = fonts
    split_x = 730

    # বাম রঙিন প্যানেল (0 .. 730)
    draw.rectangle([0, 0, split_x, H], fill=theme["bar_bg"])
    draw.rectangle([split_x, 0, split_x + 12, H], fill=theme["accent"])

    # ডান ক্যানভাস (742 .. 1920)
    draw_subtle_grid_background(draw, split_x + 12, 0, W, H, theme["canvas"], theme["grid"])

    # বাম প্যানেলে: টপ ট্যাগ পিল + বড় ২-লাইনের প্রতিষ্ঠানের নাম + লোগো/হাইলাইট
    left_cx = split_x // 2
    draw_pill(
        draw, left_cx, 110, data["top_tag"], bar_font,
        max_w=640, max_h=92, bg_color=theme["org_pill"], text_color=theme["org_text"],
        pad_x=32, pad_y=10, start_fs=58, min_fs=32,
    )

    l1, l2 = wrap_two_lines(data["org_short"])
    if matched_logo:
        if l2:
            fs_o1, _, _ = get_best_fitted_mixed_font_size(l1, max_w=650, max_h=115, bn_font_path=bar_font, start_size=110, min_size=54)
            fs_o2, _, _ = get_best_fitted_mixed_font_size(l2, max_w=650, max_h=115, bn_font_path=bar_font, start_size=110, min_size=54)
            fs_o = min(fs_o1, fs_o2)
            draw_mixed_text_centered(draw, left_cx, 255, l1, bar_font, fs_o, theme["bar_text"])
            draw_mixed_text_centered(draw, left_cx, 365, l2, bar_font, fs_o, theme["bar_text"])
        else:
            fs_o, _, _ = get_best_fitted_mixed_font_size(l1, max_w=650, max_h=140, bn_font_path=bar_font, start_size=120, min_size=56)
            draw_mixed_text_centered(draw, left_cx, 300, l1, bar_font, fs_o, theme["bar_text"])
        render_logo_card(img, draw, matched_logo, (165, 455, 565, 815), theme["accent"], shadow_color=theme["shadow"])
    else:
        if l2:
            fs_o1, _, _ = get_best_fitted_mixed_font_size(l1, max_w=650, max_h=150, bn_font_path=bar_font, start_size=130, min_size=60)
            fs_o2, _, _ = get_best_fitted_mixed_font_size(l2, max_w=650, max_h=150, bn_font_path=bar_font, start_size=130, min_size=60)
            fs_o = min(fs_o1, fs_o2)
            draw_mixed_text_centered(draw, left_cx, 360, l1, bar_font, fs_o, theme["bar_text"])
            draw_mixed_text_centered(draw, left_cx, 495, l2, bar_font, fs_o, theme["bar_text"])
        else:
            fs_o, _, _ = get_best_fitted_mixed_font_size(l1, max_w=650, max_h=180, bn_font_path=bar_font, start_size=140, min_size=64)
            draw_mixed_text_centered(draw, left_cx, 420, l1, bar_font, fs_o, theme["bar_text"])

        if not is_private:
            gov_logo_p = os.path.join(PHOTOS_DIR, "Govbd.png")
            if os.path.exists(gov_logo_p):
                try:
                    with Image.open(gov_logo_p) as gl:
                        gl_rgba = gl.convert("RGBA").resize((150, 150), Image.LANCZOS)
                        img.paste(gl_rgba, (left_cx - 75, 620), gl_rgba)
                except Exception:
                    pass

    # বাম প্যানেলের নিচে ১ম হাইলাইট
    h0 = _chip_text(data["highlights"][0])
    draw_pill(
        draw, left_cx, 945, h0, bar_font,
        max_w=650, max_h=110, bg_color=theme["accent"], text_color="#0F172A",
        pad_x=32, pad_y=14, start_fs=62, min_fs=34,
    )

    # ডান ক্যানভাসে: হিরো + সাব + ২টি চিপ + টাইমস্ট্যাম্প-সেফ CTA
    right_cx = 1330
    fs1, _, _ = get_best_fitted_mixed_font_size(data["hero_text"], max_w=1080, max_h=240, bn_font_path=font1, start_size=230, min_size=82)
    draw_mixed_text_centered(draw, right_cx, 275, data["hero_text"], font1, fs1, theme["hero_color"], shadow_color=theme["shadow"], shadow_offset=5)

    fs2, _, _ = get_best_fitted_mixed_font_size(data["sub_text"], max_w=1080, max_h=170, bn_font_path=font2, start_size=165, min_size=62)
    draw_mixed_text_centered(draw, right_cx, 505, data["sub_text"], font2, fs2, theme["sub_color"])

    c1 = _chip_text(data["highlights"][1])
    c2 = _chip_text(data["highlights"][2])
    draw_pill(draw, 1055, 710, c1, bar_font, max_w=510, max_h=108, bg_color=theme["chip_bg"], text_color=theme["chip_text"], border_color=theme["chip_border"], border_w=4, pad_x=22, pad_y=12, start_fs=58, min_fs=30)
    draw_pill(draw, 1605, 710, c2, bar_font, max_w=510, max_h=108, bg_color=theme["chip_bg"], text_color=theme["chip_text"], border_color=theme["chip_border"], border_w=4, pad_x=22, pad_y=12, start_fs=58, min_fs=30)

    # বটম CTA পিল (ডান কোণার 3:35 টাইমস্ট্যাম্প থেকে নিরাপদ)
    draw_pill(
        draw, 1160, 935, data["bot_text"], bar_font,
        max_w=780, max_h=118, bg_color=theme["bot_bg"], text_color=theme["bot_text"],
        pad_x=40, pad_y=14, start_fs=72, min_fs=38, shadow_color=theme["shadow"],
    )


def _render_headline_first(img, draw, W, H, theme, data, fonts, matched_logo, is_private):
    bar_font, font1, font2 = fonts
    draw_subtle_grid_background(draw, 0, 0, W, 910, theme["canvas"], theme["grid"])
    draw.rectangle([0, 0, W, 14], fill=theme["bar_bg"])

    cx = 635 if matched_logo else W // 2
    max_w = 1160 if matched_logo else 1740

    if matched_logo:
        render_logo_card(img, draw, matched_logo, (1270, 50, 1865, 865), theme["bar_bg"], shadow_color=theme["shadow"])

    # সবার আগে ছোট ট্যাগ ও বিশাল হিরো হেডলাইন
    draw_pill(
        draw, cx, 78, data["top_tag"], bar_font,
        max_w=720, max_h=82, bg_color=theme["chip_bg"], text_color=theme["chip_text"],
        border_color=theme["chip_border"], border_w=3, pad_x=34, pad_y=10, start_fs=52, min_fs=30,
    )
    if not matched_logo:
        draw_header_emblems(img, draw, W, 78, 96, is_private, theme["bar_bg"])

    fs1, _, _ = get_best_fitted_mixed_font_size(data["hero_text"], max_w=max_w, max_h=190, bn_font_path=font1, start_size=225, min_size=78)
    draw_mixed_text_centered(draw, cx, 228, data["hero_text"], font1, fs1, theme["hero_color"], shadow_color=theme["shadow"], shadow_offset=5)

    # মাঝখানে ফুল-রিবনে বিশাল প্রতিষ্ঠানের নাম (345 .. 530)
    rib_x2 = 1235 if matched_logo else W
    draw.rectangle([0, 345, rib_x2, 354], fill=theme["accent"])
    draw.rectangle([0, 354, rib_x2, 524], fill=theme["bar_bg"])
    draw.rectangle([0, 524, rib_x2, 533], fill=theme["accent"])

    fs_org, _, _ = get_best_fitted_mixed_font_size(data["org_short"], max_w=max_w, max_h=140, bn_font_path=bar_font, start_size=132, min_size=56)
    draw_mixed_text_centered(draw, cx, 439, data["org_short"], bar_font, fs_org, theme["bar_text"])

    # নিচে সাব-হেডলাইন + ইনফো চিপস
    fs2, _, _ = get_best_fitted_mixed_font_size(data["sub_text"], max_w=max_w, max_h=145, bn_font_path=font2, start_size=155, min_size=58)
    draw_mixed_text_centered(draw, cx, 628, data["sub_text"], font2, fs2, theme["sub_color"])

    chips = [_chip_text(h) for h in data["highlights"][: (2 if matched_logo else 3)]]
    chip_w = 545 if matched_logo else 550
    gap = 32
    total_span = len(chips) * chip_w + (len(chips) - 1) * gap
    first_cx = cx - total_span // 2 + chip_w // 2
    for idx, ch_txt in enumerate(chips):
        draw_pill(
            draw, first_cx + idx * (chip_w + gap), 800, ch_txt, bar_font,
            max_w=chip_w, max_h=108, bg_color=theme["chip_bg"], text_color=theme["chip_text"],
            border_color=theme["chip_border"], border_w=4, pad_x=24, pad_y=12, start_fs=62, min_fs=32,
        )

    # ফুটার
    draw.rectangle([0, 905, W, 914], fill=theme["accent"])
    draw.rectangle([0, 914, W, H], fill=theme["bot_bg"])
    fs_bot, _, _ = get_best_fitted_mixed_font_size(data["bot_text"], max_w=1440, max_h=120, bn_font_path=bar_font, start_size=110, min_size=50)
    draw_mixed_text_centered(draw, 840, 996, data["bot_text"], bar_font, fs_bot, theme["bot_text"])


def _render_dark_bold(img, draw, W, H, theme, data, fonts, matched_logo, is_private):
    bar_font, font1, font2 = fonts
    # নিশ্চিতভাবে একটি ডার্ক থিম নেওয়া
    if not theme["is_dark"]:
        theme = random.choice(DARK_THEMES)

    draw.rectangle([0, 0, W, 130], fill=theme["bar_bg"])
    draw.rectangle([0, 130, W, 138], fill=theme["accent"])
    draw_header_emblems(img, draw, W, 65, 98, is_private, theme["accent"])

    fs_top, _, _ = get_best_fitted_mixed_font_size(data["top_tag"], max_w=W - 440, max_h=100, bn_font_path=bar_font, start_size=96, min_size=48)
    draw_mixed_text_centered(draw, W // 2, 65, data["top_tag"], bar_font, fs_top, theme["bar_text"])

    draw_subtle_grid_background(draw, 0, 138, W, 905, theme["canvas"], theme["grid"])

    cx = 635 if matched_logo else W // 2
    max_w = 1150 if matched_logo else 1740

    if matched_logo:
        render_logo_card(img, draw, matched_logo, (1270, 175, 1865, 870), theme["accent"], shadow_color=theme["shadow"])

    # ডার্ক ক্যানভাসে বড় ও উজ্জ্বল প্রতিষ্ঠানের নাম
    fs_org, _, _ = get_best_fitted_mixed_font_size(data["org_short"], max_w=max_w, max_h=145, bn_font_path=bar_font, start_size=128, min_size=56)
    draw_mixed_text_centered(draw, cx, 238, data["org_short"], bar_font, fs_org, "#FFFFFF", shadow_color=theme["shadow"], shadow_offset=4)

    # উজ্জ্বল রঙিন হাইলাইট বক্সের ভেতর মূল হিরো হুক
    bx1 = 45 if matched_logo else 90
    bx2 = 1225 if matched_logo else 1830
    draw.rounded_rectangle([bx1, 340, bx2, 575], radius=30, fill=theme["org_pill"], outline=theme["accent"], width=5)
    fs1, _, _ = get_best_fitted_mixed_font_size(data["hero_text"], max_w=(bx2 - bx1) - 80, max_h=190, bn_font_path=font1, start_size=215, min_size=76)
    draw_mixed_text_centered(draw, cx, 458, data["hero_text"], font1, fs1, theme["org_text"])

    fs2, _, _ = get_best_fitted_mixed_font_size(data["sub_text"], max_w=max_w, max_h=130, bn_font_path=font2, start_size=145, min_size=56)
    draw_mixed_text_centered(draw, cx, 660, data["sub_text"], font2, fs2, theme["sub_color"])

    chips = [_chip_text(h) for h in data["highlights"][: (2 if matched_logo else 3)]]
    chip_w = 545 if matched_logo else 550
    gap = 32
    total_span = len(chips) * chip_w + (len(chips) - 1) * gap
    first_cx = cx - total_span // 2 + chip_w // 2
    for idx, ch_txt in enumerate(chips):
        draw_pill(
            draw, first_cx + idx * (chip_w + gap), 812, ch_txt, bar_font,
            max_w=chip_w, max_h=108, bg_color=theme["chip_bg"], text_color=theme["chip_text"],
            border_color=theme["chip_border"], border_w=4, pad_x=24, pad_y=12, start_fs=60, min_fs=32,
        )

    draw.rectangle([0, 905, W, 914], fill=theme["accent"])
    draw.rectangle([0, 914, W, H], fill=theme["bot_bg"])
    fs_bot, _, _ = get_best_fitted_mixed_font_size(data["bot_text"], max_w=1440, max_h=120, bn_font_path=bar_font, start_size=110, min_size=50)
    draw_mixed_text_centered(draw, 840, 996, data["bot_text"], bar_font, fs_bot, theme["bot_text"])


def _render_stat_cards(img, draw, W, H, theme, data, fonts, matched_logo, is_private):
    bar_font, font1, font2 = fonts
    draw.rectangle([0, 0, W, 138], fill=theme["bar_bg"])
    draw.rectangle([0, 138, W, 146], fill=theme["accent"])
    draw_header_emblems(img, draw, W, 69, 102, is_private, theme["accent"])

    fs_top, _, _ = get_best_fitted_mixed_font_size(data["top_tag"], max_w=W - 440, max_h=105, bn_font_path=bar_font, start_size=102, min_size=48)
    draw_mixed_text_centered(draw, W // 2, 69, data["top_tag"], bar_font, fs_top, theme["bar_text"])

    draw_subtle_grid_background(draw, 0, 146, W, 905, theme["canvas"], theme["grid"])

    cx = 635 if matched_logo else W // 2
    max_w = 1160 if matched_logo else 1740

    if matched_logo:
        render_logo_card(img, draw, matched_logo, (1270, 180, 1865, 870), theme["bar_bg"], shadow_color=theme["shadow"])

    draw_pill(
        draw, cx, 232, data["org_short"], bar_font,
        max_w=max_w, max_h=136, bg_color=theme["org_pill"], text_color=theme["org_text"],
        pad_x=48, pad_y=12, start_fs=104, min_fs=48, shadow_color=theme["shadow"],
    )

    fs1, _, _ = get_best_fitted_mixed_font_size(data["hero_text"], max_w=max_w, max_h=168, bn_font_path=font1, start_size=190, min_size=72)
    draw_mixed_text_centered(draw, cx, 392, data["hero_text"], font1, fs1, theme["hero_color"], shadow_color=theme["shadow"], shadow_offset=4)

    # নিচে ২/৩টি ভিজ্যুয়াল স্ট্যাট কার্ড (প্রতিটিতে হেডার স্ট্রিপ + বড় লেখা)
    cards = data["highlights"][: (2 if matched_logo else 3)]
    card_w = 550 if matched_logo else 560
    gap = 36
    total_span = len(cards) * card_w + (len(cards) - 1) * gap
    first_x1 = cx - total_span // 2
    cy1, cy2 = 505, 860

    card_body_bg = "#1F2937" if theme["is_dark"] else "#FFFFFF"
    card_val_col = "#FFFFFF" if theme["is_dark"] else theme["sub_color"]

    for idx, h in enumerate(cards):
        x1 = first_x1 + idx * (card_w + gap)
        x2 = x1 + card_w
        draw.rounded_rectangle([x1 + 5, cy1 + 7, x2 + 5, cy2 + 7], radius=24, fill=theme["shadow"])
        draw.rounded_rectangle([x1, cy1, x2, cy2], radius=24, fill=card_body_bg, outline=theme["bar_bg"], width=4)
        # কার্ডের উপরের রঙিন হেডার স্ট্রিপ
        draw.rounded_rectangle([x1, cy1, x2, cy1 + 105], radius=24, fill=theme["bar_bg"])
        draw.rectangle([x1, cy1 + 75, x2, cy1 + 105], fill=theme["bar_bg"])

        fs_lbl, _, _ = get_best_fitted_mixed_font_size(h["label"], max_w=card_w - 40, max_h=75, bn_font_path=bar_font, start_size=62, min_size=34)
        draw_mixed_text_centered(draw, (x1 + x2) // 2, cy1 + 52, h["label"], bar_font, fs_lbl, theme["bot_text"])

        fs_val, _, _ = get_best_fitted_mixed_font_size(h["value"], max_w=card_w - 48, max_h=180, bn_font_path=font2, start_size=90, min_size=40)
        draw_mixed_text_centered(draw, (x1 + x2) // 2, cy1 + 230, h["value"], font2, fs_val, card_val_col)

    draw.rectangle([0, 905, W, 914], fill=theme["accent"])
    draw.rectangle([0, 914, W, H], fill=theme["bot_bg"])
    fs_bot, _, _ = get_best_fitted_mixed_font_size(data["bot_text"], max_w=1440, max_h=120, bn_font_path=bar_font, start_size=110, min_size=50)
    draw_mixed_text_centered(draw, 840, 996, data["bot_text"], bar_font, fs_bot, theme["bot_text"])


LAYOUT_RENDERERS = {
    "poster_classic": _render_poster_classic,
    "split_impact": _render_split_impact,
    "headline_first": _render_headline_first,
    "dark_bold": _render_dark_bold,
    "stat_cards": _render_stat_cards,
}


def generate_dynamic_thumbnail(title, output_path, thumb_meta=None):
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), "#F8FAFC")
    draw = ImageDraw.Draw(img)

    if not thumb_meta:
        thumb_meta = {}

    job_cat = strip_unwanted_chars(thumb_meta.get("job_category", ""))
    is_private = _detect_is_private(title, job_cat)

    top_tag = strip_unwanted_chars(thumb_meta.get("top_tag") or "")
    if not top_tag:
        top_tag = "বেসরকারি চাকরির নিয়োগ" if is_private else "সরকারি চাকরির নিয়োগ"
    if is_private and "সরকারি" in top_tag and "বেসরকারি" not in top_tag:
        top_tag = "বেসরকারি চাকরির নিয়োগ"

    org_short = strip_unwanted_chars(thumb_meta.get("org_short") or thumb_meta.get("top_text") or "")
    if not org_short:
        clean_t = title.split('|')[0].split('-')[0].strip()
        org_short = " ".join((clean_t.split("নিয়োগ")[0].strip() if "নিয়োগ" in clean_t else clean_t).split()[:4])

    hero_text = strip_unwanted_chars(thumb_meta.get("hero_text") or thumb_meta.get("main_red") or thumb_meta.get("row1_text") or "জরুরি নিয়োগ বিজ্ঞপ্তি")
    sub_text = strip_unwanted_chars(thumb_meta.get("sub_text") or thumb_meta.get("main_dark") or thumb_meta.get("row2_text") or "যোগ্যতা ও বিস্তারিত")
    bot_text = strip_unwanted_chars(thumb_meta.get("bot_text") or "প্রতিটি পদের যোগ্যতা, বেতন ও ফি")
    highlights = _extract_highlights(thumb_meta)

    data = {
        "top_tag": top_tag,
        "org_short": org_short,
        "hero_text": hero_text,
        "sub_text": sub_text,
        "highlights": highlights,
        "bot_text": bot_text,
    }

    # সম্পূর্ণ র‍্যান্ডম লেআউট ও র‍্যান্ডম কালার থিম নির্বাচন
    layout_style = str(thumb_meta.get("layout_style", "")).strip()
    if layout_style not in LAYOUT_RENDERERS:
        layout_style = random.choice(VALID_LAYOUTS)

    theme = random.choice(ALL_THEMES)
    bar_font = get_fixed_bar_font()
    font_line1, font_line2 = get_two_distinct_middle_fonts()
    matched_logo = find_matched_org_logo(title) or find_matched_org_logo(org_short)

    renderer = LAYOUT_RENDERERS[layout_style]
    renderer(img, draw, W, H, theme, data, (bar_font, font_line1, font_line2), matched_logo, is_private)

    img.save(output_path, "JPEG", quality=100, subsampling=0)
    print(f"✅ Pro Random Thumbnail [{layout_style}]: '{org_short}' | '{hero_text}' | '{sub_text}'")
