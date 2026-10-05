# -*- coding: utf-8 -*-
import os, random
import numpy as np
from PIL import Image
from moviepy.editor import AudioFileClip, VideoClip, concatenate_videoclips, ImageClip, CompositeVideoClip

def crop_circular_region(pil_img, focus_region):
    """
    সার্কুলারের আবেদন সংক্রান্ত জটিল নিয়ম বাদ দিয়ে শুধুমাত্র পদের তালিকা ও হেডারে ফোকাস করে
    """
    w, h = pil_img.size
    region = str(focus_region).lower()

    if "header" in region:
        # প্রতিষ্ঠানের নাম ও বিজ্ঞপ্তির শিরোনাম
        return pil_img.crop((0, 0, w, int(h * 0.32)))
    elif "post_1" in region:
        # ১ম পদের বিবরণ (পদের নাম, সংখ্যা, বেতন ও যোগ্যতা)
        return pil_img.crop((0, int(h * 0.18), w, int(h * 0.48)))
    elif "post_2" in region:
        # ২য় পদের বিবরণ
        return pil_img.crop((0, int(h * 0.34), w, int(h * 0.64)))
    elif "post_3" in region:
        # ৩য় পদের বিবরণ
        return pil_img.crop((0, int(h * 0.48), w, int(h * 0.78)))
    elif "terms" in region or "age" in region:
        # বয়সসীমা ও শিক্ষাগত যোগ্যতার শর্ত
        return pil_img.crop((0, int(h * 0.58), w, int(h * 0.85)))
    else:
        # পুরো পদের টেবিল
        return pil_img.crop((0, int(h * 0.15), w, int(h * 0.75)))

def make_synchronized_frame(img_path, focus_region, duration, target_w=1920, target_h=1080):
    with Image.open(img_path) as full_img:
        cropped_section = crop_circular_region(full_img.convert("RGB"), focus_region)

    w, h = cropped_section.size
    target_ratio = target_w / target_h
    zoom_factor = 1.08

    if (w / h) >= target_ratio:
        new_h = int(target_h * zoom_factor)
        new_w = int((new_h / h) * w)
    else:
        new_w = int(target_w * zoom_factor)
        new_h = int((new_w / w) * h)

    new_w = max(target_w, new_w)
    new_h = max(target_h, new_h)

    img_np = np.array(cropped_section.resize((new_w, new_h), Image.LANCZOS))
    max_y_offset = max(0, new_h - target_h)
    max_x_offset = max(0, new_w - target_w)

    def frame_getter(t):
        prog = min(1.0, max(0.0, t / duration if duration > 0 else 0))
        y_start = int(prog * max_y_offset)
        x_start = int(prog * max_x_offset)
        return img_np[y_start : y_start + target_h, x_start : x_start + target_w]

    return VideoClip(frame_getter, duration=duration)

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
            scale_ratio = 0.35 if target_w >= target_h else 0.45
            scaled_w = int(target_w * scale_ratio)
            scaled_h = int((scaled_w / pil_front.width) * pil_front.height)
            pil_front_resized = pil_front.resize((scaled_w, scaled_h), Image.LANCZOS)
            front_np = np.array(pil_front_resized)
            pil_front.close()

            front_clip = ImageClip(front_np[:, :, :3]).set_duration(main_clip.duration)
            mask_clip = ImageClip(front_np[:, :, 3] / 255.0, ismask=True).set_duration(main_clip.duration)
            front_clip = front_clip.set_mask(mask_clip)
            
            pad = 30
            avail_w = max(1, target_w - scaled_w - 2 * pad)
            avail_h = max(1, target_h - scaled_h - 2 * pad)
            speed_x = 26.0
            speed_y = 18.0
            
            init_x_phase = random.uniform(0, 2 * avail_w)
            init_y_phase = random.uniform(0, 2 * avail_h)
            dir_x = random.choice([-1.0, 1.0])
            dir_y = random.choice([-1.0, 1.0])
            
            def floating_pos(t):
                curr_x = (init_x_phase + dir_x * speed_x * t) % (2 * avail_w)
                curr_y = (init_y_phase + dir_y * speed_y * t) % (2 * avail_h)
                x = curr_x if curr_x <= avail_w else (2 * avail_w - curr_x)
                y = curr_y if curr_y <= avail_h else (2 * avail_h - curr_y)
                return (pad + int(x), pad + int(y))
            
            front_clip = front_clip.set_position(floating_pos)
            main_clip = CompositeVideoClip([main_clip, front_clip]).set_audio(main_clip.audio)
        except Exception: pass
    return main_clip

def render_synchronized_video(audio_path, img_files, segments, out_file, is_vertical=False):
    if not img_files: raise ValueError("No images provided.")
    target_w, target_h = (1080, 1920) if is_vertical else (1920, 1080)
    full_audio = AudioFileClip(audio_path)
    total_audio_duration = full_audio.duration

    num_segments = len(segments) if segments else 1
    duration_per_segment = total_audio_duration / num_segments

    video_clips = []
    num_images = len(img_files)

    for idx, seg in enumerate(segments):
        focus = seg.get("focus_region", "header")
        img_idx = seg.get("image_index", 1) - 1
        actual_img_path = img_files[img_idx % num_images]

        clip = make_synchronized_frame(actual_img_path, focus, duration_per_segment, target_w, target_h)
        video_clips.append(clip)

    final_video = concatenate_videoclips(video_clips).set_audio(full_audio)
    final_video = apply_front_overlay(final_video, target_w, target_h)

    print(f"🎬 Exporting {round(total_audio_duration/60, 1)}-minute Synced Video...")
    final_video.write_videofile(
        out_file, fps=30, codec="libx264", audio_codec="aac", audio_bitrate="192k",
        threads=4, preset="ultrafast",
        ffmpeg_params=["-g", "60", "-keyint_min", "60", "-sc_threshold", "0", "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
        logger=None
    )
    final_video.close()
    full_audio.close()
    for c in video_clips: c.close()
