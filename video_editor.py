# -*- coding: utf-8 -*-
import os, numpy as np
from PIL import Image
from moviepy.editor import AudioFileClip, VideoClip, concatenate_videoclips, ImageClip, CompositeVideoClip

def make_video_frame(img_path, duration, target_w=1920, target_h=1080):
    pil_img = Image.open(img_path).convert("RGB")
    w, h = pil_img.size
    ratio = w / h
    target_ratio = target_w / target_h

    if target_w < target_h:
        if ratio < (9.0 / 16.0) - 0.01:
            new_w, new_h = target_w, max(target_h, int((target_w / w) * h))
            img_np = np.array(pil_img.resize((new_w, new_h), Image.LANCZOS))
            return VideoClip(lambda t: img_np[int((t / duration if duration > 0 else 0) * (new_h - target_h)):int((t / duration if duration > 0 else 0) * (new_h - target_h))+target_h, 0:target_w], duration=duration)
        elif (9.0 / 16.0) - 0.01 <= ratio < (16.0 / 9.0) - 0.01:
            scale = min(target_w / w, target_h / h)
            resized = pil_img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
            canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
            canvas.paste(resized, ((target_w - int(w * scale)) // 2, (target_h - int(h * scale)) // 2))
            img_np = np.array(canvas)
            return VideoClip(lambda t: img_np, duration=duration)
        else:
            new_h, new_w = target_h, max(target_w, int((target_h / h) * w))
            img_np = np.array(pil_img.resize((new_w, new_h), Image.LANCZOS))
            return VideoClip(lambda t: img_np[0:target_h, int((t / duration if duration > 0 else 0) * (new_w - target_w)):int((t / duration if duration > 0 else 0) * (new_w - target_w))+target_w], duration=duration)
    else:
        if ratio >= target_ratio: new_h, new_w = target_h, int((target_h / h) * w)
        else: new_w, new_h = target_w, int((target_w / w) * h)
        if new_w < target_w: new_w, new_h = target_w, int((new_w / w) * h)
        if new_h < target_h: new_h, new_w = target_h, int((new_h / h) * w)
        img_np = np.array(pil_img.resize((new_w, new_h), Image.LANCZOS))
        return VideoClip(lambda t: img_np[int((t / duration if duration > 0 else 0) * (new_h - target_h)):int((t / duration if duration > 0 else 0) * (new_h - target_h))+target_h, int((t / duration if duration > 0 else 0) * (new_w - target_w)):int((t / duration if duration > 0 else 0) * (new_w - target_w))+target_w], duration=duration)

def find_front_overlay_file():
    for c in ["Front.png", "front.png", "FRONT.PNG"]:
        if os.path.exists(c): return c
    for f in os.listdir("."):
        if f.lower() == "front.png": return f
    return None

def apply_front_overlay(main_clip, target_w, target_h):
    front_path = find_front_overlay_file()
    if front_path and os.path.exists(front_path):
        try:
            pil_front = Image.open(front_path).convert("RGBA")
            scale_ratio = 0.28 if target_w >= target_h else 0.38
            scaled_w = int(target_w * scale_ratio)
            scaled_h = int((scaled_w / pil_front.width) * pil_front.height)
            pil_front_resized = pil_front.resize((scaled_w, scaled_h), Image.LANCZOS)
            
            front_np = np.array(pil_front_resized)
            front_clip = ImageClip(front_np[:, :, :3]).set_duration(main_clip.duration)
            mask_clip = ImageClip(front_np[:, :, 3] / 255.0, ismask=True).set_duration(main_clip.duration)
            front_clip = front_clip.set_mask(mask_clip)
            
            pad = 25
            avail_w = max(1, target_w - scaled_w - 2 * pad)
            avail_h = max(1, target_h - scaled_h - 2 * pad)
            vx, vy = avail_w / 45.0, avail_h / 32.0
            
            def floating_pos(t):
                x_val = (t * vx) % (2 * avail_w)
                x = x_val if x_val <= avail_w else (2 * avail_w - x_val)
                y_val = (t * vy) % (2 * avail_h)
                y = y_val if y_val <= avail_h else (2 * avail_h - y_val)
                return (pad + int(x), pad + int(y))
            
            front_clip = front_clip.set_position(floating_pos)
            main_clip = CompositeVideoClip([main_clip, front_clip]).set_audio(main_clip.audio)
        except Exception: pass
    return main_clip

def render_video_slideshow(audio_path, img_files, out_file, is_vertical=False):
    target_w, target_h = (1080, 1920) if is_vertical else (1920, 1080)
    audio_clip = AudioFileClip(audio_path)
    per_img_duration = audio_clip.duration / len(img_files)

    clips = [make_video_frame(v, per_img_duration, target_w, target_h) for v in img_files]
    final_video = concatenate_videoclips(clips).set_audio(audio_clip)
    final_video = apply_front_overlay(final_video, target_w, target_h)

    final_video.write_videofile(
        out_file, fps=30, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast",
        ffmpeg_params=["-g", "60", "-keyint_min", "60", "-sc_threshold", "0", "-pix_fmt", "yuv420p"],
        logger=None
    )
    final_video.close()
    audio_clip.close()
    for c in clips: c.close()
