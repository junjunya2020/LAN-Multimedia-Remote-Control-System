import aiohttp
import asyncio
import json
import re


class DouyinParser:
    def __init__(self):
        self.url = None
        self.session = None
        self.data = None

        self.headers = {
            'user-agent': 'Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36',
            'referer': 'https://www.douyin.com/?is_from_mobile_home=1&recommend=1'
        }

    def set_url(self, url: str):
        self.url = url

    async def _create_session(self):
        self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def parse(self):
        if not self.url:
            raise ValueError("未设置 URL，请先调用 set_url(url)")

        await self._create_session()

        try:
            async with self.session.get(self.url, headers=self.headers, timeout=10) as resp:
                html = await resp.text()

            # 抽取 JSON
            try:
                raw_json = re.findall(r'window\._ROUTER_DATA = (.*?)</script>', html)[0]
                router_data = json.loads(raw_json)
            except Exception:
                raise Exception("解析失败：未找到 JSON 数据")

            # item_list
            try:
                item = router_data['loaderData']['video_(id)/page']['videoInfoRes']['item_list'][0]
            except Exception:
                raise Exception("解析失败：未找到视频/图集 item_list")

            # --------------- 安全获取字段 ----------------

            # 标题
            title = item.get('desc') or "标题不存在"

            # awemeID
            aweme_id = item.get('aweme_id') or "aweme_id 不存在"

            # 视频
            video = None
            video_info = item.get("video", {})
            if isinstance(video_info, dict):
                play_addr = video_info.get("play_addr", {})
                if isinstance(play_addr, dict):
                    uri = play_addr.get("uri")
                    if isinstance(uri, str):
                        video = f"https://www.douyin.com/aweme/v1/play/?video_id={uri}"

            # 封面
            cover = None
            cover_block = video_info.get("cover", {}) if isinstance(video_info, dict) else {}
            if isinstance(cover_block, dict):
                url_list = cover_block.get("url_list")
                if isinstance(url_list, list) and url_list:
                    cover = url_list[0]

            # 图集
            images = None
            raw_images = item.get("images")
            if isinstance(raw_images, list):
                images_tmp = []
                for img in raw_images:
                    if isinstance(img, dict):
                        url_list = img.get("url_list")
                        if isinstance(url_list, list) and url_list:
                            images_tmp.append(url_list[0])
                images = images_tmp if images_tmp else None

            # 保存数据
            self.data = {
                "title": title,
                "aweme_id": aweme_id,
                "video": video,
                "cover": cover,
                "images": images
            }

            return True

        finally:
            await self.close()

    # -------- 访问接口 -------
    def get_title(self): return self.data.get("title") if self.data else None
    def get_aweme_id(self): return self.data.get("aweme_id") if self.data else None
    def get_video(self): return self.data.get("video") if self.data else None
    def get_cover(self): return self.data.get("cover") if self.data else None
    def get_image(self): return self.data.get("images") if self.data else None

# 测试
if __name__ == "__main__":
    async def run():
        parser = DouyinParser()
        parser.set_url("https://v.douyin.com/U_dlf3SR8Kg/")

        await parser.parse()

        print("标题:", parser.get_title())
        print("AwemeID:", parser.get_aweme_id())
        print("视频:", parser.get_video() or "没有视频")
        print("封面:", parser.get_cover() or "没有封面")

        images = parser.get_image()
        if images:
            print("图片:")
            for img in images:
                print(img)
        else:
            print("没有图片")

    asyncio.run(run())
