# scraper/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ScraperAPIViewSet, TrackScrapeView

router = DefaultRouter()
router.register(r'apis', ScraperAPIViewSet, basename='scraper-api')

urlpatterns = [
    path('', include(router.urls)),
    path('track/<int:track_id>/scrape/', TrackScrapeView.as_view(), name='track-scrape'),
]