let lastPlayMode = null; // 缓存上一次的播放模式
let lastStatus = null; // 缓存上一次的播放状态
let lastVolume = null; // 缓存上一次的音量
function syncBroadcastData(data) {
    // 处理其他事件广播
    // 实时动态_播放模式被动更新的信息弹窗
    if ('play_mode' in data && data.play_mode !== lastPlayMode) {
        lastPlayMode = data.play_mode;
        show.log('实时动态_当前播放模式：', lastPlayMode);
    }
    // 实时动态_当前播放状态被动更新的信息弹窗
    if ('status' in data && data.status !== lastStatus) {
        lastStatus = data.status;
        // 将英文状态映射为中文
        const statusMap = {
            'NothingSpecial': '无特殊状态',
            'Opening':        '正在打开',
            'Buffering':      '缓冲中',
            'Playing':        '正在播放',
            'Paused':         '已暂停',
            'Stopped':        '已停止',
            'Ended':          '播放结束',
            'Error':          '播放错误'
        };
        const chineseStatus = statusMap[lastStatus] || lastStatus;
        // 仅“正在播放/已暂停/已停止”用 show.log，其余用 show.debug；错误用 show.error
        if (lastStatus === 'Playing' || lastStatus === 'Paused' || lastStatus === 'Stopped') {
            show.log('实时动态_当前播放状态：', chineseStatus);
        } else if (lastStatus === 'Error') {
            show.error('实时动态_当前播放状态：', chineseStatus);
        } else {
            show.debug('实时动态_当前播放状态：', chineseStatus);
        }
    }
    // 实时动态_当前音量被动更新的信息弹窗
    if ('volume' in data && data.volume !== lastVolume) {
        lastVolume = data.volume;
        show.log('实时动态_当前音量：', lastVolume);
    }

    // 更新refresh token和相关资源（仅在变化时）
    if (data.refresh_token !== lastRefreshToken) {
        lastRefreshToken = data.refresh_token;
        // 延迟加载非关键资源，避免阻塞主要同步
        setTimeout(() => {
            loadAlbumCover();
            loadAudioMetadata();
            initPlaylist();
            initPlaySource();
        }, 100);
    }

    // 使用status字段更新播放状态
    if (data.status) {
        const status = data.status;
        const btn = document.getElementById('playPauseButton');
        
        // 处理错误状态
        if (status === 'Error') {
            show.error('播放器错误状态:', status);
            isPlaying = false;
            if (btn) btn.textContent = '▶️';
        }
        // 处理播放状态
        else if (status === 'Playing') {
            isPlaying = true;
            if (btn) btn.textContent = '⏸️';
        }
        // 处理暂停状态
        else if (status === 'Paused') {
            isPlaying = false;
            if (btn) btn.textContent = '▶️';
        }
        // 处理停止状态
        else if (status === 'Stopped' || status === 'Ended') {
            isPlaying = false;
            if (btn) btn.textContent = '▶️';
        }
        // 其他状态（Opening, Buffering）保持当前isPlaying状态
        //show.log('播放器状态:', status);
    } else if ('playing' in data) {
        // 向后兼容旧版playing字段
        isPlaying = data.playing;
        const btn = document.getElementById('playPauseButton');
        if (btn) btn.textContent = isPlaying ? '⏸️' : '▶️';
    }

    // 更新进度和歌词
    if ('current_time' in data && 'total_time' in data) {
        document.getElementById('progress-fill').style.width = `${data.progress || 0}%`;
        document.getElementById('current-time').textContent = formatTime(data.current_time || 0);
        document.getElementById('total-time').textContent = formatTime(data.total_time || 0);
        const lyricsElement = document.getElementById('current-lyrics');
        if (lyricsElement) {
            let lyricsText = data.current_lyrics || '暂无歌词';
            
            // 应用简繁转换
            if (typeof traditionalChineseEnabled !== 'undefined' && traditionalChineseEnabled) {
                if (window.opencc && typeof window.opencc.s2t === 'function') {
                    lyricsText = window.opencc.s2t(lyricsText);
                }
            }
            
            lyricsElement.textContent = lyricsText;
        }
    }

    // 更新播放模式显示
    if ('play_mode' in data && 'play_mode_value' in data) {
        updatePlayModeDisplay(data.play_mode, data.play_mode_value);
    }

    // 更新音量信息（仅在用户最近没有操作时更新）
    if ('volume' in data) {
        // 如果用户最近3秒内没有操作，才更新显示
        if (Date.now() - lastUserVolumeUpdate > 3000) {
            updateVolumeDisplay(data.volume);
        }
    }
}
// 获取播放进度并更新进度条
function updateProgress() {

    api(`api/progress?id=${browserUUID}`).then(({ success, data }) => {
        if (!success) {
            resetProgressBar();
            isPlaying = false;
            const btn = document.getElementById('playPauseButton');
            if (btn) btn.textContent = '▶️';
            return;
        }
        //更新随机请求延时制作卡顿假象
        time_sleep=Math.floor(Math.random() * 1000) + 1000;
        syncBroadcastData(data);
    });
}