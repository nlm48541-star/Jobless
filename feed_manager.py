# -*- coding: utf-8 -*-
import os, json, time, re, requests, feedparser
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

WORKSPACE_DIR = "workspace"

def clean_filename(text):
    return re.sub(r'[\\/*?:"<>|]', "", text)

def download_image(url, output_path):
    try:
        req = requests.get(url, timeout=10)
        if req.status_code == 200:
            with open(output_path, 'wb') as f: f.write(req.content)
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

                folder_path = os.path.join(WORKSPACE_DIR, folder_title)
                os.makedirs(folder_path, exist_ok=True)
                existing.append(folder_title)
                
                try:
                    with open(history_file, 'a', encoding='utf-8') as hf: f.write(f"{folder_title}\n")
                except Exception: pass

                with open(os.path.join(folder_path, "title.txt"), "w", encoding="utf-8") as text_file:
                    text_file.write(entry.title)

                content = entry.content[0].value if hasattr(entry, 'content') else getattr(entry, 'summary', "")
                images = BeautifulSoup(content, 'html.parser').find_all('img')
                
                img_count = 1
                for img in images:
                    src = img.get('src')
                    if src and src.startswith("http"):
                        img_path = os.path.join(folder_path, f"{img_count}.jpg")
                        if download_image(src, img_path): img_count += 1
