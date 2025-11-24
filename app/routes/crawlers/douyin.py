import re
import os
import asyncio
import aiohttp
from datetime import datetime
from quart import jsonify, request
from quart.views import MethodView
from app.core.player import player_manager
from app.core.error_handler import PlayerErrorHandler

class AddPlayPistDouyinView(MethodView):
    def _convert_to_mp3(self, input_path, output_path):
        """
        使用ffmpeg将视频文件转换为mp3
        """
        import subprocess
        
        try:
            # 构建ffmpeg命令
            cmd = ['ffmpeg', '-i', input_path, output_path]
            
            # 执行ffmpeg转换
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # 检查转换是否成功
            if not os.path.exists(output_path):
                raise Exception("转换后的mp3文件不存在")
                
        except subprocess.CalledProcessError as e:
            raise Exception(f"ffmpeg执行失败: {e.stderr}")
        except Exception as e:
            raise Exception(f"转换过程中发生错误: {str(e)}")
    
    @PlayerErrorHandler.create_error_handler
    async def post(self):
        from app.core.crawlers import douyin
        """
        添加抖音音频到播放列表
        路由：/api/add_play_list_douyin
        参数：
            url - 抖音音频URL（必需）
            only_audio - 是否只提取音频，转换为MP3（可选，默认为true）
        返回：添加结果
        """
        # 获取参数
        data = await request.get_json()
        if not data:
            return jsonify({
                "status": "error", 
                "message": "No JSON data provided"
            }), 400
        
        url = data.get('url')
        only_audio = data.get('only_audio', False)  # 默认为true，转换为MP3
        
        if not url:
            return jsonify({
                "status": "error", 
                "message": "URL parameter is required"
            }), 400
        
        # 从输入文本中提取抖音URL
        douyin_url_pattern = r'https?://(?:v\.)?douyin\.com/\S+'
        match = re.search(douyin_url_pattern, url)
        
        if match:
            url = match.group(0)
        else:
            return jsonify({
                "status": "error",
                "message": "未找到有效的抖音URL，请确保输入包含正确的抖音链接"
            }), 400
        
        loop = asyncio.get_running_loop()
        
        # 异步解析抖音内容
        temp_path = None
        try:
            # 创建解析器实例并设置URL
            parser = douyin.DouyinParser()
            parser.set_url(url)
            
            # 异步解析URL
            await parser.parse()
            
            # 获取解析结果
            title = parser.get_title()
            video_url = parser.get_video()
            
            if not video_url:
                return jsonify({
                    "status": "error",
                    "message": "无法获取视频地址，请检查URL是否正确"
                }), 400
            
            # 处理标题，使其适合用作文件名
            if title:
                # 去除路径不可用字符，将空格替换为下划线，限制长度为50字符
                # 移除路径不安全的字符：/ \ : * ? " < > |
                safe_title = re.sub(r'[\\/:*?"<>|]', '', title)
                # 将空格替换为下划线
                safe_title = re.sub(r'\s+', '_', safe_title)
                # 限制长度为50字符
                safe_title = safe_title[:50]
                # 如果处理后为空，使用默认名称
                if not safe_title:
                    safe_title = "抖音视频"
            else:
                safe_title = "抖音视频"
            
            # 创建项目临时目录
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            temp_dir = os.path.join(project_root, "downloads/douyin")
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 使用处理后的标题作为文件名
            temp_filename = f"{safe_title}_{timestamp}.mp4"
            temp_path = os.path.join(temp_dir, temp_filename)
            
            # 异步下载文件
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url, timeout=30) as response:
                    if response.status == 200:
                        with open(temp_path, 'wb') as f:
                            while True:
                                chunk = await response.content.read(8192)
                                if not chunk:
                                    break
                                f.write(chunk)
                    else:
                        return jsonify({
                            "status": "error",
                            "message": f"下载失败，HTTP状态码: {response.status}"
                        }), 400
            
            # 根据only_audio参数决定是否转换为MP3
            if only_audio:
                # 使用ffmpeg将下载的mp4转换为mp3
                mp3_filename = f"{safe_title}_{timestamp}.mp3"
                mp3_path = os.path.join(temp_dir, mp3_filename)
                
                try:
                    # 执行ffmpeg转换
                    await loop.run_in_executor(None, self._convert_to_mp3, temp_path, mp3_path)
                    
                    # 删除原始mp4文件以节省空间
                    os.remove(temp_path)
                    
                    # 使用转换后的mp3文件路径
                    final_path = mp3_path
                except Exception as e:
                    # 如果转换失败，清理文件并返回错误
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    if os.path.exists(mp3_path):
                        os.remove(mp3_path)
                    return jsonify({
                        "status": "error",
                        "message": f"ffmpeg转换失败: {str(e)}"
                    }), 500
            else:
                # 直接使用下载的mp4文件路径
                final_path = temp_path
            
            # 调用播放列表添加方法
            result = await loop.run_in_executor(None, player_manager.add_to_playlist, title or "抖音音频", final_path)
            
        except Exception as e:
            # 清理临时文件（如果存在）
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            
            return jsonify({
                "status": "error",
                "message": f"处理失败: {str(e)}"
            }), 500
        
        return jsonify(result), 200 if result["status"] == "success" else 400