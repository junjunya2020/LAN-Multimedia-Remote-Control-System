//进度更新
// 启动进度更新
function startProgressUpdates() {
    // 先检查是否启用了WebSocket，如果是则不启动轮询
    const checkbox = document.getElementById('enableSocket');
    if (checkbox && checkbox.checked) {
        show.log('WebSocket已启用，跳过轮询启动');
        return;
    }
    
    // 先停止之前的定时器
    stopProgressUpdates();
    // 立即更新一次
    updateProgress();
    // 用这种老旧的接口该有的惩罚！
    time_sleep=Math.floor(Math.random() * 2000) + 1000;
    progressInterval = setInterval(updateProgress, time_sleep);
    show.debug('轮询已启动');
}

// 停止进度更新
function stopProgressUpdates() {
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
        show.debug('轮询已停止');
    }
}