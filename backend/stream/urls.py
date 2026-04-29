# stream/urls.py
from django.urls import path
from .views import stream_audio

urlpatterns = [
    # 定义播放地址，例如：/stream/1/
    path('<int:track_id>/', stream_audio, name='stream_audio'),
]