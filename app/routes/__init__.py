# app/routes/__init__.py
"""
app.routes 模块
统一管理 player_bp 和路由注册
"""

from quart import Blueprint

# 创建主 Blueprint（唯一实例！）
player_bp = Blueprint('player', __name__, url_prefix='')

# 导入视图类（延迟导入，避免循环依赖）
from .player import (
    IndexView, ListDirectoryView, SetDirectoryView, SetFileView,
    PlayView, PauseView, StopView,
    NextTrackView, PrevTrackView, SetPositionView,
    LyricsView, AlbumCoverView, AudioMetadataView, ProgressView,
    SetDeviceView, DevicesView, OnlineUsersView, SetPlayModeView,
    SettingsView, RestorePlaybackView, SavePlaybackView, UpdatePositionView,
    VolumeView, SetVolumeView,
    AddToPlaylistView, RemoveFromPlaylistView, GetPlaylistView, ClearPlaylistView,
    SearchView, SetIndexView,
    # 重启路由
    RestartView,
    # 播放历史记录路由
    PlaybackHistoryView,
    # 切换音频轨道路由
    SetAudioTrackView,
    # AI音频分离路由
    AIseparatesaudioView,
)
from .crawlers.douyin import AddPlayPistDouyinView
from .crawlers.Netease import SearchLyricsView, SelectLyricsView, SaveLyricsView
# ================== 统一注册路由 ==================
def _register_routes():
    player_bp.add_url_rule("/", view_func=IndexView.as_view('index'))
    #播放控制类
    player_bp.add_url_rule("/api/play", view_func=PlayView.as_view('play'))
    player_bp.add_url_rule("/api/pause", view_func=PauseView.as_view('pause'))
    player_bp.add_url_rule("/api/stop", view_func=StopView.as_view('stop'))
    player_bp.add_url_rule("/api/next", view_func=NextTrackView.as_view('next'))
    player_bp.add_url_rule("/api/prev", view_func=PrevTrackView.as_view('prev'))
    player_bp.add_url_rule("/api/set_position", view_func=SetPositionView.as_view('set_position'))
    player_bp.add_url_rule("/api/set_play_mode", view_func=SetPlayModeView.as_view('set_play_mode'))
    #播放查询类
    player_bp.add_url_rule("/api/current_lyrics", view_func=LyricsView.as_view('current_lyrics'))
    player_bp.add_url_rule("/api/full_lyrics", view_func=LyricsView.as_view('full_lyrics'))
    player_bp.add_url_rule("/api/album_cover", view_func=AlbumCoverView.as_view('album_cover'))
    player_bp.add_url_rule("/api/audio_metadata", view_func=AudioMetadataView.as_view('audio_metadata'))
    player_bp.add_url_rule("/api/progress", view_func=ProgressView.as_view('progress'))
    player_bp.add_url_rule("/api/volume", view_func=VolumeView.as_view('volume'))
    player_bp.add_url_rule("/api/set_volume", view_func=SetVolumeView.as_view('set_volume'))

    #文件操作类
    player_bp.add_url_rule("/api/list_directory", view_func=ListDirectoryView.as_view('list_directory'))
    player_bp.add_url_rule("/api/set_directory", view_func=SetDirectoryView.as_view('set_directory'))
    player_bp.add_url_rule("/api/set_file", view_func=SetFileView.as_view('set_file'))
    player_bp.add_url_rule("/api/set_device", view_func=SetDeviceView.as_view('set_device'))
    player_bp.add_url_rule("/api/devices", view_func=DevicesView.as_view('devices'))
    #用户类
    player_bp.add_url_rule("/api/online_users", view_func=OnlineUsersView.as_view('online_users'))
    # 设置相关类
    player_bp.add_url_rule("/api/settings", view_func=SettingsView.as_view('settings'))
    player_bp.add_url_rule("/api/restore_playback", view_func=RestorePlaybackView.as_view('restore_playback'))
    player_bp.add_url_rule("/api/save_playback", view_func=SavePlaybackView.as_view('save_playback'))
    player_bp.add_url_rule("/api/update_position", view_func=UpdatePositionView.as_view('update_position'))
    # 播放列表管理路由
    player_bp.add_url_rule("/api/add_to_playlist", view_func=AddToPlaylistView.as_view('add_to_playlist'))
    player_bp.add_url_rule("/api/remove_from_playlist", view_func=RemoveFromPlaylistView.as_view('remove_from_playlist'))
    player_bp.add_url_rule("/api/playlist", view_func=GetPlaylistView.as_view('playlist'))
    player_bp.add_url_rule("/api/clear_playlist", view_func=ClearPlaylistView.as_view('clear_playlist'))
    # 抖音音频添加路由
    player_bp.add_url_rule("/api/add_play_list_douyin", view_func=AddPlayPistDouyinView.as_view('add_play_list_douyin'))
    # 搜索路由
    player_bp.add_url_rule("/api/search", view_func=SearchView.as_view('search'))
    # 设置索引路由
    player_bp.add_url_rule("/api/set_index", view_func=SetIndexView.as_view('set_index'))
    # 重启路由
    player_bp.add_url_rule("/api/restart", view_func=RestartView.as_view('restart'))
    # 播放历史记录路由
    player_bp.add_url_rule("/api/playback_history", view_func=PlaybackHistoryView.as_view('playback_history'))
    # 网易云歌词路由
    player_bp.add_url_rule("/api/netease/search_lyrics", view_func=SearchLyricsView.as_view('netease_search_lyrics'))
    player_bp.add_url_rule("/api/netease/select_lyrics", view_func=SelectLyricsView.as_view('netease_select_lyrics'))
    player_bp.add_url_rule("/api/netease/save_lyrics", view_func=SaveLyricsView.as_view('netease_save_lyrics'))
    # 切换音频轨道路由
    player_bp.add_url_rule("/api/set_audio_track", view_func=SetAudioTrackView.as_view('set_audio_track'))
    # AI音频分离路由
    player_bp.add_url_rule("/api/ai_separate_audio", view_func=AIseparatesaudioView.as_view('ai_separate_audio'))
_register_routes()

__all__ = ['player_bp']