// 设置音量
async function setVolume(volume, isUserAction = false) {
    if (volume < 0 || volume > 100) {
        show.error('音量值必须在0-100之间');
        return false;
    }
    
    // 如果是用户操作，记录时间戳
    if (isUserAction) {
        lastUserVolumeUpdate = Date.now();
    }
    
    try {
        const { success, data } = await apiGet('api/set_volume', { volume: volume });
        if (success) {
            updateVolumeDisplay(volume);
            //show.log(`音量已设置为: ${volume}%`);
            return true;
        } else {
            show.error('设置音量失败:', data?.message || '未知错误');
            return false;
        }
    } catch (error) {
        show.error('设置音量时出错:', error);
        return false;
    }
}

// 更新音量显示
function updateVolumeDisplay(volume) {
    const volumeFill = document.getElementById('volume-fill');
    const volumeValue = document.getElementById('volume-value');
    
    if (volumeFill && volumeValue) {
        volumeFill.style.width = `${volume}%`;
        volumeValue.textContent = `${volume}%`;
        
        // 根据音量值调整颜色
        if (volume === 0) {
            volumeFill.style.background = '#95a5a6'; // 静音时为灰色
        } else if (volume <= 30) {
            volumeFill.style.background = '#2ecc71'; // 低音量时为绿色
        } else if (volume <= 70) {
            volumeFill.style.background = '#f39c12'; // 中音量时为橙色
        } else {
            volumeFill.style.background = '#e74c3c'; // 高音量时为红色
        }
    }
}

// 点击音量条设置音量
function setVolumeFromClick(event) {
    const volumeBar = event.currentTarget;
    const rect = volumeBar.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const percentage = Math.max(0, Math.min(100, (clickX / rect.width) * 100));
    
    setVolume(Math.round(percentage));
}

// 音量条拖动功能
let isDraggingVolume = false;
let lastUserVolumeUpdate = 0; // 记录用户最后一次更新音量的时间戳

// 初始化音量条拖动事件
document.addEventListener('DOMContentLoaded', function() {
    const volumeBar = document.querySelector('.volume-bar');
    
    if (volumeBar) {
        // 鼠标按下开始拖动
        volumeBar.addEventListener('mousedown', function(event) {
            isDraggingVolume = true;
            lastUserVolumeUpdate = Date.now(); // 记录用户操作时间
            updateVolumeOnDrag(event);
        });
        
        // 鼠标移动时更新音量
        document.addEventListener('mousemove', function(event) {
            if (isDraggingVolume) {
                updateVolumeOnDrag(event);
            }
        });
        
        // 鼠标释放时结束拖动
        document.addEventListener('mouseup', function() {
            if (isDraggingVolume) {
                isDraggingVolume = false;
            }
        });
        
        // 触摸设备支持
        volumeBar.addEventListener('touchstart', function(event) {
            isDraggingVolume = true;
            lastUserVolumeUpdate = Date.now(); // 记录用户操作时间
            event.preventDefault();
            updateVolumeOnTouch(event);
        });
        
        document.addEventListener('touchmove', function(event) {
            if (isDraggingVolume) {
                event.preventDefault();
                updateVolumeOnTouch(event);
            }
        });
        
        document.addEventListener('touchend', function() {
            if (isDraggingVolume) {
                isDraggingVolume = false;
            }
        });
    }
});

// 拖动时更新音量
function updateVolumeOnDrag(event) {
    const volumeBar = document.querySelector('.volume-bar');
    if (!volumeBar) return;
    
    const rect = volumeBar.getBoundingClientRect();
    const clientX = event.clientX || event.touches?.[0]?.clientX;
    
    if (clientX) {
        const clickX = clientX - rect.left;
        const percentage = Math.max(0, Math.min(100, (clickX / rect.width) * 100));
        
        // 实时更新显示但不发送API请求
        updateVolumeDisplay(Math.round(percentage));
    }
}

// 触摸设备音量更新
function updateVolumeOnTouch(event) {
    const volumeBar = document.querySelector('.volume-bar');
    if (!volumeBar) return;
    
    const rect = volumeBar.getBoundingClientRect();
    const touch = event.touches[0];
    
    if (touch) {
        const touchX = touch.clientX - rect.left;
        const percentage = Math.max(0, Math.min(100, (touchX / rect.width) * 100));
        
        // 实时更新显示但不发送API请求
        updateVolumeDisplay(Math.round(percentage));
    }
}

// 鼠标释放时发送音量设置请求
document.addEventListener('mouseup', function() {
    if (isDraggingVolume) {
        const volumeFill = document.getElementById('volume-fill');
        if (volumeFill) {
            const currentWidth = parseFloat(volumeFill.style.width);
            if (!isNaN(currentWidth)) {
                setVolume(Math.round(currentWidth), true);
            }
        }
        isDraggingVolume = false;
    }
});

// 触摸结束时发送音量设置请求
document.addEventListener('touchend', function() {
    if (isDraggingVolume) {
        const volumeFill = document.getElementById('volume-fill');
        if (volumeFill) {
            const currentWidth = parseFloat(volumeFill.style.width);
            if (!isNaN(currentWidth)) {
                setVolume(Math.round(currentWidth), true);
            }
        }
        isDraggingVolume = false;
    }
});
