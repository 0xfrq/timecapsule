from django.urls import path
from . import views

urlpatterns = [
    path('scrape/tiktok/', views.scrape_tiktok_view, name='scrape-tiktok'),
    path('scrape/insta/', views.scrape_insta_view, name='scrape-insta'),
]