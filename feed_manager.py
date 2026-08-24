# -*- coding: utf-8 -*-
import os, json, time, re, shutil, requests, feedparser
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

WORKSPACE_DIR = "workspace"

def clean_filename(text):
    return re.sub(r'[\\/*?:"<>|]', "", text)

def download_image(url, output_path):
    try:
        req = requests.get(url, timeout=10)
        if req.status_code == 200 and len(req.content) > 3000:
            with open(output_path, 'wb') as f:
                f.write(req.content)
            return True
    except Exception: pass
    return False

def check_new_articles_and_prepare_folders():
    print("Checking for new RSS items (Last 24 Hours)...")
    if not os.path.exists(WORKSPACE_DIR): os.makedirs(WORKSPACE_DIR)
    if not os.path.exists('config.json'): return

    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            rss_links = config_data.get('rss_links', [])
    except Exception: return

    time_limit = datetime.now() - timedelta(hours=24)
    existing = [f for f in os.listdir(WORKSPACE_DIR) if os.path.isdir(os.path.join(WORKSPACE_DIR, f))]
    
    history_file = os.path.join(WORKSPACE_DIR, "history.txt")
    history_logs = []
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as hf:
                history_logs = [line.strip() for line in hf if line.strip()]
        except Exception: pass

    req_headers = {'User-Agent': 'Mozilla/5.0'}

    for feed_url in rss_links:
        try:
            resp = requests.get(feed_url, headers=req_headers, timeout=15)
            feed = feedparser.parse(resp.content) if resp.status_code == 200 else feedparser.parse(feed_url)
        except Exception: continue
        
        for entry in feed.entries:
            try: published_time = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            except Exception: continue

            if published_time >= time_limit:
                folder_title = clean_filename(entry.title).strip()
                if folder_title.lower() == "shorts" or not folder_title or folder_title in existing or folder_title in history_logs: 
                    continue 

                content = entry.content[0].value if hasattr(entry, 'content') else getattr(entry, 'summary', "")
                images = BeautifulSoup(content, 'html.parser').find_all('img')
                valid_img_urls = [img.get('src') for img in images if img.get('src') and img.get('src').startswith("http")]

                # 🌟 যদি আর্টিকেলে কোনো ছবি না থাকে, তবে ফোল্ডার তৈরি হবে না
                if not valid_img_urls:
                    print(f"⏩ Skipping '{folder_title}' (No images found in article).")
                    continue

                folder_path = os.path.join(WORKSPACE_DIR, folder_title)
                os.makedirs(folder_path, exist_ok=True)
                
                img_count = 1
                for src in valid_img_urls:
                    img_path = os.path.join(folder_path, f"{img_count}.jpg")
                    if download_image(src, img_path):
                        img_count += 1

                # 🌟 যদি ছবি ডাউনলোড ব্যর্থ হয় এবং ০ ছবি থাকে, তবে ফোল্ডারটি মুছে ফেলবে
                if img_count == 1:
                    print(f"⏩ Removing '{folder_title}' (Failed to download images).")
                    shutil.rmtree(folder_path, ignore_errors=True)
                    continue

                print(f"✅ New Article with {img_count - 1} Images: {folder_title}")
                with open(os.path.join(folder_path, "title.txt"), "w", encoding="utf-8") as text_file:
                    text_file.write(entry.title)

                existing.append(folder_title)
                history_logs.append(folder_title)
                try:
                    with open(history_file, 'a', encoding='utf-8') as hf:
                        hf.write(f"{folder_title}\n")
                except Exception: pass
