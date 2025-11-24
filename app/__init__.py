# app/__init__.py
import asyncio
import logging

from quart import Quart
import socketio
from app.core.logging import LoggerManager

def create_app():
    # 初始化日志系统，设置为DEBUG级别
    LoggerManager.initialize(log_level=logging.DEBUG)
    
    app = Quart(__name__)
    app.config['SECRET_KEY'] = 'secret!'
    
    # 配置静态资源不缓存
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # 禁用默认缓存
    
    # 添加静态资源路由处理，禁用缓存
    @app.after_request
    async def add_no_cache_headers(response):
        # 检查是否为静态资源请求
        content_type = response.headers.get('Content-Type', '')
        if content_type.startswith(('text/css', 'application/javascript', 'text/javascript', 'image/', 'font/')):
            # 禁用所有缓存机制
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['Surrogate-Control'] = 'no-store'
            
            # 添加ETag和Last-Modified头，但设置为当前时间，确保每次不同
            import time
            response.headers['ETag'] = str(int(time.time()))
            response.headers['Last-Modified'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
        return response

    # 创建 ASGI Socket.IO 服务器
    sio = socketio.AsyncServer(
        async_mode='asgi',
        cors_allowed_origins="*",
        logger=False,
        engineio_logger=False
    )

    # 包装为 ASGI 应用
    socketio_app = socketio.ASGIApp(sio, app)

    # 注册 Blueprint
    from .routes import player_bp
    app.register_blueprint(player_bp)

    # 注册 SocketIO 事件
    from .sockets.sync import register_socket_events
    register_socket_events(sio)

    # ============================= 新增：启动保底推送 =============================
    @app.before_serving
    async def startup():
        sio.start_force_sync()  # ← 关键！调用 sync.py 中的启动函数
        
        # ============================= 新增：初始化同步管理器 =============================
        from app.core.player import player_manager
        from app.core.sync_manager import get_sync_manager
        
        # 初始化同步管理器（单例模式）
        sync_manager = get_sync_manager(player_manager)
        print(f"[App Startup] 同步管理器已初始化")
        
        # ============================= 新增：自动恢复上次播放 =============================
        
        # 检查是否启用记住播放进度
        playback_info = player_manager.settings.get_last_playback_info()
        if playback_info["remember_playback"] and playback_info["file"]:
            print(f"[App Startup] 检测到上次播放记录，尝试自动恢复...")
            print(f"[App Startup] 文件: {playback_info['file']}")
            print(f"[App Startup] 位置: {playback_info['position']}秒")
            
            # 尝试恢复播放
            success = player_manager.restore_last_playback()
            if success:
                print("[App Startup] 成功恢复上次播放")
            else:
                print("[App Startup] 恢复播放失败")
        else:
            print("[App Startup] 未启用记住播放进度或没有播放记录")
        
        # ============================= 新增：自动恢复播放列表 =============================
        print("[App Startup] 尝试恢复播放列表...")
        playlist_restored = player_manager.load_playlist_from_file()
        if playlist_restored:
            print("[App Startup] 播放列表恢复成功")
            print(f"[App Startup] 恢复的播放列表包含 {len(player_manager.playlist)} 个文件")
        else:
            print("[App Startup] 播放列表恢复失败或没有播放列表文件")
        
        # ===========================================================================
    return app, socketio_app, sio