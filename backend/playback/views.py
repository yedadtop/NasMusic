# playback/views.py
# 多设备同步播放的三个端点：
# - GET  /api/playback/stream/   SSE 实时广播（只读，无需令牌；普通 Django 视图，
#                                规避 DRF 内容协商对长连接的缓冲）
# - POST /api/playback/command/  提交播放指令（写操作，全局令牌鉴权生效）
# - GET  /api/playback/state/   会话快照（只读，无需令牌；重连兜底/调试）
import json
import re

from django.http import StreamingHttpResponse, HttpResponseNotAllowed
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .hub import hub, ConnectionLimitError

CLIENT_ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,64}$')


def _track_fingerprint(track):
    """曲目指纹：transport 轻量事件用于校验本地曲目是否与会话一致"""
    if not isinstance(track, dict):
        return None
    if track.get('is_bilibili'):
        return f"b{track.get('bvid')}"
    return f"t{track.get('id')}"


def _format_event(kind, snap, light=False):
    """把会话快照格式化为一条 SSE data 事件（统一信封含 seq/时钟/leader 等元信息）"""
    envelope = {
        'kind': kind,
        'seq': snap['seq'],
        'server_time': snap['server_time'],
        'leader_id': snap['leader_id'],
        'online': snap['online'],
    }
    if kind == 'state':
        envelope.update(
            track=snap['track'],
            playlist=snap['playlist'],
            index=snap['index'],
            play_mode=snap['play_mode'],
            shuffle_history=snap['shuffle_history'],
            is_playing=snap['is_playing'],
            position=snap['position'],
            position_at=snap['position_at'],
        )
    elif kind == 'transport':
        envelope.update(
            track_fp=_track_fingerprint(snap['track']),
            is_playing=snap['is_playing'],
            position=snap['position'],
            position_at=snap['position_at'],
        )
    return f"data: {json.dumps(envelope, ensure_ascii=False)}\n\n".encode('utf-8')


def playback_stream(request):
    """SSE 长连接：连接后先发全量 state，此后实时推送指令变化与 roster 变化"""
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])
    client_id = request.GET.get('client_id', '')
    if not CLIENT_ID_RE.match(client_id):
        return HttpResponseNotAllowed(['GET'])

    def event_stream():
        try:
            hub.subscribe(client_id)
        except ConnectionLimitError:
            yield 'event: error\ndata: {"message": "在线设备数已达上限"}\n\n'.encode('utf-8')
            return
        try:
            # 连接建立：告知浏览器断线后 5s 再重连，并发送当前全量状态
            snap = hub.snapshot()
            yield b'retry: 5000\n\n'
            yield _format_event('state', snap)
            last_seq, last_roster = snap['seq'], snap['roster_version']
            while True:
                snap = hub.wait(last_seq, last_roster)
                if snap is None:
                    # 心跳：保持连接活性，同时供前端做时钟偏移采样
                    yield b': ping\n\n'
                    continue
                if snap['seq'] != last_seq:
                    # 指令变化：按最近一次指令类型发送全量或轻量载荷
                    yield _format_event(snap['last_kind'], snap, light=True)
                else:
                    # 仅 roster 变化（设备上线/掉线/leader 易主）
                    yield _format_event('roster', snap)
                last_seq, last_roster = snap['seq'], snap['roster_version']
        finally:
            hub.unsubscribe(client_id)

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    # nginx 反向代理场景下禁用缓冲，保证事件即时送达
    response['X-Accel-Buffering'] = 'no'
    return response


class PlaybackCommandView(APIView):
    """提交播放指令（写操作，全局 TokenRequiredForUnsafe 生效：需携带令牌）"""

    def post(self, request):
        kind = request.data.get('kind')
        if kind not in ('state', 'transport'):
            return Response({'message': 'kind 必须为 state 或 transport'}, status=400)
        snap = hub.apply_command(kind, request.data)
        return Response(snap)


class PlaybackStateView(APIView):
    """当前播放会话快照（只读，无需令牌）"""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(hub.snapshot())
