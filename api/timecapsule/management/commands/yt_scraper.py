from django.core.management.base import BaseCommand
# Import fungsi YouTube dari utils.py
from timecapsule.utils import scrape_youtube_data, save_youtube_to_db

class Command(BaseCommand):
    help = 'Download & Scrape YouTube Video (via yt-dlp)'

    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='YouTube URL')

    def handle(self, *args, **kwargs):
        url = kwargs['url']
        self.stdout.write(f"Processing YouTube: {url}")
        self.stdout.write("Downloading video... (This might take a while)") 

        # 1. Scrape & Download (Langsung satu paket di utils)
        data = scrape_youtube_data(url)
        
        if data:
            # 2. Save to DB
            post = save_youtube_to_db(data)
            if post:
                self.stdout.write(self.style.SUCCESS(f'Success! Saved ID: {post.id}'))
                self.stdout.write(self.style.WARNING(f'File saved at: {data["local_file"]}'))
            else:
                self.stdout.write(self.style.ERROR('DB Save Error'))
        else:
            self.stdout.write(self.style.ERROR('Download Failed (Check URL or Server Connection)'))