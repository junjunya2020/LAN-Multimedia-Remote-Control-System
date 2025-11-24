# app/sockets/sync.py
import time
import asyncio
from quart import current_app
from app.core.player import player_manager  # 导入单例实例
from app.core.sync_manager import get_sync_manager  # 导入同步管理器

# 全局变量：保存 sio 实例
_sio = None

def register_socket_events(sio):
    global _sio
    _sio = sio

    @sio.on('connect')
    async def handle_connect(sid, environ):
        print(f"[Socket.IO] 客户端连接: {sid}")
        await sio.enter_room(sid, 'sync')
        await sio.enter_room(sid, 'control')
        await broadcast_sync()

    @sio.on('disconnect')
    async def handle_disconnect(sid):
        print(f"[Socket.IO] 客户端断开: {sid}")

    @sio.on('control')
    async def handle_control(sid, data):
        print(f"[Socket.IO] 收到 control: {data}")

    @sio.on('traditional_chinese_toggle')
    async def handle_traditional_chinese_toggle(sid, data):
        """处理简繁转换切换事件"""
        print(f"[Socket.IO] 收到简繁转换切换: {data}")
        # 广播给所有客户端
        await _sio.emit('traditional_chinese_toggle', data, room='sync')

    def start_force_sync():
        async def _force_sync_loop():
            while True:
                await asyncio.sleep(0.1)
                if _sio:
                    await broadcast_sync()
        asyncio.create_task(_force_sync_loop())

    sio.start_force_sync = start_force_sync


async def broadcast_sync():
    if not _sio:
        return

    loop = asyncio.get_running_loop()

    # 使用同步管理器获取同步数据
    sync_manager = get_sync_manager()
    sync_data = await loop.run_in_executor(None, sync_manager.get_sync_data)

    await _sio.emit('sync', sync_data, room='sync')