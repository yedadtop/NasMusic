# scraper/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BilibiliCookieView, TrackScrapeView, BatchScrapeCoverView
from .views import TrackScrapeLyricsView, BatchScrapeLyricsView
from .bilibili_views import BiliSearchView, BiliPlayUrlView, BiliProxyStreamView

router = DefaultRouter()

urlpatterns = [
    path('bilibili_cookie/', BilibiliCookieView.as_view(), name='bilibili-cookie'),
    path('', include(router.urls)),
    path('track/<int:track_id>/scrape/', TrackScrapeView.as_view(), name='track-scrape'),
    path('batch/scrape/', BatchScrapeCoverView.as_view(), name='batch-scrape-cover'),
    path('track/<int:track_id>/scrape_lyrics/', TrackScrapeLyricsView.as_view(), name='scrape-track-lyrics'),
    path('batch/scrape_lyrics/', BatchScrapeLyricsView.as_view(), name='batch-scrape-lyrics'),
    path('bili/search/', BiliSearchView.as_view(), name='bili-search'),
    path('bili/playurl/', BiliPlayUrlView.as_view(), name='bili-playurl'),
    path('bili/proxy/', BiliProxyStreamView.as_view(), name='bili-proxy'),
]
