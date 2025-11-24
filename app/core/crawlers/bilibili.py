# bili_login.py  （终极工业级版本）
import asyncio
import re
import json
import os
from bilibili_api import Credential, sync, video
from typing import Optional, Literal

class BiliLogin:
    """
    Bilibili 终极登录管理器（面向对象版）

    使用流程：
        1. login_manager = BiliLogin()                     # 创建实例
        2. login_manager.set_credential_path("my_cred.json")  # 设置保存路径（可不设置，默认 credential.json）
        3. login_manager.load()          # 方法①：优先尝试加载本地凭据（推荐）
           或
           login_manager.login_by_cookie(cookie_str)  # 方法②：粘贴 Cookie 登录
    """

    def __init__(self, credential_path: str = "credential.json"):
        self.credential_path = credential_path
        self.credential: Optional[Credential] = None

    def set_credential_path(self, path: str) -> None:
        """设置凭据保存路径（支持自定义文件名和目录）"""
        self.credential_path = path
        print(f"凭据保存路径已设置为：{os.path.abspath(path)}")

    def _extract(self, cookie_str: str, key: str) -> Optional[str]:
        match = re.search(rf"{key}=([^;]+)", cookie_str)
        return match.group(1) if match else None

    def _refresh_if_needed(self, credential: Credential) -> Credential:
        try:
            if sync(credential.check_refresh()):
                print("检测到凭据需要刷新，正在自动刷新...")
                sync(credential.refresh())
                print("刷新成功！")
            else:
                print("凭据正常，无需刷新")
        except Exception as e:
            print(f"刷新失败（可能已严重过期）：{e}")
        return credential

    def save(self) -> None:
        """手动保存当前凭据到文件（最稳定方式）"""
        if not self.credential:
            print("未登录，无法保存")
            return

        data = {
            "sessdata": self.credential.sessdata,
            "bili_jct": self.credential.bili_jct,
            "buvid3": self.credential.buvid3,
            "dedeuserid": self.credential.dedeuserid,
            "ac_time_value": self.credential.ac_time_value
        }
        os.makedirs(os.path.dirname(self.credential_path) or '.', exist_ok=True)
        with open(self.credential_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"凭据已成功保存到：{os.path.abspath(self.credential_path)}")

    def load(self) -> bool:
        """
        方法①：尝试从本地文件加载凭据
        返回：True=登录成功 / False=文件不存在或无效
        """
        if not os.path.exists(self.credential_path):
            print(f"未找到凭据文件：{self.credential_path}")
            print("请使用 login_by_cookie() 登录并保存")
            return False

        try:
            with open(self.credential_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.credential = Credential(
                sessdata=data["sessdata"],
                bili_jct=data["bili_jct"],
                buvid3=data.get("buvid3"),
                dedeuserid=data.get("dedeuserid"),
                ac_time_value=data.get("ac_time_value")
            )

            self.credential = self._refresh_if_needed(self.credential)
            print(f"已成功从 {self.credential_path} 加载并登录！")
            self._print_info()
            return True

        except Exception as e:
            print(f"加载凭据失败：{e}")
            return False

    def login_by_cookie(self, cookie_str: str) -> bool:
        """
        方法②：通过粘贴完整 Cookie 登录
        返回：True=登录成功 / False=失败
        """
        print("正在解析 Cookie 并登录...")
        sessdata = self._extract(cookie_str, "SESSDATA")
        bili_jct = self._extract(cookie_str, "bili_jct")
        buvid3 = self._extract(cookie_str, "buvid3")
        dedeuserid = self._extract(cookie_str, "DedeUserID")

        if not sessdata or not bili_jct:
            print("错误：Cookie 中未找到 SESSDATA 或 bili_jct")
            return False

        self.credential = Credential(
            sessdata=sessdata,
            bili_jct=bili_jct,
            buvid3=buvid3 or None,
            dedeuserid=dedeuserid or None
        )

        self.credential = self._refresh_if_needed(self.credential)
        print("Cookie 登录成功！")
        self._print_info()

        # 自动保存
        save = input("是否立即保存到本地文件？(y/n，默认y) ").strip().lower()
        if save in ["", "y", "yes", "1"]:
            self.save()

        return True

    def _print_info(self):
        if not self.credential:
            return
        c = self.credential.get_cookies()
        print("=" * 50)
        print(f"登录账号   : UID {c.get('DedeUserID', '未知')}")
        try:
            from bilibili_api.user import get_self_info
            info = sync(get_self_info(self.credential))
            print(f"用户名     : {info['name']}")
            print(f"等级       : Lv.{info['level_info']['current_level']}")
        except:
            print("用户名     : 查询失败（轻微风控）")
        print(f"SESSDATA   : {c.get('SESSDATA', '')[:40]}...")
        print(f"bili_jct   : {c.get('bili_jct')}")
        print("=" * 50)

    def get_credential(self) -> Optional[Credential]:
        """获取当前登录的 Credential 对象"""
        return self.credential

class VideoStreamInfo:
    """封装一条视频/音频流的信息，方便外部调用"""
    def __init__(self, stream_obj):
        self.stream = stream_obj
        self.url = stream_obj.url
        self.size = getattr(stream_obj, 'size', 0)  # 字节数
        self.size_mb = round(self.size / 1024 / 1024, 2) if self.size else 0
        self.quality = getattr(stream_obj, 'quality_description', '未知画质')
        self.codecs = getattr(stream_obj, 'codecs', '未知编码')
        self.type = stream_obj.__class__.__name__  # VideoStream / AudioStream / FLVStream

    def __str__(self):
        return f"{self.type} | {self.quality} | {self.size_mb}MB | {self.codecs}"

class BiliVideoResolver:
    """
    B站视频下载链接解析器（极致优雅版）

    使用方式：
        resolver = BiliVideoResolver()
        resolver.set_credential(credential)
        resolver.set_bvid("BV1nqyMBKEqv")
        resolver.parse()
        streams = resolver.get_streams()

        print("视频流:", streams.video.url)
        print("音频流:", streams.audio.url if streams.audio else "无独立音频流")
    """

    def __init__(self):
        self.info = None
        self.credential: Optional[Credential] = None
        self.bvid: Optional[str] = None
        self.detecter = None
        self.is_flv = False
        self.video_stream: Optional[VideoStreamInfo] = None
        self.audio_stream: Optional[VideoStreamInfo] = None

    def set_credential(self, credential: Credential) -> None:
        """设置登录凭据（必须）"""
        self.credential = credential
        print("已设置登录凭据")

    def set_bvid(self, bvid: str, page: int = 0) -> None:
        """设置要解析的 BV 号和分P"""
        self.bvid = bvid
        self.page = page
        print(f"已设置视频：{bvid} 第 {page+1}P")

    def parse(self) -> None:
        """解析视频下载链接（核心方法）"""
        if not self.credential:
            raise ValueError("请先调用 set_credential() 设置凭据")
        if not self.bvid:
            raise ValueError("请先调用 set_bvid() 设置 BV 号")

        print(f"正在解析 {self.bvid} 的下载链接...")
        v = video.Video(bvid=self.bvid, credential=self.credential)

        self.info=sync(v.get_info())
        download_data = sync(v.get_download_url(self.page))

        self.detecter = video.VideoDownloadURLDataDetecter(download_data)
        self.is_flv = self.detecter.check_flv_mp4_stream()

        best = self.detecter.detect_best_streams()

        if self.is_flv:
            # FLV 单流（音视频已混合）
            self.video_stream = VideoStreamInfo(best[0])
            self.audio_stream = None
            print("检测到 FLV 单流（已混流）")
        else:
            # MP4 分离流
            self.video_stream = VideoStreamInfo(best[0])  # 视频流
            self.audio_stream = VideoStreamInfo(best[1])  # 音频流
            print("检测到 MP4 分离流（需混流）")

        print("解析完成！")

    def get_streams(self):
        """返回一个方便使用的流容器对象"""
        if not self.detecter:
            raise RuntimeError("请先调用 parse() 解析视频")

        class StreamsResult:
            def __init__(self, resolver):
                self.resolver = resolver
                self.video = resolver.video_stream
                self.audio = resolver.audio_stream
                self.is_flv = resolver.is_flv

            def __repr__(self):
                if self.is_flv:
                    return f"<FLV单流: {self.video}>"
                else:
                    return f"<视频: {self.video} | 音频: {self.audio}>"

        return StreamsResult(self)

async def ffmpeg_stream_merge(
    video_url: str,
    audio_url: Optional[str],
    output_path: str,
    *,
    ffmpeg_path: str = "ffmpeg",
    progress_callback=None
) -> str:
    """
    终极版：ffmpeg 直接从网络流混流（零临时文件！全程内存 + 管道）

    参数：
        video_url : 视频流 URL（必填）
        audio_url : 音频流 URL（None 表示 FLV 单流）
        output_path : 输出路径
        ffmpeg_path : ffmpeg 可执行文件路径
        progress_callback: 可选进度回调 (current_mb, total_mb)
    """
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    # 构建 ffmpeg 命令
    if audio_url:
        # MP4 分离流 → 双输入混流
        cmd = [
            ffmpeg_path, "-y", "-loglevel", "error",
            "-i", video_url,
            "-i", audio_url,
            "-c", "copy",
            output_path
        ]
        print("检测到 MP4 分离流 → 直接网络混流（无临时文件）")
    else:
        # FLV 单流 → 直接转封装
        cmd = [
            ffmpeg_path, "-y", "-loglevel", "error",
            "-i", video_url,
            "-c", "copy",
            "-movflags", "+faststart",
            output_path
        ]
        print("检测到 FLV 单流 → 直接网络转封装（无临时文件）")

    print(f"开始下载并混流 → {output_path}")
    print(f"ffmpeg 命令: {' '.join(cmd)}")

    # 创建子进程
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # 实时读取进度（可选，ffmpeg 输出到 stderr）
    if progress_callback:
        import re
        pattern = re.compile(r"size=\s*(\d+)kB\s+time=\d+:\d+:\d+\.\d+\s+bitrate=\s*(\d+\.\d+)kbits/s")

        async def read_progress():
            while True:
                line = await proc.stderr.readline()
                if not line:
                    break
                line = line.decode(errors='ignore')
                match = pattern.search(line)
                if match:
                    size_kb = int(match.group(1))
                    current_mb = size_kb / 1024
                    # 这里不准，但能看到进度在走
                    progress_callback(current_mb, None, "混流进行中")

        asyncio.create_task(read_progress())

    # 等待完成
    await proc.wait()

    if proc.returncode == 0:
        print(f"下载完成！文件保存在：{os.path.abspath(output_path)}")
        return output_path
    else:
        raise RuntimeError("ffmpeg 执行失败，可能是网络问题或链接失效")

if __name__ == "__main__":
    # 1. 登录
    login = BiliLogin()
    login.set_credential_path("../../../bili_cred.json")
    login.load()
    cred = login.get_credential()

    # 2. 创建解析器
    resolver = BiliVideoResolver()
    resolver.set_credential(cred)
    resolver.set_bvid("BV1nqyMBKEqv")  # 换你想解析的视频

    # 3. 解析
    resolver.parse()

    # 4. 获取流对象
    streams = resolver.get_streams()

    print(resolver.info)
#输出示例{'bvid': 'BV1nqyMBKEqv', 'aid': 115585740512849, 'videos': 1, 'tid': 27, 'tid_v2': 2023, 'tname': '综合', 'tname_v2': 'AI音乐', 'copyright': 1, 'pic': 'http://i1.hdslb.com/bfs/archive/b6ab1bbbcaafd31e4e097d4b73c768324e5172f0.jpg', 'title': '《大木叶是我的故乡》', 'pubdate': 1763718000, 'ctime': 1763698590, 'desc': '·', 'desc_v2': [{'raw_text': '·', 'type': 1, 'biz_id': 0}], 'state': 0, 'duration': 190, 'mission_id': 4051039, 'rights': {'bp': 0, 'elec': 0, 'download': 1, 'movie': 0, 'pay': 0, 'hd5': 1, 'no_reprint': 1, 'autoplay': 1, 'ugc_pay': 0, 'is_cooperation': 0, 'ugc_pay_preview': 0, 'no_background': 0, 'clean_mode': 0, 'is_stein_gate': 0, 'is_360': 0, 'no_share': 0, 'arc_pay': 0, 'free_watch': 0}, 'owner': {'mid': 448039667, 'name': '冷淡熊', 'face': 'https://i2.hdslb.com/bfs/face/afe334d673fda9bd834923aa0a67f207120e5eee.jpg'}, 'stat': {'aid': 115585740512849, 'view': 1342518, 'danmaku': 1556, 'reply': 2393, 'favorite': 24386, 'coin': 32781, 'share': 18843, 'now_rank': 0, 'his_rank': 38, 'like': 85892, 'dislike': 0, 'evaluation': '', 'vt': 0}, 'argue_info': {'argue_msg': '作者声明：该视频使用人工智能合成技术', 'argue_type': 0, 'argue_link': ''}, 'dynamic': '', 'cid': 34150944461, 'dimension': {'width': 1920, 'height': 1080, 'rotate': 0}, 'premiere': None, 'teenage_mode': 1, 'is_chargeable_season': False, 'is_story': False, 'is_upower_exclusive': False, 'is_upower_play': False, 'is_upower_preview': False, 'enable_vt': 0, 'vt_display': '', 'is_upower_exclusive_with_qa': False, 'no_cache': False, 'pages': [{'cid': 34150944461, 'page': 1, 'from': 'vupload', 'part': '《大木叶是我的故乡》', 'duration': 190, 'vid': '', 'weblink': '', 'dimension': {'width': 1920, 'height': 1080, 'rotate': 0}, 'first_frame': 'http://i1.hdslb.com/bfs/storyff/_00002lmr0k7g07uhi22wuer5o14g6ib_firsti.jpg', 'ctime': 1763698590}], 'subtitle': {'allow_submit': False, 'list': []}, 'label': {'type': 1}, 'is_season_display': False, 'user_garb': {'url_image_ani_cut': ''}, 'honor_reply': {'honor': [{'aid': 115585740512849, 'type': 3, 'desc': '全站排行榜最高第38名', 'weekly_recommend_num': 0}, {'aid': 115585740512849, 'type': 7, 'desc': '热门收录', 'weekly_recommend_num': 0}]}, 'like_icon': '', 'need_jump_bv': False, 'disable_show_up_info': False, 'is_story_play': 1, 'is_view_self': False}
