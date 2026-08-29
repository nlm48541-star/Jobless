# -*- coding: utf-8 -*-
import os, re, shutil, requests, feedparser
from urllib.parse import urljoin
from bs4 import BeautifulSoup

WORKSPACE_DIR = "workspace"
RSS_URLS = [
    # আপনার আরএসএস ফিড লিংকগুলো এখানে দিন (যদি কোনো নির্দিষ্ট তালিকা থাকে)
    "https://bdgovtjob.net/feed/",
    "https://chakrirkhobor.net/feed/"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

def clean_filename(text):
    """ফোল্ডারের নাম নিরাপদ ও পরিষ্কার করে"""
    text = re.sub(r'[\\/*?:"<>|]', "", str(text))
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:90]

def is_forbidden_article(text):
    """এনজিও বা ব্যাংক সংক্রান্ত সার্কুলার ফিল্টার করে"""
    if not text: return False
    text_lower = text.lower()
    forbidden = ["এনজিও", "ব্যাংক", "ngo", "bank"]
    return any(k in text_lower for k in forbidden)

def extract_image_urls_from_html(html_content, base_url=""):
    """HTML থেকে সব ধরনের লেজি-লোড ও সাধারণ ছবির URL বের করে"""
    if not html_content: return []
    soup = BeautifulSoup(html_content, 'html.parser')
    img_urls = []
    
    # মূল পোস্ট কনটেইনারগুলোকে প্রাধান্য দেওয়া
    containers = soup.find_all(['div', 'article', 'section'], class_=re.compile(r'(post-body|entry-content|post-content|article-body|td-post-content|main-content)', re.I))
    elements = containers if containers else [soup]

    for container in elements:
        for img in container.find_all('img'):
            src = (
                img.get('data-original') or 
                img.get('data-src') or 
                img.get('data-lazy-src') or 
                img.get('data-orig-file') or 
                img.get('src')
            )
            if not src:
                srcset = img.get('srcset')
                if srcset:
                    src = srcset.split(',')[0].split()[0]

            if src:
                src = src.strip()
                if base_url:
                    src = urljoin(base_url, src)
                    
                src_lower = src.lower()
                # লোগো, আইকন, ইমোজি, অবতার ইত্যাদি বাদ দেওয়া
                if any(ext in src_lower for ext in ['.jpg', '.jpeg', '.png', '.webp']) or 'uploads' in src_lower:
                    if not any(bad in src_lower for bad in ['logo', 'avatar', 'gravatar', 'icon', 'emoji', 'share', 'button', 'badge']):
                        if src.startswith("http") and src not in img_urls:
                            img_urls.append(src)
                            
    return img_urls

def scrape_images_from_webpage(page_url):
    """আরএসএসে ছবি না থাকলে সরাসরি আর্টিকেলের ওয়েবপেজ ভিজিট করে ছবি সংগ্রহ করে"""
    try:
        req_headers = HEADERS.copy()
        req_headers["Referer"] = page_url
        resp = requests.get(page_url, headers=req_headers, timeout=15)
        if resp.status_code == 200:
            return extract_image_urls_from_html(resp.text, base_url=page_url)
    except Exception as e:
        print(f"⚠️ Webpage scrape notice for {page_url}: {e}")
    return []

def download_image(img_url, save_path, referer_url=""):
    """নিরাপদভাবে ছবি ডাউনলোড করে (৩ কেবি-র ছোট আইকন বাদ দেয়)"""
    try:
        req_headers = HEADERS.copy()
        if referer_url:
            req_headers["Referer"] = referer_url
            
        r = requests.get(img_url, headers=req_headers, timeout=20)
        if r.status_code == 200 and len(r.content) > 3072: # ৩ কেবি-র বড় হতে হবে
            with open(save_path, "wb") as f:
                f.write(r.content)
            return True
    except Exception:
        pass
    return False

def check_new_articles_and_prepare_folders():
    """আরএসএস ও ওয়েবসাইট থেকে নতুন সার্কুলার এবং ছবি ডাউনলোড করে ফোল্ডার প্রস্তুত করে"""
    print("\n🔍 Checking for new RSS items & circular images...")
    os.makedirs(WORKSPACE_DIR, exist_ok=True)

    for rss_url in RSS_URLS:
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                title = entry.get('title', '').strip()
                link = entry.get('link', '').strip()
                
                if not title or not link: continue

                # ১. এনজিও / ব্যাংক ফিল্টার
                content_text = entry.get('summary', '') or (entry.content[0].value if hasattr(entry, 'content') else '')
                if is_forbidden_article(title) or is_forbidden_article(content_text):
                    print(f"🚫 [FILTERED] Skipping '{title}' (Matches forbidden keyword: 'এনজিও' / 'ব্যাংক').")
                    continue

                folder_name = clean_filename(title)
                folder_path = os.path.join(WORKSPACE_DIR, folder_name)

                # ফোল্ডার ইতিমধ্যে থাকলে স্কিপ
                if os.path.exists(folder_path):
                    continue

                # ২. ছবি খোঁজা: প্রথমে RSS কনটেন্টে
                img_urls = extract_image_urls_from_html(content_text, base_url=link)
                
                # RSS-এ না পাওয়া গেলে সরাসরি লাইভ ওয়েবপেজে গিয়ে ছবি খোঁজা
                if not img_urls:
                    print(f"🌐 Fetching live article page for images: '{title[:45]}...'")
                    img_urls = scrape_images_from_webpage(link)

                # ৩. যদি কোনোভাবেই ছবি না পাওয়া যায়
                if not img_urls:
                    print(f"⏩ Skipping '{title}' (No images found in article).")
                    continue

                # ৪. ফোল্ডার তৈরি ও ছবি ডাউনলোড
                os.makedirs(folder_path, exist_ok=True)
                downloaded_count = 0

                for idx, img_url in enumerate(img_urls[:5], start=1):
                    ext = img_url.lower().split('.')[-1].split('?')[0]
                    if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                        ext = 'jpg'
                    img_save_path = os.path.join(folder_path, f"image_{idx}.{ext}")
                    if download_image(img_url, img_save_path, referer_url=link):
                        downloaded_count += 1

                # যদি ডাউনলোড সফল না হয় তবে ফাঁকা ফোল্ডার মুছে ফেলা
                if downloaded_count == 0:
                    shutil.rmtree(folder_path, ignore_errors=True)
                    print(f"⏩ Skipping '{title}' (Image download failed).")
                    continue

                # সার্কুলার টাইটেল সেভ
                with open(os.path.join(folder_path, "title.txt"), "w", encoding="utf-8") as tf:
                    tf.write(title)

                print(f"📥 [PREPARED] Successfully prepared '{folder_name}' with {downloaded_count} image(s).")

        except Exception as e:
            print(f"⚠️ RSS Feed Error ({rss_url}): {e}")
