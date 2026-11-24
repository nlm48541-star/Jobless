# -*- coding: utf-8 -*-
import os
import re
from motion_themes import EN_DIGITS, remove_emojis, to_bn_num


def _parse_first_int(text):
    if not text:
        return 0
    m = re.search(r'([0-9০-৯]+)', str(text))
    if not m:
        return 0
    try:
        return int(m.group(1).translate(EN_DIGITS))
    except Exception:
        return 0


def _clean_short_badge_val(text, fallback="নির্ধারিত", max_len=20):
    s = remove_emojis(text or "").strip()
    if len(s) > max_len:
        s = re.sub(r'\s*\([^)]*\)', '', s).strip()
    if len(s) > max_len:
        s = s[:max_len].strip()
    return s or fallback


def build_motion_timeline(verified_data, voiceover_script, title, duration, segment_timings=None):
    """
    ১. segment_timings পাওয়া গেলে প্রতিটি সেগমেন্টের নির্ভুল প্রকৃত অডিও সময়ের সাথে ফ্রেম-টু-ফ্রেম টাইমলাইন বানায়।
    ২. না থাকলে script_segments-এর ক্যারেক্টার দৈর্ঘ্য অথবা স্ট্যান্ডার্ড অনুপাতে সময় ভাগ করে।
    """
    duration = max(12.0, float(duration))
    vd = verified_data if isinstance(verified_data, dict) else {}

    org = remove_emojis(vd.get("org_short") or vd.get("organization") or title).strip()
    org_full = remove_emojis(vd.get("organization") or org).strip()
    cat_badge = remove_emojis(vd.get("job_category") or "নিয়োগ বিজ্ঞপ্তি").strip()

    total_vac_raw = remove_emojis(vd.get("total_vacancies") or "").strip()
    vac_num = _parse_first_int(total_vac_raw)
    vac_display = total_vac_raw or (f"{to_bn_num(vac_num)}টি" if vac_num > 0 else "বিভিন্ন পদ")

    deadline = remove_emojis(vd.get("deadline") or "নির্ধারিত সময়সীমা").strip() or "নির্ধারিত সময়সীমা"
    district = remove_emojis(vd.get("district_eligibility") or "৬৪ জেলা").strip()
    elig_sum = remove_emojis(vd.get("eligibility_summary") or "বিজ্ঞপ্তি অনুযায়ী").strip()
    fee_sum = remove_emojis(vd.get("application_fee_summary") or "বিজ্ঞপ্তি অনুযায়ী").strip()
    age_limit = remove_emojis(vd.get("age_limit") or "১৮ থেকে ৩২ বছর").strip()

    wa_num = os.environ.get("WHATSAPP_NUMBER", "01540503092").strip() or "01540503092"
    wa_formatted = (wa_num[:5] + "-" + wa_num[5:]) if (len(wa_num) == 11 and wa_num.startswith("01") and "-" not in wa_num) else wa_num

    raw_posts = vd.get("posts") if isinstance(vd.get("posts"), list) and vd.get("posts") else []
    posts = []
    for idx, p in enumerate(raw_posts[:16], 1):
        if not isinstance(p, dict):
            continue
        posts.append({
            "index": idx,
            "post_name": remove_emojis(p.get("post_name") or f"{to_bn_num(idx)} নম্বর পদ"),
            "vacancy": _clean_short_badge_val(p.get("vacancy_count"), fallback="নির্ধারিত"),
            "salary": remove_emojis(p.get("salary_scale") or "বিজ্ঞপ্তি অনুযায়ী"),
            "qualification": remove_emojis(p.get("educational_qualification") or elig_sum),
            "fee": remove_emojis(p.get("application_fee") or fee_sum),
            "duties": remove_emojis(p.get("key_duties") or "সংশ্লিষ্ট প্রাতিষ্ঠানিক দায়িত্ব পালন"),
        })

    if not posts:
        posts = [{
            "index": 1,
            "post_name": "বিভিন্ন পদে নিয়োগ",
            "vacancy": _clean_short_badge_val(vac_display, fallback="নির্ধারিত"),
            "salary": "সরকারি / প্রাতিষ্ঠানিক স্কেল",
            "qualification": elig_sum,
            "fee": fee_sum,
            "duties": "সংশ্লিষ্ট দাপ্তরিক ও প্রাতিষ্ঠানিক কার্যক্রম পরিচালনা",
        }]

    def _scene_for_segment_id(seg_id):
        if seg_id == "intro":
            return "intro", {
                "org": org,
                "cat_badge": cat_badge,
                "vac_num": vac_num,
                "vac_display": vac_display,
                "elig_sum": elig_sum,
            }
        if seg_id == "org_overview":
            return "org_overview", {
                "org": org_full,
                "vac_num": vac_num,
                "vac_display": vac_display,
                "district": district,
                "deadline": deadline,
                "fee_sum": fee_sum,
            }
        if seg_id == "post_0_part1":
            return "post_spotlight", {"post": posts[0], "total_posts": len(posts), "part": "overview"}
        if seg_id == "post_0_part2":
            return "post_details", {"post": posts[0], "total_posts": len(posts), "part": "qual_fee"}
        if seg_id.startswith("post_"):
            try:
                p_idx = int(seg_id.split("_")[1])
            except Exception:
                p_idx = 0
            p_idx = max(0, min(len(posts) - 1, p_idx))
            return "post_spotlight", {"post": posts[p_idx], "total_posts": len(posts), "part": "full"}
        if seg_id == "conditions":
            return "conditions", {
                "age_limit": age_limit,
                "district": district,
                "elig_sum": elig_sum,
                "fee_sum": fee_sum,
            }
        if seg_id == "deadline":
            return "deadline", {
                "deadline": deadline,
                "cat_badge": cat_badge,
                "org": org,
            }
        if seg_id == "whatsapp_cta":
            return "whatsapp_cta", {
                "wa_formatted": wa_formatted,
                "org": org,
            }
        return None, None

    beats = []

    # ---------------- মোড ১: নির্ভুল অডিও সেগমেন্ট টাইমস্ট্যাম্প (১০০% সিঙ্ক) ----------------
    if segment_timings and isinstance(segment_timings, list):
        valid_segs = [s for s in segment_timings if isinstance(s, dict) and s.get("id")]
        if valid_segs:
            timings_total = float(valid_segs[-1].get("end", 0.0) or 0.0)
            scale = (duration / timings_total) if (timings_total > 0 and abs(duration - timings_total) > 0.05) else 1.0

            for seg in valid_segs:
                b_type, payload = _scene_for_segment_id(str(seg["id"]))
                if not b_type:
                    continue
                start_t = 0.0 if not beats else beats[-1]["end"]
                end_t = min(duration, float(seg.get("end", start_t + 1.0)) * scale)
                if end_t <= start_t + 0.2:
                    end_t = min(duration, start_t + 0.5)
                beats.append({
                    "type": b_type,
                    "start": start_t,
                    "end": end_t,
                    "duration": max(0.35, end_t - start_t),
                    "payload": payload,
                })

            if beats:
                beats[-1]["end"] = duration
                beats[-1]["duration"] = max(0.35, duration - beats[-1]["start"])
                print(f"🎯 [Motion Timeline] Exact Audio-Synced Timings Applied ({len(beats)} beats, total={duration:.2f}s)")
                return {
                    "org": org,
                    "org_full": org_full,
                    "cat_badge": cat_badge,
                    "vac_display": vac_display,
                    "vac_num": vac_num,
                    "deadline": deadline,
                    "district": district,
                    "wa_formatted": wa_formatted,
                    "beats": beats,
                }

    # ---------------- মোড ২: কাস্টম অডিও বা প্রি-এক্সিস্টিং অডিওর জন্য অনুপাতিক টাইমলাইন ----------------
    script_segs = vd.get("script_segments")
    if isinstance(script_segs, list) and script_segs:
        weights = []
        mapped = []
        for seg in script_segs:
            if not isinstance(seg, dict):
                continue
            b_type, payload = _scene_for_segment_id(str(seg.get("id", "")))
            if not b_type:
                continue
            w = max(40, len(str(seg.get("text", "")).strip()))
            weights.append(w)
            mapped.append((b_type, payload))

        total_w = float(sum(weights)) if weights else 1.0
        if mapped:
            cursor = 0.0
            for (b_type, payload), w in zip(mapped, weights):
                b_dur = duration * (w / total_w)
                end_t = min(duration, cursor + b_dur)
                beats.append({
                    "type": b_type,
                    "start": cursor,
                    "end": end_t,
                    "duration": max(0.5, end_t - cursor),
                    "payload": payload,
                })
                cursor = end_t
            beats[-1]["end"] = duration
            beats[-1]["duration"] = max(0.5, duration - beats[-1]["start"])
            return {
                "org": org,
                "org_full": org_full,
                "cat_badge": cat_badge,
                "vac_display": vac_display,
                "vac_num": vac_num,
                "deadline": deadline,
                "district": district,
                "wa_formatted": wa_formatted,
                "beats": beats,
            }

    # ---------------- মোড ৩: চূড়ান্ত ফলব্যাক টাইমলাইন ----------------
    intro_dur = max(6.0, min(11.0, duration * 0.08))
    about_dur = max(6.5, min(14.0, duration * 0.11))
    cond_dur = max(7.0, min(14.0, duration * 0.10))
    deadline_dur = max(5.5, min(10.0, duration * 0.07))
    cta_dur = max(6.0, min(12.0, duration * 0.09))

    fixed_sum = intro_dur + about_dur + cond_dur + deadline_dur + cta_dur
    if fixed_sum >= duration * 0.65:
        scale_f = (duration * 0.55) / fixed_sum
        intro_dur *= scale_f
        about_dur *= scale_f
        cond_dur *= scale_f
        deadline_dur *= scale_f
        cta_dur *= scale_f
        fixed_sum = intro_dur + about_dur + cond_dur + deadline_dur + cta_dur

    posts_total_dur = max(6.0, duration - fixed_sum)
    post_beats = []
    if len(posts) == 1:
        half = posts_total_dur / 2.0
        post_beats.append(("post_spotlight", half, {"post": posts[0], "total_posts": 1, "part": "overview"}))
        post_beats.append(("post_details", half, {"post": posts[0], "total_posts": 1, "part": "qual_fee"}))
    else:
        per_post = posts_total_dur / float(len(posts))
        for p in posts:
            post_beats.append(("post_spotlight", per_post, {"post": p, "total_posts": len(posts), "part": "full"}))

    raw_timeline = [
        ("intro", intro_dur, _scene_for_segment_id("intro")[1]),
        ("org_overview", about_dur, _scene_for_segment_id("org_overview")[1]),
        *post_beats,
        ("conditions", cond_dur, _scene_for_segment_id("conditions")[1]),
        ("deadline", deadline_dur, _scene_for_segment_id("deadline")[1]),
        ("whatsapp_cta", cta_dur, _scene_for_segment_id("whatsapp_cta")[1]),
    ]

    cursor = 0.0
    for b_type, b_dur, payload in raw_timeline:
        end_t = min(duration, cursor + b_dur)
        beats.append({
            "type": b_type,
            "start": cursor,
            "end": end_t,
            "duration": max(0.5, end_t - cursor),
            "payload": payload,
        })
        cursor = end_t
    if beats:
        beats[-1]["end"] = duration
        beats[-1]["duration"] = max(0.5, duration - beats[-1]["start"])

    return {
        "org": org,
        "org_full": org_full,
        "cat_badge": cat_badge,
        "vac_display": vac_display,
        "vac_num": vac_num,
        "deadline": deadline,
        "district": district,
        "wa_formatted": wa_formatted,
        "beats": beats,
    }
