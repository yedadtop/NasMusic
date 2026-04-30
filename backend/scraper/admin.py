# scraper/admin.py
from django.contrib import admin
from .models import ScraperAPI

@admin.register(ScraperAPI)
class ScraperAPIAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'priority', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'url')
    list_editable = ('priority', 'is_active')