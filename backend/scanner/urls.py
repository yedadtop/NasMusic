# scanner/urls.py
from django.urls import path
from .views import ScanLibraryView, ScanStatusView

urlpatterns = [
    # API 路径为： /api/scanner/run/
    path('run/', ScanLibraryView.as_view(), name='run-scan'),
    path('status/', ScanStatusView.as_view(), name='scan-status'),
]