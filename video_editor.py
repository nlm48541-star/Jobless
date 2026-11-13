# -*- coding: utf-8 -*-
import os, random, subprocess
import numpy as np
from PIL import Image
from moviepy.editor import AudioFileClip, VideoClip, concatenate_videoclips, ImageClip, CompositeVideoClip

TMP_RENDER_DIR = "temp_assets"

def find_front_overlay_file():
    for c in ["Front.png", "front.png", "FRONT.PNG"]:
        if os.path.exists(c): return c
    for f in os.listdir("."):
        if f.lower() == "front.png": return f
    return None

def prepare_image_for_ffmpeg(img_path, out_path, target_w, target_h):
    """ছবিটিকে FFmpeg স্ক্রলিংয়ের উপযোগী করে জোড় (Even) পিক্সেল সাইজে প্রস্তুত করে"""
    with Image.open(img_path) as raw:
        pil_img = raw.convert("RGB")
        w, h = pil_img.size
        ratio = w / h
        target_ratio = target_w / target_h

        if target_w < target_h:
            # ৯:১৬ পোর্ট্রেট মোড
            if ratio < (9.0 / 16.0) - 0.01:
                new_w = target_w
                new_h = max(target_h, int((target_w / w) * h))
                canvas = pil_img.resize((new_w, new_h), Image.LANCZOS)
            elif (9.0 / 16.0) - 0.01 <= ratio < (16.0 / 9.0) - 0.01:
                scale = min(target_w / w, target_h / h)
                resized = pil_img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
                canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
                canvas.paste(resized, ((target_w - int(w * scale)) // 2, (target_h - int(h * scale)) // 2))
            else:
                new_h = target_h
                new_w = max(target_w, int((target_h / h) * w))
                canvas = pil_img.resize((new_w, new_h), Image.LANCZOS)
        else:
            # ১৬:৯ ল্যান্ডস্কেপ মোড (সার্কুলার পেজ ওপর থেকে নিচে স্ক্রল হবে)
            if ratio >= target_ratio:
                new_h, new_w = target_h, int((target_h / h) * w)
            else:
                new_w, new_h = target_w, int((target_w / w) * h)
            if new_w < target_w: new_w, new_h = target_w, int((new_w / w) * h)
            if new_h < target_h: new_h, new_w = target_h, int((new_h / h) * w)
            canvas = pil_img.resize((new_w, new_h), Image.LANCZOS)

        # জোড় সংখ্যা (Even dimensions) নিশ্চিত করা যাতে x264 এনকোডার ক্র্যাশ না করে
        cw, ch = canvas.size
        cw = cw - (cw % 2)
        ch = ch - (ch % 2)
        if cw != canvas.width or ch != canvas.height:
            canvas = canvas.crop((0, 0, cw, ch))

        canvas.save(out_path, "JPEG", quality=95)
        return cw, ch

def render_via_ffmpeg_fast(audio_path, duration, img_files, out_file, target_w, target_h):
    """
    🌟 সুপারফাস্ট C-Level FFmpeg পাইপলাইন (MoviePy-র চেয়ে ১৫ গুণ দ্রুত)
    """
    os.makedirs(TMP_RENDER_DIR, exist_ok=True)
    num_imgs = len(img_files)
    per_img_dur = duration / num_imgs

    prep_files = []
    prep_dims = []
    for idx, img_p in enumerate(img_files):
        p_out = os.path.join(TMP_RENDER_DIR, f"prep_{target_w}_{idx}.jpg")
        pw, ph = prepare_image_for_ffmpeg(img_p, p_out, target_w, target_h)
        prep_files.append(p_out)
        prep_dims.append((pw, ph))

    # Front.png ওয়াটারমার্ক প্রিপারেশন
    front_path = find_front_overlay_file()
    scaled_front_p = None
    avail_w, avail_h = 100, 100
    if front_path and os.path.exists(front_path):
        try:
            with Image.open(front_path) as pf:
                pil_front = pf.convert("RGBA")
                scale_ratio = 0.35 if target_w >= target_h else 0.45
                scaled_w = int(target_w * scale_ratio)
                scaled_h = int((scaled_w / pil_front.width) * pil_front.height)
                pil_front_resized = pil_front.resize((scaled_w, scaled_h), Image.LANCZOS)
                scaled_front_p = os.path.join(TMP_RENDER_DIR, f"front_scaled_{target_w}.png")
                pil_front_resized.save(scaled_front_p, "PNG")
                avail_w = max(10, target_w - scaled_w - 60)
                avail_h = max(10, target_h - scaled_h - 60)
        except Exception:
            scaled_front_p = None

    # FFmpeg কমান্ড তৈরি
    cmd = ["ffmpeg", "-y"]
    for p_file in prep_files:
        cmd.extend(["-loop", "1", "-t", f"{per_img_dur:.3f}", "-i", p_file])

    front_idx = num_imgs
    audio_idx = num_imgs
    if scaled_front_p:
        cmd.extend(["-i", scaled_front_p])
        audio_idx = num_imgs + 1

    cmd.extend(["-i", audio_path])

    # ফিল্টার কমপ্লেক্স: প্রতিটি ছবি স্ক্রল করা ও কনক্যাট করা
    filters = []
    concat_inputs = ""
    for idx, (pw, ph) in enumerate(prep_dims):
        max_x = max(0, pw - target_w)
        max_y = max(0, ph - target_h)
        crop_expr = f"crop=w={target_w}:h={target_h}:x='{max_x}*min(1\\,t/{per_img_dur:.3f})':y='{max_y}*min(1\\,t/{per_img_dur:.3f})'"
        filters.append(f"[{idx}:v]{crop_expr},fps=24,setsar=1[v{idx}]")
        concat_inputs += f"[v{idx}]"

    filters.append(f"{concat_inputs}concat=n={num_imgs}:v=1:a=0[vbase]")

    if scaled_front_p:
        init_x = random.randint(0, 2 * avail_w)
        init_y = random.randint(0, 2 * avail_h)
        # Triangle-wave বাউন্সিং ফর্মুলা (র‍্যান্ডম শুরু, নির্দিষ্ট ধীর গতি)
        x_expr = f"30+abs(mod({init_x}+t*26\\,{2*avail_w})-{avail_w})"
        y_expr = f"30+abs(mod({init_y}+t*18\\,{2*avail_h})-{avail_h})"
        filters.append(f"[vbase][{front_idx}:v]overlay=x='{x_expr}':y='{y_expr}':shortest=1[vout]")
        v_map = "[vout]"
    else:
        v_map = "[vbase]"

    filter_complex = ";".join(filters)

    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", v_map,
        "-map", f"{audio_idx}:a",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "stillimage",
        "-pix_fmt", "yuv420p",
        "-g", "48",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        out_file
    ])

    print(f"⚡ [FFmpeg Fast Engine] Rendering {round(duration/60, 1)}-minute video ({target_w}x{target_h})...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and os.path.exists(out_file) and os.path.getsize(out_file) > 10000:
        print(f"✅ [FFmpeg Success] Video rendered cleanly at high speed!")
        return True
    else:
        print(f"⚠️ FFmpeg notice: {res.stderr[-300:] if res.stderr else 'Unknown error'}")
        return False

# =========================================================================
# 🌟 ব্যাকআপ MoviePy ইঞ্জিন (অপ্টিমাইজড ১৫ FPS)
# =========================================================================

def make_video_frame(img_path, duration, target_w=1920, target_h=1080):
    pil_img = Image.open(img_path).convert("RGB")
    w, h = pil_img.size
    ratio = w / h
    target_ratio = target_w / target_h

    if target_w < target_h:
        if ratio < (9.0 / 16.0) - 0.01:
            new_w, new_h = target_w, max(target_h, int((target_w / w) * h))
            img_np = np.array(pil_img.resize((new_w, new_h), Image.LANCZOS))
            max_offset = max(0, new_h - target_h)
            clip = VideoClip(lambda t: img_np[int(min(1.0, max(0.0, t/duration))*max_offset):int(min(1.0, max(0.0, t/duration))*max_offset)+target_h, 0:target_w], duration=duration)
        elif (9.0 / 16.0) - 0.01 <= ratio < (16.0 / 9.0) - 0.01:
            scale = min(target_w / w, target_h / h)
            resized = pil_img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
            canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
            canvas.paste(resized, ((target_w - int(w * scale)) // 2, (target_h - int(h * scale)) // 2))
            clip = VideoClip(lambda t: np.array(canvas), duration=duration)
        else:
            new_h, new_w = target_h, max(target_w, int((target_h / h) * w))
            img_np = np.array(pil_img.resize((new_w, new_h), Image.LANCZOS))
            max_offset = max(0, new_w - target_w)
            clip = VideoClip(lambda t: img_np[0:target_h, int(min(1.0, max(0.0, t/duration))*max_offset):int(min(1.0, max(0.0, t/duration))*max_offset)+target_w], duration=duration)
    else:
        if ratio >= target_ratio: new_h, new_w = target_h, int((target_h / h) * w)
        else: new_w, new_h = target_w, int((target_w / w) * h)
        if new_w < target_w: new_w, new_h = target_w, int((new_w / w) * h)
        if new_h < target_h: new_h, new_w = target_h, int((new_h / h) * w)
        img_np = np.array(pil_img.resize((new_w, new_h), Image.LANCZOS))
        max_y = max(0, new_h - target_h)
        max_x = max(0, new_w - target_w)
        clip = VideoClip(lambda t: img_np[int(min(1.0, max(0.0, t/duration))*max_y):int(min(1.0, max(0.0, t/duration))*max_y)+target_h, int(min(1.0, max(0.0, t/duration))*max_x):int(min(1.0, max(0.0, t/duration))*max_x)+target_w], duration=duration)
    pil_img.close()
    return clip

def render_video_slideshow(audio_path, img_files, out_file, is_vertical=False):
    if not img_files: raise ValueError("No images provided.")
    target_w, target_h = (1080, 1920) if is_vertical else (1920, 1080)

    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration
    audio_clip.close()

    # 🌟 ১. প্রথমে সুপারফাস্ট FFmpeg ইঞ্জিন চেষ্টা করবে (১৫ গুণ দ্রুত)
    if render_via_ffmpeg_fast(audio_path, duration, img_files, out_file, target_w, target_h):
        return

    # 🌟 ২. কোনো কারণে FFmpeg ফেইল করলে ব্যাকআপ হিসেবে অপ্টিমাইজড MoviePy (15 FPS)
    print("🔄 Falling back to MoviePy backup renderer (15 FPS)...")
    audio_clip = AudioFileClip(audio_path)
    per_img_duration = audio_clip.duration / len(img_files)
    clips = [make_video_frame(v, per_img_duration, target_w, target_h) for v in img_files]
    final_video = concatenate_videoclips(clips).set_audio(audio_clip)

    final_video.write_videofile(
        out_file, fps=15, codec="libx264", audio_codec="aac", audio_bitrate="192k",
        threads=4, preset="ultrafast",
        ffmpeg_params=["-g", "30", "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
        logger=None
    )
    final_video.close()
    audio_clip.close()
    for c in clips: c.close()
