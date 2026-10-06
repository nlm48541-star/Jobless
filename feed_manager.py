# -*- coding: utf-8 -*-
import os, json, time, re, shutil, requests, feedparser
from datetime import datetime, timedelta
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from PIL import Image

WORKSPACE_DIR = "workspace"
FORBIDDEN_KEYWORDS = ['এনজিও', 'ngo', 'ব্যাংক', 'bank', 'চলমান']

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}

def is_forbidden_article(text):
    if not text: return False
    return any(k in str(text).lower() for k in FORBIDDEN_KEYWORDS)

def clean_filename(text):
    text = re.sub(r'[\\/*?:"<>|]', "", str(text))
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:90]

def extract_image_urls_from_html(html_content, base_url=""):
    if not html_content: return []
    soup = BeautifulSoup(html_content, 'html.parser')
    img_urls = []
    
    containers = soup.find_all(['div', 'article', 'section'], class_=re.compile(r'(post-body|entry-content|post-content|article-body|td-post-content|main-content)', re.I))
    elements = containers if containers else [soup]

    for container in elements:
        for img in container.find_all('img'):
            src = (
                img.get('data-original') or img.get('data-src') or 
                img.get('data-lazy-src') or img.get('data-orig-file') or img.get('src')
            )
            if not src:
                srcset = img.get('srcset')
                if srcset: src = srcset.split(',')[0].split()[0]

            if src:
                src = src.strip()
                if base_url: src = urljoin(base_url, src)
                src_lower = src.lower()
                if any(ext in src_lower for ext in ['.jpg', '.jpeg', '.png', '.webp']) or 'uploads' in src_lower:
                    if not any(bad in src_lower for bad in ['logo', 'avatar', 'gravatar', 'icon', 'emoji', 'share', 'button', 'badge']):
                        if src.startswith("http") and src not in img_urls:
                            img_urls.append(src)
    return img_urls

def scrape_article_content_and_images(page_url):
    """
    🌟 ওয়েবসাইট থেকে সম্পূর্ণ আর্টিকেলের পরিষ্কার টেক্সট এবং ছবি সংগ্রহ করে
    """
    title = ""
    clean_text = ""
    img_urls = []
    try:
        resp = requests.get(page_url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')

            h1 = soup.find('h1')
            if h1: title = h1.get_text(strip=True)
            elif soup.title: title = soup.title.get_text(strip=True).split('-')[0].split('|')[0].strip()

            target = soup.find(['div', 'article', 'section'], class_=re.compile(r'(post-body|entry-content|post-content|article-body|td-post-content|main-content)', re.I))
            if not target: target = soup

            for tag in target(['script', 'style', 'noscript', 'nav', 'footer']):
                tag.decompose()

            clean_text = target.get_text(separator='\n', strip=True)
            img_urls = extract_image_urls_from_html(resp.text, base_url=page_url)
    except Exception as e:
        print(f"⚠️ Error scraping article: {e}")
    return title, clean_text, img_urls

def download_image(url, output_path, referer_url=""):
    try:
        req_headers = HEADERS.copy()
        if referer_url: req_headers["Referer"] = referer_url
        req = requests.get(url, headers=req_headers, timeout=15)
        if req.status_code == 200 and len(req.content) > 3000:
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
            rss_links = json.load(f).get('rss_links', [])
    except Exception: return

    time_limit = datetime.now() - timedelta(hours=24)
    existing = [f for f in os.listdir(WORKSPACE_DIR) if os.path.isdir(os.path.join(WORKSPACE_DIR, f))]
    
    history_file = os.path.join(WORKSPACE_DIR, "history.txt")
    history_logs = set()
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as hf:
                history_logs = {line.strip().lower() for line in hf if line.strip()}
        except Exception: pass

    for feed_url in rss_links:
        try:
            resp = requests.get(feed_url, headers=HEADERS, timeout=15)
            feed = feedparser.parse(resp.content) if resp.status_code == 200 else feedparser.parse(feed_url)
        except Exception: continue
        
        for entry in feed.entries:
            try: published_time = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            except Exception: continue

            if published_time >= time_limit:
                raw_title = entry.title.strip()
                folder_title = clean_filename(raw_title).strip()
                link = entry.get('link', '').strip()

                if folder_title.lower() == "shorts" or not folder_title or folder_title in existing:
                    continue

                if link.lower() in history_logs or raw_title.lower() in history_logs:
                    continue

                if is_forbidden_article(raw_title) or is_forbidden_article(folder_title):
                    print(f"🚫 [FILTERED] Skipping '{folder_title}'.")
                    continue

                # 🌟 ওয়েবসাইট থেকে সম্পূর্ণ আর্টিকেল টেক্সট ও ছবি সংগ্রহ
                scraped_title, article_text, img_urls = scrape_article_content_and_images(link)
                if not img_urls:
                    print(f"⏩ Skipping '{folder_title}' (No images found).")
                    continue

                folder_path = os.path.join(WORKSPACE_DIR, folder_title)
                os.makedirs(folder_path, exist_ok=True)
                
                downloaded_temp_files = []
                for idx, src in enumerate(img_urls, start=1):
                    temp_img_path = os.path.join(folder_path, f"temp_{idx}.jpg")
                    if download_image(src, temp_img_path, referer_url=link):
                        downloaded_temp_files.append(temp_img_path)

                if not downloaded_temp_files:
                    shutil.rmtree(folder_path, ignore_errors=True)
                    continue

                # ব্যানার রিমুভার
                if len(downloaded_temp_files) > 1:
                    try:
                        with Image.open(downloaded_temp_files[0]) as first_img:
                            w, h = first_img.size
                            if (w / h) >= (16.0 / 9.0) - 0.05:
                                os.remove(downloaded_temp_files[0])
                                downloaded_temp_files.pop(0)
                                print(f"✂️ [Banner Removed] Dropped 1st banner image ({w}x{h}).")
                    except Exception: pass

                final_img_count = 0
                for final_idx, temp_path in enumerate(downloaded_temp_files, start=1):
                    final_path = os.path.join(folder_path, f"{final_idx}.jpg")
                    try:
                        os.rename(temp_path, final_path)
                        final_img_count += 1
                    except Exception: pass

                if final_img_count == 0:
                    shutil.rmtree(folder_path, ignore_errors=True)
                    continue

                # 🌟 টাইটেল, লিংক এবং আর্টিকেলের ফুল টেক্সট সেভ করা
                with open(os.path.join(folder_path, "title.txt"), "w", encoding="utf-8") as tf:
                    tf.write(raw_title)
                if link:
                    with open(os.path.join(folder_path, "link.txt"), "w", encoding="utf-8") as lf:
                        lf.write(link)
                if article_text:
                    with open(os.path.join(folder_path, "article.txt"), "w", encoding="utf-8") as af:
                        af.write(article_text)

                print(f"✅ Prepared Article: {folder_title} ({final_img_count} Images, Text Saved)")
                existing.append(folder_title)
