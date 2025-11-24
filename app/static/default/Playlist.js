// ========== 播放列表功能 ==========

// 播放列表数据结构
let playlist = [];
let currentPlaylistIndex = -1;

// 初始化播放列表
async function initPlaylist() {
    await refreshPlaylist();
}

// 刷新播放列表
async function refreshPlaylist() {
    const { success, data } = await api('api/playlist');
    if (success && data && data.playlist) {
        playlist = data.playlist;
        renderPlaylist();
    } else {
        show.log('获取播放列表失败，使用空列表');
        playlist = [];
        renderPlaylist();
    }
}

// 渲染播放列表
function renderPlaylist() {
    const playlistContainer = document.getElementById('playlist-items');
    if (!playlistContainer) return;

    if (playlist.length === 0) {
        playlistContainer.innerHTML = '<div class="empty-playlist">播放列表为空，请添加音乐文件</div>';
        return;
    }

    let html = '';
    playlist.forEach((item, index) => {
        const isCurrent = index === currentPlaylistIndex;
        html += `
            <div class="playlist-item ${isCurrent ? 'current' : ''}" data-index="${index}">
                <div class="playlist-item-info">
                    <div class="playlist-item-title">${item.name || item.title || '未知标题'}</div>
                    <div class="playlist-item-artist">${item.artist || '未知艺术家'}</div>
                    <div class="playlist-item-file">${item.path || item.file || ''}</div>
                </div>
                <div class="playlist-item-actions">
                    <button onclick="playPlaylistItem(${index})" title="播放此曲">▶️</button>
                    <button onclick="deletePlaylistItem(${index})" title="从播放列表删除">🗑️</button>
                    <button onclick="editPlaylistItem(${index})" title="修改信息">✏️</button>
                </div>
            </div>
        `;
    });
    
    playlistContainer.innerHTML = html;
}

// 播放播放列表中的指定项目
async function playPlaylistItem(index) {
    if (index < 0 || index >= playlist.length) return;
    
    const item = playlist[index];
    if (!item.path && !item.file) return;
    
    const filePath = item.path || item.file;
    
    // 调用播放API
    const { success } = await apiGet('api/set_file', { file: filePath });
    if (success) {
        currentPlaylistIndex = index;
        renderPlaylist(); // 重新渲染以显示当前播放项
        // 开始播放
        await api('api/play');
        isPlaying = true;
        const btn = document.getElementById('playPauseButton');
        if (btn) btn.textContent = '⏸️';
    }
}

// 删除播放列表项目
async function deletePlaylistItem(index) {
    if (index < 0 || index >= playlist.length) return;
    
    const item = playlist[index];
    
    const { success } = await apiGet('api/remove_from_playlist', { 
        name: item.name || item.title || item.file || item.path || ''
    });
    
    if (success) {
        // 如果删除的是当前播放项目，更新播放状态
        if (index === currentPlaylistIndex) {
            currentPlaylistIndex = -1;
            // 如果这是最后一个项目，停止播放
            if (playlist.length === 1) {
                stop();
            }
        } else if (index < currentPlaylistIndex) {
            // 如果删除的项目在当前播放项之前，调整索引
            currentPlaylistIndex--;
        }
        
        await refreshPlaylist();
    }
}

// 修改播放列表项目信息（暂未实现对话框）
function editPlaylistItem(index) {
    if (index < 0 || index >= playlist.length) return;
    
    const item = playlist[index];
    alert(`修改功能暂未实现\n\n当前项目信息：\n标题：${item.title || '未知'}\n艺术家：${item.artist || '未知'}\n文件：${item.file || item.path}`);
}

// 添加文件到播放列表
async function addToPlaylist(filePath, title = '', artist = '') {
    const { success } = await apiGet('api/add_to_playlist', { 
        name: title || filePath.split('\\').pop() || '未知标题',
        path: filePath
    });
    
    if (success) {
        await refreshPlaylist();
        return true;
    }
    return false;
}

// 添加抖音音频到播放列表
async function addDouyinAudio() {
    // 获取抖音URL
    const url = prompt('请输入抖音音频URL:');
    if (!url || url.trim() === '') {
        return; // 用户取消或输入为空
    }

    try {
        // 调用后端API添加抖音音频
        const response = await apiPost('api/add_play_list_douyin', {
            url: url.trim()
        });
        
        if (response.success) {
            show.log('抖音音频添加成功');
            await refreshPlaylist(); // 刷新播放列表
        } else {
            // 根据debug变量决定显示内容
            const errorMsg = (typeof debug !== 'undefined' && debug) 
                ? JSON.stringify(response.data, null, 2)
                : response.data.message;
            show.error('添加抖音音频失败: ' + errorMsg);
        }
    } catch (error) {
        // 根据debug变量决定显示内容
        const errorMsg = (typeof debug !== 'undefined' && debug) 
            ? error 
            : '添加抖音音频时发生错误';
        show.error(errorMsg);
    }
}

// 添加Bilibili视频到播放列表
async function addBilibiliVideo() {
    // 获取Bilibili URL或BV号
    const input = prompt('请输入Bilibili视频URL或BV号:');
    if (!input || input.trim() === '') {
        return; // 用户取消或输入为空
    }

    try {
        // 调用后端API添加Bilibili视频
        const response = await apiGet('api/add_play_list_bilibili', {
            url: input.trim()
        });
        
        if (response.success) {
            show.log('Bilibili视频添加成功');
            await refreshPlaylist(); // 刷新播放列表
        } else {
            // 根据debug变量决定显示内容
            const errorMsg = (typeof debug !== 'undefined' && debug) 
                ? JSON.stringify(response.data, null, 2)
                : response.data.message;
            show.error('添加Bilibili视频失败: ' + errorMsg);
        }
    } catch (error) {
        // 根据debug变量决定显示内容
        const errorMsg = (typeof debug !== 'undefined' && debug) 
            ? error 
            : '添加Bilibili视频时发生错误';
        show.error(errorMsg);
    }
}

// 清空播放列表
async function clearPlaylist() {
    if (playlist.length === 0) return;
    
    const { success } = await api('api/clear_playlist');
    if (success) {
        playlist = [];
        currentPlaylistIndex = -1;
        renderPlaylist();
        stop(); // 停止当前播放
    }
}

// 播放模式改变时更新播放列表高亮
function updatePlaylistHighlight() {
    renderPlaylist();
}
