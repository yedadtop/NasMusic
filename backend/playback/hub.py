# playback/hub.py
# 多设备同步播放的内存状态枢纽：
# - 保存一份"播放会话快照"（由发起设备本地计算后提交，服务器不参与选歌决策）
# - 指令进来时合并状态、seq 递增并唤醒所有 SSE 连接广播（last-write-wins）
# - 维护 SSE 连接注册表，最老连接者为 leader（负责切歌推进），掉线即时重选
# 纯内存实现：服务器重启本就会中断音频流，会话丢失可接受，不做持久化
import threading
import time

# SSE 并发连接上限（WSGI 每条连接占一个线程，家用内网规模足够）
MAX_CLIENTS = 16


class ConnectionLimitError(Exception):
    """在线设备数达到上限"""


class PlaybackHub:
    """线程安全的播放会话状态 + SSE 连接注册表"""

    def __init__(self):
        self._cond = threading.Condition()
        # 会话状态：track/playlist/index/play_mode/shuffle_history 为发起设备
        # 的本地计算结果；position_at 记录 position 对应的服务器时间戳，
        # 各端用 position + (服务器当前时间 - position_at) 外推实际进度
        self._state = {
            'track': None,
            'playlist': [],
            'index': -1,
            'play_mode': 'sequential',
            'shuffle_history': [],
            'is_playing': False,
            'position': 0.0,
            'position_at': time.time(),
        }
        self._seq = 0
        self._roster_version = 0
        self._last_kind = 'state'
        # client_id -> {'conn': 连接句柄, 'at': 连接时间}（最老者为 leader）。
        # 注册表按 client_id 计数/选主，但注销必须按连接句柄：同一浏览器刷新页面时，
        # 新连接先顶替注册条目，旧连接（死 socket，最迟在下一次心跳写入时才察觉）
        # 的 finally 若按 client_id 注销会误删新连接的注册，导致事件照常广播
        # 但 online 恒为 0（"能同步播放却显示 0 台设备"）
        self._clients = {}
        self._conns = {}  # 连接句柄 -> client_id（注销时反查，句柄单调递增）
        self._conn_seq = 0

    # ---------- 连接管理 ----------

    def subscribe(self, client_id):
        """注册一条 SSE 连接，返回该连接的句柄；同一 client_id 重连保留原连接时间（防抖动导致 leader 易主）"""
        with self._cond:
            if client_id not in self._clients and len(self._clients) >= MAX_CLIENTS:
                raise ConnectionLimitError()
            prev = self._clients.get(client_id)
            self._conn_seq += 1
            conn = self._conn_seq
            self._clients[client_id] = {'conn': conn, 'at': prev['at'] if prev else time.time()}
            self._conns[conn] = client_id
            self._roster_version += 1
            self._cond.notify_all()
            return conn

    def unsubscribe(self, conn):
        """按连接句柄注销；仅当该句柄仍是此 client_id 的当前注册连接时才移除注册"""
        with self._cond:
            client_id = self._conns.pop(conn, None)
            removed = False
            if client_id is not None:
                cur = self._clients.get(client_id)
                if cur is not None and cur['conn'] == conn:
                    del self._clients[client_id]
                    removed = True
            if removed:
                self._roster_version += 1
            self._cond.notify_all()

    # ---------- 指令与状态 ----------

    def apply_command(self, kind, payload):
        """合并一次指令并唤醒广播：state=全量，transport=仅传输态；返回最新快照"""
        with self._cond:
            if kind == 'state':
                for key in ('track', 'playlist', 'index', 'play_mode', 'shuffle_history'):
                    if key in payload:
                        self._state[key] = payload[key]
            elif kind != 'transport':
                raise ValueError(f'未知的指令类型: {kind}')
            if 'is_playing' in payload:
                self._state['is_playing'] = bool(payload['is_playing'])
            if 'position' in payload:
                try:
                    self._state['position'] = max(0.0, float(payload['position']))
                except (TypeError, ValueError):
                    pass
            self._state['position_at'] = time.time()
            self._seq += 1
            self._last_kind = kind
            self._cond.notify_all()
            return self._snapshot_locked()

    def snapshot(self):
        with self._cond:
            return self._snapshot_locked()

    def wait(self, last_seq, last_roster, timeout=3.0):
        """阻塞等待 seq/roster 变化；有变化返回快照，超时返回 None（调用方发心跳）"""
        with self._cond:
            if self._seq == last_seq and self._roster_version == last_roster:
                self._cond.wait(timeout)
            if self._seq != last_seq or self._roster_version != last_roster:
                return self._snapshot_locked()
            return None

    # ---------- 内部 ----------

    def _snapshot_locked(self):
        leader = None
        if self._clients:
            leader = min(self._clients, key=lambda cid: self._clients[cid]['at'])
        snap = dict(self._state)
        snap['seq'] = self._seq
        snap['roster_version'] = self._roster_version
        snap['last_kind'] = self._last_kind
        snap['server_time'] = time.time()
        snap['leader_id'] = leader
        snap['online'] = len(self._clients)
        return snap


# 模块级单例：所有视图共享同一份会话状态
hub = PlaybackHub()
