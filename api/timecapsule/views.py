from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Post, PostTime
from .serializers import PostSerializer

# Import utils (Perhatikan: kita tidak butuh extract/parse lagi di sini)
from .utils import (
    scrape_tiktok_data, save_tiktok_to_db,
    scrape_insta_data, save_insta_to_db,
    scrape_youtube_data, save_youtube_to_db
)

# ==================== TIKTOK VIEW ====================
@api_view(['POST'])
def scrape_tiktok_view(request):
    url = request.data.get('url')
    if not url:
        return Response({"error": "URL is required"}, status=400)
    
    # PERUBAHAN: Langsung lempar URL Asli.
    # Utils akan otomatis ekstrak ID di dalam dan milih mau pake Requests/Yt-dlp.
    data = scrape_tiktok_data(url)
    
    if not data:
        return Response({"error": "Scrape Failed (Check Link/Quota)"}, status=500)
        
    post = save_tiktok_to_db(data)
    if post:
        serializer = PostSerializer(post)
        return Response({
            "status": "success",
            "message": "TikTok Scraped & Downloaded Successfully",
            "data": serializer.data 
        })
    return Response({"error": "Database Save Error"}, status=500)

# ==================== INSTAGRAM VIEW ====================
@api_view(['POST'])
def scrape_insta_view(request):
    url = request.data.get('url')
    if not url:
        return Response({"error": "URL is required"}, status=400)
        
    # PERUBAHAN: Langsung lempar URL Asli.
    data = scrape_insta_data(url)
    
    if not data:
        return Response({"error": "Scrape Failed (Check Link/Quota)"}, status=500)
        
    post = save_insta_to_db(data)
    if post:
        serializer = PostSerializer(post)
        return Response({
            "status": "success",
            "message": "Instagram Scraped & Downloaded Successfully",
            "data": serializer.data
        })
    return Response({"error": "Database Save Error"}, status=500)

# ==================== YOUTUBE VIEW ====================
@api_view(['POST'])
def scrape_youtube_view(request):
    url = request.data.get('url')
    if not url:
        return Response({"error": "URL is required"}, status=400)

    data = scrape_youtube_data(url)
    if not data:
        return Response({"error": "Failed to download YouTube video"}, status=500)
    
    post = save_youtube_to_db(data)
    if not post:
        return Response({"error": "Failed to save to database"}, status=500)

    serializer = PostSerializer(post)
    return Response({
        "status": "success",
        "message": "YouTube downloaded successfully",
        "data": serializer.data
    })

# ==================== GETTERS (TETAP SAMA) ====================
@api_view(['GET'])
def get_post_detail(request, post_id):
    try:
        post = Post.objects.get(id=post_id)
        serializer = PostSerializer(post)
        return Response({"status": "success", "data": serializer.data})
    except Post.DoesNotExist:
        return Response({"error": "Post not found"}, status=404)

@api_view(['GET'])
def get_posts_by_year(request, year):
    times = PostTime.objects.filter(year=year)
    if not times.exists():
        return Response({"status": "error", "message": f"Belum ada post di tahun {year}"}, status=404)

    posts = [t.post for t in times]
    serializer = PostSerializer(posts, many=True)
    return Response({
        "status": "success",
        "year": year,
        "total_found": len(posts),
        "data": serializer.data
    })