from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
# Import from utils.py
from .utils import (
    extract_tiktok_id, scrape_tiktok_data, save_tiktok_to_db,
    parse_instagram_url, scrape_insta_data, save_insta_to_db
)

@api_view(['POST'])
def scrape_tiktok_view(request):
    # 1. URL from body request
    url = request.data.get('url')
    
    # 2. Validation & Extract ID
    video_id = extract_tiktok_id(url)
    if not video_id:
        return Response({"error": "Invalid TikTok URL"}, status=400)
        
    # 3. Scrape Data
    data = scrape_tiktok_data(video_id)
    if not data:
        return Response({"error": "Scrape Failed (Check Link/Quota)"}, status=500)
        
    # 4. Save to Database
    post = save_tiktok_to_db(data)
    if post:
        return Response({
            "status": "success",
            "message": "TikTok Scraped Successfully",
            "post_id": post.id,
            "data": data
        })
    return Response({"error": "Database Save Error"}, status=500)

@api_view(['POST'])
def scrape_insta_view(request):
    # 1. URL from body request
    url = request.data.get('url')
    
    # 2. Validation & Extract Shortcode
    shortcode, api_type = parse_instagram_url(url)
    if not shortcode:
        return Response({"error": "Invalid Instagram URL"}, status=400)
        
    # 3. Scrape Data
    data = scrape_insta_data(url, shortcode, api_type)
    if not data:
        return Response({"error": "Scrape Failed (Check Link/Quota)"}, status=500)
        
    # 4. Save to Database
    post = save_insta_to_db(data)
    if post:
        return Response({
            "status": "success",
            "message": "Instagram Scraped Successfully",
            "post_id": post.id,
            "data": data
        })
    return Response({"error": "Database Save Error"}, status=500)