# app/core/signal_handler.py
"""
信号处理模块 - 程序退出时的清理工作

本模块负责捕获系统信号（如Ctrl+C、程序终止等）并执行相应的清理工作。
确保资源正确释放，数据正确保存。
"""

import signal
import sys
import threading
import time
from typing import Callable, List, Optional
from .logging import player_logger


class SignalHandler:
    """
    信号处理器 - 单例模式
    
    负责管理程序退出时的清理工作，确保资源正确释放。
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """初始化信号处理器"""
        self._cleanup_handlers: List[Callable] = []
        self._is_shutting_down = False
        self._shutdown_lock = threading.Lock()
        
        # 注册信号处理
        self._register_signal_handlers()
        
        player_logger.info("[SignalHandler] 信号处理器初始化完成")
    
    def _register_signal_handlers(self):
        """注册系统信号处理函数"""
        try:
            # Windows系统特殊处理
            if sys.platform == "win32":
                # Windows上的Ctrl+C处理 - 使用SIGINT
                signal.signal(signal.SIGINT, self._signal_handler)
                # Windows上的Ctrl+Break处理
                if hasattr(signal, 'SIGBREAK'):
                    signal.signal(signal.SIGBREAK, self._signal_handler)
            else:
                # Unix/Linux系统
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
            
            player_logger.debug("[SignalHandler] 系统信号处理器注册成功")
        except Exception as e:
            player_logger.warning(f"[SignalHandler] 信号处理器注册失败: {e}")
    
    def _signal_handler(self, signum, frame):
        """信号处理函数"""
        signal_name = self._get_signal_name(signum)
        player_logger.info(f"[SignalHandler] 收到信号: {signal_name} ({signum})")
        
        # 防止重复调用
        with self._shutdown_lock:
            if self._is_shutting_down:
                player_logger.debug("[SignalHandler] 清理工作已在执行中，忽略重复信号")
                return
            self._is_shutting_down = True
        
        # 执行清理工作
        self._perform_cleanup()
        
        # 退出程序
        player_logger.info("[SignalHandler] 程序正常退出")
        sys.exit(0)
    
    def _get_signal_name(self, signum: int) -> str:
        """获取信号名称"""
        signal_names = {}
        
        # 通用信号
        if hasattr(signal, 'SIGINT'):
            signal_names[signal.SIGINT] = "SIGINT (Ctrl+C)"
        if hasattr(signal, 'SIGTERM'):
            signal_names[signal.SIGTERM] = "SIGTERM (终止信号)"
        
        # Windows特有信号
        if sys.platform == "win32" and hasattr(signal, 'SIGBREAK'):
            signal_names[signal.SIGBREAK] = "SIGBREAK (Windows Ctrl+Break)"
        
        return signal_names.get(signum, f"未知信号 ({signum})")
    
    def register_cleanup_handler(self, handler: Callable, name: str = ""):
        """
        注册清理处理器
        
        Args:
            handler: 清理函数，不接受参数
            name: 处理器名称，用于日志记录
        """
        if not callable(handler):
            player_logger.warning(f"[SignalHandler] 无效的清理处理器: {handler}")
            return
        
        self._cleanup_handlers.append((handler, name))
        player_logger.debug(f"[SignalHandler] 注册清理处理器: {name or handler.__name__}")
    
    def unregister_cleanup_handler(self, handler: Callable):
        """取消注册清理处理器"""
        for i, (h, name) in enumerate(self._cleanup_handlers):
            if h == handler:
                self._cleanup_handlers.pop(i)
                player_logger.debug(f"[SignalHandler] 取消注册清理处理器: {name or handler.__name__}")
                return
    
    def _perform_cleanup(self):
        """执行所有注册的清理工作"""
        player_logger.info("[SignalHandler] 开始执行清理工作...")
        
        total_handlers = len(self._cleanup_handlers)
        if total_handlers == 0:
            player_logger.info("[SignalHandler] 没有注册的清理处理器")
            return
        
        player_logger.info(f"[SignalHandler] 需要执行 {total_handlers} 个清理处理器")
        
        # 按注册顺序执行清理工作
        for i, (handler, name) in enumerate(self._cleanup_handlers, 1):
            handler_name = name or handler.__name__
            player_logger.info(f"[SignalHandler] 执行清理处理器 [{i}/{total_handlers}]: {handler_name}")
            
            try:
                start_time = time.time()
                handler()
                elapsed_time = time.time() - start_time
                player_logger.info(f"[SignalHandler] 清理处理器 {handler_name} 执行成功 (耗时: {elapsed_time:.2f}秒)")
            except Exception as e:
                player_logger.error(f"[SignalHandler] 清理处理器 {handler_name} 执行失败: {e}")
        
        player_logger.info("[SignalHandler] 所有清理工作执行完成")
    
    def is_shutting_down(self) -> bool:
        """检查是否正在关闭"""
        return self._is_shutting_down
    
    def manual_shutdown(self):
        """手动触发关闭流程"""
        player_logger.info("[SignalHandler] 手动触发关闭流程")
        self._signal_handler(signal.SIGTERM, None)


# 全局信号处理器实例
signal_handler = SignalHandler()


def get_signal_handler() -> SignalHandler:
    """获取信号处理器实例"""
    return signal_handler


def register_cleanup_handler(handler: Callable, name: str = ""):
    """注册清理处理器的便捷函数"""
    signal_handler.register_cleanup_handler(handler, name)


def unregister_cleanup_handler(handler: Callable):
    """取消注册清理处理器的便捷函数"""
    signal_handler.unregister_cleanup_handler(handler)


def is_shutting_down() -> bool:
    """检查是否正在关闭的便捷函数"""
    return signal_handler.is_shutting_down()


# 预定义的清理函数示例
def default_player_cleanup():
    """默认播放器清理函数（需要配合PlayerManager使用）"""
    try:
        # 导入PlayerManager（延迟导入避免循环依赖）
        from .player import PlayerManager
        player = PlayerManager()
        
        # 保存当前播放状态
        if player.current_file:
            current_time = player.player.get_time() / 1000.0  # 毫秒转秒
            player.settings.update_last_playback(player.current_file, current_time)
            player_logger.info(f"[SignalHandler] 保存播放状态: {player.current_file} 位置: {current_time:.1f}秒")
        
        # 停止播放
        if player.player.is_playing():
            player.player.stop()
            player_logger.info("[SignalHandler] 停止播放器")
        
        # 释放VLC资源
        player.player.release()
        player_logger.info("[SignalHandler] 释放VLC资源")
        
    except Exception as e:
        player_logger.error(f"[SignalHandler] 播放器清理失败: {e}")


# 模块初始化时自动注册默认清理函数
# 注意：这需要在PlayerManager初始化后手动调用
# register_cleanup_handler(default_player_cleanup, "播放器清理")


__all__ = [
    'SignalHandler',
    'signal_handler',
    'get_signal_handler',
    'register_cleanup_handler',
    'unregister_cleanup_handler',
    'is_shutting_down',
    'default_player_cleanup'
]