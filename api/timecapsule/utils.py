from .models import Post, Tag, PostTime
import requests
import re
from datetime import datetime


# TIKTOK LOGIC
def extract_tiktok_id(url):
    pattern = r"(?:video|photo)/(\d+)"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def scrape_tiktok_data(video_id):
    url = "https://tiktok-api23.p.rapidapi.com/api/post/detail"
    headers = {
        "x-rapidapi-key": "31b6bb776fmshf2f28b986086358p1bdcc1jsn15e4b0eb8f34",
        "x-rapidapi-host": "tiktok-api23.p.rapidapi.com"
    }
    try:
        response = requests.get(url, headers=headers, params={"videoId": video_id})
        data = response.json()

        if data.get('statusCode') == 0:
            post = data['itemInfo']['itemStruct']
            
            # Media Type & Thumbnail
            if post.get('imagePost'):
                media_type = 'photo'
                target_url = f"https://www.tiktok.com/photo/{post['id']}"
                try:
                    thumb = post['imagePost']['images'][0]['imageURL']['urlList'][0]
                except (IndexError, KeyError, TypeError):
                    thumb = ""
            else:
                media_type = 'video'
                target_url = f"https://www.tiktok.com/video/{post['id']}"
                thumb = post.get('video', {}).get('cover', '')

            desc = post.get('desc', '')
            raw_time = int(post.get('createTime', 0))
            year = datetime.fromtimestamp(raw_time).year if raw_time > 0 else datetime.now().year
            tags = re.findall(r"#(\w+)", desc)

            return {
                "url": target_url, "description": desc, "media_type": media_type,
                "thumbnail": thumb, "year": year, "tags": tags
            }
        return None
    except Exception as e:
        print(f"Scraper Error: {e}")
        return None

def save_tiktok_to_db(data):
    try:
        post = Post.objects.create(
            url=data['url'], media_type=data['media_type'],
            thumb_url=data['thumbnail'], description=data['description']
        )
        PostTime.objects.create(post=post, year=data['year'])
        for tag_text in data['tags']:
            tag_obj, _ = Tag.objects.get_or_create(name=tag_text)
            post.tags.add(tag_obj)
        return post
    except Exception as e:
        print(f"DB Error: {e}")
        return None


# 2. INSTAGRAM LOGIC
def parse_instagram_url(url):
    pattern = r"(?:p|reel|tv)/([A-Za-z0-9_-]+)"
    match = re.search(pattern, url)
    if match:
        shortcode = match.group(1)
        api_type = "reel" if "/reel/" in url else "post"
        return shortcode, api_type
    return None, None

def scrape_insta_data(target_url, shortcode_input, api_type):
    headers = {
        "x-rapidapi-key": "46d4e4b9f5msh0972b8339f1dcf1p1f160ejsn0e31d76f2c25",
        "x-rapidapi-host": "instagram-scraper-stable-api.p.rapidapi.com"
    }

    clean_url = f"https://www.instagram.com/{'reel' if api_type == 'reel' else 'p'}/{shortcode_input}/"
    thumbnail_url, description = "", ""
    media_type_db = "photo"
    year = datetime.now().year
    tags = []

    try:
        # Visual Data
        res_vis = requests.get("https://instagram-scraper-stable-api.p.rapidapi.com/get_media_data_v2.php", headers=headers, params={"media_code": shortcode_input})
        data_vis = res_vis.json()
        if not data_vis.get('id'):
            return None

        thumbnail_url = data_vis.get('thumbnail_src', '')
        media_type_db = 'video' if data_vis.get('is_video') else 'photo'
        raw_time = data_vis.get('taken_at_timestamp') or data_vis.get('taken_at')
        if raw_time:
            year = datetime.fromtimestamp(int(raw_time)).year

        # Text Data
        res_text = requests.get("https://instagram-scraper-stable-api.p.rapidapi.com/get_reel_title.php", headers=headers, params={"reel_post_code_or_url": target_url, "type": api_type})
        data_text = res_text.json()
        description = data_text.get('post_caption') or data_text.get('title') or ""
        tags = re.findall(r"#(\w+)", description)

        return {
            "url": clean_url, "description": description, "media_type": media_type_db,
            "thumbnail": thumbnail_url, "year": year, "tags": tags
        }
    except Exception as e:
        print(f"Insta Scraper Error: {e}")
        return None

def save_insta_to_db(data):
    try:
        post = Post.objects.create(
            url=data['url'], media_type=data['media_type'],
            thumb_url=data['thumbnail'], description=data['description']
        )
        PostTime.objects.create(post=post, year=data['year'])
        for tag_text in data['tags']:
            tag_obj, _ = Tag.objects.get_or_create(name=tag_text)
            post.tags.add(tag_obj)
        return post
    except Exception as e:
        print(f"DB Error: {e}")
        return None