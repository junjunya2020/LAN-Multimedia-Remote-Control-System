// 音轨控制功能

// 切换音频轨道
async function changeAudioTrack() {
    const audioTrackSelect = document.getElementById('audioTrackSelect');
    if (!audioTrackSelect) {
        console.error('音频轨道选择器未找到');
        return;
    }
    
    const selectedTrack = audioTrackSelect.value;
    const trackNames = {
        '0': '正常播放',
        '1': '人声',
        '2': '伴奏'
    };
    
    const trackName = trackNames[selectedTrack] || `轨道${selectedTrack}`;
    
    try {
        show.log(`正在切换到: ${trackName}`);
        
        const { success, data } = await apiGet('api/set_audio_track', { track: selectedTrack });
        
        if (success) {
            show.log(`音轨切换成功: ${trackName}`);
            
            // 广播音轨切换状态（如果有Socket.IO连接）
            if (typeof socket !== 'undefined' && socket && socket.connected) {
                socket.emit('audio_track_change', {
                    track: selectedTrack,
                    trackName: trackName,
                    timestamp: Date.now()
                });
            }
        } else {
            show.error('切换音轨失败:', data?.message || '未知错误');
            // 恢复选择器到之前的状态
            restoreAudioTrackSelect();
        }
    } catch (error) {
        show.error('切换音轨时出错:', error);
        // 恢复选择器到之前的状态
        restoreAudioTrackSelect();
    }
}

// 恢复音频轨道选择器到之前的状态
function restoreAudioTrackSelect() {
    const audioTrackSelect = document.getElementById('audioTrackSelect');
    if (audioTrackSelect) {
        // 这里可以根据需要恢复之前的状态
        // 目前简单重置为0（正常播放）
        audioTrackSelect.value = '0';
    }
}

// 获取当前音频轨道状态
async function getCurrentAudioTrack() {
    try {
        const { success, data } = await api('api/audio_metadata');
        if (success && data) {
            // 注意：这里需要后端返回当前音轨信息
            // 目前先返回默认的0
            return 0;
        }
        return 0;
    } catch (error) {
        console.error('获取当前音轨失败:', error);
        return 0;
    }
}

// 初始化音轨选择器
async function initAudioTrackSelect() {
    const audioTrackSelect = document.getElementById('audioTrackSelect');
    if (!audioTrackSelect) {
        console.error('音频轨道选择器未找到');
        return;
    }
    
    try {
        // 获取当前音轨状态
        const currentTrack = await getCurrentAudioTrack();
        
        // 设置选择器值
        audioTrackSelect.value = String(currentTrack);
        
        show.debug('音轨选择器初始化完成');
    } catch (error) {
        show.error('初始化音轨选择器失败:', error);
    }
}

// 监听Socket.IO音轨切换事件
function setupAudioTrackSocketListeners() {
    if (typeof socket !== 'undefined' && socket) {
        socket.on('audio_track_change', function(data) {
            if (data && typeof data.track !== 'undefined') {
                const audioTrackSelect = document.getElementById('audioTrackSelect');
                if (audioTrackSelect) {
                    audioTrackSelect.value = String(data.track);
                    show.log(`音轨已切换: ${data.trackName || '轨道' + data.track}`);
                }
            }
        });
    }
}

// AI分离音频功能
async function aiSeparateAudio() {
    const aiSeparateBtn = document.getElementById('aiSeparateBtn');
    
    if (!aiSeparateBtn) {
        show.error('AI分离按钮未找到');
        return;
    }
    
    try {
        // 禁用按钮并显示处理中状态
        aiSeparateBtn.disabled = true;
        const originalText = aiSeparateBtn.innerHTML;
        aiSeparateBtn.innerHTML = '🤖 處理中...';
        show.log('正在開始AI分離音頻...');
        
        // 获取当前音频文件路径
        show.log('正在獲取音頻文件路徑...');
        const { success: metadataSuccess, data: metadata } = await apiGet('api/audio_metadata');
        
        if (!metadataSuccess || !metadata || !metadata.file_path) {
            show.error('無法獲取音頻文件路徑');
            return;
        }
        
        const filePath = metadata.file_path;
        show.log('文件路徑:', filePath);
        
        // 调用AI分离音频API
        show.log('正在調用AI分離接口...');
        const { success, data } = await apiGet('api/ai_separate_audio', { file_path: filePath });
        
        if (success) {
            show.log('AI分離成功:', data);
            
            // 显示分离结果
            if (data.message) {
                show.success(data.message);
            }
            
            // 如果有输出文件路径，显示它们
            if (data.vocal_path) {
                show.success('人聲文件已保存: ' + data.vocal_path);
            }
            if (data.accompaniment_path) {
                show.success('伴奏文件已保存: ' + data.accompaniment_path);
            }
            
            // 可选：自动切换到人声音轨
            if (data.vocal_path) {
                const audioTrackSelect = document.getElementById('audioTrackSelect');
                if (audioTrackSelect) {
                    audioTrackSelect.value = '1'; // 切换到人聲
                    show.log('已自動切換到人聲音軌');
                }
            }
        } else {
            show.error('AI分離失敗:', data?.message || '未知錯誤');
        }
        
    } catch (error) {
        show.error('AI分離音頻時出錯:', error);
    } finally {
        // 恢复按钮状态
        if (aiSeparateBtn) {
            aiSeparateBtn.disabled = false;
            aiSeparateBtn.innerHTML = '🤖 AI分離';
        }
    }
}

// 页面加载时初始化音轨控制
window.addEventListener('DOMContentLoaded', function() {
    initAudioTrackSelect();
    setupAudioTrackSocketListeners();
});