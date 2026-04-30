# scraper/views.py
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from library.models import Track
from .models import ScraperAPI
from .serializers import ScraperAPISerializer
from .utils import fetch_and_embed_cover


class ScraperAPIViewSet(viewsets.ModelViewSet):
    """
    刮削接口的增删改查视图
    """
    queryset = ScraperAPI.objects.all()
    serializer_class = ScraperAPISerializer


class TrackScrapeView(APIView):
    """
    手动触发单首歌曲的封面高清刮削
    """

    def post(self, request, track_id):
        track = get_object_or_404(Track, id=track_id)

        success, message = fetch_and_embed_cover(track)

        if success:
            return Response({"message": message}, status=status.HTTP_200_OK)
        else:
            return Response({"error": message}, status=status.HTTP_404_NOT_FOUND)