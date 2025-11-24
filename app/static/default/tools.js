function getBrowserUUID() {
    let uuid = localStorage.getItem('browser_uuid');
    if (!uuid) {
        // polyfill for crypto.randomUUID
        if (typeof crypto === 'object' && typeof crypto.randomUUID === 'function') {
            uuid = crypto.randomUUID();
        } else {
            // 老浏览器降级方案：时间戳 + 随机数
            uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                const r = Math.random() * 16 | 0;
                const v = c === 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
        }
        localStorage.setItem('browser_uuid', uuid);
    }
    return uuid;
}
// ===== 新增：万能 API 工具（只加这几行，后面所有函数都靠它） =====

async function api(relativeUrl) {
    // 去除多余斜杠
    relativeUrl = relativeUrl.replace(/^\//, '');
    const fullUrl = baseApiUrl + '/' + relativeUrl;
    try {
        const res = await fetch(fullUrl);
        const data = await res.json();
        return res.ok && (!data.status || data.status !== "error")
            ? { success: true, data }
            : { success: false, data };
    } catch (err) {
        show.error('API Error:', err);
        return { success: false, data: null };
    }
}

async function apiGet(endpoint, params = {}) {
    // 只构建相对路径，如 'set_file?file=xxx'
    let relativeUrl = endpoint.replace(/^\//, '');
    if (Object.keys(params).length) {
        const searchParams = new URLSearchParams();
        Object.keys(params).forEach(k => params[k] !== undefined && searchParams.append(k, params[k]));
        relativeUrl += '?' + searchParams.toString();
    }
    return api(relativeUrl); // api 会加 baseApiUrl
}
async function apiPost(endpoint, body = {}) {
    // 只构建相对路径，如 'set_volume'
    let relativeUrl = endpoint.replace(/^\//, '');
    return fetch(baseApiUrl + '/' + relativeUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    })
    .then(async res => {
        const data = await res.json();
        return res.ok && (!data.status || data.status !== "error")
            ? { success: true, data }
            : { success: false, data };
    })
    .catch(err => {
        show.error('API POST Error:', err);
        return { success: false, data: null };
    });
}
// 更新播放模式显示
function updatePlayModeDisplay(playMode, playModeValue) {
    const playModeButton = document.getElementById('playModeButton');
    const nextButton = document.getElementById('nextButton');
    const prevButton = document.getElementById('prevButton');
    if (!playModeButton) return;
    
    // 根据播放模式值设置对应的图标和标题
    switch (playModeValue) {
        case 0: // SINGLE
            playModeButton.textContent = '🔽'; // 单曲循环
            playModeButton.title = '不自动播放';
            if (nextButton) nextButton.textContent = '⏭️';
            if (prevButton) prevButton.textContent = '⏮️';
            currentPlayMode = 'SINGLE';
            break;
        case 1: // SEQUENTIAL
            playModeButton.textContent = '🔁'; // 顺序播放
            playModeButton.title = '顺序播放';
            if (nextButton) nextButton.textContent = '⏭️';
            if (prevButton) prevButton.textContent = '⏮️';
            currentPlayMode = 'SEQUENTIAL';
            break;
        case 2: // LOOP
            playModeButton.textContent = '🔂'; // 单曲循环
            playModeButton.title = '单曲循环';
            if (nextButton) nextButton.textContent = '⏭️';
            if (prevButton) prevButton.textContent = '⏮️';
            currentPlayMode = 'LOOP';
            break;
        case 3: // RANDOM
            playModeButton.textContent = '🔀'; // 随机播放
            playModeButton.title = '随机播放';
            if (nextButton) nextButton.textContent = '🔀';
            if (prevButton) prevButton.textContent = '🔀';
            currentPlayMode = 'RANDOM';
            break;
        default:
            playModeButton.textContent = '🔁'; // 默认顺序播放
            playModeButton.title = '顺序播放';
            if (nextButton) nextButton.textContent = '⏭️';
            if (prevButton) prevButton.textContent = '⏮️';
            currentPlayMode = 'SEQUENTIAL';
    }
}
// 格式化时间（秒转分:秒）
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// 重置进度条
function resetProgressBar() {
    document.getElementById('progress-fill').style.width = '0%';
    document.getElementById('current-time').textContent = '00:00';
    document.getElementById('total-time').textContent = '00:00';
}

function viewFullLyrics() {
    // 在新标签页打开完整歌词API
    window.open('/api/full_lyrics', '_blank');
}

// 重启播放器
async function restartPlayer() {
    if (!confirm('确定要重启播放器吗？重启后需要重新加载页面。')) {
        return;
    }
    
    show.log('正在重启播放器...');
    
    try {
        const { success, data } = await api('api/restart');
        if (success) {
            show.log('播放器重启命令已发送，请等待重启完成...');
            // 等待一段时间后重新加载页面
        } else {
            show.error('重启失败:', data?.message || '未知错误');
        }
    } catch (error) {
        show.error('重启时出错:', error);
    }
}