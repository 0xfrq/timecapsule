from django.urls import path
from . import views

urlpatterns = [
    path('scrape/tiktok/', views.scrape_tiktok_view, name='scrape-tiktok'),
    path('scrape/insta/', views.scrape_insta_view, name='scrape-insta'),
    path('scrape/youtube/', views.scrape_youtube_view, name='scrape-youtube'),
    path('post/<int:post_id>/', views.get_post_detail, name='post-detail'),
    path('posts/year/<int:year>/', views.get_posts_by_year, name='posts-by-year'),
]