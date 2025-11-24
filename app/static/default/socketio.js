// ==========socketio连接 ========
function initSocketCheckbox() {
    const checkbox = document.getElementById('enableSocket');
    const saved = localStorage.getItem('socketEnabled') === 'true';
    checkbox.checked = saved;

    // 切换时立即执行
    checkbox.addEventListener('change', function () {
        localStorage.setItem('socketEnabled', this.checked);
        if (this.checked) {
            // 立即停止轮询，确保不会同时运行
            stopProgressUpdates();
            // 断开任何可能存在的旧连接
            if (socket) {
                socket.disconnect();
                socket = null;
            }
            // 重新连接socket
            connectSocket();
            //show.debug('已切换到WebSocket模式，轮询已停止');
        } else {
            // 断开socket连接
            if (socket) {
                socket.disconnect();
                socket = null;
                //show.log('WebSocket已断开');
            }
            // 恢复轮询
            startProgressUpdates();
            show.debug('已切换到轮询模式');
        }
    });

    // 页面加载时立即按状态执行
    if (saved) {
        // 确保先停止轮询
        stopProgressUpdates();
        // 再连接socket
        connectSocket();
    }
}

function connectSocket() {
    if (socket?.connected) return;

    try {
        socket = io(baseApiUrl, {
            query: { id: browserUUID },
            transports: ['websocket'],
            timeout: 5000,
            reconnection: true,           // 启用自动重连
            reconnectionAttempts: 5,     // 最大重连尝试次数
            reconnectionDelay: 1000,     // 初始重连延迟
            reconnectionDelayMax: 10000,  // 最大重连延迟
            randomizationFactor: 0.5      // 随机化因子
        });

        socket.on('connect', () => {
            show.log('Socket.IO 已连接，实时同步已启用');
            // 确认轮询已停止
            if (progressInterval) {
                show.warn('警告：WebSocket连接后轮询仍在运行，正在停止...');
                stopProgressUpdates();
            }
        });

        socket.on('sync', (data) => {
            // 处理其他事件广播
            syncBroadcastData(data);
        });

        socket.on('traditional_chinese_toggle', (data) => {
            // 处理简繁转换事件
            handleTraditionalChineseToggle(data);
        });

        socket.on('disconnect', () => {
            show.log('Socket.IO 断开连接');
            // 检查是否应该恢复轮询
            const checkbox = document.getElementById('enableSocket');
            if (checkbox && !checkbox.checked) {
                startProgressUpdates();
            }
        });

        socket.on('connect_error', (error) => {
            show.error('Socket.IO连接失败:', error.message);
            // 不再手动重连，使用内置的自动重连机制
        });

        socket.on('reconnect', (attemptNumber) => {
            show.log(`Socket.IO 重新连接成功，第${attemptNumber}次尝试`);
        });

        socket.on('reconnect_attempt', (attemptNumber) => {
            show.debug(`Socket.IO 正在尝试重新连接，第${attemptNumber}次尝试`);
        });

        socket.on('reconnect_error', (error) => {
            show.error('Socket.IO 重连失败:', error.message);
        });

        socket.on('reconnect_failed', () => {
            show.error('Socket.IO 重连失败，已达到最大重连次数');
            // 重连失败后，如果checkbox仍为勾选状态，恢复轮询
            const checkbox = document.getElementById('enableSocket');
            if (checkbox && checkbox.checked) {
                show.warn('WebSocket重连失败，切换到轮询模式');
                startProgressUpdates();
            }
        });
    } catch (error) {
        show.error('WebSocket初始化错误:', error);
    }
}

// 处理简繁转换事件
function handleTraditionalChineseToggle(data) {
    if (data && typeof data.enabled !== 'undefined') {
        // 更新本地状态
        traditionalChineseEnabled = data.enabled;
        
        // 更新按钮状态
        const toggleBtn = document.getElementById('toggle-traditional');
        if (toggleBtn) {
            if (traditionalChineseEnabled) {
                toggleBtn.textContent = '简';
                toggleBtn.classList.add('active');
                toggleBtn.title = '切换到简体中文';
            } else {
                toggleBtn.textContent = '繁';
                toggleBtn.classList.remove('active');
                toggleBtn.title = '切换到繁体中文';
            }
        }
        
        // 转换当前显示的歌词
        convertCurrentLyrics();
        
        // 保存状态到localStorage
        localStorage.setItem('traditionalChineseEnabled', traditionalChineseEnabled.toString());
        
        show.log(`简繁转换已${traditionalChineseEnabled ? '启用' : '禁用'}`);
    }
}