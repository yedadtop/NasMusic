# scanner/urls.py
from django.urls import path
from .views import ScanLibraryView, ScanStatusView, SystemConfigView, TrashManagerView

urlpatterns = [
    path('run/', ScanLibraryView.as_view(), name='run-scan'),
    path('status/', ScanStatusView.as_view(), name='scan-status'),
    path('config/', SystemConfigView.as_view(), name='system-config'),
    path('trash/', TrashManagerView.as_view(), name='trash-manager'),
]