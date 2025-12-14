from django.core.management.base import BaseCommand
from timecapsule.utils import scrape_insta_data, save_insta_to_db

class Command(BaseCommand):
    help = 'Download & Scrape Instagram Post/Reel'

    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='Instagram URL')

    def handle(self, *args, **kwargs):
        url = kwargs['url']
        self.stdout.write(f"Processing: {url}")
        self.stdout.write("Downloading media... (Please wait)") 

        # LANGSUNG SCRAPE
        data = scrape_insta_data(url)
        
        if data:
            post = save_insta_to_db(data)
            if post:
                self.stdout.write(self.style.SUCCESS(f'Success! Saved ID: {post.id}'))
                self.stdout.write(self.style.WARNING(f'File saved at: {data["local_file"]}'))
            else:
                self.stdout.write(self.style.ERROR('DB Save Error'))
        else:
            self.stdout.write(self.style.ERROR('Scrape/Download Failed'))