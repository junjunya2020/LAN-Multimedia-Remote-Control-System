import aiohttp
import asyncio
import json


class NetEaseApiSearch:
    def __init__(self):
        self.keyword = ""
        self.song_data = []

    def set_search_query(self, keyword: str):
        self.keyword = keyword

    async def start_search(self):
        url = "https://music.163.com/api/search/get/web"
        params = {
            "s": self.keyword,
            "type": 1,
            "limit": 10,
            "offset": 0,
            "total": "true"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    print(f"搜索失败，状态码：{resp.status}")
                    return []
                text = await resp.text()
                data = json.loads(text)
                self.song_data = data.get("result", {}).get("songs", [])
                return self.song_data

    def get_search_data(self):
        result = []
        for song in self.song_data:
            album = song.get("album", {})
            pic_id = album.get("picId", 0)
            cover = f"https://p1.music.126.net/{pic_id}/pic.jpg" if pic_id else ""

            artists = " / ".join(ar["name"] for ar in song.get("artists", []))

            info = {
                "song_id": song["id"],
                "song_name": song["name"],
                "artists": artists,
                "duration": song["duration"] / 1000,  # 原始秒数（小数）
                "album": album.get("name", ""),
                "cover": cover,
            }
            result.append(info)
        return result


class NetEaseApiLyric:
    def __init__(self):
        self.song_id = None

    def set_song_id_for_lyrics(self, song_id: int):
        self.song_id = song_id

    async def start_lyrics_search(self):
        if not self.song_id:
            return {"lyric": "", "status": "failed"}

        url = "https://music.163.com/api/song/lyric"
        params = {"os": "pc", "id": self.song_id, "lv": -1, "kv": -1, "tv": -1}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                text = await resp.text()
                data = json.loads(text)
                lrc = data.get("lrc", {}).get("lyric", "")
                trans = data.get("tlyric", {}).get("lyric", "")
                return {"lyric": lrc, "translate": trans, "status": "success"}
