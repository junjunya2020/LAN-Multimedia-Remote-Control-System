# run.py
import uvicorn
from app import create_app

app, socketio_app, sio = create_app()

if __name__ == "__main__":
    print("局域网音频远程控制播放系统（Quart + Socket.IO ASGI）启动中...")
    uvicorn.run(
        "run:socketio_app",
        host="0.0.0.0",
        port=5000,
        log_level="debug"
    )