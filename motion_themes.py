# -*- coding: utf-8 -*-
import os
import re
import subprocess
import unicodedata
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONTS_DIR = "Fonts"
PHOTOS_DIR = "Photos"

# =========================================================================
# 🌟 ২০টি প্রফেশনাল মিনিমালিস্টিক কালার থিম (১৪টি লাইট + ৬টি ডার্ক)
# =========================================================================
MOTION_PALETTES = [
    # --- ১৪টি ক্রিস্প লাইট এডিটোরিয়াল থিম ---
    {"name": "CreamTerracotta", "is_dark": False, "bg": (251, 248, 243), "shape": (244, 224, 212), "card": (255, 255, 255), "tint": (253, 237, 228), "border": (238, 222, 212), "hairline": (238, 226, 216), "ink": (34, 24, 20), "muted": (118, 102, 94), "accent": (217, 78, 31), "accent_2": (15, 118, 110)},
    {"name": "PearlEmerald", "is_dark": False, "bg": (248, 250, 249), "shape": (220, 240, 231), "card": (255, 255, 255), "tint": (236, 253, 245), "border": (209, 238, 224), "hairline": (224, 234, 229), "ink": (17, 24, 39), "muted": (94, 110, 104), "accent": (5, 122, 85), "accent_2": (29, 78, 216)},
    {"name": "IvoryCobalt", "is_dark": False, "bg": (249, 250, 252), "shape": (224, 234, 252), "card": (255, 255, 255), "tint": (239, 246, 255), "border": (210, 226, 248), "hairline": (226, 232, 240), "ink": (15, 23, 42), "muted": (96, 108, 128), "accent": (29, 78, 216), "accent_2": (220, 38, 38)},
    {"name": "MistCrimson", "is_dark": False, "bg": (250, 248, 249), "shape": (246, 222, 228), "card": (255, 255, 255), "tint": (255, 241, 242), "border": (245, 214, 220), "hairline": (232, 226, 230), "ink": (24, 24, 27), "muted": (104, 100, 112), "accent": (190, 18, 60), "accent_2": (15, 23, 42)},
    {"name": "SageBotanical", "is_dark": False, "bg": (246, 249, 244), "shape": (218, 236, 220), "card": (255, 255, 255), "tint": (231, 245, 234), "border": (208, 232, 214), "hairline": (220, 232, 222), "ink": (18, 36, 24), "muted": (90, 112, 98), "accent": (21, 128, 61), "accent_2": (180, 83, 9)},
    {"name": "LilacIndigo", "is_dark": False, "bg": (248, 247, 253), "shape": (228, 223, 247), "card": (255, 255, 255), "tint": (238, 234, 253), "border": (218, 212, 245), "hairline": (228, 223, 242), "ink": (30, 27, 46), "muted": (106, 102, 128), "accent": (79, 70, 229), "accent_2": (190, 24, 93)},
    {"name": "SandTeal", "is_dark": False, "bg": (250, 249, 245), "shape": (215, 239, 236), "card": (255, 255, 255), "tint": (240, 253, 250), "border": (204, 235, 230), "hairline": (228, 232, 226), "ink": (19, 32, 34), "muted": (92, 112, 114), "accent": (15, 118, 110), "accent_2": (217, 119, 6)},
    {"name": "IceRoyalBlue", "is_dark": False, "bg": (244, 248, 254), "shape": (214, 230, 250), "card": (255, 255, 255), "tint": (224, 242, 254), "border": (196, 222, 248), "hairline": (218, 228, 242), "ink": (12, 28, 52), "muted": (86, 108, 134), "accent": (2, 132, 199), "accent_2": (15, 23, 42)},
    {"name": "WarmAmber", "is_dark": False, "bg": (253, 250, 244), "shape": (252, 232, 198), "card": (255, 255, 255), "tint": (254, 243, 199), "border": (245, 218, 165), "hairline": (238, 228, 210), "ink": (38, 26, 12), "muted": (120, 98, 72), "accent": (180, 83, 9), "accent_2": (6, 95, 70)},
    {"name": "BlushPlum", "is_dark": False, "bg": (252, 247, 250), "shape": (245, 218, 236), "card": (255, 255, 255), "tint": (253, 242, 248), "border": (242, 208, 230), "hairline": (236, 222, 232), "ink": (46, 16, 40), "muted": (124, 88, 116), "accent": (157, 23, 77), "accent_2": (88, 28, 135)},
    {"name": "ArcticSlate", "is_dark": False, "bg": (245, 247, 250), "shape": (222, 228, 238), "card": (255, 255, 255), "tint": (241, 245, 249), "border": (203, 213, 225), "hairline": (222, 228, 236), "ink": (15, 23, 42), "muted": (92, 104, 122), "accent": (51, 65, 85), "accent_2": (220, 38, 38)},
    {"name": "MintCoral", "is_dark": False, "bg": (246, 252, 250), "shape": (214, 242, 232), "card": (255, 255, 255), "tint": (255, 241, 240), "border": (248, 210, 206), "hairline": (222, 235, 230), "ink": (20, 32, 30), "muted": (88, 108, 104), "accent": (225, 29, 72), "accent_2": (13, 148, 136)},
    {"name": "SoftLavender", "is_dark": False, "bg": (249, 246, 254), "shape": (232, 218, 250), "card": (255, 255, 255), "tint": (243, 232, 255), "border": (222, 200, 248), "hairline": (232, 220, 244), "ink": (34, 18, 56), "muted": (110, 92, 134), "accent": (109, 40, 217), "accent_2": (5, 150, 105)},
    {"name": "ClassicGovOlive", "is_dark": False, "bg": (248, 250, 246), "shape": (224, 236, 212), "card": (255, 255, 255), "tint": (236, 246, 228), "border": (208, 228, 192), "hairline": (224, 234, 218), "ink": (22, 34, 18), "muted": (92, 110, 84), "accent": (63, 98, 18), "accent_2": (185, 28, 28)},

    # --- ৬টি ডার্ক এক্সিকিউটিভ থিম ---
    {"name": "MidnightCyan", "is_dark": True, "bg": (11, 17, 32), "shape": (24, 38, 66), "card": (21, 33, 56), "tint": (18, 52, 78), "border": (48, 72, 110), "hairline": (32, 48, 76), "ink": (248, 250, 252), "muted": (158, 174, 196), "accent": (56, 189, 248), "accent_2": (250, 204, 21)},
    {"name": "ObsidianMint", "is_dark": True, "bg": (9, 19, 17), "shape": (22, 46, 40), "card": (18, 38, 33), "tint": (14, 56, 44), "border": (38, 76, 66), "hairline": (28, 56, 48), "ink": (240, 253, 244), "muted": (152, 202, 180), "accent": (16, 185, 129), "accent_2": (253, 224, 71)},
    {"name": "CarbonAmber", "is_dark": True, "bg": (15, 15, 19), "shape": (34, 34, 46), "card": (28, 28, 38), "tint": (60, 42, 14), "border": (58, 58, 76), "hairline": (42, 42, 56), "ink": (250, 250, 250), "muted": (166, 166, 180), "accent": (245, 158, 11), "accent_2": (56, 189, 248)},
    {"name": "DeepMaroonGold", "is_dark": True, "bg": (24, 10, 14), "shape": (52, 20, 28), "card": (40, 16, 22), "tint": (68, 24, 32), "border": (88, 34, 46), "hairline": (60, 24, 32), "ink": (254, 242, 242), "muted": (212, 165, 172), "accent": (251, 191, 36), "accent_2": (251, 113, 133)},
    {"name": "VioletNight", "is_dark": True, "bg": (16, 12, 30), "shape": (38, 28, 68), "card": (28, 22, 52), "tint": (48, 34, 88), "border": (74, 54, 124), "hairline": (46, 36, 80), "ink": (245, 243, 255), "muted": (178, 168, 214), "accent": (167, 139, 250), "accent_2": (52, 211, 153)},
    {"name": "GraphiteRose", "is_dark": True, "bg": (17, 19, 24), "shape": (36, 40, 50), "card": (28, 31, 39), "tint": (64, 24, 38), "border": (60, 64, 78), "hairline": (42, 46, 56), "ink": (248, 250, 252), "muted": (168, 176, 190), "accent": (251, 113, 133), "accent_2": (250, 204, 21)},
]

BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
EN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def to_bn_num(n):
    return str(int(n)).translate(BN_DIGITS)


def clean_motion_text(text):
    """
    🌟 ফন্ট বক্স (□□□□) দূর করার মাস্টার ফিল্টার
    অদৃশ্য ইউনিকোড ক্যারেক্টার, কার্লি কোট ও মিসিং সিম্বল পরিষ্কার করে
    """
    if not text:
        return ""
    s = unicodedata.normalize("NFC", str(text))
    s = re.sub(r'[\u200b-\u200f\ufeff\u202a-\u202e\xa0]', ' ', s)
    s = s.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    s = s.replace('—', '-').replace('–', '-').replace('…', '...')
    s = re.sub(r'\s*৳', ' টাকা', s)
    s = re.sub(r'[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|✪|★|☆', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def remove_emojis(text):
    return clean_motion_text(text)


# =========================================================================
# 🌟 ফন্ট ও টেক্সট শেপিং
# =========================================================================

_FONT_CACHE = {}


def _is_valid_bengali_font(fp):
    try:
        tf = ImageFont.truetype(fp, 36)
        m = tf.getmask("বাংলাদেশ চাকরি")
        return m.size[0] > 0 and m.size[1] > 0
    except Exception:
        return False


def find_bengali_font_path(preferred_keywords=None):
    key = tuple(preferred_keywords or [])
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    candidates = []
    if os.path.exists(FONTS_DIR):
        for f in sorted(os.listdir(FONTS_DIR)):
            if f.lower().endswith(('.ttf', '.otf')) and f.lower() != "akhand.ttf":
                candidates.append(os.path.join(FONTS_DIR, f))

    sys_fallbacks = [
        "/usr/share/fonts/truetype/noto/NotoSansBengali-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf",
        "/usr/share/fonts/truetype/lohit-bengali/Lohit-Bengali.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    candidates.extend([p for p in sys_fallbacks if os.path.exists(p)])

    if preferred_keywords:
        for kw in preferred_keywords:
            for c in candidates:
                if kw.lower() in os.path.basename(c).lower() and _is_valid_bengali_font(c):
                    _FONT_CACHE[key] = c
                    return c

    for c in candidates:
        if _is_valid_bengali_font(c):
            _FONT_CACHE[key] = c
            return c

    return candidates[0] if candidates else None


def get_display_font(size):
    fp = find_bengali_font_path(["Li Ador", "Shokuntola", "kalpurush", "SolaimanLipi", "Siyamrupali", "NotoSansBengali"])
    if fp:
        try:
            return ImageFont.truetype(fp, size)
        except Exception:
            pass
    return ImageFont.load_default()


def get_body_font(size):
    fp = find_bengali_font_path(["kalpurush", "SolaimanLipi", "NotoSansBengali", "Siyamrupali"])
    if fp:
        try:
            return ImageFont.truetype(fp, size)
        except Exception:
            pass
    return ImageFont.load_default()


def get_english_bold_font(size):
    eng_sz = max(14, int(size * 0.86))
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    ]:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, eng_sz)
            except Exception:
                pass
    return ImageFont.load_default()


def _split_script_segments(text):
    clean_t = clean_motion_text(text)
    tokens = re.split(r'([A-Za-z0-9/.\-:]+)', clean_t)
    segs = []
    for t in tokens:
        if not t:
            continue
        is_eng = bool(re.match(r'^[A-Za-z0-9/.\-:]+$', t))
        segs.append((t, is_eng))
    return segs


def measure_mixed_text(draw, text, bn_font, font_size):
    eng_font = get_english_bold_font(font_size)
    total_w, max_h = 0, 0
    for seg, is_eng in _split_script_segments(text):
        f = eng_font if is_eng else bn_font
        bbox = f.getbbox(seg)
        total_w += (bbox[2] - bbox[0])
        h = bbox[3] - bbox[1]
        if h > max_h:
            max_h = h
    return total_w, max_h


def draw_mixed_text(draw, x, y, text, bn_font, font_size, fill, anchor="mm"):
    eng_font = get_english_bold_font(font_size)
    segs = _split_script_segments(text)
    widths = []
    total_w = 0
    for seg, is_eng in segs:
        f = eng_font if is_eng else bn_font
        bbox = f.getbbox(seg)
        w = bbox[2] - bbox[0]
        widths.append(w)
        total_w += w

    if anchor.startswith("m"):
        cur_x = x - total_w // 2
    elif anchor.startswith("r"):
        cur_x = x - total_w
    else:
        cur_x = x

    for (seg, is_eng), w in zip(segs, widths):
        f = eng_font if is_eng else bn_font
        draw.text((cur_x, y), seg, font=f, fill=fill, anchor="lm")
        cur_x += w


def fit_single_line_font(draw, text, font_fn, start_sz, min_sz, max_w):
    clean_t = clean_motion_text(text)
    floor_sz = min(min_sz, 16)
    for sz in range(start_sz, floor_sz - 1, -2):
        f = font_fn(sz)
        w, _ = measure_mixed_text(draw, clean_t, f, sz)
        if w <= max_w:
            return f, sz
    return font_fn(floor_sz), floor_sz


def fit_single_line_text(draw, text, font_fn, start_sz, min_sz, max_w):
    """এক লাইনে টেক্সট ফিট করে; সর্বনিম্ন ফন্টেও বড় হলে সুন্দরভাবে '...' দিয়ে সীমাবদ্ধ করে"""
    clean_t = clean_motion_text(text)
    for sz in range(start_sz, min_sz - 1, -2):
        f = font_fn(sz)
        w, _ = measure_mixed_text(draw, clean_t, f, sz)
        if w <= max_w:
            return f, sz, clean_t

    f = font_fn(min_sz)
    if measure_mixed_text(draw, clean_t, f, min_sz)[0] <= max_w:
        return f, min_sz, clean_t

    words = clean_t.split()
    cur = clean_t
    while words and measure_mixed_text(draw, cur + "...", f, min_sz)[0] > max_w:
        words.pop()
        cur = " ".join(words)
    if not cur:
        cur = clean_t
        while len(cur) > 1 and measure_mixed_text(draw, cur + "...", f, min_sz)[0] > max_w:
            cur = cur[:-1]
    return f, min_sz, (cur + "...") if cur else "..."


def fit_multiline_font(draw, text, font_fn, start_sz, min_sz, max_w, max_lines):
    clean_t = clean_motion_text(text)
    words = clean_t.split()
    if not words:
        return font_fn(min_sz), min_sz, [""]

    for sz in range(start_sz, min_sz - 1, -2):
        f = font_fn(sz)
        lines = []
        cur = ""
        for w in words:
            cand = f"{cur} {w}".strip()
            cw, _ = measure_mixed_text(draw, cand, f, sz)
            if cw <= max_w:
                cur = cand
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        if len(lines) <= max_lines and all(measure_mixed_text(draw, ln, f, sz)[0] <= max_w for ln in lines):
            return f, sz, lines

    f = font_fn(min_sz)
    lines = []
    cur = ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if measure_mixed_text(draw, cand, f, min_sz)[0] <= max_w:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return f, min_sz, lines[:max_lines]


def fit_multiline_to_box(draw, text, font_fn, start_sz, min_sz, max_w, max_h, line_gap=8):
    """কার্ডের প্রস্থ ও উচ্চতা উভয়ের মধ্যেই লেখা নিখুঁতভাবে ফিট করে (কলিশন/ওভারফ্লো প্রতিরোধক)"""
    clean_t = clean_motion_text(text)
    words = clean_t.split()
    if not words:
        return font_fn(min_sz), min_sz, [""]

    def _wrap(f, sz):
        lines = []
        cur = ""
        for w in words:
            cand = f"{cur} {w}".strip()
            if measure_mixed_text(draw, cand, f, sz)[0] <= max_w:
                cur = cand
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    for sz in range(start_sz, min_sz - 1, -2):
        f = font_fn(sz)
        lines = _wrap(f, sz)
        lh = sz + line_gap
        if len(lines) * lh <= max_h and all(measure_mixed_text(draw, ln, f, sz)[0] <= max_w for ln in lines):
            return f, sz, lines

    f = font_fn(min_sz)
    lines = _wrap(f, min_sz)
    lh = min_sz + line_gap
    max_lines = max(1, max_h // lh)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and measure_mixed_text(draw, last + "...", f, min_sz)[0] > max_w:
            parts = last.split()
            if len(parts) > 1:
                last = " ".join(parts[:-1])
            else:
                last = last[:-1]
        lines[-1] = (last + "...") if last else "..."
    return f, min_sz, lines


# =========================================================================
# 🌟 ইজিং ও গ্রাফিক্স প্রিমিটিভ
# =========================================================================

def ease_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 4 * t * t * t if t < 0.5 else 1.0 - ((-2 * t + 2) ** 3) / 2.0


def ease_out_back(t, s=1.55):
    t = max(0.0, min(1.0, t))
    return 1.0 + (s + 1.0) * ((t - 1.0) ** 3) + s * ((t - 1.0) ** 2)


def paste_sprite(canvas, sp, cx, cy, scale=1.0, opacity=1.0):
    if opacity <= 0.02 or scale <= 0.02 or sp is None:
        return
    if abs(scale - 1.0) > 0.015:
        nw = max(2, int(round(sp.width * scale)))
        nh = max(2, int(round(sp.height * scale)))
        sp = sp.resize((nw, nh), Image.BILINEAR)
    alpha = sp.getchannel("A")
    if opacity < 0.99:
        alpha = alpha.point([int(i * opacity) for i in range(256)])
    canvas.paste(sp, (int(round(cx - sp.width / 2)), int(round(cy - sp.height / 2))), alpha)


def render_masked_rise(canvas, sp, cx, cy, prog, rise_px=48):
    p = ease_out_cubic(prog)
    if p <= 0.02 or sp is None:
        return
    vis_h = max(2, int(round(sp.height * min(1.0, p * 1.15))))
    dy = int(round(rise_px * (1.0 - p)))
    cropped = sp.crop((0, 0, sp.width, vis_h))
    alpha = cropped.getchannel("A")
    if p < 0.72:
        f = p / 0.72
        alpha = alpha.point([int(i * f) for i in range(256)])
    canvas.paste(cropped, (int(round(cx - sp.width / 2)), int(round(cy - sp.height / 2 + dy))), alpha)


def make_card(w, h, radius=32, fill=(255, 255, 255), border=None, border_w=2, pad=20, shadow_alpha=24):
    cw, ch = w + pad * 2, h + pad * 2
    sh = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    if shadow_alpha > 0:
        ImageDraw.Draw(sh).rounded_rectangle(
            [pad, pad + 5, pad + w, pad + h + 5], radius=radius, fill=(10, 15, 28, shadow_alpha + 12)
        )
        sh = sh.filter(ImageFilter.GaussianBlur(6))
    ImageDraw.Draw(sh).rounded_rectangle(
        [pad, pad, pad + w, pad + h],
        radius=radius,
        fill=fill + (255,),
        outline=(border + (255,)) if border else None,
        width=border_w,
    )
    return sh


def make_text_sprite(text, font_fn, start_sz, min_sz, max_w, max_lines, color, align="mm"):
    clean_t = clean_motion_text(text)
    tmp = Image.new("RGBA", (max_w + 40, 420), (0, 0, 0, 0))
    td = ImageDraw.Draw(tmp)
    f, sz, lines = fit_multiline_font(td, clean_t, font_fn, start_sz, min_sz, max_w, max_lines)
    lh = sz + 14
    h = max(sz + 32, len(lines) * lh + 24)
    sp = Image.new("RGBA", (max_w + 40, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sp)
    cx = sp.width // 2 if align == "mm" else (sp.width - 14 if align == "rm" else 14)
    y = (h - len(lines) * lh) // 2 + lh // 2
    for ln in lines:
        draw_mixed_text(sd, cx, y, ln, f, sz, color, anchor=align)
        y += lh
    return sp


def make_word_sprites(text, font_fn, start_sz, min_sz, max_w, max_lines, color, center_x, center_y):
    clean_t = clean_motion_text(text)
    tmp = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    td = ImageDraw.Draw(tmp)
    f, sz, lines = fit_multiline_font(td, clean_t, font_fn, start_sz, min_sz, max_w, max_lines)
    lh = sz + 18
    total_h = len(lines) * lh
    cur_y = center_y - total_h // 2 + lh // 2
    word_items = []
    for line in lines:
        words = line.split()
        sp_w = measure_mixed_text(td, " ", f, sz)[0] or int(sz * 0.28)
        widths = [measure_mixed_text(td, w, f, sz)[0] for w in words]
        line_w = sum(widths) + sp_w * max(0, len(words) - 1)
        cur_x = center_x - line_w / 2.0
        for w, ww in zip(words, widths):
            pad_w, pad_h = ww + 28, sz + 36
            wsp = Image.new("RGBA", (max(16, pad_w), max(24, pad_h)), (0, 0, 0, 0))
            draw_mixed_text(ImageDraw.Draw(wsp), pad_w // 2, pad_h // 2, w, f, sz, color, anchor="mm")
            word_items.append((wsp, cur_x + ww / 2.0, cur_y))
            cur_x += ww + sp_w
        cur_y += lh
    return word_items


def draw_icon(d, cx, cy, kind, col):
    if kind == "age":
        d.ellipse([cx - 16, cy - 32, cx + 16, cy], fill=col)
        d.pieslice([cx - 30, cy + 6, cx + 30, cy + 50], start=180, end=360, fill=col)
    elif kind == "salary":
        d.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], outline=col, width=6)
        d.line([(cx - 14, cy - 10), (cx + 14, cy - 10)], fill=col, width=6)
        d.line([(cx - 14, cy + 8), (cx + 14, cy + 8)], fill=col, width=6)
        d.line([(cx, cy - 18), (cx, cy + 18)], fill=col, width=6)
    elif kind == "fee":
        d.rounded_rectangle([cx - 24, cy - 28, cx + 24, cy + 28], radius=8, outline=col, width=6)
        d.line([(cx - 12, cy - 8), (cx + 12, cy - 8)], fill=col, width=5)
        d.line([(cx - 12, cy + 8), (cx + 12, cy + 8)], fill=col, width=5)
    elif kind == "edu":
        d.polygon([(cx, cy - 26), (cx + 34, cy - 8), (cx, cy + 10), (cx - 34, cy - 8)], outline=col, width=5)
        d.arc([cx - 20, cy - 2, cx + 20, cy + 26], start=0, end=180, fill=col, width=5)
    elif kind == "loc":
        d.ellipse([cx - 22, cy - 30, cx + 22, cy + 14], outline=col, width=6)
        d.ellipse([cx - 8, cy - 16, cx + 8, cy], fill=col)
        d.polygon([(cx - 18, cy + 4), (cx + 18, cy + 4), (cx, cy + 32)], fill=col)
    else:
        d.rounded_rectangle([cx - 28, cy - 20, cx + 28, cy + 24], radius=8, outline=col, width=6)
        d.arc([cx - 14, cy - 34, cx + 14, cy - 12], start=180, end=360, fill=col, width=5)


def make_emblem_sprite(pal):
    sz = 250
    sp = Image.new("RGBA", (sz * 2, sz * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(sp)
    cx, cy = sz, sz
    d.ellipse([cx - 205, cy - 205, cx + 205, cy + 205], fill=pal["card"] + (255,), outline=pal["accent"] + (255,), width=10)
    d.ellipse([cx - 172, cy - 172, cx + 172, cy + 172], outline=pal["hairline"] + (255,), width=5)
    d.rounded_rectangle([cx - 72, cy - 88, cx + 72, cy + 88], radius=18, fill=pal["tint"] + (255,), outline=pal["accent"] + (255,), width=8)
    d.line([(cx - 38, cy - 32), (cx + 38, cy - 32)], fill=pal["accent"] + (255,), width=10)
    d.line([(cx - 38, cy), (cx + 38, cy)], fill=pal["ink"] + (220,), width=9)
    d.line([(cx - 38, cy + 32), (cx + 18, cy + 32)], fill=pal["ink"] + (220,), width=9)
    return sp.resize((sz, sz), Image.LANCZOS)


def make_whatsapp_sprite():
    for cand in [os.path.join(PHOTOS_DIR, "whatsapp.png"), "whatsapp.png"]:
        if os.path.exists(cand):
            try:
                return Image.open(cand).convert("RGBA").resize((230, 230), Image.LANCZOS)
            except Exception:
                pass
    sz = 230
    sp = Image.new("RGBA", (sz * 2, sz * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(sp)
    d.rounded_rectangle([28, 42, 432, 446], radius=104, fill=(21, 128, 61, 255))
    d.rounded_rectangle([28, 22, 432, 426], radius=104, fill=(34, 197, 94, 255))
    d.ellipse([108, 102, 352, 346], outline=(255, 255, 255, 255), width=22)
    d.polygon([(116, 296), (92, 366), (166, 338)], fill=(255, 255, 255, 255))
    d.arc([164, 160, 296, 292], start=35, end=220, fill=(255, 255, 255, 255), width=26)
    return sp.resize((sz, sz), Image.LANCZOS)


def make_curl_sprite(H):
    sp = Image.new("RGBA", (80, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(sp)
    for x in range(40):
        d.line([(x, 0), (x, H)], fill=(15, 23, 42, int(68 * ((x / 40.0) ** 2))))
    for x in range(40, 80):
        t = 1.0 - (x - 40) / 40.0
        d.line([(x, 0), (x, H)], fill=(255, 255, 255, int(135 * (t ** 1.5))))
    return sp


def apply_transition(frame_a, frame_b, prog, style, curl_sp):
    W, H = frame_a.size
    p = ease_in_out_cubic(prog)
    if style == "curl":
        cut_x = int(round(W * (1.0 - p)))
        if cut_x <= 0:
            return frame_b
        if cut_x >= W:
            return frame_a
        out = frame_b.copy()
        out.paste(frame_a.crop((0, 0, cut_x, H)), (0, 0))
        paste_sprite(out, curl_sp, cut_x, H // 2)
        return out
    elif style == "push_left":
        shift = int(round(W * p))
        if shift <= 0:
            return frame_a
        if shift >= W:
            return frame_b
        out = frame_a.copy()
        out.paste(frame_b.crop((0, 0, shift, H)), (W - shift, 0))
        paste_sprite(out, curl_sp, W - shift, H // 2)
        return out
    elif style == "slide_up":
        shift = int(round(H * p))
        if shift <= 0:
            return frame_a
        if shift >= H:
            return frame_b
        out = frame_a.copy()
        out.paste(frame_b.crop((0, 0, W, shift)), (0, H - shift))
        return out
    else:
        return Image.blend(frame_a, frame_b, p)


def stream_frames_to_ffmpeg(total_frames, fps, W, H, audio_path, output_path, frame_fn):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    if os.path.exists(output_path):
        os.remove(output_path)

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps),
        "-i", "-", "-i", audio_path,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-shortest", "-movflags", "+faststart", output_path
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for f_idx in range(total_frames):
            proc.stdin.write(frame_fn(f_idx).tobytes())
        proc.stdin.close()
        err_msg = proc.stderr.read().decode("utf-8", errors="ignore")
        ret = proc.wait(timeout=600)
        if ret != 0 and err_msg:
            print(f"  ⚠️ [FFmpeg Notice] {err_msg[:220]}")
    except Exception as e:
        print(f"  ❌ [Motion Render Error] {e}")
        try:
            proc.kill()
        except Exception:
            pass
        return False

    ok = os.path.exists(output_path) and os.path.getsize(output_path) > 10000
    if ok:
        mb = round(os.path.getsize(output_path) / (1024 * 1024), 2)
        print(f"  ✅ [Motion Graphics Rendered] {W}x{H} ({mb} MB)")
    return ok
