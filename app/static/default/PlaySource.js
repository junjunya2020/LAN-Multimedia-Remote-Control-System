// ========== 播放来源设置功能 ==========

// 初始化播放来源设置
let lastPlaySource = null; // 缓存上一次的播放来源
async function initPlaySource() {
    // 获取当前设置
    const { success, data } = await api('api/settings');
    if (success && data) {
        const current = data.settings.play_source || 1;
        // 仅当播放来源发生变化时才弹出提示
        if (current !== lastPlaySource) {
            show.log('当前播放来源:', current);
            lastPlaySource = current;
        }
        updatePlaySourceDisplay(current);
    }
}

// 更新播放来源显示
function updatePlaySourceDisplay(playSource) {
    const playlistRadio = document.getElementById('play_source_playlist');
    const directoryRadio = document.getElementById('play_source_directory');
    const hint = document.getElementById('play-source-hint');
    
    if (playSource === 1) {
        // 播放列表模式
        if (playlistRadio) playlistRadio.checked = true;
        if (hint) {
            hint.textContent = '当前模式：播放列表模式';
            hint.className = 'play-source-hint playlist-mode';
        }
    } else if (playSource === 2) {
        // 磁盘路径模式
        if (directoryRadio) directoryRadio.checked = true;
        if (hint) {
            hint.textContent = '当前模式：磁盘路径模式（播放列表已锁定为只读）';
            hint.className = 'play-source-hint directory-mode';
        }
    }
}

// 更新播放来源设置
async function updatePlaySource(playSource) {
    const { success, error } = await apiPost('api/settings', {
        play_source: playSource
    });
    
    if (success) {
        updatePlaySourceDisplay(playSource);
        show.log(`播放来源已更新为: ${playSource === 1 ? '播放列表' : '磁盘路径'}`);
        
        // 显示成功提示
        const hint = document.getElementById('play-source-hint');
        if (hint) {
            const originalText = hint.textContent;
            hint.textContent = '设置已保存';
            hint.style.color = '#4CAF50';
            setTimeout(() => {
                updatePlaySourceDisplay(playSource);
                hint.style.color = '';
            }, 1000);
        }
    } else {
        show.error('更新播放来源失败:', error);
        alert('更新播放来源失败: ' + (error || '未知错误'));
    }
}

// 播放来源单选按钮变化事件处理
function onPlaySourceChange(value) {
    updatePlaySource(parseInt(value));
}