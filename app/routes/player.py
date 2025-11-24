# app/routes/player.py
import re
import base64
import asyncio
import time
import io
import os
import sys
import tempfile
import aiohttp
from datetime import datetime
import vlc
from quart import Blueprint, jsonify, current_app, request, send_file, redirect
from quart.views import MethodView
from app.core.player import player_manager, PlayMode, PlayerManager
from app.core.error_handler import PlayerErrorHandler
from app.core.logging import player_logger
from app.core.sync_manager import get_sync_manager  # 导入同步管理器
from app.core.search_file import file_indexer  # 导入搜索索引器单例
# ================== 类视图定义 ==================
class IndexView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        return redirect("/static/default/index.html")
class ListDirectoryView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        """列出目录下的文件和文件夹，并支持分页"""
        path = request.args.get('path', default='', type=str)  # 获取路径参数
        page = request.args.get('page', default=1, type=int)  # 获取页码参数，默认页码为1
        page_size = request.args.get('page_size', default=10, type=int)  # 每页显示多少条，默认10条

        # 如果没有传入路径，返回系统中所有的磁盘
        if not path:
            drives = player_manager.get_drives()
            return jsonify({"status": "success", "drives": drives}), 200

        # 获取完整的路径
        full_path = os.path.abspath(path)
        if not os.path.exists(full_path):
            return jsonify({"status": "error", "message": "Directory does not exist"}), 404

        # 获取目录下的文件和文件夹
        try:
            files_and_folders = []
            for entry in os.listdir(full_path):
                entry_path = os.path.join(full_path, entry)
                if os.path.isdir(entry_path):
                    entry_info = {"name": entry, "type": "folder", "path": entry_path}
                else:
                    entry_info = {"name": entry, "type": "file", "path": entry_path}
                files_and_folders.append(entry_info)

            # 按文件名排序
            files_and_folders.sort(key=lambda x: x["name"])

            # 计算分页起始位置
            start = (page - 1) * page_size
            end = start + page_size
            paginated_files = files_and_folders[start:end]

            return jsonify({
                "status": "success",
                "directory": full_path,
                "page": page,
                "page_size": page_size,
                "total_files": len(files_and_folders),
                "files": paginated_files
            }), 200

        except PermissionError:
            return jsonify({"status": "error", "message": "Permission denied"}), 403
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
class PlayView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        if not player_manager.current_file:
            return jsonify({"status": "error", "message": "No file loaded"}), 400

        loop = asyncio.get_running_loop()

        # 获取当前状态
        state = await loop.run_in_executor(None, player_manager.player.get_state)

        await loop.run_in_executor(None, player_manager.player.play)

        player_logger.debug(f"[Play] 正在播放: {player_manager.current_file}")
        player_manager.new_token()  # 生成新 token

        return jsonify({"status": "playing"}), 200
class PauseView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        global refresh_token
        if not player_manager.current_file:
            return jsonify({"status": "error", "message": "No file loaded"}), 400

        loop = asyncio.get_running_loop()
        state = await loop.run_in_executor(None, player_manager.player.get_state)

        if state != vlc.State.Playing:
            return jsonify({"status": "already paused"}), 200

        await loop.run_in_executor(None, player_manager.player.pause)
        refresh_token = player_manager.new_token()
        player_logger.debug(f"[Pause] 已暂停: {player_manager.current_file}")
        return jsonify({"status": "paused"}), 200
class StopView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        await asyncio.get_running_loop().run_in_executor(None, player_manager.player.stop)
        player_logger.debug(f"[Stop] 已停止: {player_manager.current_file}")
        return jsonify({"status": "stopped"}), 200
class NextTrackView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        return await player_manager.switch_track(1, request)
class PrevTrackView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        return await player_manager.switch_track(-1, request)
class SettingsView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        """获取当前设置"""
        settings = player_manager.get_settings()
        # 添加播放来源设置
        settings["play_source"] = player_manager.settings.get_play_source()
        return jsonify({"status": "success", "settings": settings}), 200
    
    @PlayerErrorHandler.create_error_handler
    async def post(self):
        """更新设置"""
        data = await request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        # 处理播放来源设置
        if "play_source" in data:
            play_source = data["play_source"]
            if play_source in [1, 2]:
                player_manager.settings.set_play_source(play_source)
            else:
                return jsonify({"status": "error", "message": "播放来源值无效，必须为1或2"}), 400
        
        # 处理记住播放进度设置
        if "remember_playback" in data:
            player_manager.set_remember_playback(data["remember_playback"])
        
        # 处理音量设置
        if "volume" in data:
            player_manager.settings.set_volume(data["volume"])
        
        # 处理播放模式设置
        if "play_mode" in data:
            player_manager.settings.set_play_mode(data["play_mode"])
        
        return jsonify({"status": "success", "message": "Settings updated"}), 200
class RestorePlaybackView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        """恢复上次播放"""
        success = player_manager.restore_last_playback()
        if success:
            return jsonify({"status": "success", "message": "Playback restored"}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to restore playback"}), 400
class SavePlaybackView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        """手动保存播放信息"""
        player_manager.save_playback_settings()
        return jsonify({"status": "success", "message": "Playback settings saved"}), 200
class UpdatePositionView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def post(self):
        """更新播放位置"""
        data = await request.get_json()
        if not data or "position" not in data:
            return jsonify({"status": "error", "message": "No position provided"}), 400
        
        position = float(data["position"])
        player_manager.update_playback_position(position)
        return jsonify({"status": "success", "message": "Position updated"}), 200
class SetDirectoryView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        directory = request.args.get('directory')
        if not directory:
            return jsonify({"status": "error", "message": "No directory provided"}), 400

        # 安全处理路径
        directory = os.path.abspath(directory)
        if not os.path.isdir(directory):
            return jsonify({"status": "error", "message": "Directory does not exist"}), 404

        # 直接设置全局目录
        current_directory = directory

        player_logger.debug(f"[SetDirectory] 已切换目录: {current_directory}")

        return jsonify({
            "status": "directory set",
            "directory": current_directory
        }), 200
class SetFileView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        file_path = request.args.get('file')
        if not file_path:
            return jsonify({"status": "error", "message": "No file provided"}), 400

        file_path = os.path.abspath(file_path)
        if not os.path.isfile(file_path):
            return jsonify({"status": "error", "message": "File not exists"}), 404

        loop = asyncio.get_running_loop()

        # === 1. 使用set_file方法设置文件（这会自动更新播放记录）===
        await loop.run_in_executor(None, player_manager.set_file, file_path)
        player_logger.debug(f"[SetFile] 准备加载: {player_manager.current_file}")
        # === 2. 异步加载歌词（使用工具函数）===
        global_lyrics = await loop.run_in_executor(None, player_manager.load_lyrics)
        player_logger.debug(f"[SetFile] 歌词加载: {len(global_lyrics) if global_lyrics else 0} 字符")
        # === 3. 设置媒体 + 播放 ===
        await loop.run_in_executor(None, player_manager.player.play)
        # === 4. 生成新 token ===
        player_manager.new_token()
        player_logger.debug(f"[SetFile] 成功加载并播放: {os.path.basename(player_manager.current_file)}")
        return jsonify({
            "status": "loaded",
            "file": player_manager.current_file,
            "lyrics_loaded": bool(global_lyrics)
        }), 200
class LyricsView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        # 1. 检查是否有歌词（由 set_file 预先加载）
        if not player_manager.global_lyrics:
            return jsonify({
                "status": "no_lyrics",
                "message": "No lyrics loaded for current song"
            }), 200

        loop = asyncio.get_running_loop()

        # 2. 路由分支
        if request.path == "/api/full_lyrics":
            # 返回完整歌词
            return jsonify({
                "status": "success",
                "full_lyrics": player_manager.global_lyrics,
                "line_count": len([line for line in player_manager.global_lyrics.split('\n') if line.strip()])
            }), 200

        elif request.path == "/api/current_lyrics":
            # 获取当前播放时间
            current_time_ms = await loop.run_in_executor(None, player_manager.player.get_time)
            current_time = current_time_ms / 1000.0 if current_time_ms > 0 else 0.0

            # 解析当前歌词行
            current_line = await loop.run_in_executor(
                None, player_manager.get_lyrics_context, current_time
            )

            return jsonify({
                "status": "success",
                "current_lyrics": current_line,
                "current_time": round(current_time, 2)
            }), 200

        else:
            return jsonify({"status": "error", "message": "Invalid lyrics endpoint"}), 404
class AlbumCoverView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        if not player_manager.current_file:
            return jsonify({"status": "error", "message": "No file selected"}), 400

        # 使用 player_manager 实例调用 extract_album_cover
        cover = await asyncio.get_running_loop().run_in_executor(
            None, player_manager.extract_album_cover, player_manager.current_file  # 正确传文件路径
        )

        if cover:
            return await send_file(
                io.BytesIO(cover),
                mimetype="image/jpeg"
            )

        return jsonify({"status": "no_cover", "message": "No album cover found"}), 200
class AudioMetadataView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        if not player_manager.current_file:
            return jsonify({"status": "error", "message": "No file selected"}), 400

        loop = asyncio.get_running_loop()

        # 复用你的 extract_album_cover
        cover_data = await loop.run_in_executor(None, player_manager.extract_album_cover, player_manager.current_file)
        cover_b64 = base64.b64encode(cover_data).decode() if cover_data else None

        # 简单获取时长（你原来的逻辑）
        duration = await loop.run_in_executor(None, lambda: player_manager.player.get_length() / 1000)

        return jsonify({
            "status": "success",
            "title": os.path.splitext(os.path.basename(player_manager.current_file))[0],
            "duration": round(duration, 2),
            "cover_base64": cover_b64,
            "file_path": player_manager.current_file
        }), 200
class ProgressView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        user_id = request.args.get("id")
        user_ip = request.remote_addr
        user_ua = request.headers.get("User-Agent", "Unknown UA")

        loop = asyncio.get_running_loop()

        # === 1. 更新在线用户 ===
        await loop.run_in_executor(None, player_manager.update_online_user, user_id, user_ip, user_ua)

        # === 2. 使用同步管理器获取同步数据 ===
        sync_manager = get_sync_manager()
        sync_data = await loop.run_in_executor(None, sync_manager.get_sync_data)

        return jsonify(sync_data), 200

    def _update_online_users(self, user_id, user_ip, user_ua, now):
        """线程安全更新在线用户"""
        with player_manager.refresh_lock:
            expired = [uid for uid, info in player_manager.online_users.items() if now - info["last_seen"] > player_manager.ONLINE_TIMEOUT]
            for uid in expired:
                del player_manager.online_users[uid]
            if user_id:
                player_manager.online_users[user_id] = {
                    "ip": user_ip,
                    "ua": user_ua,
                    "last_seen": now
                }

    def _get_lyrics_context(self, current_time: float):
        """
        返回三行歌词上下文：
        - prev: 上一句
        - current: 当前句
        - next: 下一句
        """
        if not player_manager.global_lyrics:
            return ""

        import re

        # 解析所有时间戳和歌词
        lines = []
        for line in player_manager.global_lyrics.split('\n'):
            matches = re.findall(r'\[(\d+):(\d+(?:\.\d+)?)\]', line)
            text = re.sub(r'\[.+?\]', '', line).strip()
            if matches and text:
                # 取最后一个时间戳（支持多时间戳）
                m = matches[-1]
                ts = int(m[0]) * 60 + float(m[1])
                lines.append((ts, text))

        if not lines:
            return ""

        lines.sort(key=lambda x: x[0])  # 按时间排序

        # 找到当前句
        current_idx = -1
        for i, (ts, _) in enumerate(lines):
            if ts <= current_time:
                current_idx = i
            else:
                break

        # 构造三行
        prev_line = lines[current_idx - 1][1] if current_idx > 0 else ""
        current_line = lines[current_idx][1] if current_idx >= 0 else ""
        next_line = lines[current_idx + 1][1] if current_idx + 1 < len(lines) else ""

        return current_line
class SetPositionView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        player_logger.debug(f"SetPosition_current_file: {player_manager.current_file}")
        position = request.args.get('position', type=float)
        if position is None or not 0 <= position <= 100:
            return jsonify({"status": "error", "message": "Position must be 0-100"}), 400

        if not player_manager.current_file:
            return jsonify({"status": "error", "message": "No file selected"}), 400

        loop = asyncio.get_running_loop()

        # 检查媒体是否加载
        media = await loop.run_in_executor(None, player_manager.player.get_media)
        if media is None:
            return jsonify({"status": "error", "message": "Media not loaded"}), 400

        # 检查播放器状态
        state = await loop.run_in_executor(None, player_manager.player.get_state)
        if state not in (vlc.State.Playing, vlc.State.Paused):
            player_logger.debug(f"[SetPosition] VLC 状态异常: {state}, 强制激活...")
            await loop.run_in_executor(None, player_manager.player.play)
            await asyncio.sleep(0.2)
            await loop.run_in_executor(None, player_manager.player.pause)

        # 执行跳转
        await loop.run_in_executor(None, player_manager.player.set_position, position / 100)
        # 验证实际位置
        actual_pos = await loop.run_in_executor(None, player_manager.player.get_position)
        player_logger.debug(f"[SetPosition] 目标: {position}% → 实际: {actual_pos*100:.2f}%")

        return jsonify({
            "status": "success",
            "position": round(position, 2),
            "actual": round(actual_pos * 100, 2),
            "file": player_manager.current_file
        }), 200
class SetDeviceView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        return jsonify({"status": "success", "note": "set_device 路由就绪"})
class DevicesView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        return jsonify({"devices": [], "note": "devices 路由就绪"})
class OnlineUsersView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        """
        返回当前所有在线用户列表
        路由：/api/online_users
        """
        # 可选：允许管理员强制刷新（?refresh=1）
        if request.args.get('refresh'):
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._cleanup_expired_users)

        # 线程安全读取 online_users
        with player_manager.refresh_lock:
            users_list = []
            now = time.time()
            for uid, info in player_manager.online_users.items():
                users_list.append({
                    "id": uid,
                    "ip": info["ip"],
                    "ua": info["ua"],
                    "last_seen": round(info["last_seen"], 2),
                    "online_seconds": round(now - info["last_seen"], 1)
                })

        return jsonify({
            "status": "success",
            "online_count": len(users_list),
            "users": users_list
        }), 200

    def _cleanup_expired_users(self):
        """清理过期用户（> ONLINE_TIMEOUT 秒）"""
        with player_manager.refresh_lock:
            now = time.time()
            expired = [
                uid for uid, info in player_manager.online_users.items()
                if now - info["last_seen"] > player_manager.ONLINE_TIMEOUT
            ]
            for uid in expired:
                player_logger.debug(f"[OnlineUsers] 清理离线用户: {uid}")
                del player_manager.online_users[uid]
class SetPlayModeView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        """
        设置播放模式
        路由：/api/set_play_mode
        参数：mode - 播放模式 (single_once/sequence/single_loop/random)，可选
        如果没有传入mode参数，则按顺序循环切换播放模式
        返回：当前播放模式和状态
        """
        # 获取播放模式参数
        mode = request.args.get('mode')
        
        # 如果没有传入mode参数，则按顺序循环切换播放模式
        if not mode:
            # 调用PlayerManager的循环切换方法
            loop = asyncio.get_running_loop()
            new_mode = await loop.run_in_executor(None, player_manager.cycle_play_mode)
            
            # 映射回前端可识别的模式名称
            mode_mapping = {
                PlayMode.SINGLE: 'single_once',
                PlayMode.SEQUENTIAL: 'sequence', 
                PlayMode.LOOP: 'single_loop',
                PlayMode.RANDOM: 'random'
            }
            
            current_mode_name = mode_mapping[new_mode]
            player_logger.debug(f"[SetPlayMode] 循环切换播放模式: {new_mode} -> {current_mode_name}")
            
            # 返回当前播放模式和所有支持的模式
            return jsonify({
                "status": "success",
                "current_mode": current_mode_name,
                "available_modes": list(mode_mapping.values()),
                "mode_name": new_mode.name,
                "action": "cycled"
            }), 200
            
        # 验证模式值并映射到PlayMode枚举
        mode_mapping = {
            'single_once': PlayMode.SINGLE,
            'sequence': PlayMode.SEQUENTIAL,
            'single_loop': PlayMode.LOOP,
            'random': PlayMode.RANDOM
        }
        
        if mode not in mode_mapping:
            valid_modes = list(mode_mapping.keys())
            return jsonify({
                "status": "error", 
                "message": f"Invalid mode. Valid modes are: {', '.join(valid_modes)}"
            }), 400
        
        # 设置播放模式
        play_mode_enum = mode_mapping[mode]
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, player_manager.set_play_mode, play_mode_enum)
        player_logger.debug(f"[SetPlayMode] 已设置播放模式: {mode} -> {play_mode_enum}")
        
        # 返回当前播放模式和所有支持的模式
        return jsonify({
            "status": "success",
            "current_mode": mode,
            "available_modes": list(mode_mapping.keys()),
            "mode_name": player_manager.get_play_mode().name,
            "action": "set"
        }), 200
class VolumeView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        """
        获取当前音量
        路由：/api/volume
        返回：当前音量值
        """
        loop = asyncio.get_running_loop()
        
        # 获取当前音量
        current_volume = await loop.run_in_executor(None, player_manager.get_volume)
        
        return jsonify({
            "status": "success",
            "volume": current_volume
        }), 200
class SetVolumeView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        """
        设置音量
        路由：/api/set_volume
        参数：volume - 音量值 (0-100)
        返回：设置结果
        """
        # 获取音量参数
        volume = request.args.get('volume', type=int)
        if volume is None:
            return jsonify({"status": "error", "message": "No volume provided"}), 400
            
        # 验证音量范围
        if not 0 <= volume <= 100:
            return jsonify({
                "status": "error", 
                "message": "Volume must be between 0 and 100"
            }), 400
        
        loop = asyncio.get_running_loop()
        
        # 设置音量
        success = await loop.run_in_executor(None, player_manager.set_volume, volume)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Volume set to {volume}",
                "volume": volume
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to set volume"
            }), 500
class AddToPlaylistView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        """
        添加项目到播放列表
        路由：/api/add_to_playlist
        参数：
            name - 项目名称（必需）
            path - 文件路径或网址（必需）
        返回：添加结果
        """
        # 获取参数
        name = request.args.get('name')
        path = request.args.get('path')
        
        if not name or not path:
            return jsonify({
                "status": "error", 
                "message": "Both name and path parameters are required"
            }), 400
        
        loop = asyncio.get_running_loop()
        
        # 调用播放列表添加方法
        result = await loop.run_in_executor(None, player_manager.add_to_playlist, name, path)
        
        return jsonify(result), 200 if result["status"] == "success" else 400

class RemoveFromPlaylistView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        """
        从播放列表中删除项目
        路由：/api/remove_from_playlist
        参数：
            id - 项目ID（可选，与name二选一）
            name - 项目名称（可选，与id二选一）
        返回：删除结果
        """
        # 获取参数
        item_id = request.args.get('id', type=int)
        name = request.args.get('name')
        
        if item_id is None and not name:
            return jsonify({
                "status": "error", 
                "message": "Either id or name parameter is required"
            }), 400
        
        # 确定使用哪个标识符
        identifier = item_id if item_id is not None else name
        
        loop = asyncio.get_running_loop()
        
        # 调用播放列表删除方法
        result = await loop.run_in_executor(None, player_manager.remove_from_playlist, identifier)
        
        return jsonify(result), 200 if result["status"] == "success" else 400
class GetPlaylistView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        """
        获取播放列表
        路由：/api/playlist
        返回：播放列表内容
        """
        loop = asyncio.get_running_loop()
        
        # 调用播放列表获取方法
        playlist = await loop.run_in_executor(None, player_manager.get_playlist)
        
        return jsonify({
            "status": "success",
            "playlist": playlist,
            "count": len(playlist)
        }), 200
class ClearPlaylistView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        """
        清空播放列表
        路由：/api/clear_playlist
        返回：清空结果
        """
        loop = asyncio.get_running_loop()
        
        # 调用播放列表清空方法
        result = await loop.run_in_executor(None, player_manager.clear_playlist)
        
        return jsonify(result), 200
class SearchView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def post(self):
        """搜索文件"""
        data = await request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "请求数据格式错误"}), 400
        
        # 获取搜索关键词
        keyword = data.get('keyword', '').strip()
        if not keyword:
            return jsonify({"status": "error", "message": "搜索关键词不能为空"}), 400

        # 检查是否启用正则搜索
        use_regex = data.get('re', False)

        # 检查索引是否已构建
        if not file_indexer._trie:
            return jsonify({"status": "error", "message": "搜索索引尚未构建"}), 400

        try:
            # 根据re参数选择搜索方法
            if use_regex:
                print("输入的正则表达式:",keyword)
                matched_files = await file_indexer.regex_search(keyword)
            else:
                matched_files = await file_indexer.search(keyword)
            
            # 返回搜索结果
            return jsonify({
                "status": "success",
                "keyword": keyword,
                "match_count": len(matched_files),
                "files": matched_files,
                "search_type": "regex" if use_regex else "normal"
            }), 200
            
        except Exception as e:
            player_logger.error(f"搜索失败: {str(e)}")
            return jsonify({"status": "error", "message": f"搜索失败: {str(e)}"}), 500
class SetIndexView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        """
        设置搜索索引路径
        路由：/api/set_index
        参数：
            path - 要索引的目录路径
        """
        # 获取路径参数
        path = request.args.get('path', type=str)
        if not path:
            return jsonify({"status": "error", "message": "路径参数不能为空"}), 400

        # 检查路径是否存在
        if not os.path.exists(path):
            return jsonify({"status": "error", "message": f"路径不存在: {path}"}), 400

        # 检查路径是否为目录
        if not os.path.isdir(path):
            return jsonify({"status": "error", "message": f"路径不是目录: {path}"}), 400

        try:
            # 使用单例索引器设置索引路径并构建索引
            file_indexer.set_root(path)
            await file_indexer.count_files()
            await file_indexer.build_trie()
            
            # 返回成功结果
            return jsonify({
                "status": "success",
                "message": f"索引路径设置成功: {path}",
                "indexed_path": path,
                "file_count": len(file_indexer._trie) if file_indexer._trie else 0
            }), 200
            
        except Exception as e:
            player_logger.error(f"设置索引路径失败: {str(e)}")
            return jsonify({"status": "error", "message": f"设置索引路径失败: {str(e)}"}), 500
class RestartView(MethodView):
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        """
        重启整个音频播放系统
        路由：/api/RESTART
        返回：重启状态
        """
        player_logger.info("[Restart] 收到重启请求")
        
        try:
            # 在重启前异步执行播放器清理工作，设置10秒超时
            player_logger.info("[Restart] 开始异步执行播放器清理工作，超时时间10秒...")
            
            # 异步调用播放器清理函数，设置10秒超时
            try:
                loop = asyncio.get_running_loop()
                # 使用run_in_executor在后台线程中执行清理工作
                await asyncio.wait_for(
                    loop.run_in_executor(None, player_manager._cleanup_player),
                    timeout=10.0
                )
                player_logger.info("[Restart] 播放器清理工作完成")
            except asyncio.TimeoutError:
                player_logger.warning("[Restart] 播放器清理工作超时（10秒），继续执行重启流程")
            except Exception as e:
                player_logger.error(f"[Restart] 播放器清理工作发生错误: {e}")
                player_logger.warning("[Restart] 清理工作出错，继续执行重启流程")
            
            # 获取当前工作目录和Python解释器路径（使用绝对路径）
            project_dir = os.path.dirname(os.path.abspath(__file__))
            project_dir = os.path.dirname(os.path.dirname(project_dir))  # 回到项目根目录
            python_exe = os.path.abspath(sys.executable)
            restart_script = os.path.join(project_dir, "restart_manager.py")
            
            player_logger.info(f"[Restart] 项目目录: {project_dir}")
            player_logger.info(f"[Restart] Python路径: {python_exe}")
            player_logger.info(f"[Restart] 重启脚本: {restart_script}")
            
            # 检查重启脚本是否存在
            if not os.path.exists(restart_script):
                player_logger.error("[Restart] 重启脚本不存在")
                return jsonify({
                    "status": "error",
                    "message": "重启脚本不存在，请检查文件路径"
                }), 500
            
            # 启动独立的重启管理器进程
            import subprocess
            
            # 在Windows上使用CREATE_NEW_PROCESS_GROUP标志
            if os.name == 'nt':
                process = subprocess.Popen(
                    [python_exe, restart_script],  # 使用绝对路径
                    cwd=project_dir,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                process = subprocess.Popen(
                    [python_exe, restart_script],  # 使用绝对路径
                    cwd=project_dir
                )
            
            player_logger.info(f"[Restart] 重启管理器已启动，PID: {process.pid}")
            
            # 立即返回响应，不等待重启完成
            return jsonify({
                "status": "success",
                "message": "重启进程已启动",
                "restart_pid": process.pid,
                "note": "系统将在后台进行优雅重启，请稍后重新访问服务"
            }), 200
            
        except Exception as e:
            player_logger.error(f"[Restart] 重启失败: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"重启失败: {str(e)}"
            }), 500

    @PlayerErrorHandler.create_error_handler
    async def get(self):
        """
        获取屏幕直播流
        路由：/api/GET_LIVE
        返回：获取屏幕直播流
        """
        return "获取屏幕直播流"
