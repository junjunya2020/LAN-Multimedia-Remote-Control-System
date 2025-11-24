# app/core/sync_manager.py
"""
播放状态同步管理器
封装播放状态获取和同步相关的重复逻辑
"""
import time
import threading
from typing import Dict, Any
from app.core.player import PlayerManager 

player_manager = PlayerManager()
import asyncio
class SyncManager:
    """
    播放状态同步管理器
    封装播放状态获取和同步相关的重复逻辑
    """
    
    def __init__(self, player_manager):
        """
        初始化同步管理器
        
        Args:
            player_manager: PlayerManager实例
        """
        self.player_manager = player_manager
        self._sync_lock = threading.Lock()

    def get_sync_data(self) -> Dict[str, Any]:
        """
        获取完整的同步数据
        封装了ProgressView和sync.py中重复的播放状态获取逻辑
        
        Returns:
            Dict[str, Any]: 包含播放状态、进度、音量、歌词等信息的字典
        """
        with self._sync_lock:
            # 获取播放时间信息
            current_time_ms = self.player_manager.player.get_time()
            current_time = current_time_ms / 1000.0 if current_time_ms > 0 else 0.0
            total_time = self.player_manager.player.get_length() / 1000.0
            progress = (current_time / total_time * 100) if total_time > 0 else 0
            
            # 获取当前音量
            current_volume = self.player_manager.get_volume()
            
            # 获取当前歌词
            lyrics_context = self.player_manager.get_lyrics_context(current_time)
            
            # 获取播放状态
            state_raw = self.player_manager.player.get_state()
            state = self.player_manager.vlc_state_to_obj(state_raw)
            
            # 获取播放模式信息
            current_play_mode = self.player_manager.get_play_mode()
            play_mode_str = str(current_play_mode)
            play_mode_value = current_play_mode.value
            
                
            # 获取在线用户信息
            with self.player_manager.refresh_lock:
                current_refresh_token = self.player_manager.refresh_token
                online_count = len(self.player_manager.online_users)
            
            data={
                "current_time": round(current_time, 2),
                "total_time": round(total_time, 2) if total_time > 0 else 0,
                "progress": round(progress, 2),
                "volume": current_volume,
                "refresh_token": current_refresh_token,
                "online_users": online_count,
                "status": state.name,
                "current_lyrics": lyrics_context,
                "play_mode": play_mode_str,
                "play_mode_value": play_mode_value,
                "other_event_broadcast": self.player_manager.get_other_event_broadcast(),
                "traditional_chinese_enabled": False,  # 简繁转换状态（纯前端功能）
            }
            
            
            return data
    def update_online_user(self, user_id: str, ip: str, ua: str) -> int:
        """
        更新在线用户信息
        
        Args:
            user_id: 用户ID
            ip: 用户IP地址
            ua: 用户代理信息
            
        Returns:
            int: 当前在线用户数量
        """
        now = time.time()
        with self.player_manager.refresh_lock:
            # 清理过期用户
            expired = [
                uid for uid, info in self.player_manager.online_users.items()
                if now - info["last_seen"] > self.player_manager.ONLINE_TIMEOUT
            ]
            for uid in expired:
                del self.player_manager.online_users[uid]
            
            # 更新或添加当前用户
            if user_id:
                self.player_manager.online_users[user_id] = {
                    "ip": ip,
                    "ua": ua,
                    "last_seen": now
                }
            
            return len(self.player_manager.online_users)
    
    def get_online_users_count(self) -> int:
        """
        获取当前在线用户数量
        
        Returns:
            int: 在线用户数量
        """
        with self.player_manager.refresh_lock:
            return len(self.player_manager.online_users)
    
    def get_refresh_token(self) -> str:
        """
        获取当前刷新令牌
        
        Returns:
            str: 刷新令牌
        """
        with self.player_manager.refresh_lock:
            return self.player_manager.refresh_token


# 创建全局同步管理器实例
_sync_manager_instance = None
_sync_manager_lock = threading.Lock()


def get_sync_manager(player_manager=None):
    """
    获取同步管理器实例（单例模式）
    
    Args:
        player_manager: PlayerManager实例，仅在首次调用时传入
        
    Returns:
        SyncManager: 同步管理器实例
    """
    global _sync_manager_instance
    
    if _sync_manager_instance is None and player_manager is not None:
        with _sync_manager_lock:
            if _sync_manager_instance is None:
                _sync_manager_instance = SyncManager(player_manager)
    
    return _sync_manager_instance