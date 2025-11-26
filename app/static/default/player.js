
// 播放函数
function play() {
    api('api/play').then(({ success }) => {
        if (success) {
            isPlaying = true;
            startProgressUpdates();
        }
    });
}
// 切换播放/暂停
function togglePlayPause() {
    // 立即更新本地状态，确保UI响应迅速
    const newPlayingState = !isPlaying;
    const btn = document.getElementById('playPauseButton');
    if (btn) btn.textContent = isPlaying ? '⏸️' : '▶️';
    api(newPlayingState ? 'api/play' : 'api/pause');
}
// 进度条跳转
function seekToPosition(event) {
    const progressBar = event.currentTarget;
    const clickX = event.offsetX;
    const barWidth = progressBar.offsetWidth;
    const seekPercent = (clickX / barWidth) * 100;

    // 先更新UI显示，然后调用API
    document.getElementById('progress-fill').style.width = `${seekPercent}%`;
    
    //show.log(`进度条跳转至: ${seekPercent.toFixed(1)}%`);

    // 调用正确的API端点
    apiGet('api/set_position', { position: seekPercent }).then(({ success, data }) => {
        if (success) {
            show.log('进度跳转到:', data.position+"%");
            
        } else {
            show.error('跳转失败:', data?.message || '未知错误');
        }
    }).catch(error => {
        show.error('跳转时出错:', error);
    });
}

// 停止播放
function stop() {
    // 立即更新本地状态和UI
    isPlaying = false;
    const btn = document.getElementById('playPauseButton');
    if (btn) btn.textContent = '▶️';
    
    // 然后调用API
    api('api/stop');
}

// 上一曲
function prevTrack() {
    api('api/prev');
}

// 下一曲
function nextTrack() {
    api('api/next').then(({ success, data }) => {
        if (success) {
            show.debug('下一曲:', data.title || '未知标题');
        } else {
            show.error('下一曲失败:', data?.message || '未知错误');
        }
    });
}
let last_musicname = '';
function loadAudioMetadata() {
    api('api/audio_metadata').then(({ success, data }) => {
        if (!success || data.status === "error") {
            document.getElementById('track-title').textContent = '未选择曲目';
            document.getElementById('track-artist').textContent = '';
            document.getElementById('track-album').textContent = '';
            currentFile = ''; // 清空当前文件路径
            return;
        }
        
        // 歌曲改变时弹窗提示
        if (last_musicname && last_musicname !== data.title) {
            show.log(`${last_musicname} → ${data.title || '未知标题'}`);
        }
        last_musicname = data.title || '未知标题';

        document.getElementById('track-title').textContent = data.title || '未知标题';
        document.getElementById('track-artist').textContent = data.artist || '';
        document.getElementById('track-album').textContent = data.album || '';
        document.getElementById('track-bitrate').textContent = data.bitrate || '';
        document.getElementById('track-file-path').textContent = data.file_path || '';
        
        // 更新当前文件路径
        if (data.file_path) {
            currentFile = data.file_path;
        }
    });
}
// 播放模式切换
async function togglePlayMode() {
    // 只需要调用一次API切换模式，不需要参数
    const { success, data } = await api('api/set_play_mode');
    if (success) {
        // 英文模式名到中文的对照表
        const modeMap = {
            'single_once': '不自动播放',
            'sequence': '顺序播放',
            'single_loop': '单曲循环',
            'random': '随机播放'
        };
        const chineseMode = modeMap[data.current_mode] || data.current_mode;
        // 如果后端返回了新的模式值，立即刷新按钮显示
        if (data.play_mode_value !== undefined) {
            updatePlayModeDisplay(data.play_mode, data.play_mode_value);
        }
    } else {
        show.error('切换播放模式失败:', data?.message || '未知错误');
    }
}

function loadAlbumCover() {
    const albumImage = document.getElementById('album-image');
    const timestamp = Date.now();

    // 先设置默认文字（防止闪烁）
    albumImage.src = '';
    albumImage.alt = '音频文件无封面';
    albumImage.style.background = '#333';  // 灰底

    // 尝试加载封面
    const testImg = new Image();
    testImg.onload = () => {
        // 有图：加载成功
        albumImage.src = `${baseApiUrl}/api/album_cover?t=${timestamp}`;
        albumImage.alt = '专辑封面';
        albumImage.style.background = 'none';  // 清除背景
    };
    testImg.onerror = () => {
        // 无图：加载失败，保持文字
        albumImage.src = '';  // 清空 src，显示 alt
        albumImage.alt = '音频文件无封面';
        albumImage.style.background = '#333';
        show.debug('无专辑封面，使用文字提示');
    };

    // 触发加载测试
    testImg.src = `${baseApiUrl}/api/album_cover?t=${timestamp}`;
}