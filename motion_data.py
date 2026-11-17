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


def build_motion_timeline(verified_data, voiceover_script, title, duration):
    """
    অডিওর দৈর্ঘ্য ও প্রতিটি পদের অনুপাতে ডাইনামিক মোশন গ্রাফিক্স টাইমলাইন (beats) তৈরি করে।
    ফলে ভিডিও কখনোই অনেকক্ষণ স্থির হয়ে থাকে না—প্রতিটি পদের কথা শুরুর সাথে সাথে পর্দায় সেই পদের
    নাম, লোক সংখ্যা, বেতন, দায়িত্ব, যোগ্যতা ও ফি-র অ্যানিমেশন চলে আসে!
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
            "vacancy": remove_emojis(p.get("vacancy_count") or "নির্ধারিত"),
            "salary": remove_emojis(p.get("salary_scale") or "বিজ্ঞপ্তি অনুযায়ী"),
            "qualification": remove_emojis(p.get("educational_qualification") or elig_sum),
            "fee": remove_emojis(p.get("application_fee") or fee_sum),
            "duties": remove_emojis(p.get("key_duties") or "সংশ্লিষ্ট প্রাতিষ্ঠানিক দায়িত্ব পালন"),
        })

    if not posts:
        posts = [{
            "index": 1,
            "post_name": "বিভিন্ন পদে নিয়োগ",
            "vacancy": vac_display,
            "salary": "সরকারি / প্রাতিষ্ঠানিক স্কেল",
            "qualification": elig_sum,
            "fee": fee_sum,
            "duties": "সংশ্লিষ্ট দাপ্তরিক ও প্রাতিষ্ঠানিক কার্যক্রম পরিচালনা",
        }]

    # ---------------- প্রতিটি সেকশনের আনুপাতিক সময় নির্ধারণ ----------------
    # স্ক্রিপ্টের কাঠামো: [১] ইন্ট্রো + পরিচিতি -> [২] এক এক করে প্রতিটি পদ -> [৩] শর্ত/সুবিধা -> [৪] সময়সীমা -> [৫] WhatsApp CTA
    intro_dur = max(6.0, min(11.0, duration * 0.08))
    about_dur = max(6.5, min(12.0, duration * 0.09))
    cond_dur = max(7.0, min(14.0, duration * 0.10))
    deadline_dur = max(6.0, min(11.0, duration * 0.08))
    cta_dur = max(6.0, min(11.0, duration * 0.09))

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

    # যদি মাত্র ১টি পদ থাকে, তবে সেটিকে ২টি আলাদা বিটে ভেঙে দেখানো হবে যাতে স্ক্রিন দীর্ঘক্ষণ স্থির না থাকে
    post_beats = []
    if len(posts) == 1:
        p = posts[0]
        half = posts_total_dur / 2.0
        post_beats.append(("post_spotlight", half, {"post": p, "total_posts": 1, "part": "overview"}))
        post_beats.append(("post_details", half, {"post": p, "total_posts": 1, "part": "qual_fee"}))
    else:
        per_post = posts_total_dur / float(len(posts))
        for p in posts:
            post_beats.append(("post_spotlight", per_post, {"post": p, "total_posts": len(posts), "part": "full"}))

    raw_timeline = [
        ("intro", intro_dur, {
            "org": org,
            "cat_badge": cat_badge,
            "vac_num": vac_num,
            "vac_display": vac_display,
            "elig_sum": elig_sum,
        }),
        ("org_overview", about_dur, {
            "org": org_full,
            "vac_num": vac_num,
            "vac_display": vac_display,
            "district": district,
            "deadline": deadline,
            "fee_sum": fee_sum,
        }),
        *post_beats,
        ("conditions", cond_dur, {
            "age_limit": age_limit,
            "district": district,
            "elig_sum": elig_sum,
            "fee_sum": fee_sum,
        }),
        ("deadline", deadline_dur, {
            "deadline": deadline,
            "cat_badge": cat_badge,
            "org": org,
        }),
        ("whatsapp_cta", cta_dur, {
            "wa_formatted": wa_formatted,
            "org": org,
        }),
    ]

    beats = []
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
