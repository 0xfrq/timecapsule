from django.core.management.base import BaseCommand
# Import from utils.py
from timecapsule.utils import extract_tiktok_id, scrape_tiktok_data, save_tiktok_to_db

class Command(BaseCommand):
    # Usage: python manage.py tiktok_scraper "YOUR_URL"
    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='TikTok URL')

    def handle(self, *args, **kwargs):
        url = kwargs['url']
        self.stdout.write(f"Processing: {url}")
        
        # 1. Extract ID
        video_id = extract_tiktok_id(url)
        if not video_id:
            self.stdout.write(self.style.ERROR('Invalid URL'))
            return

        # 2. Run Scraper (Utils)
        data = scrape_tiktok_data(video_id)
        if data:
            # 3. Save to DB (Utils)
            post = save_tiktok_to_db(data)
            if post:
                self.stdout.write(self.style.SUCCESS(f'Success! Saved ID: {post.id}'))
            else:
                self.stdout.write(self.style.ERROR('DB Save Error'))
        else:
            self.stdout.write(self.style.ERROR('Scrape Failed'))