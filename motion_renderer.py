# -*- coding: utf-8 -*-
import math
import os
import random
import subprocess
import wave
from PIL import Image, ImageDraw

from motion_data import build_motion_timeline
from motion_themes import (
    MOTION_PALETTES,
    apply_transition,
    draw_icon,
    draw_mixed_text,
    ease_out_back,
    ease_out_cubic,
    fit_multiline_font,
    fit_single_line_font,
    get_body_font,
    get_display_font,
    get_english_bold_font,
    make_card,
    make_curl_sprite,
    make_emblem_sprite,
    make_text_sprite,
    make_whatsapp_sprite,
    make_word_sprites,
    paste_sprite,
    render_masked_rise,
    stream_frames_to_ffmpeg,
    to_bn_num,
)


def _get_audio_duration(audio_path: str) -> float:
    try:
        with wave.open(str(audio_path), "rb") as wf:
            sr = wf.getframerate()
            if sr > 0:
                return wf.getnframes() / float(sr)
    except Exception:
        pass
    try:
        res = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15
        )
        val = float(res.stdout.strip())
        if val > 0:
            return val
    except Exception:
        pass
    try:
        from moviepy.editor import AudioFileClip
        clip = AudioFileClip(audio_path)
        d = float(clip.duration)
        clip.close()
        return d
    except Exception:
        return 30.0


def _make_icon_badge(size: int, kind: str, bg_col, icon_col, border_col=None):
    sp = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(sp)
    pad = 4
    d.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=size // 4,
        fill=bg_col + (255,),
        outline=(border_col + (255,)) if border_col else None,
        width=3,
    )
    draw_icon(d, size // 2, size // 2, kind, icon_col + (255,))
    return sp


def _make_labeled_card(w, h, label, value, pal, icon_kind, val_color=None, radius=28):
    card = make_card(w, h, radius=radius, fill=pal["card"], border=pal["border"], border_w=2, pad=18, shadow_alpha=22)
    d = ImageDraw.Draw(card)
    ox, oy = 18, 18

    # বামে হালকা আইকন ব্যাজ
    ib_sz = min(84, int(h * 0.56))
    ib = _make_icon_badge(ib_sz, icon_kind, pal["tint"], pal["accent"], pal["border"])
    ix = ox + 26
    iy = oy + (h - ib_sz) // 2
    card.paste(ib, (ix, iy), ib.getchannel("A"))

    # ডানে লেবেল + বড় ভ্যালু
    tx_left = ix + ib_sz + 24
    text_max_w = max(120, (ox + w - 24) - tx_left)
    tx_cx = tx_left + text_max_w // 2

    lf, lsz = fit_single_line_font(d, label, get_body_font, 32, 22, text_max_w)
    draw_mixed_text(d, tx_left, oy + int(h * 0.28), label, lf, lsz, pal["muted"], anchor="lm")

    vf, vsz, vlines = fit_multiline_font(d, value, get_body_font, 44, 24, text_max_w, 3)
    lh = vsz + 10
    start_y = oy + int(h * 0.64) - ((len(vlines) - 1) * lh) // 2
    for ln in vlines:
        draw_mixed_text(d, tx_left, start_y, ln, vf, vsz, val_color or pal["ink"], anchor="lm")
        start_y += lh

    return card


def _prepare_scene_assets(beat, timeline, pal, W, H, is_vertical):
    """প্রতিটি বিটের জন্য একবারই সব কার্ড/টেক্সট স্প্রাইট তৈরি করে নেয় (দ্রুত রেন্ডারিংয়ের জন্য)"""
    btype = beat["type"]
    p = beat["payload"]
    assets = {"type": btype}

    if btype == "intro":
        org_max_w = int(W * (0.88 if is_vertical else 0.82))
        org_cy = 675 if is_vertical else 435
        assets["emblem"] = make_emblem_sprite(pal)
        assets["org_words"] = make_word_sprites(
            p["org"], get_display_font, 88 if is_vertical else 96, 46, org_max_w, 2, pal["ink"], W // 2, org_cy
        )
        bw, bh = (620, 126) if is_vertical else (660, 114)
        badge = make_card(bw, bh, radius=bh // 2, fill=pal["accent"], shadow_alpha=28)
        bd = ImageDraw.Draw(badge)
        bf, bsz = fit_single_line_font(bd, p["cat_badge"], get_body_font, 52, 30, bw - 60)
        draw_mixed_text(bd, badge.width // 2, badge.height // 2, p["cat_badge"], bf, bsz, (255, 255, 255), anchor="mm")
        assets["badge"] = badge

        sub_txt = f"মোট শূন্যপদ: {p['vac_display']}  |  {p['elig_sum']}"
        assets["sub_sp"] = make_text_sprite(sub_txt, get_body_font, 46, 26, org_max_w, 2, pal["muted"])

    elif btype == "org_overview":
        cw, ch = (880, 350) if is_vertical else (880, 290)
        vac_card = make_card(cw, ch, radius=38, fill=pal["card"], border=pal["border"], border_w=2)
        vd = ImageDraw.Draw(vac_card)
        vd.rounded_rectangle([20, 20, 20 + cw, 110], radius=34, fill=pal["tint"] + (255,))
        vd.rectangle([20, 75, 20 + cw, 110], fill=pal["tint"] + (255,))
        draw_mixed_text(vd, vac_card.width // 2, 65, "মোট শূন্যপদ", get_body_font(44), 44, pal["accent"], anchor="mm")
        assets["vac_card"] = vac_card
        assets["vac_num"] = p["vac_num"]
        assets["static_num"] = make_text_sprite(p["vac_display"], get_display_font, 155, 64, cw - 80, 1, pal["ink"])
        assets["count_cache"] = {}

        chips = [
            ("যোগ্য এলাকা", p["district"], "loc"),
            ("আবেদনের শেষ সময়", p["deadline"], "fee"),
            ("আবেদন ফি", p["fee_sum"], "salary"),
        ]
        chip_w = 880 if is_vertical else 520
        chip_h = 140 if is_vertical else 135
        assets["chips"] = [
            _make_labeled_card(chip_w, chip_h, lbl, val, pal, kind, radius=28)
            for lbl, val, kind in chips
        ]

    elif btype == "post_spotlight":
        post = p["post"]
        total_posts = p["total_posts"]
        idx_lbl = f"পদ {to_bn_num(post['index'])} / {to_bn_num(total_posts)}"

        pw_idx = 340 if is_vertical else 340
        idx_pill = make_card(pw_idx, 82, radius=41, fill=pal["tint"], border=pal["accent"], border_w=3, shadow_alpha=12)
        draw_mixed_text(ImageDraw.Draw(idx_pill), idx_pill.width // 2, idx_pill.height // 2, idx_lbl, get_body_font(38), 38, pal["accent"], anchor="mm")
        assets["idx_pill"] = idx_pill

        vac_pill = make_card(pw_idx, 82, radius=41, fill=pal["accent"], shadow_alpha=18)
        vf, vsz = fit_single_line_font(ImageDraw.Draw(vac_pill), f"পদ: {post['vacancy']}", get_body_font, 38, 24, pw_idx - 40)
        draw_mixed_text(ImageDraw.Draw(vac_pill), vac_pill.width // 2, vac_pill.height // 2, f"পদ: {post['vacancy']}", vf, vsz, (255, 255, 255), anchor="mm")
        assets["vac_pill"] = vac_pill

        title_w = 940 if is_vertical else 1560
        title_h = 180 if is_vertical else 138
        t_card = make_card(title_w, title_h, radius=32, fill=pal["card"], border=pal["accent"], border_w=3, shadow_alpha=26)
        tf, tsz, tlines = fit_multiline_font(ImageDraw.Draw(t_card), post["post_name"], get_display_font, 60 if is_vertical else 58, 30, title_w - 70, 2)
        tlh = tsz + 12
        ty = t_card.height // 2 - ((len(tlines) - 1) * tlh) // 2
        for ln in tlines:
            draw_mixed_text(ImageDraw.Draw(t_card), t_card.width // 2, ty, ln, tf, tsz, pal["ink"], anchor="mm")
            ty += tlh
        assets["title_card"] = t_card

        if is_vertical:
            assets["sal_card"] = _make_labeled_card(940, 195, "বেতন স্কেল ও গ্রেড", post["salary"], pal, "salary", val_color=pal["accent"])
            assets["qual_card"] = _make_labeled_card(940, 225, "শিক্ষাগত যোগ্যতা ও অভিজ্ঞতা", post["qualification"], pal, "edu")
            assets["duty_card"] = _make_labeled_card(940, 210, "পদের দায়িত্ব ও কাজ", post["duties"], pal, "briefcase")
            assets["fee_card"] = _make_labeled_card(940, 170, "আবেদন ফি", post["fee"], pal, "fee", val_color=pal["accent_2"])
        else:
            assets["sal_card"] = _make_labeled_card(760, 215, "বেতন স্কেল ও গ্রেড", post["salary"], pal, "salary", val_color=pal["accent"])
            assets["qual_card"] = _make_labeled_card(760, 215, "শিক্ষাগত যোগ্যতা ও অভিজ্ঞতা", post["qualification"], pal, "edu")
            assets["duty_card"] = _make_labeled_card(1060, 175, "পদের দায়িত্ব ও কাজ", post["duties"], pal, "briefcase")
            assets["fee_card"] = _make_labeled_card(460, 175, "আবেদন ফি", post["fee"], pal, "fee", val_color=pal["accent_2"])

    elif btype == "post_details":
        post = p["post"]
        assets["hdr"] = make_text_sprite(f"{post['post_name']} — বিস্তারিত শর্ত", get_display_font, 56, 32, 920 if is_vertical else 1560, 2, pal["ink"])
        if is_vertical:
            assets["qual_card"] = _make_labeled_card(940, 340, "শিক্ষাগত যোগ্যতা ও অভিজ্ঞতা", post["qualification"], pal, "edu")
            assets["duty_card"] = _make_labeled_card(940, 300, "পদের দায়িত্ব ও কাজ", post["duties"], pal, "briefcase")
            assets["fee_card"] = _make_labeled_card(940, 250, "আবেদন ফি", post["fee"], pal, "fee", val_color=pal["accent"])
        else:
            assets["qual_card"] = _make_labeled_card(840, 420, "শিক্ষাগত যোগ্যতা ও অভিজ্ঞতা", post["qualification"], pal, "edu")
            assets["duty_card"] = _make_labeled_card(680, 200, "পদের দায়িত্ব ও কাজ", post["duties"], pal, "briefcase")
            assets["fee_card"] = _make_labeled_card(680, 200, "আবেদন ফি", post["fee"], pal, "fee", val_color=pal["accent"])

    elif btype == "conditions":
        assets["hdr"] = make_text_sprite("আবেদনের শর্ত ও সুযোগ-সুবিধা", get_display_font, 60, 38, 900 if is_vertical else 1400, 1, pal["ink"])
        cw, ch = (450, 400) if is_vertical else (760, 270)
        items = [
            ("বয়সসীমা", p["age_limit"], "age"),
            ("যোগ্যতা", p["elig_sum"], "edu"),
            ("আবেদন জেলা", p["district"], "loc"),
            ("সুযোগ-সুবিধা", "সরকারি / প্রাতিষ্ঠানিক ভাতা ও বোনাস", "salary"),
        ]
        cards = []
        for idx4, (lbl, val, kind) in enumerate(items):
            if is_vertical:
                c = make_card(cw, ch, radius=34, fill=pal["tint"] if idx4 in (1, 2) else pal["card"], border=pal["border"], border_w=2)
                ib = _make_icon_badge(104, kind, pal["card"] if idx4 in (1, 2) else pal["tint"], pal["accent"])
                paste_sprite(c, ib, c.width // 2, 95)
                lsp = make_text_sprite(lbl, get_body_font, 40, 28, cw - 40, 1, pal["muted"])
                vsp = make_text_sprite(val, get_body_font, 46, 26, cw - 48, 3, pal["ink"])
                paste_sprite(c, lsp, c.width // 2, 185)
                paste_sprite(c, vsp, c.width // 2, 295)
            else:
                c = _make_labeled_card(cw, ch, lbl, val, pal, kind, radius=32)
            cards.append(c)
        assets["cards"] = cards

    elif btype == "deadline":
        assets["hdr"] = make_text_sprite("আবেদনের সময়সীমা", get_display_font, 64, 42, 860 if is_vertical else 1200, 1, pal["ink"])
        cw, ch = (920, 430) if is_vertical else (1360, 340)
        card = make_card(cw, ch, radius=38, fill=pal["card"], border=pal["border"], border_w=2)
        d = ImageDraw.Draw(card)
        lx = int(card.width * 0.25)
        rx = int(card.width * 0.75)
        draw_mixed_text(d, lx, int(card.height * 0.30), "আবেদন অবস্থা", get_body_font(40), 40, pal["muted"], anchor="mm")
        draw_mixed_text(d, lx, int(card.height * 0.62), "চলমান", get_display_font(66), 66, pal["ink"], anchor="mm")
        draw_mixed_text(d, rx, int(card.height * 0.30), "শেষ তারিখ", get_body_font(40), 40, pal["accent"], anchor="mm")
        rf, rsz, rlines = fit_multiline_font(d, p["deadline"], get_display_font, 58, 30, int(cw * 0.40), 2)
        ry = int(card.height * 0.62) - ((len(rlines) - 1) * (rsz + 10)) // 2
        for ln in rlines:
            draw_mixed_text(d, rx, ry, ln, rf, rsz, pal["accent"], anchor="mm")
            ry += rsz + 10
        assets["card"] = card

        urg = make_card(720 if is_vertical else 780, 118, radius=59, fill=pal["accent"], shadow_alpha=26)
        draw_mixed_text(ImageDraw.Draw(urg), urg.width // 2, urg.height // 2, "সময়মতো আবেদন সম্পন্ন করুন", get_body_font(44), 44, (255, 255, 255), anchor="mm")
        assets["urg"] = urg

    elif btype == "whatsapp_cta":
        assets["wa"] = make_whatsapp_sprite()
        assets["title_words"] = make_word_sprites("যোগাযোগ (হোয়াটসঅ্যাপ)", get_display_font, 62, 38, 900 if is_vertical else 1200, 1, pal["ink"], W // 2, 665 if is_vertical else 455)

        pw, ph = (900, 192) if is_vertical else (880, 168)
        pill_empty = make_card(pw, ph, radius=ph // 2, fill=pal["accent"], shadow_alpha=32)
        num_sp = Image.new("RGBA", (pw - 60, 130), (0, 0, 0, 0))
        draw_mixed_text(ImageDraw.Draw(num_sp), num_sp.width // 2, 65, p["wa_formatted"], get_english_bold_font(86), 86, (255, 255, 255), anchor="mm")

        mask = Image.new("L", pill_empty.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([20, 20, 20 + pw, 20 + ph], radius=ph // 2, fill=255)
        sheen = Image.new("RGBA", (220, pill_empty.height), (0, 0, 0, 0))
        ImageDraw.Draw(sheen).polygon([(70, 0), (170, 0), (100, pill_empty.height), (0, pill_empty.height)], fill=(255, 255, 255, 75))

        assets["pill_empty"] = pill_empty
        assets["num_sp"] = num_sp
        assets["pill_mask"] = mask
        assets["sheen"] = sheen
        assets["sub_words"] = make_word_sprites("আবেদন করতে সরাসরি মেসেজ দিন", get_body_font, 52, 32, 900 if is_vertical else 1200, 1, pal["muted"], W // 2, 1070 if is_vertical else 790)

    return assets


def render_motion_video(verified_data, voiceover_script, title, audio_path, output_path, is_vertical=False, fps=25):
    """
    ১৬:৯ (1920x1080) এবং ৯:১৬ (1080x1920) — উভয় ফরম্যাটে ২০টি র‍্যান্ডম কালার থিমে
    অডিও-সিঙ্কড প্রিমিয়াম মিনিমালিস্টিক মোশন গ্রাফিক্স ভিডিও রেন্ডার করে।
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio missing for motion render: {audio_path}")

    duration = max(12.0, _get_audio_duration(audio_path))
    W, H = (1080, 1920) if is_vertical else (1920, 1080)
    pal = random.choice(MOTION_PALETTES)
    timeline = build_motion_timeline(verified_data, voiceover_script, title, duration)
    beats = timeline["beats"]

    print(f"🎬 [Motion Graphics Engine] Theme='{pal['name']}' | Size={W}x{H} | Duration={duration:.1f}s | Beats={len(beats)}")

    bg_base = Image.new("RGB", (W, H), pal["bg"])
    curl_sp = make_curl_sprite(H)

    # ফ্লোটিং টপ হেডার বার (intro ও whatsapp_cta বাদে বাকি সব বিটে থাকবে)
    hw, hh = (920, 104) if is_vertical else (1460, 82)
    hdr_sp = make_card(hw, hh, radius=hh // 2, fill=pal["card"], border=pal["border"], border_w=2, pad=18, shadow_alpha=20)
    hd = ImageDraw.Draw(hdr_sp)
    hf, hsz = fit_single_line_font(hd, timeline["org"], get_body_font, 42 if is_vertical else 38, 22, hw - 290)
    draw_mixed_text(hd, 76, hdr_sp.height // 2, timeline["org"], hf, hsz, pal["ink"], anchor="lm")
    bx1 = hdr_sp.width - 220
    hd.rounded_rectangle([bx1, 28, hdr_sp.width - 34, hdr_sp.height - 28], radius=22, fill=pal["tint"] + (255,), outline=pal["accent"] + (255,), width=2)
    draw_mixed_text(hd, (bx1 + hdr_sp.width - 34) // 2, hdr_sp.height // 2, "বিজ্ঞপ্তি", get_body_font(30), 30, pal["accent"], anchor="mm")

    # সবগুলো বিটের স্প্রাইট প্রি-রেন্ডার করা
    scene_assets = [_prepare_scene_assets(b, timeline, pal, W, H, is_vertical) for b in beats]
    trans_styles = ["curl", "push_left", "slide_up", "fade"]
    trans_sec = min(0.42, duration * 0.025)

    def draw_ambient_motion(frame, abs_t):
        fd = ImageDraw.Draw(frame)
        # ডায়নামিক ভাসমান মিনিমালিস্টিক জ্যামিতিক শেপ
        x1 = int((abs_t * 62) % (W + 360)) - 180
        x2 = int(W + 180 - ((abs_t * 50) % (W + 360)))
        y_top = 80 if is_vertical else 52
        y_bot = H - 270 if is_vertical else H - 140
        fd.ellipse([x1 - 90, y_top - 40, x1 + 90, y_top + 140], outline=pal["shape"], width=3)
        fd.ellipse([x2 - 105, y_bot - 60, x2 + 105, y_bot + 150], outline=pal["shape"], width=3)
        fd.rounded_rectangle([x1 + 110, y_top + 25, x1 + 250, y_top + 32], radius=3, fill=pal["shape"])
        fd.rounded_rectangle([x2 - 250, y_bot + 25, x2 - 110, y_bot + 32], radius=3, fill=pal["shape"])
        fd.ellipse([x1 + 265, y_top + 22, x1 + 277, y_top + 34], fill=pal["accent"])

    def draw_header_and_progress(frame, b_idx, local_t, abs_t):
        btype = beats[b_idx]["type"]
        fd = ImageDraw.Draw(frame)
        if btype not in ("intro", "whatsapp_cta"):
            hy = 140 if is_vertical else 75
            if b_idx == 1 and local_t < 0.35:
                hy = int((50 if is_vertical else 25) + (90 if is_vertical else 50) * ease_out_cubic(local_t / 0.35))
            paste_sprite(frame, hdr_sp, W // 2, hy)
            dot_x = (W - hw) // 2 + 44
            dot_r = 9 + int(3 * math.sin(abs_t * 5.0))
            fd.ellipse([dot_x - dot_r, hy - dot_r, dot_x + dot_r, hy + dot_r], fill=pal["accent"])

        # গ্লোবাল নিচের স্মুথ প্রগ্রেস বার
        px1, px2 = (140, 940) if is_vertical else (260, 1660)
        py = 1715 if is_vertical else 990
        ratio = max(0.0, min(1.0, abs_t / duration))
        fd.rounded_rectangle([px1, py, px2, py + 10], radius=5, fill=pal["hairline"])
        fx = max(px1 + 12, px1 + int((px2 - px1) * ratio))
        fd.rounded_rectangle([px1, py, fx, py + 10], radius=5, fill=pal["accent"])
        fd.ellipse([fx - 9, py - 4, fx + 9, py + 14], fill=pal["accent"])

    def render_beat(b_idx, local_t, abs_t):
        frame = bg_base.copy()
        draw_ambient_motion(frame, abs_t)
        fd = ImageDraw.Draw(frame)
        beat = beats[b_idx]
        b_dur = beat["duration"]
        btype = beat["type"]
        ast = scene_assets[b_idx]

        if btype == "intro":
            ey = 400 if is_vertical else 235
            ep = ease_out_back(min(1.0, local_t / 0.42))
            paste_sprite(frame, ast["emblem"], W // 2, ey + int(7 * math.sin(abs_t * 2.5)), scale=0.3 + 0.7 * ep, opacity=min(1.0, local_t / 0.22))
            for wi, (wsp, wx, wy) in enumerate(ast["org_words"]):
                st = 0.14 + wi * 0.08
                if local_t > st:
                    render_masked_rise(frame, wsp, wx, wy, (local_t - st) / 0.30, rise_px=48)
            div_y = 835 if is_vertical else 575
            if local_t > 0.30:
                hl = int((195 if is_vertical else 260) * ease_out_cubic((local_t - 0.30) / 0.35))
                fd.rounded_rectangle([W // 2 - hl, div_y, W // 2 + hl, div_y + 7], radius=3, fill=pal["accent"])
            if local_t > 0.42:
                bp = ease_out_back((local_t - 0.42) / 0.36)
                by = 965 if is_vertical else 675
                paste_sprite(frame, ast["badge"], W // 2, by, scale=0.68 + 0.32 * bp, opacity=min(1.0, (local_t - 0.42) / 0.20))
            if local_t > 0.62:
                sy = 1145 if is_vertical else 815
                render_masked_rise(frame, ast["sub_sp"], W // 2, sy, (local_t - 0.62) / 0.35, rise_px=38)

        elif btype == "org_overview":
            vy = 540 if is_vertical else 355
            cp = ease_out_back(min(1.0, local_t / 0.40))
            paste_sprite(frame, ast["vac_card"], W // 2, vy, scale=0.8 + 0.2 * cp, opacity=min(1.0, local_t / 0.20))

            vnum = ast["vac_num"]
            num_y = vy + 45
            if vnum > 0:
                cnt_p = ease_out_cubic(min(1.0, max(0.0, local_t - 0.12) / 1.15))
                cur_val = max(1, int(round(vnum * cnt_p)))
                cache = ast["count_cache"]
                if cur_val not in cache:
                    if len(cache) > 50:
                        cache.clear()
                    cache[cur_val] = make_text_sprite(to_bn_num(cur_val) + "টি", get_display_font, 155, 64, 780, 1, pal["ink"])
                land_t = local_t - 1.27
                pop_sc = (1.0 + 0.12 * math.sin((land_t / 0.32) * math.pi)) if 0.0 <= land_t <= 0.32 else 1.0
                paste_sprite(frame, cache[cur_val], W // 2, num_y, scale=pop_sc)
            else:
                paste_sprite(frame, ast["static_num"], W // 2, num_y, scale=0.8 + 0.2 * cp, opacity=min(1.0, local_t / 0.25))

            # ৩টি চিপ একের পর এক আসবে (০.৭s, ১.৮s, ২.৯s পর)
            chip_coords = [(540, 880), (540, 1055), (540, 1230)] if is_vertical else [(395, 665), (960, 665), (1525, 665)]
            for idx_c, chip_sp in enumerate(ast["chips"]):
                st = 0.65 + idx_c * min(1.1, b_dur * 0.14)
                if local_t > st:
                    cx, cy = chip_coords[idx_c]
                    sp_p = ease_out_back((local_t - st) / 0.34)
                    paste_sprite(frame, chip_sp, cx, cy, scale=0.82 + 0.18 * sp_p, opacity=min(1.0, (local_t - st) / 0.20))

        elif btype == "post_spotlight":
            # প্রতি পদের কার্ডগুলো কথার সাথে ধাপে ধাপে (০%, ১০%, ২২%, ৪০%, ৬০%, ৭৮%) আসবে
            u = local_t / max(0.5, b_dur)
            if is_vertical:
                paste_sprite(frame, ast["idx_pill"], 295, 300, scale=0.75 + 0.25 * ease_out_back(local_t / 0.32), opacity=min(1.0, local_t / 0.18))
                if local_t > 0.12:
                    paste_sprite(frame, ast["vac_pill"], 785, 300, scale=0.75 + 0.25 * ease_out_back((local_t - 0.12) / 0.32), opacity=min(1.0, (local_t - 0.12) / 0.18))
                if local_t > 0.22:
                    render_masked_rise(frame, ast["title_card"], 540, 470, (local_t - 0.22) / 0.35, rise_px=42)
                if u >= 0.18:
                    t_s = u * b_dur - 0.18 * b_dur
                    sc = 1.016 if 0.18 <= u < 0.38 else 1.0
                    paste_sprite(frame, ast["sal_card"], 540, 700, scale=(0.86 + 0.14 * ease_out_back(t_s / 0.35)) * sc, opacity=min(1.0, t_s / 0.20))
                if u >= 0.36:
                    t_q = u * b_dur - 0.36 * b_dur
                    sc = 1.016 if 0.36 <= u < 0.58 else 1.0
                    paste_sprite(frame, ast["qual_card"], 540, 945, scale=(0.86 + 0.14 * ease_out_back(t_q / 0.35)) * sc, opacity=min(1.0, t_q / 0.20))
                if u >= 0.56:
                    t_d = u * b_dur - 0.56 * b_dur
                    sc = 1.016 if 0.56 <= u < 0.76 else 1.0
                    paste_sprite(frame, ast["duty_card"], 540, 1200, scale=(0.86 + 0.14 * ease_out_back(t_d / 0.35)) * sc, opacity=min(1.0, t_d / 0.20))
                if u >= 0.74:
                    t_f = u * b_dur - 0.74 * b_dur
                    sc = 1.022 if u >= 0.74 else 1.0
                    paste_sprite(frame, ast["fee_card"], 540, 1435, scale=(0.82 + 0.18 * ease_out_back(t_f / 0.35)) * sc, opacity=min(1.0, t_f / 0.20))
            else:
                paste_sprite(frame, ast["idx_pill"], 350, 200, scale=0.75 + 0.25 * ease_out_back(local_t / 0.32), opacity=min(1.0, local_t / 0.18))
                if local_t > 0.12:
                    paste_sprite(frame, ast["vac_pill"], 1570, 200, scale=0.75 + 0.25 * ease_out_back((local_t - 0.12) / 0.32), opacity=min(1.0, (local_t - 0.12) / 0.18))
                if local_t > 0.22:
                    render_masked_rise(frame, ast["title_card"], 960, 325, (local_t - 0.22) / 0.35, rise_px=40)
                if u >= 0.18:
                    t_s = u * b_dur - 0.18 * b_dur
                    sc = 1.018 if 0.18 <= u < 0.38 else 1.0
                    paste_sprite(frame, ast["sal_card"], 555, 540, scale=(0.86 + 0.14 * ease_out_back(t_s / 0.35)) * sc, opacity=min(1.0, t_s / 0.20))
                if u >= 0.36:
                    t_q = u * b_dur - 0.36 * b_dur
                    sc = 1.018 if 0.36 <= u < 0.58 else 1.0
                    paste_sprite(frame, ast["qual_card"], 1365, 540, scale=(0.86 + 0.14 * ease_out_back(t_q / 0.35)) * sc, opacity=min(1.0, t_q / 0.20))
                if u >= 0.56:
                    t_d = u * b_dur - 0.56 * b_dur
                    sc = 1.018 if 0.56 <= u < 0.76 else 1.0
                    paste_sprite(frame, ast["duty_card"], 710, 775, scale=(0.86 + 0.14 * ease_out_back(t_d / 0.35)) * sc, opacity=min(1.0, t_d / 0.20))
                if u >= 0.74:
                    t_f = u * b_dur - 0.74 * b_dur
                    sc = 1.024 if u >= 0.74 else 1.0
                    paste_sprite(frame, ast["fee_card"], 1510, 775, scale=(0.82 + 0.18 * ease_out_back(t_f / 0.35)) * sc, opacity=min(1.0, t_f / 0.20))

        elif btype == "post_details":
            u = local_t / max(0.5, b_dur)
            hy = 295 if is_vertical else 210
            render_masked_rise(frame, ast["hdr"], W // 2, hy, local_t / 0.32, rise_px=34)
            if is_vertical:
                if local_t > 0.15:
                    paste_sprite(frame, ast["qual_card"], 540, 560, scale=0.85 + 0.15 * ease_out_back((local_t - 0.15) / 0.35), opacity=min(1.0, (local_t - 0.15) / 0.2))
                if u >= 0.32:
                    t2 = u * b_dur - 0.32 * b_dur
                    paste_sprite(frame, ast["duty_card"], 540, 935, scale=0.85 + 0.15 * ease_out_back(t2 / 0.35), opacity=min(1.0, t2 / 0.2))
                if u >= 0.62:
                    t3 = u * b_dur - 0.62 * b_dur
                    paste_sprite(frame, ast["fee_card"], 540, 1265, scale=0.85 + 0.15 * ease_out_back(t3 / 0.35), opacity=min(1.0, t3 / 0.2))
            else:
                if local_t > 0.15:
                    paste_sprite(frame, ast["qual_card"], 595, 535, scale=0.85 + 0.15 * ease_out_back((local_t - 0.15) / 0.35), opacity=min(1.0, (local_t - 0.15) / 0.2))
                if u >= 0.32:
                    t2 = u * b_dur - 0.32 * b_dur
                    paste_sprite(frame, ast["duty_card"], 1400, 425, scale=0.85 + 0.15 * ease_out_back(t2 / 0.35), opacity=min(1.0, t2 / 0.2))
                if u >= 0.62:
                    t3 = u * b_dur - 0.62 * b_dur
                    paste_sprite(frame, ast["fee_card"], 1400, 650, scale=0.85 + 0.15 * ease_out_back(t3 / 0.35), opacity=min(1.0, t3 / 0.2))

        elif btype == "conditions":
            hy = 325 if is_vertical else 210
            render_masked_rise(frame, ast["hdr"], W // 2, hy, local_t / 0.32, rise_px=34)
            coords = [(295, 620), (785, 620), (295, 1085), (785, 1085)] if is_vertical else [(555, 420), (1365, 420), (555, 725), (1365, 725)]
            active_c = int(abs_t * 0.85) % 4
            for i, c_sp in enumerate(ast["cards"]):
                st = 0.10 + i * min(1.1, b_dur * 0.15)
                if local_t <= st:
                    continue
                gx, gy = coords[i]
                cp = ease_out_back((local_t - st) / 0.34)
                act = 1.024 if (local_t > 1.2 and i == active_c) else 1.0
                paste_sprite(frame, c_sp, gx, gy, scale=(0.8 + 0.2 * cp) * act, opacity=min(1.0, (local_t - st) / 0.20))

        elif btype == "deadline":
            hy = 370 if is_vertical else 235
            render_masked_rise(frame, ast["hdr"], W // 2, hy, local_t / 0.32, rise_px=36)
            cy = 720 if is_vertical else 505
            if local_t > 0.10:
                cp = ease_out_back((local_t - 0.10) / 0.38)
                paste_sprite(frame, ast["card"], W // 2, cy, scale=0.82 + 0.18 * cp, opacity=min(1.0, (local_t - 0.10) / 0.22))
            if local_t > 0.30:
                phase = (abs_t * 2.5) % 1.0
                for ci, cx_off in enumerate([-36, 0, 36]):
                    col_c = pal["accent"] if abs(((phase * 3.0) - ci) % 3.0) < 0.8 else pal["hairline"]
                    cx_a, cy_a = W // 2 + cx_off, cy + (36 if is_vertical else 28)
                    fd.line([(cx_a - 14, cy_a - 22), (cx_a + 12, cy_a), (cx_a - 14, cy_a + 22)], fill=col_c, width=8)
            if local_t > 0.55:
                up = ease_out_back((local_t - 0.55) / 0.36)
                uy = 1105 if is_vertical else 795
                paste_sprite(frame, ast["urg"], W // 2, uy, scale=(0.82 + 0.18 * up) * (1.0 + 0.024 * math.sin(abs_t * 4.2)), opacity=min(1.0, (local_t - 0.55) / 0.22))

        elif btype == "whatsapp_cta":
            wy = 435 if is_vertical else 260
            for ri in range(2):
                rp = ((abs_t * 0.65) + ri * 0.5) % 1.0
                rr = int(120 + 145 * rp)
                fd.ellipse([W // 2 - rr, wy - rr, W // 2 + rr, wy + rr], outline=pal["border"], width=3)

            wp = ease_out_back(min(1.0, local_t / 0.40))
            paste_sprite(frame, ast["wa"], W // 2, wy + int(7 * math.sin(abs_t * 2.6)), scale=0.3 + 0.7 * wp, opacity=min(1.0, local_t / 0.20))

            for wi, (wsp, wx, wty) in enumerate(ast["title_words"]):
                st = 0.14 + wi * 0.08
                if local_t > st:
                    render_masked_rise(frame, wsp, wx, wty, (local_t - st) / 0.28, rise_px=34)

            py = 865 if is_vertical else 625
            if local_t > 0.30:
                pp = ease_out_back((local_t - 0.30) / 0.38)
                pe = ast["pill_empty"]
                scaled_pe = pe.resize((max(40, int(pe.width * max(0.15, min(1.0, pp)))), pe.height), Image.BILINEAR)
                paste_sprite(frame, scaled_pe, W // 2, py, opacity=min(1.0, (local_t - 0.30) / 0.18))
            if local_t > 0.46:
                np_p = ease_out_cubic((local_t - 0.46) / 0.34)
                nsp = ast["num_sp"]
                num_crop = nsp.crop((0, 0, max(12, int(nsp.width * np_p)), nsp.height))
                frame.paste(num_crop, ((W - nsp.width) // 2, py - nsp.height // 2), num_crop.getchannel("A"))
                if np_p >= 0.99:
                    cs = (local_t - 0.80) % 2.1
                    if 0.0 <= cs <= 0.75:
                        pe = ast["pill_empty"]
                        tmp_sh = Image.new("RGBA", pe.size, (0, 0, 0, 0))
                        tmp_sh.paste(ast["sheen"], (int(-220 + (pe.width + 220) * (cs / 0.75)), 0))
                        masked_sh = Image.new("RGBA", pe.size, (0, 0, 0, 0))
                        masked_sh.paste(tmp_sh, (0, 0), ast["pill_mask"])
                        paste_sprite(frame, masked_sh, W // 2, py)

            for si, (wsp, wx, wsy) in enumerate(ast["sub_words"]):
                st = 0.64 + si * 0.06
                if local_t > st:
                    render_masked_rise(frame, wsp, wx, wsy, (local_t - st) / 0.24, rise_px=24)

        draw_header_and_progress(frame, b_idx, local_t, abs_t)
        return frame

    total_frames = max(int(math.ceil(duration * fps)), fps * 5)

    def get_frame(f_idx):
        abs_t = min(duration - 0.001, f_idx / float(fps))
        b_idx = len(beats) - 1
        for i, b in enumerate(beats):
            if b["start"] <= abs_t < b["end"]:
                b_idx = i
                break

        cur_b = beats[b_idx]
        local_t = abs_t - cur_b["start"]
        frame_cur = render_beat(b_idx, local_t, abs_t)

        if b_idx < len(beats) - 1 and (cur_b["end"] - abs_t) < trans_sec:
            tp = 1.0 - (cur_b["end"] - abs_t) / trans_sec
            next_frame = render_beat(b_idx + 1, 0.25, abs_t)
            return apply_transition(frame_cur, next_frame, tp, trans_styles[b_idx % len(trans_styles)], curl_sp)

        return frame_cur

    return stream_frames_to_ffmpeg(total_frames, fps, W, H, audio_path, output_path, get_frame)
