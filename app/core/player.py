# app/core/player.py
import os
import re
import struct
import time
import uuid
import threading
import random
import json
import eyed3
import vlc
from enum import Enum
from typing import Optional, List, Dict, Union


class Settings:
    """
    播放器设置管理器
    自动读取和保存播放器设置到配置文件
    """
    def __init__(self, config_file: str = "player_settings.json"):
        self.config_file = config_file
        # 在VLC对象创建前就加载设置
        self.settings = self._load_settings()
    
    def _load_settings(self):
        """从配置文件加载设置，如果不存在则创建默认设置"""
        default_settings = {
            "last_played_file": None,  # 上次关闭时播放的文件
            "remember_playback": True,  # 记住播放文件及进度
            "last_position": 0.0,  # 上次播放位置（秒）
            "volume": 80,  # 音量设置
            "play_mode": "SINGLE",  # 播放模式
            "play_source": 1,  # 播放来源：1=播放列表，2=磁盘路径
            "popup_window": True  # 是否弹出窗口播放视频
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # 只更新存在的键，保持默认值
                    for key in default_settings:
                        if key in loaded_settings:
                            default_settings[key] = loaded_settings[key]
                print(f"[Settings] 设置已从 {self.config_file} 加载")
            else:
                # 创建默认设置文件
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_settings, f, indent=2, ensure_ascii=False)
                print(f"[Settings] 创建默认设置文件: {self.config_file}")
        except Exception as e:
            print(f"[Settings] 加载设置失败: {e}")
        
        return default_settings
    
    def save_settings(self):
        """保存设置到配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            print(f"[Settings] 设置已保存到 {self.config_file}")
        except Exception as e:
            print(f"[Settings] 保存设置失败: {e}")
    
    def get(self, key: str, default=None):
        """获取设置值"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value):
        """设置值并自动保存"""
        if key in self.settings:
            self.settings[key] = value
            self.save_settings()
        else:
            print(f"[Settings] 未知设置项: {key}")
    
    def update_last_playback(self, file_path: str, position: float = 0.0):
        """更新上次播放信息（每次播放时调用）"""
        # DEBUG: 打印当前remember_playback状态
        print(f"[DEBUG] update_last_playback: remember_playback = {self.settings['remember_playback']}")
        print(f"[DEBUG] update_last_playback: 传入文件路径 = {file_path}")
        
        # 无论remember_playback设置如何，都更新播放记录
        old_file = self.settings.get("last_played_file", "")
        old_position = self.settings.get("last_position", 0.0)
        
        self.settings["last_played_file"] = file_path
        self.settings["last_position"] = position
        
        # DEBUG: 打印更新前后的对比
        print(f"[DEBUG] update_last_playback: 更新前文件 = {old_file}")
        print(f"[DEBUG] update_last_playback: 更新后文件 = {self.settings['last_played_file']}")
        print(f"[DEBUG] update_last_playback: 更新前位置 = {old_position}")
        print(f"[DEBUG] update_last_playback: 更新后位置 = {self.settings['last_position']}")
        
        # 立即保存到磁盘
        self.save_settings()
        print(f"[Settings] 更新播放记录并保存到磁盘: {os.path.basename(file_path)} 位置: {position:.1f}秒")
    
    def save_playback_info(self):
        """保存播放信息（外部触发保存）"""
        if self.settings["remember_playback"]:
            self.save_settings()
            print("[Settings] 播放信息已保存")
    
    def get_last_playback_info(self):
        """获取上次播放信息"""
        return {
            "file": self.settings["last_played_file"],
            "position": self.settings["last_position"],
            "remember_playback": self.settings["remember_playback"]
        }
    
    def set_remember_playback(self, enabled: bool):
        """设置是否记住播放进度"""
        self.settings["remember_playback"] = enabled
        self.save_settings()
        print(f"[Settings] 记住播放进度: {'启用' if enabled else '禁用'}")
    
    def set_volume(self, volume: int):
        """设置音量"""
        if 0 <= volume <= 100:
            self.settings["volume"] = volume
            self.save_settings()
            print(f"[Settings] 音量设置为: {volume}")
    
    def set_play_mode(self, mode: str):
        """设置播放模式"""
        if mode in ["SINGLE", "SEQUENTIAL", "LOOP", "RANDOM"]:
            self.settings["play_mode"] = mode
            self.save_settings()
            print(f"[Settings] 播放模式设置为: {mode}")
    
    def set_play_source(self, source: int):
        """设置播放来源"""
        if source in [1, 2]:
            self.settings["play_source"] = source
            self.save_settings()
            source_name = "播放列表" if source == 1 else "磁盘路径"
            print(f"[Settings] 播放来源设置为: {source_name}")
        else:
            print(f"[Settings] 播放来源值无效: {source}，必须为1(播放列表)或2(磁盘路径)")
    
    def get_play_source(self) -> int:
        """获取播放来源"""
        return self.settings.get("play_source", 1)
    
    def set_popup_window(self, enabled: bool):
        """设置是否弹出窗口播放视频"""
        self.settings["popup_window"] = enabled
        self.save_settings()
        print(f"[Settings] 弹出窗口播放视频: {'启用' if enabled else '禁用'}")
    
    def get_popup_window(self) -> bool:
        """获取是否弹出窗口播放视频"""
        return self.settings.get("popup_window", True)


class PlayMode(Enum):
    """
    播放模式枚举类
    """
    SINGLE = 0  # 单曲不重复播放
    SEQUENTIAL = 1  # 顺序播放（自动下一曲）
    LOOP = 2  # 单曲循环
    RANDOM = 3  # 随机播放
    
    @staticmethod
    def next_mode(current_mode):
        """获取下一个播放模式"""
        modes = list(PlayMode)
        current_index = modes.index(current_mode)
        next_index = (current_index + 1) % len(modes)
        return modes[next_index]
    
    def __str__(self):
        mode_names = {
            PlayMode.SINGLE: "单曲不重复",
            PlayMode.SEQUENTIAL: "顺序播放",
            PlayMode.LOOP: "单曲循环",
            PlayMode.RANDOM: "随机播放"
        }
        return mode_names.get(self, "未知模式")


class PlayerManager:
    """
    播放器状态管理器（单例）
    所有状态和操作都集中在此类中
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
        # 在VLC对象创建前就读取设置
        self.settings = Settings()
        
        # 根据设置初始化播放模式
        play_mode_str = self.settings.get("play_mode", "SINGLE")
        play_mode_map = {
            "SINGLE": PlayMode.SINGLE,
            "SEQUENTIAL": PlayMode.SEQUENTIAL,
            "LOOP": PlayMode.LOOP,
            "RANDOM": PlayMode.RANDOM
        }
        self.play_mode = play_mode_map.get(play_mode_str, PlayMode.SINGLE)
        
        # 初始化其他属性
        self.player = vlc.MediaPlayer()
        self.current_file: Optional[str] = None
        self.current_directory: Optional[str] = None
        self.global_lyrics: Optional[str] = None
        self.refresh_token: str = str(uuid.uuid4())
        self.refresh_lock = threading.Lock()
        self.online_users: Dict[str, dict] = {}
        self.session_to_user_id: Dict[str, str] = {}
        self.ONLINE_TIMEOUT = 10
        self.played_files = []  # 已播放文件列表
        self.file_index = -1  # 当前文件索引
        
        # 播放列表相关
        self.playlist = []  # 播放列表数据结构
        self.playlist_lock = threading.Lock()  # 播放列表线程锁
        
        # 播放历史记录（用于随机播放模式下的上一曲功能）
        self.playback_history = []  # 播放历史记录列表
        self.max_history_size = 50  # 最多保存50条历史记录
        self.other_event_broadcast = ""
        # 设置VLC事件监听器（自动播放检测）
        self._setup_vlc_event_manager()
        
        # 注册信号处理器（程序退出时的清理工作）
        self._register_signal_handlers()
        
        # 同步到类属性（向下兼容）
        PlayerManager.player = self.player
        PlayerManager.current_file = self.current_file
        PlayerManager.current_directory = self.current_directory
        PlayerManager.global_lyrics = self.global_lyrics
        PlayerManager.refresh_token = self.refresh_token
        PlayerManager.refresh_lock = self.refresh_lock
        PlayerManager.online_users = self.online_users
        PlayerManager.session_to_user_id = self.session_to_user_id
        PlayerManager.ONLINE_TIMEOUT = self.ONLINE_TIMEOUT
        PlayerManager.play_mode = self.play_mode
        PlayerManager.played_files = self.played_files
        PlayerManager.file_index = self.file_index
        PlayerManager.settings = self.settings

    def _register_signal_handlers(self):
        """注册信号处理器，用于程序退出时的清理工作"""
        try:
            # 导入信号处理器
            from .signal_handler import get_signal_handler
            
            # 获取信号处理器实例
            signal_handler = get_signal_handler()
            
            # 注册播放器清理处理器
            signal_handler.register_cleanup_handler(self._cleanup_player)
            
            print("[PlayerManager] 信号处理器注册完成 - 播放器清理处理器已注册")
            
        except Exception as e:
            print(f"[PlayerManager] 信号处理器注册失败: {e}")
    
    def _cleanup_player(self):
        """播放器清理函数，在程序退出时执行"""
        print("[PlayerManager] 开始执行播放器清理工作...")
        try: 
            # 保存当前播放状态
            if self.current_file and self.settings.get("remember_playback"):
                current_position = self.player.get_time() / 1000.0  # 转换为秒
                if current_position > 0:
                    self.settings.update_last_playback(self.current_file, current_position)
                    print(f"[PlayerManager] 已保存播放进度: {current_position:.2f}秒")
            
            # 保存播放列表到文件
            if self.playlist:
                result = self.save_playlist_to_file()
                if result["status"] == "success":
                    print(f"[PlayerManager] 播放列表已保存，共 {result['count']} 个项目")
                else:
                    print(f"[PlayerManager] 播放列表保存失败: {result['message']}")
            else:
                print("[PlayerManager] 播放列表为空，跳过保存")
            
            # 停止播放
            if self.player.is_playing():
                self.player.stop()
                print("[PlayerManager] 播放器已停止")
            
            # 释放VLC资源
            self.player.release()
            print("[PlayerManager] VLC资源已释放")
            
            # 保存设置
            self.settings.save_playback_info()
            print("[PlayerManager] 播放设置已保存")
            
            print("[PlayerManager] 播放器清理工作完成")
            
        except Exception as e:
            print(f"[PlayerManager] 播放器清理过程中发生错误: {e}")

    # ============================= 状态设置（同步类属性）=============================
    def set_other_event_broadcast(self, event: str):
        """
        设置其他事件广播
        """
        try:
            self.other_event_broadcast = event
        except Exception as e:
            player_logger.error(f"设置其他事件广播失败: {e}")
            return {"other_event_broadcast": "", "success": False}  
        return {"other_event_broadcast": self.other_event_broadcast, "success": True}
    
    def get_other_event_broadcast(self) -> str:
        """
        获取其他事件广播
        """
        return self.other_event_broadcast
    
    def set_file(self, path: str, position: float = 0.0):
        """
        设置当前播放文件，并自动更新播放记录
        注意 如果要设置文件请调用此方法 不需要额外调用vlc.MediaPlayer去设置文件 会导致数据不一致
        Args:
            path: 文件路径
            position: 播放位置（秒），默认为0
        """
        self.current_directory = os.path.dirname(path)
        self.current_file = path
        
        # 更新播放列表信息
        all_files = self.get_audio_files_in_directory(self.current_directory)
        if all_files:
            self.file_index = all_files.index(path) if path in all_files else 0
        else:
            self.file_index = -1
            
        # 如果是新的文件且不是单曲循环模式，添加到已播放列表
        if path not in self.played_files and self.play_mode != PlayMode.LOOP:
            self.played_files.append(path)
        # 添加到播放历史记录（用于随机播放模式下的上一曲功能）
        self._add_to_playback_history(path)
        #关键！！！调用vlc设置文件
        self.player.set_media(vlc.Media(self.current_file))
        # 根据popup_window设置决定是否全屏播放
        if self.get_popup_window():
            self.player.set_fullscreen(True)
        else:
            self.player.set_fullscreen(False)
        # 同步到类属性
        PlayerManager.current_directory = self.current_directory
        PlayerManager.current_file = self.current_file
        PlayerManager.file_index = self.file_index
        PlayerManager.played_files = self.played_files

    def restore_last_playback(self) -> bool:
        """
        恢复上次播放的文件和位置
        
        Returns:
            bool: 是否成功恢复
        """
        playback_info = self.settings.get_last_playback_info()
        
        # 检查是否启用记住播放进度
        if not playback_info["remember_playback"]:
            print("[PlayerManager] 未启用记住播放进度")
            return False
            
        # 检查上次播放文件是否为空
        last_file = playback_info["file"]
        if not last_file:
            print("[PlayerManager] 上次播放文件为空，不进行自动播放")
            return False
        
        last_position = playback_info["position"]
        
        # 检查文件是否存在
        if not os.path.exists(last_file):
            print(f"[PlayerManager] 上次播放的文件不存在: {last_file}")
            return False
        
        try:
            # 设置文件
            self.set_file(last_file, last_position)
            self.player.play()
            # 如果上次有播放位置，设置播放位置
            if last_position > 0:
                self.player.set_time(int(last_position * 1000))  # 转换为毫秒
            
            print(f"[PlayerManager] 恢复上次播放: {os.path.basename(last_file)} 位置: {last_position:.1f}秒")
            return True
            
        except Exception as e:
            print(f"[PlayerManager] 恢复播放失败: {e}")
            raise e
            return False
    
    def set_play_mode(self, mode: PlayMode):
        """
        设置播放模式
        """
        self.play_mode = mode
        PlayerManager.play_mode = mode
        print(f"[PlayerManager] 设置播放模式: {mode}")
        return mode
    
    def get_play_mode(self) -> PlayMode:
        """
        获取当前播放模式
        """
        return self.play_mode
    
    def toggle_play_mode(self) -> PlayMode:
        """
        切换到下一个播放模式
        """
        self.play_mode = PlayMode.next_mode(self.play_mode)
        PlayerManager.play_mode = self.play_mode
        print(f"[PlayerManager] 切换播放模式: {self.play_mode}")
        return self.play_mode

    def cycle_play_mode(self) -> PlayMode:
        """
        按顺序循环切换播放模式：
        single_once -> sequence -> single_loop -> random -> single_once
        
        Returns:
            PlayMode: 切换后的播放模式
        """
        # 获取当前播放模式
        current_mode = self.get_play_mode()
        
        # 按顺序切换到下一个模式
        next_mode = PlayMode.next_mode(current_mode)
        
        # 设置新的播放模式
        self.set_play_mode(next_mode)
        
        # 保存到设置
        mode_mapping = {
            PlayMode.SINGLE: "SINGLE",
            PlayMode.SEQUENTIAL: "SEQUENTIAL", 
            PlayMode.LOOP: "LOOP",
            PlayMode.RANDOM: "RANDOM"
        }
        self.settings.set("play_mode", mode_mapping[next_mode])
        
        print(f"[PlayerManager] 循环切换播放模式: {current_mode} -> {next_mode}")
        return next_mode

    def _setup_vlc_event_manager(self):
        """设置VLC事件监听器，监听播放结束事件"""
        try:
            # 获取VLC事件管理器
            event_manager = self.player.event_manager()
            
            # 监听播放结束事件
            event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_media_end_reached)
            
            print("[PlayerManager] VLC事件监听器设置完成 - 监听播放结束事件")
        except Exception as e:
            print(f"[PlayerManager] VLC事件监听器设置失败: {e}")
    
    def _on_media_end_reached(self, event):
        """VLC播放结束事件回调函数"""
        try:
            print("[PlayerManager] 检测到播放结束事件，触发自动播放检查")
            
            # 在新线程中执行自动播放检查，避免阻塞事件回调
            threading.Timer(0.1, lambda: self._check_and_auto_next()).start()
            
        except Exception as e:
            print(f"[PlayerManager] 播放结束事件处理错误: {e}")
    
    def set_volume(self, volume: int):
        """
        设置VLC播放器音量
        
        Args:
            volume: 音量值 (0-100)
        """
        if not 0 <= volume <= 100:
            print(f"[PlayerManager] 音量值无效: {volume}，必须在0-100范围内")
            return False
            
        try:
            # 设置VLC播放器音量
            self.player.audio_set_volume(volume)
            
            # 同时更新设置中的音量值
            self.settings.set_volume(volume)
            
            # 同步到类属性
            PlayerManager.settings = self.settings
            
            print(f"[PlayerManager] 音量设置为: {volume}")
            return True
            
        except Exception as e:
            print(f"[PlayerManager] 设置音量失败: {e}")
            return False

    def get_volume(self) -> int:
        """获取当前VLC播放器音量
        
        Returns:
            int: 当前音量值 (0-100)
        """
        try:
            volume = self.player.audio_get_volume()
            if volume == -1:  # VLC返回-1表示获取失败
                # 返回设置中的音量值作为备用
                volume = self.settings.get("volume", 80)
            return volume
        except Exception as e:
            print(f"[PlayerManager] 获取音量失败: {e}")
            return self.settings.get("volume", 80)
    
    def set_popup_window(self, enabled: bool) -> bool:
        """
        设置是否弹出窗口播放视频
        
        Args:
            enabled: 是否启用弹出窗口播放
            
        Returns:
            bool: 设置是否成功
        """
        try:
            # 获取当前播放状态
            was_playing = self.player.is_playing()
            current_position = self.player.get_time() / 1000.0 if was_playing else 0.0
            current_file = self.current_file
            
            # 设置新的弹出窗口状态
            self.settings.set_popup_window(enabled)
            
            # 如果当前正在播放视频，需要重新设置播放器
            if was_playing and current_file:
                print(f"[PlayerManager] 切换弹出窗口设置，重新设置播放器...")
                
                # 停止当前播放
                self.player.stop()
                
                # 重新设置文件（这会根据新的popup_window设置决定是否全屏）
                self.set_file(current_file, current_position)
                
                # 重新播放
                self.player.play()
                
                # 设置播放位置
                if current_position > 0:
                    self.player.set_time(int(current_position * 1000))
                
                print(f"[PlayerManager] 播放器已重新设置，弹出窗口: {'启用' if enabled else '禁用'}")
            
            return True
            
        except Exception as e:
            print(f"[PlayerManager] 设置弹出窗口失败: {e}")
            return False
    
    def get_popup_window(self) -> bool:
        """
        获取是否弹出窗口播放视频
        
        Returns:
            bool: 是否启用弹出窗口播放
        """
        return self.settings.get_popup_window()

    def get_next_file(self, direction: int = 1) -> Optional[str]: 
        """
        根据当前播放模式和播放来源设置获取下一个/上一个要播放的文件
        
        Args:
            direction: 方向（1=下一首，-1=上一首）
            
        Returns:
            Optional[str]: 下一个/上一个文件路径，如果无法获取则返回None
            
        Raises:
            ValueError: 播放列表模式下播放列表为空时抛出异常
        """
        # 获取播放来源和播放模式
        play_source = self.settings.get_play_source()
        
        # 获取音频文件列表
        if play_source == 1:  # 播放列表模式
            playlist = self.get_playlist()
            if not playlist:
                raise ValueError("播放列表为空，无法切换音轨")
            
            # 过滤出有效的文件路径（排除网址）
            valid_files = [item['path'] for item in playlist if item['type'] == 'file' and os.path.exists(item['path'])]
            if not valid_files:
                raise ValueError("播放列表中没有有效的音频文件，无法切换音轨")
                
        else:  # 磁盘路径模式
            if not self.current_directory:
                return None
            valid_files = self.get_audio_files_in_directory(self.current_directory)
            if not valid_files:
                return None
        
        # 处理上一曲逻辑
        if direction == -1:
            if self.play_mode == PlayMode.RANDOM:
                # 随机播放模式：从播放历史记录中获取上一首
                if not self.current_file:
                    return None
                    
                # 确保当前文件在历史记录中
                if not self.playback_history or self.playback_history[-1] != self.current_file:
                    self._add_to_playback_history(self.current_file)
                
                return self._get_previous_from_history()
            else:
                # 顺序播放模式下的上一曲
                if self.current_file in valid_files:
                    current_idx = valid_files.index(self.current_file)
                    if current_idx > 0:
                        return valid_files[current_idx - 1]
                    else:
                        # 如果是第一首，上一首是最后一首
                        return valid_files[-1]
                else:
                    # 如果当前文件不在播放列表中，获取最后一首
                    return valid_files[-1] if valid_files else None
        
        # 处理下一曲逻辑（direction == 1）
        if self.play_mode == PlayMode.SINGLE:
            # 单曲不重复，播放结束后不播放任何文件
            return None
            
        elif self.play_mode == PlayMode.LOOP:
            # 单曲循环，继续播放当前文件
            return self.current_file
            
        elif self.play_mode == PlayMode.SEQUENTIAL:
            # 顺序播放
            if play_source == 1:  # 播放列表模式
                if self.current_file in valid_files:
                    current_idx = valid_files.index(self.current_file)
                    if current_idx < len(valid_files) - 1:
                        return valid_files[current_idx + 1]
                    else:
                        # 如果是最后一个文件，重新开始
                        return valid_files[0]
                else:
                    # 如果当前文件不在播放列表中，从第一首开始
                    return valid_files[0]
            else:  # 磁盘路径模式
                if self.file_index >= 0 and self.file_index < len(valid_files) - 1:
                    return valid_files[self.file_index + 1]
                elif len(valid_files) > 0:
                    # 如果是最后一个文件，重新开始
                    return valid_files[0]
                return None
            
        elif self.play_mode == PlayMode.RANDOM:
            # 随机播放，避免连续播放同一首歌
            if len(valid_files) == 1:
                return valid_files[0]
            
            # 过滤掉已播放的文件，如果都已播放，则重置
            available_files = [f for f in valid_files if f not in self.played_files]
            if not available_files:
                self.played_files = [self.current_file] if self.current_file else []
                available_files = [f for f in valid_files if f != self.current_file]
            
            if available_files:
                return random.choice(available_files)
            return random.choice(valid_files)
        
        return None

    def set_lyrics(self, lyrics: Optional[str]):
        self.global_lyrics = lyrics
        PlayerManager.global_lyrics = lyrics

    # ============================= 播放列表相关方法 =============================
    def add_to_playlist(self, name: str, path: str) -> dict:
        """
        添加播放列表项
        
        Args:
            name: 播放列表项名称
            path: 文件路径或网址
            
        Returns:
            dict: 包含添加结果的字典
        """
        with self.playlist_lock:
            # 检查播放来源设置
            play_source = self.settings.get_play_source()
            if play_source == 2:  # 磁盘路径模式
                return {"status": "error", "message": "当前播放来源为磁盘路径模式，播放列表已被锁定为只读"}
            
            # 检查是否已存在相同路径的项
            for item in self.playlist:
                if item["path"] == path:
                    return {"status": "error", "message": "该文件或网址已在播放列表中"}
            
            # 检查路径类型：本地文件或网址
            is_url = path.startswith(('http://', 'https://', 'ftp://'))
            
            if not is_url:
                # 本地文件路径检查
                if not os.path.exists(path):
                    return {"status": "error", "message": "文件路径不存在"}
            else:
                # 网址验证（基本格式检查）
                if not re.match(r'^https?://[^\s/$.?#].[^\s]*$', path):
                    return {"status": "error", "message": "网址格式不正确"}
            
            # 生成新ID（自动递增）
            new_id = max([item["id"] for item in self.playlist], default=0) + 1
            
            # 添加新项
            new_item = {
                "id": new_id,
                "name": name,
                "path": path,
                "type": "url" if is_url else "file"  # 添加类型标识
            }
            self.playlist.append(new_item)
            
            # 同步到类属性
            PlayerManager.playlist = self.playlist
            
            return {"status": "success", "message": "添加成功", "item": new_item}
    
    def remove_from_playlist(self, identifier: Union[int, str]) -> dict:
        """
        从播放列表中删除项
        
        Args:
            identifier: 可以是ID（int）或名称（str）
            
        Returns:
            dict: 包含删除结果的字典
        """
        with self.playlist_lock:
            # 检查播放来源设置
            play_source = self.settings.get_play_source()
            if play_source == 2:  # 磁盘路径模式
                return {"status": "error", "message": "当前播放来源为磁盘路径模式，播放列表已被锁定为只读"}
            
            # 查找要删除的项
            item_to_remove = None
            for item in self.playlist:
                if (isinstance(identifier, int) and item["id"] == identifier) or \
                   (isinstance(identifier, str) and item["name"] == identifier):
                    item_to_remove = item
                    break
            
            if not item_to_remove:
                return {"status": "error", "message": "未找到指定的播放列表项"}
            
            # 删除项
            self.playlist.remove(item_to_remove)
            
            # 重新排序ID
            self._reorder_playlist_ids()
            
            # 同步到类属性
            PlayerManager.playlist = self.playlist
            
            return {"status": "success", "message": "删除成功", "item": item_to_remove}
    
    def _reorder_playlist_ids(self):
        """重新排序播放列表ID"""
        for i, item in enumerate(self.playlist, 1):
            item["id"] = i
    
    def get_playlist(self) -> List[dict]:
        """获取播放列表"""
        with self.playlist_lock:
            return self.playlist.copy()
    
    def clear_playlist(self) -> dict:
        """清空播放列表"""
        with self.playlist_lock:
            self.playlist.clear()
            PlayerManager.playlist = self.playlist
            # 清空播放历史记录
            self.clear_playback_history()
            return {"status": "success", "message": "播放列表已清空"}

    # ============================= 播放列表保存和恢复功能 =============================
    def save_playlist_to_file(self, file_path: str = "playlist.json") -> dict:
        """
        保存播放列表到JSON文件
        
        Args:
            file_path: 保存的文件路径，默认为playlist.json
            
        Returns:
            dict: 包含保存结果的字典
        """
        with self.playlist_lock:
            try:
                # 准备要保存的数据
                playlist_data = {
                    "version": "1.0",
                    "timestamp": time.time(),
                    "playlist": self.playlist.copy()
                }
                
                # 保存到文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(playlist_data, f, indent=2, ensure_ascii=False)
                
                print(f"[PlayerManager] 播放列表已保存到 {file_path}，共 {len(self.playlist)} 个项目")
                return {"status": "success", "message": "播放列表保存成功", "file_path": file_path, "count": len(self.playlist)}
                
            except Exception as e:
                print(f"[PlayerManager] 保存播放列表失败: {e}")
                return {"status": "error", "message": f"保存播放列表失败: {e}"}
    
    def load_playlist_from_file(self, file_path: str = "playlist.json") -> dict:
        """
        从JSON文件恢复播放列表
        
        Args:
            file_path: 要加载的文件路径，默认为playlist.json
            
        Returns:
            dict: 包含恢复结果的字典
        """
        with self.playlist_lock:
            try:
                # 检查文件是否存在
                if not os.path.exists(file_path):
                    print(f"[PlayerManager] 播放列表文件不存在: {file_path}")
                    return {"status": "error", "message": "播放列表文件不存在"}
                
                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    playlist_data = json.load(f)
                
                # 验证数据格式
                if "playlist" not in playlist_data:
                    print(f"[PlayerManager] 播放列表文件格式错误: {file_path}")
                    return {"status": "error", "message": "播放列表文件格式错误"}
                
                # 验证播放列表项格式
                valid_playlist = []
                for item in playlist_data["playlist"]:
                    if isinstance(item, dict) and "name" in item and "path" in item:
                        # 检查文件是否存在（如果是本地文件）
                        if not item["path"].startswith(('http://', 'https://', 'ftp://')):
                            if not os.path.exists(item["path"]):
                                print(f"[PlayerManager] 文件不存在，跳过: {item['path']}")
                                continue
                        
                        # 确保有必要的字段
                        valid_item = {
                            "id": len(valid_playlist) + 1,
                            "name": item["name"],
                            "path": item["path"],
                            "type": item.get("type", "file"),
                            "artist": item.get("artist", ""),
                            "title": item.get("title", ""),
                            "duration": item.get("duration", 0)
                        }
                        valid_playlist.append(valid_item)
                
                # 更新播放列表
                self.playlist = valid_playlist
                PlayerManager.playlist = self.playlist
                
                print(f"[PlayerManager] 播放列表已从 {file_path} 恢复，共 {len(self.playlist)} 个有效项目")
                return {"status": "success", "message": "播放列表恢复成功", "file_path": file_path, "count": len(self.playlist)}
                
            except Exception as e:
                print(f"[PlayerManager] 恢复播放列表失败: {e}")
                return {"status": "error", "message": f"恢复播放列表失败: {e}"}

    # ============================= 工具方法 =============================
    def new_token(self) -> str:
        """生成新 refresh_token"""
        with self.refresh_lock:
            self.refresh_token = str(uuid.uuid4())
        #print("[PlayerManager] 已生成新token")
        return self.refresh_token
    
    def _add_to_playback_history(self, file_path: str):
        """添加到播放历史记录
        
        Args:
            file_path: 文件路径
        """
        if not file_path:
            return
            
        # 如果是当前已经在历史记录顶部的文件，不重复添加
        if self.playback_history and self.playback_history[-1] == file_path:
            return
            
        # 添加到历史记录
        self.playback_history.append(file_path)
        
        # 限制历史记录数量
        if len(self.playback_history) > self.max_history_size:
            self.playback_history.pop(0)
    
    def _get_previous_from_history(self) -> Optional[str]:
        """从播放历史记录中获取上一首歌曲
        
        Returns:
            Optional[str]: 上一首文件路径，如果没有历史记录则返回None
        """
        # 移除当前文件（历史记录的最后一项）
        if len(self.playback_history) >= 2:
            self.playback_history.pop()  # 移除当前文件
            return self.playback_history[-1]  # 返回上一首
        return None
    
    def clear_playback_history(self):
        """清空播放历史记录"""
        self.playback_history.clear()
        print("[PlayerManager] 播放历史记录已清空")

    def load_lyrics(self) -> Optional[str]:
        """加载同名 .lrc 文件"""
        #print(f"[load_lyrics] current_file: {self.current_file}")
        if not self.current_file or not self.current_directory:
            #print("[load_lyrics] 缺少文件或目录")
            self.global_lyrics = None
            return None

        base_name = os.path.splitext(os.path.basename(self.current_file))[0]
        lrc_path = os.path.join(self.current_directory, f"{base_name}.lrc")
        #print(f"[load_lyrics] 尝试加载: {lrc_path}")

        if not os.path.isfile(lrc_path):
            #print("[load_lyrics] 文件不存在")
            self.global_lyrics = None
            return None

        encodings = ['utf-8', 'gbk', 'utf-16', 'shift-jis']
        for enc in encodings:
            try:
                with open(lrc_path, 'r', encoding=enc) as f:
                    content = f.read().strip()
                    if content:
                        self.global_lyrics = content
                        #print(f"[load_lyrics] 成功加载 ({enc}): {len(content)} 字符")
                        return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                #print(f"[load_lyrics] 读取失败 ({enc}): {e}")
        #self.global_lyrics = None
                return None

    def get_lyrics_context(self, current_time: float) -> str:
        """获取当前歌词行"""
        if not self.global_lyrics:
            return "没有找到歌词"

        lines = []
        for line in self.global_lyrics.split('\n'):
            matches = re.findall(r'\[(\d+):(\d+(?:\.\d+)?)\]', line)
            text = re.sub(r'\[.+?\]', '', line).strip()
            if matches and text:
                m = matches[-1]
                ts = int(m[0]) * 60 + float(m[1])
                lines.append((ts, text))

        if not lines:
            return ""

        lines.sort(key=lambda x: x[0])
        current_idx = -1
        for i, (ts, _) in enumerate(lines):
            if ts <= current_time:
                current_idx = i
            else:
                break
        return lines[current_idx][1] if current_idx >= 0 else ""

    def get_drives(self) -> List[str]:
        """获取系统磁盘"""
        if os.name != 'nt':
            return []
        return [f"{d}" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:\\")]

    def extract_album_cover(self, file_path: str) -> Optional[bytes]:
        """提取封面"""
        audio = eyed3.load(file_path)
        if audio and audio.tag and audio.tag.images:
            return audio.tag.images[0].image_data
        return None

    def get_audio_files_in_directory(self, directory: str) -> List[str]:
        """获取目录下音频文件"""
        if not directory or not os.path.isdir(directory):
            return []
        return [
            os.path.join(directory, f)
            for f in os.listdir(directory)
            if f.lower().endswith(('.mp3', '.flac', '.wav'))
        ]

    async def switch_track(self, direction: int, request=None):
        """
        切换音轨（下一首/上一首）
        
        Args:
            direction: 方向（1=下一首，-1=上一首）
            request: 请求对象（可选，用于调用SetFileView）
            
        Returns:
            tuple: (jsonify响应对象, 状态码)
        """
        from quart import jsonify
        from app.core.logging import player_logger
        
        # 获取目标音轨文件（所有检查逻辑都在get_next_file中处理）
        try:
            next_file_path = self.get_next_file(direction)
            if not next_file_path:
                return jsonify({"status": "error", "message": "没有可切换的音轨"}), 400
        except ValueError as e:
            # 播放列表为空等异常情况，返回友好错误信息
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": f"获取音轨失败: {str(e)}"}), 500

        # 设置新文件并播放
        try:
            # 设置新文件
            self.set_file(next_file_path)
            
            # 加载歌词
            import asyncio
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.load_lyrics)
            
            # 设置媒体并播放
            await loop.run_in_executor(None, self.player.play)
            
            # 生成新token
            self.new_token()

        except Exception as e:
            return jsonify({"status": "error", "message": f"播放文件失败: {str(e)}"}), 500

        # 返回成功响应
        action = "next" if direction == 1 else "prev"
        player_logger.debug(f"[{action.upper()}] 切歌 → {os.path.basename(next_file_path)}")
            
        return jsonify({"status": action, "file": next_file_path}), 200
    
    def save_playback_settings(self):
        """保存播放设置（外部触发）"""
        self.settings.save_playback_info()
    
    def set_remember_playback(self, enabled: bool):
        """设置是否记住播放进度"""
        self.settings.set_remember_playback(enabled)
    
    def get_settings(self) -> dict:
        """获取当前设置"""
        return {
            "last_played_file": self.settings.get("last_played_file"),
            "remember_playback": self.settings.get("remember_playback"),
            "last_position": self.settings.get("last_position"),
            "volume": self.settings.get("volume"),
            "play_mode": self.settings.get("play_mode")
        }
    
    def update_playback_position(self, position: float):
        """更新当前播放位置"""
        if self.current_file and self.settings.get("remember_playback"):
            self.settings.update_last_playback(self.current_file, position)

    def update_online_user(self, user_id: str, ip: str, ua: str):
        """更新在线用户"""
        now = time.time()
        with self.refresh_lock:
            expired = [
                uid for uid, info in self.online_users.items()
                if now - info["last_seen"] > self.ONLINE_TIMEOUT
            ]
            for uid in expired:
                del self.online_users[uid]
            if user_id:
                self.online_users[user_id] = {
                    "ip": ip,
                    "ua": ua,
                    "last_seen": now
                }


    
    def _check_and_auto_next(self):
        """
        检查并自动播放下一首
        
        Returns:
            bool: True 如果成功切换到下一首，False 如果不需要自动播放
        """
        from app.core.logging import player_logger
        
        # 播放列表模式下的自动播放逻辑
        play_source = self.settings.get_play_source()
        
        if play_source == 1:  # 播放列表模式
            try:
                # 在自动播放中，如果播放列表为空，直接停止播放
                playlist = self.get_playlist()
                if not playlist:
                    player_logger.debug("[AUTO] 播放列表为空，自动播放停止")
                    return False
                
                valid_files = [item['path'] for item in playlist if item['type'] == 'file' and os.path.exists(item['path'])]
                if not valid_files:
                    player_logger.debug("[AUTO] 播放列表中没有有效的音频文件，自动播放停止")
                    return False
                
                # 获取下一个文件并自动播放
                next_file_path = self.get_next_file()
                if next_file_path:
                    self.set_file(next_file_path)
                    
                    # 加载歌词（使用线程安全的方式）
                    import threading
                    threading.Thread(target=self.load_lyrics, daemon=True).start()
                    
                    # 播放
                    media = vlc.Media(next_file_path)
                    self.player.play()
                    
                    # 生成新token
                    self.new_token()
                    
                    player_logger.info(f"[AUTO] 自动切换 → {os.path.basename(next_file_path)}")
                    return True
                else:
                    player_logger.debug("[AUTO] 无法获取下一个文件，自动播放停止")
                    return False
                    
            except ValueError as e:
                # 播放列表为空等异常，自动播放停止
                player_logger.debug(f"[AUTO] 播放列表状态异常，自动播放停止: {e}")
                return False
            except Exception as e:
                player_logger.error(f"[AUTO] 自动播放错误: {e}")
                return False
        
        # 磁盘路径模式下的自动播放逻辑（保持原有逻辑）
        else:  # play_source == 2 磁盘路径模式
            try:
                next_file_path = self.get_next_file()
                if next_file_path:
                    self.set_file(next_file_path)
                    
                    # 加载歌词（使用线程安全的方式）
                    import threading
                    threading.Thread(target=self.load_lyrics, daemon=True).start()
                    
                    # 播放
                    media = vlc.Media(next_file_path)
                    self.player.play()
                    
                    # 生成新token
                    self.new_token()
                    
                    player_logger.info(f"[AUTO] 自动切换 → {os.path.basename(next_file_path)}")
                    return True
                else:
                    player_logger.debug("[AUTO] 没有更多文件，自动播放停止")
                    return False
                    
            except Exception as e:
                player_logger.error(f"[AUTO] 自动播放错误: {e}")
                raise
                return False
    
    def _auto_play_next(self):
        """自动播放下一曲（顺序播放模式）"""
        # 检查播放来源设置
        play_source = self.settings.get_play_source()
        
        if play_source == 1:  # 播放列表模式
            try:
                # 播放列表模式下的空检查已经在get_next_file中实现
                next_file = self.get_next_file()
                if next_file and os.path.exists(next_file):
                    print(f"[PlayerManager] 自动下一曲: {os.path.basename(next_file)}")
                    self.set_file(next_file)
                    self.player.play()
                    self.load_lyrics()
                    self.new_token()
                    self.other_event_broadcast = f"自动下一曲被触发: {os.path.basename(next_file)}"
                else:
                    print("[PlayerManager] 没有下一曲可播放")
            except ValueError as e:
                # 播放列表为空等异常情况，安全停止自动播放
                print(f"[PlayerManager] 播放列表模式下自动下一曲失败: {e}")
        else:  # 磁盘路径模式
            next_file = self.get_next_file()
            if next_file and os.path.exists(next_file):
                print(f"[PlayerManager] 自动下一曲: {os.path.basename(next_file)}")
                self.set_file(next_file)
                self.player.play()
                self.load_lyrics()
                self.new_token()
            else:
                print("[PlayerManager] 没有下一曲可播放")
    
    def _auto_replay_current(self):
        """重新播放当前曲目（单曲循环模式）"""
        if self.current_file and os.path.exists(self.current_file):
            print(f"[PlayerManager] 重新播放当前曲目: {os.path.basename(self.current_file)}")
            self.player.play()
            self.new_token()
        else:
            print("[PlayerManager] 当前文件不存在，无法重新播放")
    
    def _auto_play_random(self):
        """自动播放随机下一曲（随机播放模式）"""
        # 检查播放来源设置
        play_source = self.settings.get_play_source()
        
        if play_source == 1:  # 播放列表模式
            try:
                # 播放列表模式下的空检查已经在get_next_file中实现
                next_file = self.get_next_file()
                if next_file and os.path.exists(next_file):
                    print(f"[PlayerManager] 随机下一曲: {os.path.basename(next_file)}")
                    self.set_file(next_file)
                    self.player.play()
                    self.load_lyrics()
                    self.new_token()
                else:
                    print("[PlayerManager] 没有随机曲目可播放")
            except ValueError as e:
                # 播放列表为空等异常情况，安全停止随机自动播放
                print(f"[PlayerManager] 播放列表模式下随机播放失败: {e}")
        else:  # 磁盘路径模式
            next_file = self.get_next_file()
            if next_file and os.path.exists(next_file):
                print(f"[PlayerManager] 随机下一曲: {os.path.basename(next_file)}")
                self.set_file(next_file)
                self.player.play()
                self.load_lyrics()
                self.new_token()
            else:
                print("[PlayerManager] 没有随机曲目可播放")

    # ------------------- VLC 状态包装 -------------------
    def vlc_state_to_obj(self, state) -> 'VlcState':
        state_map = {
            vlc.State.NothingSpecial: ("NothingSpecial", 0),
            vlc.State.Opening:        ("Opening", 1),
            vlc.State.Buffering:      ("Buffering", 2),
            vlc.State.Playing:        ("Playing", 3),
            vlc.State.Paused:         ("Paused", 4),
            vlc.State.Stopped:        ("Stopped", 5),
            vlc.State.Ended:          ("Ended", 6),
            vlc.State.Error:          ("Error", 7),
        }

        if state is None:
            return VlcState(0, "NothingSpecial")

        if isinstance(state, (bytes, bytearray)):
            try:
                state_int = struct.unpack('I', state[:4])[0]
                name = {v[1]: v[0] for v in state_map.values()}.get(state_int, "Unknown")
                return VlcState(state_int, name)
            except Exception:
                return VlcState(0, "NothingSpecial")

        if isinstance(state, vlc.State):
            name, val = state_map.get(state, ("NothingSpecial", 0))
            return VlcState(val, name)

        if isinstance(state, int):
            name = {v[1]: v[0] for v in state_map.values()}.get(state, "Unknown")
            return VlcState(state, name)

        return VlcState(0, "NothingSpecial")


class VlcState:
    """VLC 状态包装类"""
    def __init__(self, state_int: int, state_name: str):
        self.int = state_int
        self.name = state_name

    def __repr__(self):
        return f"VlcState({self.int}, '{self.name}')"


# ============================= 全局单例导出 =============================
player_manager = PlayerManager()
