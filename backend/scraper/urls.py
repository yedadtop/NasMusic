# scraper/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ScraperAPIViewSet, TrackScrapeView, BatchScrapeCoverView
from .views import TrackScrapeLyricsView, BatchScrapeLyricsView

router = DefaultRouter()
router.register(r'apis', ScraperAPIViewSet, basename='scraper-api')

urlpatterns = [
    path('', include(router.urls)),
    path('track/<int:track_id>/scrape/', TrackScrapeView.as_view(), name='track-scrape'),
    path('batch/scrape/', BatchScrapeCoverView.as_view(), name='batch-scrape-cover'),
    path('track/<int:track_id>/scrape_lyrics/', TrackScrapeLyricsView.as_view(), name='scrape-track-lyrics'),
    path('batch/scrape_lyrics/', BatchScrapeLyricsView.as_view(), name='batch-scrape-lyrics'),
]