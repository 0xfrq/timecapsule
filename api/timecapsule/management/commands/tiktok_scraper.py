from django.core.management.base import BaseCommand
from timecapsule.utils import scrape_tiktok_data, save_tiktok_to_db

class Command(BaseCommand):
    help = 'Download & Scrape TikTok Video/Slideshow'

    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='TikTok URL')

    def handle(self, *args, **kwargs):
        url = kwargs['url']
        self.stdout.write(f"Processing: {url}")
        self.stdout.write("Downloading media... (Please wait)") 

        # Langsung panggil scrape dengan URL
        data = scrape_tiktok_data(url)
        
        if data:
            post = save_tiktok_to_db(data)
            if post:
                self.stdout.write(self.style.SUCCESS(f'Success! Saved ID: {post.id}'))
                self.stdout.write(self.style.WARNING(f'File saved at: {data["local_file"]}'))
            else:
                self.stdout.write(self.style.ERROR('DB Save Error'))
        else:
            self.stdout.write(self.style.ERROR('Scrape/Download Failed'))