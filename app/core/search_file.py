import os

import marisa_trie
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import re
import asyncio

class FileNameIndexerSingleton:
    _instance = None
    _trie = None
    _executor = ThreadPoolExecutor()
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        """保证只有一个索引实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._root = None
                    cls._instance._total_files = 0
                    cls._instance._processed_files = 0
        return cls._instance

    def __init__(self, root=None):
        if root:
            self.set_root(root)

    def set_root(self, root):
        """设置要索引的文件夹路径"""
        self._root = root

    async def count_files(self):
        """异步统计文件总数"""
        if not self._root:
            raise ValueError("文件夹路径未设置！")

        loop = asyncio.get_running_loop()

        # 使用 followlinks=True 来支持符号链接
        walk_result = await loop.run_in_executor(
            self._executor,
            lambda: list(os.walk(self._root, followlinks=True))
        )

        total = 0
        for r, d, files in walk_result:
            total += len(files)

        self._total_files = total
        self._processed_files = 0

    async def build_trie(self):
        """异步构建 Trie 索引"""
        if not self._root:
            raise ValueError("文件夹路径未设置！")

        loop = asyncio.get_running_loop()

        # 通过线程池执行 os.walk，使用 followlinks=True 支持符号链接
        walk_result = await loop.run_in_executor(
            self._executor,
            lambda: list(os.walk(self._root, followlinks=True))
        )

        file_list = []
        for r, d, files in walk_result:
            for f in files:
                file_list.append(os.path.join(r, f))
                self._processed_files += 1
                self.show_progress()

        # 构建 Trie
        self._trie = await loop.run_in_executor(
            self._executor,
            lambda: marisa_trie.Trie(file_list)
        )

    def show_progress(self):
        """显示进度"""
        progress = (self._processed_files / self._total_files) * 100
        print(f"\r建立索引中... {self._processed_files}/{self._total_files} ({progress:.2f}%)", end="")

    async def search(self, pattern: str):
        """普通搜索：前后匹配任意字符（不区分大小写）"""
        if not self._trie:
            raise ValueError("索引尚未构建！")

        loop = asyncio.get_running_loop()

        # 获取所有文件名
        all_files = await loop.run_in_executor(self._executor, self._trie.keys, "")

        # 使用正则表达式过滤文件名，添加 re.IGNORECASE 标志
        regex = re.compile(".*" + re.escape(pattern) + ".*", re.IGNORECASE)  # 使用 .* 来匹配任意字符，不区分大小写
        matched_files = [f for f in all_files if regex.search(f)]  # 用 search 而非 match

        return matched_files

    async def regex_search(self, pattern: str):
        """完全遵守正则表达式的搜索"""
        if not self._trie:
            raise ValueError("索引尚未构建！")

        loop = asyncio.get_running_loop()

        # 获取所有文件名
        all_files = await loop.run_in_executor(self._executor, self._trie.keys, "")

        # 使用正则表达式进行精确匹配
        try:
            regex = re.compile(pattern)
        except re.error as e:
            raise ValueError(f"无效的正则表达式: {e}")

        matched_files = [f for f in all_files if regex.match(f)]  # 使用 match 进行严格的前缀匹配

        return matched_files

    async def update_index(self):
        """异步更新索引（在已有的索引下继续添加文件）"""
        if not self._root:
            raise ValueError("文件夹路径未设置！")
        if not self._trie:
            raise ValueError("索引尚未构建！")

        file_list = []
        loop = asyncio.get_running_loop()

        # 遍历文件夹，获取新文件路径，使用 followlinks=True 支持符号链接
        walk_result = await loop.run_in_executor(
            self._executor,
            lambda: list(os.walk(self._root, followlinks=True))
        )

        for r, d, files in walk_result:
            for f in files:
                file_list.append(os.path.join(r, f))
                self._processed_files += 1

        # 将新文件加入索引
        await loop.run_in_executor(self._executor, self._trie.update, file_list)

    async def rebuild_index(self):
        """异步重建索引（删除旧索引并重新建立）"""
        self._trie = None
        self._processed_files = 0
        await self.build_trie()

    def delete_index(self):
        """删除索引（清理索引，重新初始化）"""
        self._trie = None
        self._processed_files = 0

    def clear_and_exit(self):
        """清理退出，准备程序退出"""
        self.delete_index()
        print("索引已清理，程序退出。")

    def get_index_status(self):
        """获取索引状态（包括进度）"""
        if self._trie:
            progress = (self._processed_files / self._total_files) * 100
            return f"索引已完成 {self._processed_files}/{self._total_files} ({progress:.2f}%)"
        else:
            return "索引尚未开始或已被清理。"

    def save_index(self, save_path: str):
        """将索引保存到磁盘"""
        if not self._trie:
            raise ValueError("索引尚未构建！")
        self._trie.save(save_path)
        print(f"索引已保存到: {save_path}")

    def load_index(self, load_path: str):
        """从磁盘加载索引"""
        if os.path.exists(load_path):
            self._trie = marisa_trie.Trie()
            self._trie.load(load_path)
            print(f"索引已从 {load_path} 加载。")
        else:
            print(f"索引文件 {load_path} 不存在！")


# 导出单例实例
file_indexer = FileNameIndexerSingleton()

if __name__ == "__main__":
    async def main():
        file_indexer.set_root("Z:\\Jun_多媒体库_公开")
        await file_indexer.count_files()
        await file_indexer.build_trie()
        data = await file_indexer.regex_search(r".*周杰伦.*\.mp3$")
        print("搜索完成", data)

    asyncio.run(main())
