import os, json, time, re
import requests, feedparser
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from PIL import Image
import numpy as np
import io

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from moviepy.editor import AudioFileClip, VideoClip, concatenate_videoclips, VideoFileClip

# ==================== [ Google Services Setup ] ====================
def get_google_services():
    creds = Credentials(
        None,
        refresh_token=os.environ['REFRESH_TOKEN'],
        client_id=os.environ['CLIENT_ID'],
        client_secret=os.environ['CLIENT_SECRET'],
        token_uri="https://oauth2.googleapis.com/token"
    )
    # YouTube Service
    yt_service = build('youtube', 'v3', credentials=creds)
    # Drive Service
    drive_service = build('drive', 'v3', credentials=creds)
    return yt_service, drive_service

PARENT_FOLDER = os.environ['GDRIVE_PARENT_FOLDER_ID']
TMP_DIR = "temp_assets"

# ফোল্ডার বা ফাইলের নাম ঠিক করার জন্য (Bad character রিমুভ)
def clean_filename(text):
    return re.sub(r'[\\/*?:"<>|]', "", text)

# ইন্টারনেট থেকে ছবি ডাউনলোডের ফাংশন
def download_image(url, output_path):
    try:
        req = requests.get(url, stream=True, timeout=10)
        if req.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(req.content)
            return True
    except:
        pass
    return False

def download_drive_file(drive, file_id, dst):
    request = drive.files().get_media(fileId=file_id)
    fh = io.FileIO(dst, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()

# ==================== [ 1. FEED PARSING & DRIVE SYNC ] ====================
def check_new_articles_and_prepare_folders(drive):
    print("Checking for new RSS items (Last 24 Hours)...")
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            rss_links = json.load(f)['rss_links']
    except Exception as e:
        print(f"Error reading config.json: {e}")
        return

    time_limit = datetime.now() - timedelta(hours=24)
    existing_folders = {}
    
    # বর্তমান ফোল্ডারগুলো চেক করি
    try:
        query = f"'{PARENT_FOLDER}' in parents and trashed = false and mimeType='application/vnd.google-apps.folder'"
        results = drive.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        for item in results.get('files', []):
            existing_folders[item['name']] = item['id']
    except Exception as e:
        print(f"Google Drive Error: {e}")
        return

    for feed_url in rss_links:
        print(f"Parsing Feed: {feed_url}")
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            try:
                published_time = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            except:
                continue

            if published_time >= time_limit:
                folder_title = clean_filename(entry.title).strip()
                if not folder_title or folder_title in existing_folders:
                    continue 

                # ড্রাইভ এ ফোল্ডার তৈরি 
                print(f"New Article Found: {folder_title}. Preparing folder...")
                file_metadata = {
                    'name': folder_title,
                    'parents': [PARENT_FOLDER],
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                new_folder = drive.files().create(body=file_metadata, fields='id').execute()
                folder_id = new_folder.get('id')
                existing_folders[folder_title] = folder_id

                if not os.path.exists(TMP_DIR): os.makedirs(TMP_DIR)
                
                # আর্টিকেলের টাইটেল .txt এ সেভ করা
                title_txt = "title.txt"
                txt_path = os.path.join(TMP_DIR, title_txt)
                with open(txt_path, "w", encoding="utf-8") as text_file:
                    text_file.write(entry.title)

                drive.files().create(
                    body={'name': title_txt, 'parents': [folder_id]}, 
                    media_body=MediaFileUpload(txt_path, mimetype='text/plain')
                ).execute()

                # Extract and download images
                content = ""
                if hasattr(entry, 'content'):
                    content = entry.content[0].value
                elif hasattr(entry, 'summary'):
                    content = entry.summary
                
                soup = BeautifulSoup(content, 'html.parser')
                images = soup.find_all('img')
                
                img_count = 1
                for img in images:
                    src = img.get('src')
                    if src and src.startswith("http"):
                        img_path = os.path.join(TMP_DIR, f"image_{img_count}.jpg")
                        if download_image(src, img_path):
                            drive_media = MediaFileUpload(img_path, mimetype='image/jpeg')
                            drive.files().create(body={'name': f"{img_count}.jpg", 'parents': [folder_id]}, media_body=drive_media).execute()
                            img_count += 1


# ==================== [ 2. FRAME & MOVIE MAKER LOGIC ] ====================
def make_video_frame(img_path, duration):
    TARGET_W, TARGET_H = 1920, 1080
    pil_img = Image.open(img_path).convert("RGB")
    w, h = pil_img.size
    ratio = w / h

    # স্কেলিং ম্যাথমেটিকস (যাতে কোন স্ক্রিনে কাল দাগ না পড়ে)
    if ratio >= 1.777: 
        # চওড়া ছবির ক্ষেত্রে হাইটকে টার্গেট ১০৮০ ধরে স্কেল করা হবে
        new_h = TARGET_H
        new_w = int((new_h / h) * w)
    else:
        # লম্বালম্বি ছবির ক্ষেত্রে উইডথকে টার্গেট ১৯২০ ধরে স্কেল করা হবে
        new_w = TARGET_W
        new_h = int((new_w / w) * h)

    # জাস্ট ইন কেস (সেফ সাইড লজিক)
    if new_h < TARGET_H:
        new_h = TARGET_H
        new_w = int((new_h / h) * w)

    resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
    img_np = np.array(resized)
    
    def make_frame(t):
        progress = t / duration if duration > 0 else 0
        max_x = new_w - TARGET_W
        max_y = new_h - TARGET_H
        
        # উপর-নিচে স্ক্রলিং (লম্বা ছবির জন্য) এবং ডান-বাম স্ক্রলিং (চওড়া ছবির জন্য)
        y = int(progress * max_y) if max_y > 0 else 0 
        x = int(progress * max_x) if max_x > 0 else 0 
        return img_np[y:y+TARGET_H, x:x+TARGET_W]
        
    return VideoClip(make_frame, duration=duration)


# ==================== [ 3. VIDEO PROCESSING ] ====================
def process_ready_videos(drive, yt):
    print("Scanning Drive folders for Audio...")
    query = f"'{PARENT_FOLDER}' in parents and trashed = false and mimeType='application/vnd.google-apps.folder'"
    folders_req = drive.files().list(q=query, spaces='drive', fields='files(id, name)')
    results = folders_req.execute()
    
    for folder in results.get('files', []):
        sub_query = f"'{folder['id']}' in parents and trashed = false"
        sub_items = drive.files().list(q=sub_query, fields='files(id, name, mimeType)').execute().get('files', [])
        
        audio_file, txt_file = None, None
        img_files_drive = []
        for item in sub_items:
            mime = item['mimeType']
            if 'audio' in mime or item['name'].lower().endswith(('.mp3', '.wav', '.m4a')):
                audio_file = item
            elif mime == 'text/plain' or item['name'].lower().endswith('.txt'):
                txt_file = item
            elif 'image' in mime:
                img_files_drive.append(item)
                
        # ফোল্ডারে অডিও না থাকলে এটা স্কিপ করবে
        if not audio_file:
            continue
            
        print(f"==============================")
        print(f"Ready Folder Found: {folder['name']}")
        if not os.path.exists(TMP_DIR): os.makedirs(TMP_DIR)
        for f in os.listdir(TMP_DIR): os.remove(os.path.join(TMP_DIR, f))
        
        # ১. অডিও এবং টেক্সট লোকালি ডাউনলোড করা 
        audio_path = os.path.join(TMP_DIR, audio_file['name'])
        download_drive_file(drive, audio_file['id'], audio_path)
        
        video_title = folder['name']
        if txt_file:
            txt_path = os.path.join(TMP_DIR, "title.txt")
            download_drive_file(drive, txt_file['id'], txt_path)
            with open(txt_path, 'r', encoding='utf-8') as tf:
                video_title = tf.read().strip()
                
        # ২. ড্রাইভ থেকে ইমেজ ডাউনলোড 
        local_imgs = []
        # ছবির নাম অনুযায়ী সর্টিং করে নেওয়া, যেন image_1, image_2 ক্রমে আসে
        img_files_drive.sort(key=lambda x: x['name']) 
        for i_f in img_files_drive:
            ip = os.path.join(TMP_DIR, i_f['name'])
            download_drive_file(drive, i_f['id'], ip)
            local_imgs.append(ip)

        if not local_imgs:
            print("No images in this folder! Skipping...")
            continue
        
        print("Checking images for custom Thumbnail and Slide generation...")
        thumbnail_path = os.path.join(TMP_DIR, "custom_thumbnail.jpg")
        wide_img_path = None
        video_imgs = []

        # ৩. থাম্বনেইল ডিসাইড করা এবং ভিডিওর জন্য ইমেজ শর্ট আউট করা
        for lp in local_imgs:
            try:
                img = Image.open(lp)
                w, h = img.size
                if (w / h) >= 1.769:  # ১৬:৯ রেশিও (বা বেশি চওড়া)
                    wide_img_path = lp
                    break
            except:
                pass
                
        if wide_img_path:
            # চওড়া ছবি পাওয়া গিয়েছে! (এটি থাম্বনেইল হবে, ভিডিও থেকে স্কিপ হবে)
            img = Image.open(wide_img_path).convert("RGB")
            w, h = img.size
            # হাইট ৭২০ এ স্কেল করে সেন্টার ফোকাসে ক্রপ
            scale = 720 / h
            new_w = int(w * scale)
            if new_w < 1280:
                scale = 1280 / w
                new_w = 1280
            
            rs_img = img.resize((new_w, int(h * scale)), Image.LANCZOS)
            # মাঝখান থেকে ১২৮০x৭২০ কাটা হবে
            left = (rs_img.width - 1280) // 2
            right = left + 1280
            cropped_thumb = rs_img.crop((left, 0, right, 720))
            cropped_thumb.save(thumbnail_path, "JPEG", quality=95)
            print("→ Wide image found! Using it as THUMBNAIL (Excluded from Video).")
            
            # ভিডিও ইমেজে এই ছবিটি ছাড়া বাকি ছবি রাখা হচ্ছে 
            video_imgs = [ip for ip in local_imgs if ip != wide_img_path]
            
            # সেফটি চেক: যদি ফোল্ডারে আর কোনো ছবিই না থাকে! 
            if not video_imgs:
                print("→ Warning: ফোল্ডারে ভিডিও তৈরির জন্য অন্য কোনো ছবি নেই। বাধ্য হয়ে চওড়া ছবিটিকেই ভিডিওতে রাখছি।")
                video_imgs.append(wide_img_path)

        else:
            # চওড়া ছবি নেই। তাই প্রথম ছবি (লম্বা ছবি) কেই থাম্বনেইল ও ভিডিওতে নেওয়া হবে
            first_img_path = local_imgs[0]
            img = Image.open(first_img_path).convert("RGB")
            w, h = img.size
            # থাম্বনেইলের জন্য (১২৮০x৭২০), লম্বালম্বি ছবি হওয়ায় এর উইডথ-কে ১২৮০ তে ফিক্স করতে হবে 
            scale = 1280 / w
            new_h = int(h * scale)
            if new_h < 720:  
                scale = 720 / h
                new_h = 720
                
            rs_img = img.resize((int(w * scale), new_h), Image.LANCZOS)
            
            # যেহেতু লম্বা ছবি, নিচের অংশটুকু কেটে, শুধু একদম উপরের ১২৮০x৭২০ অংশটুকু (Top focus) রাখা হবে।
            cropped_thumb = rs_img.crop((0, 0, 1280, 720))
            cropped_thumb.save(thumbnail_path, "JPEG", quality=95)
            
            print("→ No wide images. First Tall image selected as THUMBNAIL (Kept Top Part). It's also kept for the Video.")
            
            # এখানে প্রথম ছবিটি সহ সবগুলো ছবিই ভিডিওতে যাবে
            video_imgs = local_imgs
        

        # ৪. মুভি / ভিডিও তৈরি করা (MoviePy)
        print("Starting video processing. Wait...")
        try:
            audio_clip = AudioFileClip(audio_path)
            audio_duration = audio_clip.duration
            per_img_duration = audio_duration / len(video_imgs)
            
            clips = []
            for v_img in video_imgs:
                clips.append(make_video_frame(v_img, per_img_duration))
                
            final_slideshow = concatenate_videoclips(clips)
            final_slideshow = final_slideshow.set_audio(audio_clip)
            
            # --- Outro.mp4 ভিডিওর শেষে যুক্ত করার ম্যাজিক ---
            outro_path = "Outro.mp4"
            if os.path.exists(outro_path):
                print("Outro.mp4 found, attaching at the end...")
                try:
                    outro_clip = VideoFileClip(outro_path)
                    if outro_clip.size != (1920, 1080):
                        outro_clip = outro_clip.resize((1920, 1080))
                    
                    # দুটি ভিডিও (স্লাইড + আউটরো) একসাথে জোড়া দেওয়া
                    final_video = concatenate_videoclips([final_slideshow, outro_clip], method="compose")
                except Exception as ex:
                    print(f"Error appending outro, going with regular slide: {ex}")
                    final_video = final_slideshow
            else:
                final_video = final_slideshow
                
            # ৫. এক্সপোর্ট করা (রেন্ডারিং) 
            output_video_path = os.path.join(TMP_DIR, "final_rendered_output.mp4")
            # Logger=None দিলে প্রচুর লগ আসবে না স্ক্রিনে
            final_video.write_videofile(
                output_video_path, fps=24, codec="libx264", audio_codec="aac", 
                threads=4, preset="ultrafast", logger=None
            )
            print("→ Video exported successfully Locally!")
            
            # ৬. YouTube Upload Calling
            upload_success = upload_to_youtube(yt, output_video_path, video_title, thumbnail_path)
            
            if upload_success:
                print(f"✓ Delete command running for the Drive folder: {folder['name']}")
                drive.files().delete(fileId=folder['id']).execute()
            else:
                print("x Video failed to upload! Drive Folder will not be deleted so you can check later.")

        except Exception as e:
            print(f"Failed creating video for {folder['name']} : {e}")

# ==================== [ 4. YOUTUBE UPLOAD LOGIC ] ====================
def upload_to_youtube(yt, video_file, title, thumbnail_path):
    print(f"Preparing to Upload on Youtube -> '{title}'")
    try:
        body = {
            'snippet': {
                'title': title,
                'description': "Generated by Auto BD Jobs Python Bot.",
                'tags': ['BD Govt Jobs', 'Govt Job News', 'BDJobs News Update', 'Today Notice']
            },
            'status': {
                'privacyStatus': 'private' # প্রাইভেসি ডিফল্ট private দেয়া আছে।
            }
        }
        
        # মেইন ভিডিও আপলোড 
        insert_request = yt.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=MediaFileUpload(video_file, chunksize=-1, resumable=True)
        )
        response = insert_request.execute()
        video_id = response.get('id')
        print(f"» Upload Success! View Private Link: https://youtube.com/watch?v={video_id}")
        
        # কাস্টম থাম্বনেইল আপলোড 
        if thumbnail_path and os.path.exists(thumbnail_path) and video_id:
            try:
                print("» Setting custom auto generated Thumbnail...")
                yt.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path, mimetype='image/jpeg')
                ).execute()
                print("» Custom Thumbnail Added!")
            except Exception as tb_e:
                print(f"! Custom Thumbnail error (Make sure Youtube Phone Verfied): {tb_e}")

        return True
    except Exception as yt_err:
        print(f"YouTube Upload Blocked by Exception: {yt_err}")
        return False

# ==================== [ MAIN EXECUTION ] ====================
if __name__ == "__main__":
    print("================== [ RSS YOUTUBE BOT ] ==================")
    try:
        yt_srv, dr_srv = get_google_services()
        # ধাপ ১: ড্রাইভ স্ক্যান ও ছবি/আর্টিকেল সেভ
        check_new_articles_and_prepare_folders(dr_srv)
        print("-" * 50)
        # ধাপ ২: অডিও পেলে মুভি বানিয়ে ইউটুবে ছাড়া
        process_ready_videos(dr_srv, yt_srv)
        
        print("\nAll Script Process Finalized Cleanly! OK :)")
    except Exception as final_e:
        print(f"Main Run Error Exception Found: {final_e}")