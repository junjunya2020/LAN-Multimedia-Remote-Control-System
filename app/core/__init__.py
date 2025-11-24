# app/core/__init__.py
# 暴露核心类的主要接口
from .player import PlayerManager, PlayMode, Settings
from .error_handler import PlayerErrorHandler
from .logging import get_logger, error_logger, info_logger, debug_logger, player_logger
from .sync_manager import get_sync_manager, SyncManager
from .signal_handler import SignalHandler, signal_handler, get_signal_handler, register_cleanup_handler, unregister_cleanup_handler, is_shutting_down, default_player_cleanup

__all__ = [
    # 播放器相关
    'PlayerManager', 'PlayMode', 'Settings',
    
    # 错误处理
    'PlayerErrorHandler',
    
    # 日志系统
    'get_logger', 'error_logger', 'info_logger', 'debug_logger', 'player_logger',
    
    # 同步管理
    'get_sync_manager', 'SyncManager',
    
    # 信号处理
    'SignalHandler', 'signal_handler', 'get_signal_handler', 'register_cleanup_handler', 'unregister_cleanup_handler', 'is_shutting_down', 'default_player_cleanup'
]