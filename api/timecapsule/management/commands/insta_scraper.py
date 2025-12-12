from django.core.management.base import BaseCommand
from timecapsule.models import Post, Tag, PostTime
import requests
import re
from datetime import datetime

class Command(BaseCommand):
    # Usage: python manage.py insta_scraper "YOUR_URL"
    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='Instagram Post/Reel URL')

    def handle(self, *args, **kwargs):
        url_input = kwargs['url']
        
        # 1. Parse URL to get Shortcode & Type
        shortcode, api_type = self.parse_instagram_url(url_input)
        
        if not shortcode:
            self.stdout.write(self.style.ERROR('Invalid URL or Shortcode not found.'))
            return

        # 2. Scrape Detail
        self.stdout.write(f"Scraping details for Shortcode: {shortcode}...")
        detail_data = self.insta_detail_scraper(url_input, shortcode, api_type)
        
        if not detail_data:
            self.stdout.write(self.style.ERROR('Failed to scrape post details.'))
            return

        # 3. Save to Django
        post_obj = self.insta_detail_db(detail_data)
        
        if post_obj:
            self.stdout.write(self.style.SUCCESS(f'Process Finished! Post saved with ID: {post_obj.id}'))
        else:
            self.stdout.write(self.style.ERROR('Failed to save to database.'))


    def parse_instagram_url(self, url):
        # Regex to find code after /p/, /reel/, or /tv/
        pattern = r"(?:p|reel|tv)/([A-Za-z0-9_-]+)"
        match = re.search(pattern, url)
        
        if match:
            shortcode = match.group(1)
            # Determine API Type parameter
            api_type = "reel" if "/reel/" in url else "post"
            
            print(f"[INFO] Shortcode found: {shortcode} (Type: {api_type})")
            return shortcode, api_type
        
        print("[ERROR] Invalid URL or Shortcode not found.")
        return None, None


    def insta_detail_scraper(self, target_url, shortcode_input, api_type):
        # API Endpoints
        URL_VISUAL = "https://instagram-scraper-stable-api.p.rapidapi.com/get_media_data_v2.php"
        URL_TEXT   = "https://instagram-scraper-stable-api.p.rapidapi.com/get_reel_title.php"
        
        headers = {
            "x-rapidapi-key": "46d4e4b9f5msh0972b8339f1dcf1p1f160ejsn0e31d76f2c25", 
            "x-rapidapi-host": "instagram-scraper-stable-api.p.rapidapi.com"
        }

        # Container Variables
        clean_url = f"https://www.instagram.com/{'reel' if api_type == 'reel' else 'p'}/{shortcode_input}/"
        thumbnail_url = ""
        media_type_db = "photo"
        description = ""
        year = datetime.now().year
        tags = []

        # --- GET VISUAL DATA (Thumbnail, Type, Time) ---
        try:
            print("   -> Requesting Visual Data...")
            res_vis = requests.get(URL_VISUAL, headers=headers, params={"media_code": shortcode_input})
            data_vis = res_vis.json()

            # Get Thumbnail
            thumbnail_url = data_vis.get('thumbnail_src', '')
            
            # Get Media Type
            if data_vis.get('is_video'):
                media_type_db = 'video'
            else:
                media_type_db = 'photo'
            
            # Get Time
            raw_time = data_vis.get('taken_at_timestamp') or data_vis.get('taken_at')
            if raw_time:
                year = datetime.fromtimestamp(int(raw_time)).year

        except Exception as e:
            print(f"[ERROR] Visual Scraper Exception: {e}")
            return None

        # --- GET TEXT DATA (Description) ---
        try:
            print("   -> Requesting Text Data...")
            res_text = requests.get(URL_TEXT, headers=headers, params={"reel_post_code_or_url": target_url, "type": api_type})
            data_text = res_text.json()

            # Get Description
            description = data_text.get('post_caption', '')
            if not description:
                description = data_text.get('title', '') 
            
            # Extract Hashtags
            tags = re.findall(r"#(\w+)", description)

        except Exception as e:
            print(f"[WARNING] Text Scraper Error: {e} (Continuing without description)")

        print(f"[INFO] Scrape Success. Desc Length: {len(description)}, Thumb Found: {bool(thumbnail_url)}")
        
        return {
            "url": clean_url,
            "description": description,
            "media_type": media_type_db,
            "thumbnail": thumbnail_url,
            "year": year,
            "tags": tags
        }

    def insta_detail_db(self, data):
        try:
            # 1. Create Post
            post = Post.objects.create(
                url=data['url'],
                media_type=data['media_type'],
                thumb_url=data['thumbnail'],
                description=data['description']
            )
            
            # 2. Create Time
            PostTime.objects.create(post=post, year=data['year'])
            
            # 3. Create/Get Tags and associate with Post
            for tag_text in data['tags']:
                tag_obj, created = Tag.objects.get_or_create(name=tag_text)
                post.tags.add(tag_obj)
                
            return post
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"DB Save Error: {e}"))
            return None