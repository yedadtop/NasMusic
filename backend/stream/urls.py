# stream/urls.py
from django.urls import path
from .views import stream_audio, download_audio

urlpatterns = [
    # 定义播放地址，例如：/stream/1/
    path('<int:track_id>/', stream_audio, name='stream_audio'),
    # 下载歌曲文件到本地设备，例如：/stream/1/download/
    path('<int:track_id>/download/', download_audio, name='download_audio'),
]