// ===== 全局调试开关 =====
const debug = false; // 设置为true启用调试信息弹窗
// 创建全局实例
const show = new ConsoleWrapper();

// 打开独立文件管理器窗口
function openFileManager() {
    window.open('/static/file_manager.html', 'file_manager', 'width=1000,height=700,scrollbars=yes,resizable=yes');
}

// 打开播放历史记录窗口
function openPlaybackHistory() {
    window.open('/static/default/playback_history.html', 'playback_history', 'width=800,height=600,scrollbars=yes,resizable=yes');
}

// 全局函数：供历史记录窗口调用以设置文件路径
function setFileByPath(filePath) {
    // 验证文件路径
    if (!filePath || typeof filePath !== 'string') {
        console.error('无效的文件路径');
        return Promise.reject(new Error('无效的文件路径'));
    }
    
    // 调用set_file API设置当前文件
    return api(`api/set_file?file_path=${encodeURIComponent(filePath)}`)
        .then(result => {
            if (result.success) {
                currentFile = filePath;
                show.log(`已选择文件: ${filePath}`);
                return result;
            } else {
                throw new Error(result.message || '设置文件失败');
            }
        })
        .catch(error => {
            console.error('设置文件失败:', error);
            show.log(`设置文件失败: ${error.message}`);
            throw error;
        });
}

// 搜索歌词
function searchLyrics() {
    // 获取当前播放的歌曲信息
    const trackTitle = document.getElementById('track-title').textContent;
    const trackArtist = document.getElementById('track-artist').textContent;
    
    // 构建搜索关键词（优先使用歌曲名，如果有艺术家信息则加上）
    let searchKeyword = trackTitle;
    if (trackArtist && trackArtist !== '') {
        searchKeyword = `${trackTitle} ${trackArtist}`;
    }
    
    // 如果当前没有播放歌曲，提示用户
    if (trackTitle === '未选择曲目' || trackTitle === '') {
        show.log('请先选择要播放的歌曲');
        return;
    }
    
    // 打开搜索歌词页面，传递当前歌曲信息
    const url = `/static/SearchLyric.html?song=${encodeURIComponent(searchKeyword)}&file=${encodeURIComponent(currentFile)}`;
    window.open(url, 'search_lyrics', 'width=900,height=700,scrollbars=yes,resizable=yes');
}

let baseApiUrl = window.location.protocol + '//' + window.location.host;
const itemsPerPage = 10; // 每页显示的文件/文件夹数量
let currentPath = ''; // 当前目录路径
let currentFile = ''; // 当前文件路径
let progressInterval; // 进度更新定时器
let isPlaying = false; // 播放状态标记
let socket = null;     // ← 新增：Socket.IO 实例
let lastRefreshToken = null; // 刷新令牌（用于检测切歌）
let currentPlayMode = 'SEQUENTIAL'; // 当前播放模式，默认顺序播放
let time_sleep = 0;
browserUUID=getBrowserUUID();
// 页面加载时，先尝试从localStorage加载上次的路径，但不自动播放
window.onload = async function() {
    document.getElementById('album-image').src = `${baseApiUrl}album_cover?t=${Date.now()}`;  // 加时间戳 + 模板字符串
    resetProgressBar();
    stopProgressUpdates();

    const { success, data } = await api(`api/progress?id=${browserUUID}`);
    lastRefreshToken = data.refresh_token || null;
    initSocketCheckbox();
    // 页面加载时，只更新一次专辑封面和元数据

    await loadAlbumCover();
    await loadAudioMetadata();
    startProgressUpdates();
    await initPlaylist();
    await initPlaySource();
};

// 键盘快捷键支持
document.addEventListener('keydown', function(event) {
    // 音量增加 (上箭头)
    if (event.key === 'ArrowUp') {
        event.preventDefault();
        const volumeFill = document.getElementById('volume-fill');
        if (volumeFill) {
            const currentVolume = parseFloat(volumeFill.style.width) || 50;
            const newVolume = Math.min(100, currentVolume + 5);
            setVolume(Math.round(newVolume), true);
        }
    }
    // 音量减少 (下箭头)
    else if (event.key === 'ArrowDown') {
        event.preventDefault();
        const volumeFill = document.getElementById('volume-fill');
        if (volumeFill) {
            const currentVolume = parseFloat(volumeFill.style.width) || 50;
            const newVolume = Math.max(0, currentVolume - 5);
            setVolume(Math.round(newVolume), true);
        }
    }
    // 播放列表快捷键
    else if (event.ctrlKey && event.key === 'r') {
        // Ctrl+R 刷新播放列表
        event.preventDefault();
        refreshPlaylist();
    }
});

// ===== 简繁转换功能 =====

// 简繁转换状态
let traditionalChineseEnabled = false;

// 切换简繁转换
function toggleTraditionalChinese() {
    traditionalChineseEnabled = !traditionalChineseEnabled;
    
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
    
    // 广播简繁转换状态
    broadcastTraditionalChineseStatus();
}

// 转换当前显示的歌词
function convertCurrentLyrics() {
    const lyricsElement = document.getElementById('current-lyrics');
    if (lyricsElement && lyricsElement.textContent !== '暫無歌詞' && lyricsElement.textContent !== '暂无歌词') {
        const originalText = lyricsElement.textContent;
        const convertedText = traditionalChineseEnabled ? 
            window.opencc.s2t(originalText) : 
            window.opencc.t2s(originalText);
        lyricsElement.textContent = convertedText;
    }
}

// 广播简繁转换状态
function broadcastTraditionalChineseStatus() {
    if (socket && socket.connected) {
        socket.emit('traditional_chinese_toggle', {
            enabled: traditionalChineseEnabled,
            timestamp: Date.now()
        });
    }
}

// 初始化简繁转换状态
function initTraditionalChinese() {
    // 从localStorage加载状态
    const savedState = localStorage.getItem('traditionalChineseEnabled');
    if (savedState !== null) {
        traditionalChineseEnabled = savedState === 'true';
    }
    
    // 初始化按钮状态
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
}

// 在页面加载时初始化简繁转换
window.addEventListener('DOMContentLoaded', function() {
    initTraditionalChinese();
});

