# AudioSphere Control - 局域网多媒体远程控制系统

[中文](README.md) | [English](README_EN.md)

## 🎵 项目简介

AudioSphere Control 是一个基于 Python 的现代化局域网多媒体远程控制系统，支持音频/视频播放、文件管理、实时同步控制等功能。通过 Web 界面和 Socket.IO 实时通信，实现跨设备的便捷媒体播放体验。

## ✨ 核心特性

### 🎮 远程控制功能
- **实时播放控制**：播放、暂停、停止、上一曲、下一曲
- **进度控制**：精确到秒的播放进度调节
- **音量管理**：0-100% 音量调节，支持静音
- **播放模式**：单曲、顺序、循环、随机四种播放模式

### 📁 智能文件管理
- **文件浏览器**：可视化目录浏览和文件选择
- **播放列表管理**：动态添加/删除播放列表项
- **搜索功能**：支持文件名和内容搜索
- **多格式支持**：MP3, MP4, AVI, MKV 等主流媒体格式

### 🔄 实时同步系统
- **多设备同步**：局域网内多客户端实时状态同步
- **Socket.IO 通信**：低延迟的实时数据传输
- **播放状态同步**：所有设备保持一致的播放状态

### 🎯 高级功能
- **断点续播**：自动记录播放位置，下次启动时继续播放
- **歌词显示**：支持网易云音乐歌词搜索和显示
- **专辑封面**：自动提取和显示音频文件元数据
- **抖音视频解析**：支持抖音视频链接解析和播放
- **多语言界面**：支持简体中文和繁体中文切换

## 🏗️ 技术架构

### 后端技术栈
- **框架**：Quart (异步 Web 框架)
- **实时通信**：Socket.IO
- **媒体播放**：VLC Media Player (python-vlc)
- **文件处理**：aiofiles, mutagen, eyed3
- **Web 服务器**：Uvicorn + Hypercorn

### 前端技术栈
- **核心**：原生 HTML5 + CSS3 + JavaScript
- **实时通信**：Socket.IO 客户端
- **UI 设计**：现代化响应式界面
- **兼容性**：支持主流现代浏览器

## 🚀 快速开始

### 环境要求
- Python 3.8+
- VLC Media Player
- Windows/Linux/macOS

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/your-username/audioshpere-control.git
cd audioshpere-control
```

2. **创建虚拟环境**
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# 或 source .venv/bin/activate  # Linux/macOS
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **启动应用**
```bash
# Windows (推荐)
start.bat

# 或直接运行
python run.py
```

5. **访问系统**
打开浏览器访问：`http://localhost:5000`

## 📱 使用指南

### 基本操作
1. **文件选择**：点击"选择文件"按钮浏览本地文件
2. **播放控制**：使用播放器界面的控制按钮
3. **音量调节**：拖动音量滑块或使用键盘快捷键
4. **播放列表**：在右侧面板管理播放列表

### 局域网访问
系统启动后，局域网内其他设备可通过以下地址访问：
```
http://[服务器IP地址]:5000
```

## 🔧 配置说明

### 播放器设置
系统会自动创建 `player_settings.json` 配置文件，包含：
- 上次播放文件记录
- 播放进度记忆
- 音量设置
- 播放模式偏好

### 日志系统
系统提供完整的日志记录：
- `logs/debug.log`：调试信息
- `logs/error.log`：错误信息
- `logs/info.log`：运行信息
- `logs/player.log`：播放器专用日志

### 日志查看
如遇问题，请查看相应日志文件获取详细错误信息。

## 🤝 贡献指南

我们欢迎各种形式的贡献！请参考以下步骤：

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [VLC Media Player](https://www.videolan.org/vlc/) - 强大的媒体播放引擎
- [Quart](https://quart.palletsprojects.com/) - 优秀的异步 Web 框架
- [Socket.IO](https://socket.io/) - 可靠的实时通信库

## 📞 联系我们

如有问题或建议，请通过以下方式联系：
- 提交 [Issue](https://github.com/your-username/audioshpere-control/issues)
- 发送邮件至：junmr3529@gmail.com

---

⭐ 如果这个项目对你有帮助，请给我们一个 Star！