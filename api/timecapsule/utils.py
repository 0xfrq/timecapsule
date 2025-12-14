import os
import uuid
import requests
import mimetypes
import yt_dlp
import re
from datetime import datetime
from django.conf import settings
from .models import Post, Tag, PostTime

# ================= HELPER 1: DOWNLOAD FOTO (Via Requests) =================
# Digunakan untuk: TikTok Slideshow & Instagram Photos
def download_media(url, folder_name="downloads"):
    """
    Download file statis (Gambar/Video) menggunakan requests.
    Dilengkapi Headers agar tidak dianggap bot oleh CDN TikTok/IG.
    """
    if not url:
        return None
    
    try:
        save_path = os.path.join(settings.MEDIA_ROOT, folder_name)
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        # Header Penyamaran
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        # Sesuaikan Referer
        if "tiktok" in url or "ttl" in url:
            headers["Referer"] = "https://www.tiktok.com/"
        elif "instagram" in url or "cdninstagram" in url or "fbcdn" in url:
            headers["Referer"] = "https://www.instagram.com/"

        print(f"⬇️ [Requests] Downloading: {url[:60]}...")
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            
            # Tentukan extension berdasarkan content-type
            if 'video' in content_type:
                ext = '.mp4'
            elif 'image' in content_type:
                ext = mimetypes.guess_extension(content_type) or '.jpg'
            else:
                ext = '.jpg'
            
            filename = f"{uuid.uuid4()}{ext}"
            full_path = os.path.join(save_path, filename)
            
            with open(full_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            
            print(f"✅ [Requests] Sukses: {filename}")
            return f"{folder_name}/{filename}"
        else:
            print(f"❌ [Requests] Gagal. Status: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ [Requests] Error: {e}")
        return None


# ================= HELPER 2: DOWNLOAD VIDEO (Via YT-DLP) =================
# Digunakan untuk: TikTok Video, YouTube
def download_video_ytdlp(target_url):
    """
    Download Video menggunakan engine yt-dlp.
    Jauh lebih kuat menembus proteksi 403 Forbidden TikTok.
    """
    folder_name = "downloads"
    save_path = os.path.join(settings.MEDIA_ROOT, folder_name)
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    filename = f"{uuid.uuid4()}.mp4"
    ydl_opts = {
        'quiet': True,
        'format': 'best[ext=mp4]/best', 
        'outtmpl': os.path.join(save_path, filename),
        'noplaylist': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        print(f"⬇️ [yt-dlp] Downloading Video: {target_url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([target_url])
        
        if os.path.exists(os.path.join(save_path, filename)):
            print(f"✅ [yt-dlp] Sukses: {filename}")
            return f"{folder_name}/{filename}"
        return None
    except Exception as e:
        print(f"❌ [yt-dlp] Error: {e}")
        return None


# ================= HELPER 3: DOWNLOAD INSTAGRAM MEDIA (Via API Data) =================
def download_instagram_media_from_api(api_data):
    """
    Download media Instagram dari data API.
    Detect carousel via edge_sidecar_to_children.
    
    Return: tuple (list_of_paths, media_type)
    """
    downloads_folder = "downloads"
    downloads_path = os.path.join(settings.MEDIA_ROOT, downloads_folder)
    
    if not os.path.exists(downloads_path):
        os.makedirs(downloads_path)
    
    final_paths = []
    media_type = 'photo'  # Default
    
    # Cek apakah ini carousel (edge_sidecar_to_children)
    sidecar = api_data.get('edge_sidecar_to_children')
    
    if sidecar and sidecar.get('edges'):
        # ========== CAROUSEL / IMAGE ALBUM ==========
        edges = sidecar['edges']
        print(f"🖼️ [IG] Detected CAROUSEL with {len(edges)} items")
        
        for idx, edge in enumerate(edges):
            node = edge.get('node', {})
            is_video = node.get('is_video', False)
            
            # Ambil URL - untuk video coba video_url dulu
            if is_video:
                item_url = node.get('video_url') or node.get('display_url')
            else:
                item_url = node.get('display_url')
            
            if item_url:
                print(f"   ⬇️ [{idx+1}/{len(edges)}] Downloading: {'video' if is_video else 'image'}...")
                saved = download_media(item_url, downloads_folder)
                if saved:
                    final_paths.append(saved)
        
        # Tentukan media_type berdasarkan jumlah file
        if len(final_paths) == 1:
            media_type = 'photo'
        else:
            media_type = 'image_album'
    
    elif api_data.get('is_video'):
        # ========== SINGLE VIDEO ==========
        print("🎥 [IG] Detected SINGLE VIDEO")
        video_url = api_data.get('video_url')
        if video_url:
            saved = download_media(video_url, downloads_folder)
            if saved:
                final_paths.append(saved)
        media_type = 'video'
    
    else:
        # ========== SINGLE PHOTO ==========
        print("📸 [IG] Detected SINGLE PHOTO")
        photo_url = api_data.get('display_url')
        if photo_url:
            saved = download_media(photo_url, downloads_folder)
            if saved:
                final_paths.append(saved)
        media_type = 'photo'
    
    print(f"🏷️ [IG] Final: {len(final_paths)} file(s) → {media_type}")
    return final_paths, media_type


# ================= TIKTOK LOGIC (HYBRID) =================
def extract_tiktok_id(url):
    pattern = r"(?:video|photo)/(\d+)"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def scrape_tiktok_data(original_url):
    # 1. Ambil ID untuk Metadata API
    video_id = extract_tiktok_id(original_url)
    if not video_id:
        return None

    # 2. Metadata API (Tetap pakai RapidAPI untuk data teks yg akurat)
    url_api = "https://tiktok-api23.p.rapidapi.com/api/post/detail"
    headers = {
        "x-rapidapi-key": "31b6bb776fmshf2f28b986086358p1bdcc1jsn15e4b0eb8f34",
        "x-rapidapi-host": "tiktok-api23.p.rapidapi.com"
    }
    try:
        response = requests.get(url_api, headers=headers, params={"videoId": video_id})
        data = response.json()

        if data.get('statusCode') == 0:
            post = data['itemInfo']['itemStruct']
            paths = []
            
            # --- HYBRID SWITCHING ---
            
            # KASUS A: IMAGE/SLIDESHOW -> Pakai Requests
            if post.get('imagePost'):
                images = post['imagePost']['images']
                thumb = images[0]['imageURL']['urlList'][-1] if images else ""
                
                print("📸 Mode: TikTok Images (Requests)")
                for img in images:
                    img_url = img['imageURL']['urlList'][-1]
                    saved = download_media(img_url, 'downloads')
                    if saved:
                        paths.append(saved)
                
                # Tentukan media_type berdasarkan jumlah gambar
                if len(paths) == 1:
                    media_type = 'photo'
                else:
                    media_type = 'image_album'
                
                print(f"🏷️ [TikTok] Detected: {len(paths)} image(s) → {media_type}")
            
            # KASUS B: VIDEO -> Pakai YT-DLP (Pake URL Asli User)
            else:
                media_type = 'video'
                thumb = post.get('video', {}).get('cover', '')
                
                print("🎥 Mode: TikTok Video (yt-dlp)")
                saved = download_video_ytdlp(original_url)
                if saved:
                    paths.append(saved)
            
            # ------------------------

            return {
                "url": original_url,
                "description": post.get('desc', ''), 
                "media_type": media_type,
                "thumbnail": thumb, 
                "year": datetime.fromtimestamp(int(post.get('createTime', 0))).year, 
                "tags": re.findall(r"#(\w+)", post.get('desc', '')),
                "local_file": ",".join(paths)
            }
        return None
    except Exception as e:
        print(f"TikTok Scraper Error: {e}")
        return None

def save_tiktok_to_db(data):
    try:
        post = Post.objects.create(
            url=data['url'], media_type=data['media_type'],
            thumb_url=data['thumbnail'], description=data['description'],
            local_file=data['local_file']
        )
        PostTime.objects.create(post=post, year=data['year'])
        for tag_text in data['tags']:
            tag_obj, _ = Tag.objects.get_or_create(name=tag_text)
            post.tags.add(tag_obj)
        return post
    except Exception as e:
        print(f"TikTok DB Error: {e}")
        return None


# ================= INSTAGRAM LOGIC (API-Based with Carousel Support) =================
def scrape_insta_data(original_url):
    """
    Instagram Scraper dengan deteksi carousel via edge_sidecar_to_children.
    
    Flow:
    1. Call API get_media_data.php → dapat struktur media + URLs
    2. Detect tipe: single photo, single video, atau carousel
    3. Download semua media via requests
    4. Call API get_reel_title.php → dapat caption
    5. Return data untuk disimpan ke DB
    """
    
    # Parsing shortcode & type dari URL
    pattern = r"(?:p|reel|tv)/([A-Za-z0-9_-]+)"
    match = re.search(pattern, original_url)
    if not match:
        print("❌ [IG] Could not extract shortcode from URL")
        return None
    
    shortcode = match.group(1)
    
    # Tentukan api_type berdasarkan URL
    if "/reel/" in original_url or "/tv/" in original_url:
        api_type = "reel"
    else:
        api_type = "post"

    print("=" * 50)
    print("🚀 [IG] Starting Instagram Scraper (API + Carousel Support)")
    print(f"📎 URL: {original_url}")
    print(f"🔖 Shortcode: {shortcode} | Type: {api_type}")
    print("=" * 50)

    # API Headers
    headers = {
        "x-rapidapi-key": "31b6bb776fmshf2f28b986086358p1bdcc1jsn15e4b0eb8f34",
        "x-rapidapi-host": "instagram-scraper-stable-api.p.rapidapi.com"
    }
    
    paths = []
    media_type = 'photo'
    thumb = ""
    desc = ""
    year = datetime.now().year
    
    # STEP 1: Get Visual/Media Data dari API
    try:
        print("📡 [IG] Fetching media data from API...")
        querystring_visual = {
            "reel_post_code_or_url": original_url,
            "type": api_type
        }
        res_vis = requests.get(
            "https://instagram-scraper-stable-api.p.rapidapi.com/get_media_data.php", 
            headers=headers, 
            params=querystring_visual,
            timeout=30
        )
        data_vis = res_vis.json()
        
        if not data_vis.get('id'):
            print("❌ [IG] API returned no valid data (no 'id' field)")
            return None
        
        # Thumbnail (selalu ambil dari root level)
        thumb = data_vis.get('thumbnail_src') or data_vis.get('display_url') or ""
        
        # Year dari timestamp
        raw_time = data_vis.get('taken_at_timestamp') or data_vis.get('taken_at')
        if raw_time and int(raw_time) > 0:
            year = datetime.fromtimestamp(int(raw_time)).year
        
        print(f"   ✓ API Response OK | Year: {year}")
        
        # STEP 2: Download media berdasarkan struktur
        paths, media_type = download_instagram_media_from_api(data_vis)
        
        if not paths:
            print("❌ [IG] No media downloaded")
            return None
            
    except Exception as e:
        print(f"❌ [IG] Visual API error: {e}")
        return None

    # STEP 3: Get Text/Caption Data
    try:
        print("📡 [IG] Fetching caption from API...")
        querystring_text = {
            "reel_post_code_or_url": original_url,
            "type": api_type
        }
        res_txt = requests.get(
            "https://instagram-scraper-stable-api.p.rapidapi.com/get_reel_title.php",
            headers=headers,
            params=querystring_text,
            timeout=15
        )
        data_txt = res_txt.json()
        
        desc = data_txt.get('post_caption') or data_txt.get('title') or ""
        print(f"   ✓ Caption: {len(desc)} chars")
        
    except Exception as e:
        print(f"⚠️ [IG] Text API error (non-fatal): {e}")
    
    # STEP 4: Compile hasil
    result = {
        "url": original_url,
        "description": desc, 
        "media_type": media_type,
        "thumbnail": thumb, 
        "year": year, 
        "tags": re.findall(r"#(\w+)", desc),
        "local_file": ",".join(paths)
    }
    
    print("=" * 50)
    print(f"✅ [IG] Scrape complete!")
    print(f"   Media Type: {media_type}")
    print(f"   Files: {len(paths)}")
    print(f"   Tags: {len(result['tags'])}")
    print("=" * 50)
    
    return result


def save_insta_to_db(data):
    try:
        post = Post.objects.create(
            url=data['url'], media_type=data['media_type'],
            thumb_url=data['thumbnail'], description=data['description'],
            local_file=data['local_file']
        )
        PostTime.objects.create(post=post, year=data['year'])
        for tag_text in data['tags']:
            tag_obj, _ = Tag.objects.get_or_create(name=tag_text)
            post.tags.add(tag_obj)
        return post
    except Exception as e:
        print(f"Insta DB Error: {e}")
        return None


# ================= YOUTUBE LOGIC (YT-DLP) =================
def scrape_youtube_data(url):
    # Selalu pakai yt-dlp
    saved_path = download_video_ytdlp(url)
    if not saved_path:
        return None

    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            
            thumb = ""
            if info.get('thumbnails'):
                thumb = info.get('thumbnails')[-1]['url']

            return {
                "url": url, 
                "description": f"{info.get('title','')}\n\n{info.get('description','')}", 
                "media_type": 'video',
                "thumbnail": thumb, 
                "year": int(info.get('upload_date')[:4]) if info.get('upload_date') else datetime.now().year, 
                "tags": info.get('tags', []),
                "local_file": saved_path
            }
    except Exception as e:
        print(f"YouTube Scraper Error: {e}")
        return None

def save_youtube_to_db(data):
    try:
        post = Post.objects.create(
            url=data['url'], media_type=data['media_type'],
            thumb_url=data['thumbnail'], description=data['description'],
            local_file=data['local_file']
        )
        PostTime.objects.create(post=post, year=data['year'])
        for tag_text in data['tags']:
            clean = re.sub(r'\W+', '', tag_text)
            if clean:
                tag_obj, _ = Tag.objects.get_or_create(name=clean)
                post.tags.add(tag_obj)
        return post
    except Exception as e:
        print(f"YouTube DB Error: {e}")
        return None