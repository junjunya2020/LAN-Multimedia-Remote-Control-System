# app/routes/crawlers/Netease.py
import os
import json
import tempfile
from quart import jsonify, request
from quart.views import MethodView
from app.core.crawlers.NetEase import NetEaseApiSearch, NetEaseApiLyric
from app.core.player import player_manager

# 临时存储歌词数据（用于前端选择后保存）
_temp_lyrics_data = {}

class SearchLyricsView(MethodView):
    """搜索歌词路由 - 传入音乐名称，返回歌曲列表"""
    
    async def get(self):
        """
        搜索歌词
        GET /api/netease/search_lyrics?keyword=音乐名称
        """
        keyword = request.args.get('keyword', '')
        if not keyword:
            return jsonify({
                "status": "error", 
                "message": "请输入搜索关键词"
            }), 400
        
        try:
            # 创建搜索实例
            search_api = NetEaseApiSearch()
            search_api.set_search_query(keyword)
            
            # 执行搜索
            songs = await search_api.start_search()
            
            if not songs:
                return jsonify({
                    "status": "success",
                    "message": "未找到相关歌曲",
                    "data": []
                }), 200
            
            # 获取格式化后的搜索结果
            search_data = search_api.get_search_data()
            
            return jsonify({
                "status": "success",
                "message": f"找到 {len(search_data)} 首相关歌曲",
                "data": search_data
            }), 200
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"搜索失败: {str(e)}"
            }), 500

class SelectLyricsView(MethodView):
    """选择歌词路由 - 传入歌曲ID，返回歌词内容"""
    
    async def post(self):
        """
        选择歌词
        POST /api/netease/select_lyrics
        {
            "song_id": 123456
        }
        """
        try:
            data = await request.get_json()
            if not data or 'song_id' not in data:
                return jsonify({
                    "status": "error",
                    "message": "缺少歌曲ID参数"
                }), 400
            
            song_id = data['song_id']
            
            # 创建歌词API实例
            lyric_api = NetEaseApiLyric()
            lyric_api.set_song_id_for_lyrics(song_id)
            
            # 获取歌词
            lyric_result = await lyric_api.start_lyrics_search()
            
            if lyric_result["status"] != "success":
                return jsonify({
                    "status": "error",
                    "message": "获取歌词失败"
                }), 500
            
            # 生成临时ID用于后续保存
            import uuid
            temp_id = str(uuid.uuid4())
            
            # 存储歌词数据到临时存储
            _temp_lyrics_data[temp_id] = {
                "song_id": song_id,
                "lyric": lyric_result["lyric"],
                "translate": lyric_result["translate"],
                "timestamp": json.dumps({"song_id": song_id})
            }
            
            # 清理过期的临时数据（保留最近10条）
            if len(_temp_lyrics_data) > 10:
                # 删除最旧的数据
                oldest_key = list(_temp_lyrics_data.keys())[0]
                del _temp_lyrics_data[oldest_key]
            
            return jsonify({
                "status": "success",
                "message": "歌词获取成功",
                "data": {
                    "lyric": lyric_result["lyric"],
                    "translate": lyric_result["translate"],
                    "temp_id": temp_id
                }
            }), 200
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"选择歌词失败: {str(e)}"
            }), 500

class SaveLyricsView(MethodView):
    """保存歌词路由 - 保存歌词到.lrc文件并加载"""
    
    async def post(self):
        """
        保存歌词
        POST /api/netease/save_lyrics
        {
            "temp_id": "uuid-string",
            "file_path": "/path/to/audio/file.mp3"
        }
        """
        try:
            data = await request.get_json()
            if not data or 'temp_id' not in data or 'file_path' not in data:
                return jsonify({
                    "status": "error",
                    "message": "缺少必要参数"
                }), 400
            
            temp_id = data['temp_id']
            file_path = data['file_path']
            
            # 验证文件路径
            if not os.path.exists(file_path):
                return jsonify({
                    "status": "error",
                    "message": "音频文件不存在"
                }), 404
            
            # 从临时存储获取歌词数据
            if temp_id not in _temp_lyrics_data:
                return jsonify({
                    "status": "error",
                    "message": "临时歌词数据已过期或不存在"
                }), 400
            
            lyric_data = _temp_lyrics_data[temp_id]
            
            # 生成.lrc文件路径（与音频文件同名）
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            directory = os.path.dirname(file_path)
            lrc_path = os.path.join(directory, f"{base_name}.lrc")
            
            # 保存歌词到.lrc文件
            try:
                # 合并歌词和翻译（如果有的话）
                lyric_content = lyric_data["lyric"]
                if lyric_data["translate"]:
                    lyric_content += "\n\n" + lyric_data["translate"]
                
                with open(lrc_path, 'w', encoding='utf-8') as f:
                    f.write(lyric_content)
                
                print(f"[SaveLyrics] 歌词已保存到: {lrc_path}")
                
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": f"保存歌词文件失败: {str(e)}"
                }), 500
            
            # 如果当前播放的文件与保存歌词的文件相同，则重新加载歌词
            if player_manager.current_file == file_path:
                try:
                    # 调用load_lyrics方法加载歌词
                    player_manager.load_lyrics()
                    print(f"[SaveLyrics] 歌词已重新加载")
                except Exception as e:
                    print(f"[SaveLyrics] 重新加载歌词失败: {str(e)}")
            
            # 清理临时数据
            del _temp_lyrics_data[temp_id]
            
            return jsonify({
                "status": "success",
                "message": "歌词保存成功",
                "data": {
                    "lrc_path": lrc_path,
                    "file_path": file_path
                }
            }), 200
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"保存歌词失败: {str(e)}"
            }), 500

# 导出视图类
__all__ = ['SearchLyricsView', 'SelectLyricsView', 'SaveLyricsView']