from django.core.management.base import BaseCommand
# Import mesin dari utils.py
from timecapsule.utils import parse_instagram_url, scrape_insta_data, save_insta_to_db

class Command(BaseCommand):
    # Usage: python manage.py insta_scraper "YOUR_URL"
    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='Instagram URL')

    def handle(self, *args, **kwargs):
        url = kwargs['url']
        self.stdout.write(f"Processing: {url}")
        
        # 1. Parse URL
        shortcode, api_type = parse_instagram_url(url)
        if not shortcode:
            self.stdout.write(self.style.ERROR('Invalid URL'))
            return

        # 2. Run Scraper (Utils)
        data = scrape_insta_data(url, shortcode, api_type)
        if data:
            # 3. Save to DB (Utils)
            post = save_insta_to_db(data)
            if post:
                self.stdout.write(self.style.SUCCESS(f'Success! Saved ID: {post.id}'))
            else:
                self.stdout.write(self.style.ERROR('DB Save Error'))
        else:
            self.stdout.write(self.style.ERROR('Scrape Failed'))