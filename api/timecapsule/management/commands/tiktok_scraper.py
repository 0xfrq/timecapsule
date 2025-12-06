from django.core.management.base import BaseCommand
from timecapsule.models import Post, Tag, PostTime
import requests
import re
from datetime import datetime

class Command(BaseCommand):
    # Usage: python manage.py tiktok_scraper "YOUR_URL"
    def add_arguments(self, parser):
        # Accepts one URL argument
        parser.add_argument('url', type=str, help='TikTok Video/Photo URL')

    def handle(self, *args, **kwargs):
        url_input = kwargs['url']
        
        # 1. Convert URL to ID
        video_id = self.extract_id(url_input)
        if not video_id:
            self.stdout.write(self.style.ERROR('Invalid URL or ID not found.'))
            return

        # 2. Scrape Detail
        self.stdout.write(f"Scraping details for ID: {video_id}...")
        detail_data = self.tiktok_detail_scraper(video_id)
        
        if not detail_data:
            self.stdout.write(self.style.ERROR('Failed to scrape video details.'))
            return

        # 3. Save to Django
        post_obj = self.tiktok_detail_db(detail_data)
        
        if post_obj:
            self.stdout.write(self.style.SUCCESS(f'Process Finished! Post saved with ID: {post_obj.id}'))
        else:
            self.stdout.write(self.style.ERROR('Failed to save to database.'))


    def extract_id(self, url):
        # Extracts digits after /video/ or /photo/ using Regex
        pattern = r"(?:video|photo)/(\d+)"
        match = re.search(pattern, url)
        return match.group(1) if match else None

    def tiktok_detail_scraper(self, video_id):
        # Fetches metadata from RapidAPI
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

                # Determine Media Type and Thumbnail
                if post.get('imagePost'):
                    media_type = 'photo'
                    target_url = f"https://www.tiktok.com/photo/{post['id']}"
                    try: 
                        thumb_url = post['imagePost']['images'][0]['imageURL']['urlList'][0]
                    except (IndexError, KeyError): 
                        thumb_url = ""
                else:
                    media_type = 'video'
                    target_url = f"https://www.tiktok.com/video/{post['id']}"
                    thumb_url = post.get('video', {}).get('cover', '')

                description = post.get('desc', '')
                
                # Year (Unix Timestamp conversion)
                raw_time = int(post.get('createTime', 0))
                year = datetime.fromtimestamp(raw_time).year if raw_time > 0 else datetime.now().year
                
                # Extract hashtags using Regex
                tags = re.findall(r"#(\w+)", description)

                return {
                    "url": target_url,
                    "description": description,
                    "media_type": media_type,
                    "thumbnail": thumb_url,
                    "year": year,
                    "tags": tags
                }
            return None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Scraper Exception: {e}"))
            return None

    def tiktok_detail_db(self, data):
        # Saves the scraped data into Django Models
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
            self.stdout.write(self.style.ERROR(f"Database Error: {e}"))
            return None