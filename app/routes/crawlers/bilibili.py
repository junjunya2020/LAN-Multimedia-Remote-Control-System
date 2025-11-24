# app/routes/crawlers/bilibili.py
import os
import re
import asyncio
from datetime import datetime
from quart import jsonify, request
from quart.views import MethodView
from app.core.crawlers.bilibili import BiliLogin, BiliVideoResolver, ffmpeg_stream_merge
from app.core.player import player_manager
from app.core.error_handler import PlayerErrorHandler

def extract_bvid_from_url(url):
    """
    从 Bilibili URL 中提取 BV 号
    支持的 URL 格式：
    - https://www.bilibili.com/video/BV1nqyMBKEqv/
    - https://www.bilibili.com/video/BV1nqyMBKEqv?p=1
    - https://b23.tv/BV1nqyMBKEqv
    - https://m.bilibili.com/video/BV1nqyMBKEqv
    """
    # 匹配 BV 号的正则表达式
    bv_pattern = r'BV[a-zA-Z0-9]{10}'
    
    # 从 URL 中查找 BV 号
    match = re.search(bv_pattern, url)
    if match:
        return match.group(0)
    return None

class AddPlayListBilibiliView(MethodView):
    """
    Bilibili 视频下载并添加到播放列表
    参考 douyin.py 的实现方式，简化API接口
    """
    
    @PlayerErrorHandler.create_error_handler
    async def get(self):
        """
        下载 Bilibili 视频并添加到播放列表
        GET /api/add_play_list_bilibili?bvid=BV1nqyMBKEqv
        或 GET /api/add_play_list_bilibili?url=https://www.bilibili.com/video/BV1nqyMBKEqv/
        
        参数：
            bvid - Bilibili 视频BV号（与url参数二选一）
            url - Bilibili 视频URL（与bvid参数二选一）
            page - 视频分P（可选，默认为0）
        """
        try:
            # 获取参数
            bvid = request.args.get('bvid')
            url = request.args.get('url')
            page = int(request.args.get('page', 0))
            
            # 检查参数
            if not bvid and not url:
                return jsonify({
                    "status": "error", 
                    "message": "缺少参数：请提供 bvid 或 url 参数"
                }), 400
            
            # 如果提供了 URL，从中提取 BV 号
            if url:
                extracted_bvid = extract_bvid_from_url(url)
                if not extracted_bvid:
                    return jsonify({
                        "status": "error",
                        "message": "无法从 URL 中提取有效的 BV 号"
                    }), 400
                bvid = extracted_bvid
            
            # 验证 BV 号格式
            if not bvid.startswith('BV'):
                return jsonify({
                    "status": "error",
                    "message": "无效的 BV 号格式"
                }), 400
            
            loop = asyncio.get_running_loop()
            
            # 创建登录管理器并加载凭据
            login_manager = BiliLogin()
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            cred_path = os.path.join(project_root, "bili_cred.json")
            login_manager.set_credential_path(cred_path)
            
            # 尝试加载凭据
            if not login_manager.load():
                return jsonify({
                    "status": "error",
                    "message": "请先登录 Bilibili，调用 /api/bilibili/login 接口"
                }), 401
            
            credential = login_manager.get_credential()
            
            # 创建解析器
            resolver = BiliVideoResolver()
            resolver.set_credential(credential)
            resolver.set_bvid(bvid, page)
            
            # 解析视频
            resolver.parse()
            streams = resolver.get_streams()
            
            # 获取视频信息
            video_info = resolver.info
            title = video_info.get('title', f"Bilibili {bvid}")
            
            # 处理标题，使其适合用作文件名
            if title:
                # 去除路径不可用字符，将空格替换为下划线，限制长度为50字符
                safe_title = re.sub(r'[\\/:*?"<>|]', '', title)
                safe_title = re.sub(r'\s+', '_', safe_title)
                safe_title = safe_title[:50]
                # 如果处理后为空，使用默认名称
                if not safe_title:
                    safe_title = "Bilibili视频"
            else:
                safe_title = "Bilibili视频"
            
            # 创建下载目录
            download_dir = os.path.join(project_root, "downloads", "bilibili")
            os.makedirs(download_dir, exist_ok=True)
            
            # 生成文件名（使用视频标题）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_title}_{timestamp}.mp4"
            output_path = os.path.join(download_dir, filename)
            
            # 异步下载视频
            async def download_task():
                return await ffmpeg_stream_merge(
                    video_url=streams.video.url,
                    audio_url=streams.audio.url if streams.audio else None,
                    output_path=output_path
                )
            
            # 执行下载
            final_path = await download_task()
            
            # 添加到播放列表
            if os.path.exists(final_path):
                result = await loop.run_in_executor(None, player_manager.add_to_playlist, title, final_path)
            else:
                return jsonify({
                    "status": "error",
                    "message": "下载完成但文件不存在"
                }), 500
            
            return jsonify({
                "status": "success",
                "message": "下载完成并已添加到播放列表",
                "data": {
                    "bvid": bvid,
                    "page": page,
                    "title": title,
                    "file_path": final_path,
                    "file_size": os.path.getsize(final_path) if os.path.exists(final_path) else 0,
                    "playlist_result": result
                }
            }), 200
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"处理失败: {str(e)}"
            }), 500