# playback/urls.py
from django.urls import path
from .views import playback_stream, PlaybackCommandView, PlaybackStateView

app_name = 'playback'

urlpatterns = [
    # SSE 实时广播（普通 Django 视图，非 DRF）
    path('stream/', playback_stream, name='stream'),
    # 提交播放指令（需令牌）
    path('command/', PlaybackCommandView.as_view(), name='command'),
    # 会话快照（无需令牌，重连兜底/调试）
    path('state/', PlaybackStateView.as_view(), name='state'),
]
