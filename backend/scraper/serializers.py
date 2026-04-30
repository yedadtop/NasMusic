# scraper/serializers.py
from rest_framework import serializers
from .models import ScraperAPI

class ScraperAPISerializer(serializers.ModelSerializer):
    class Meta:
        model = ScraperAPI
        fields = '__all__'