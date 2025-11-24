// IE6兼容的JSON解析支持
if (!window.JSON) {
    window.JSON = {};
    window.JSON.parse = function(text) {
        text = text.replace(/\\"/g, '""');
        return eval('(' + text + ')');
    };
}

// ==================== UUID与Cookie管理（IE6兼容） ====================
var UUID_KEY = "music_player_uuid";
var uuid = null;

// IE6兼容的cookie操作
function setCookie(name, value, days) {
    var expires = "";
    if (days) {
        var date = new Date();
        date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000);
        expires = "; expires=" + date.toGMTString();
    }
    document.cookie = name + "=" + value + expires + "; path=/";
}

function getCookie(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(';');
    for (var i = 0; i < ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) == ' ') c = c.substring(1);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length);
    }
    return null;
}

// 生成UUID v4（IE6兼容，无crypto）
function generateUUID() {
    var d = new Date().getTime();
    var uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = (d + Math.random() * 16) % 16 | 0;
        d = Math.floor(d / 16);
        return (c == 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
    return uuid;
}

// 初始化UUID：优先读cookie → 没有则生成 → 保存7天
function initUUID() {
    var cookieUUID = getCookie(UUID_KEY);
    if (cookieUUID) {
        uuid = cookieUUID;
    } else {
        uuid = generateUUID();
        setCookie(UUID_KEY, uuid, 7); // 7天有效
    }
    var myIdSpan = document.getElementById('myId');
    if (myIdSpan) {
        if (myIdSpan.textContent !== undefined) {
            myIdSpan.textContent = uuid.substring(0, 8) + '...';
        } else {
            myIdSpan.innerText = uuid.substring(0, 8) + '...';
        }
    }
}

// 获取带UUID参数的URL
function withUUID(url) {
    if (!uuid) return url;
    var separator = url.indexOf('?') === -1 ? '?' : '&';
    return url + separator + 'id=' + encodeURIComponent(uuid);
}

// ==================== 原有代码修改部分 ====================
var baseApiUrl = window.location.protocol + '//' + window.location.host + '/';
var lastRefreshToken = null; // 用于存储上一次的refresh_token

function createXHR() {
    var xhr;
    try { xhr = new XMLHttpRequest(); }
    catch (e) {
        try { xhr = new ActiveXObject('Microsoft.XMLHTTP'); }
        catch (e) { alert('您的浏览器不支持XMLHttpRequest'); return null; }
    }
    return xhr;
}

// 所有API调用都自动带上id参数
function callApi(action) {
    if (action) {
        var img = new Image();
        img.src = withUUID(baseApiUrl + action + '?_=' + new Date().getTime());

        var albumImg = document.images[0];
        if (albumImg) {
            albumImg.src = baseApiUrl + 'album_cover?t=' + new Date().getTime();
        }
    }
}

function delayedAction(action) {
    callApi(action);
    setTimeout(refreshAllInfo, 200);
}

function togglePlayPause() {
    var btn = document.getElementById('playPauseButton');
    if (btn && btn.innerHTML.indexOf('播放') !== -1) {
        delayedAction('api/play');
        btn.innerHTML = '暂停';
    } else {
        delayedAction('api/pause');
        btn.innerHTML = '播放';
    }
}

function formatTime(seconds) {
    if (isNaN(seconds) || seconds < 0) return '0:00';
    var mins = Math.floor(seconds / 60);
    var secs = Math.floor(seconds % 60);
    return mins + ':' + (secs < 10 ? '0' : '') + secs;
}

// 格式化时间戳函数（IE6兼容，不使用padStart）
function formatTimestamp(timestamp) {
    var date = new Date(timestamp * 1000);
    var year = date.getFullYear();
    var month = date.getMonth() + 1;
    month = month < 10 ? '0' + month : month;
    var day = date.getDate();
    day = day < 10 ? '0' + day : day;
    var hours = date.getHours();
    hours = hours < 10 ? '0' + hours : hours;
    var minutes = date.getMinutes();
    minutes = minutes < 10 ? '0' + minutes : minutes;
    var seconds = date.getSeconds();
    seconds = seconds < 10 ? '0' + seconds : seconds;
    return year + '-' + month + '-' + day + ' ' + hours + ':' + minutes + ':' + seconds;
}

// 显示在线用户详情
function showOnlineUsers() {
    try {
        var xhr = createXHR();
        if (!xhr) {
            alert('无法创建XMLHttpRequest对象');
            return;
        }
        
        xhr.open('GET', withUUID(baseApiUrl + 'api/online_users') + '&_=' + new Date().getTime(), true);
        xhr.onreadystatechange = function() {
            try {
                if (xhr.readyState === 4) {
                    if (xhr.status === 200) {
                        var data = JSON.parse(xhr.responseText);
                        var userInfo = '当前在线用户详情：\n\n';
                        var userCount = 0;
                        
                        for (var userId in data) {
                            if (data.hasOwnProperty(userId)) {
                                var user = data[userId];
                                userCount++;
                                userInfo += '用户ID: ' + userId.substring(0, 8) + '...\n';
                                userInfo += 'IP地址: ' + (user.ip || '未知') + '\n';
                                userInfo += '最后活动: ' + formatTimestamp(user.last_seen || 0) + '\n';
                                userInfo += '浏览器: ' + (user.ua || '未知') + '\n';
                                userInfo += '----------------------------\n';
                            }
                        }
                        
                        if (userCount === 0) {
                            userInfo += '暂无在线用户';
                        } else {
                            userInfo = '在线用户 (' + userCount + '):\n\n' + userInfo;
                        }
                        
                        alert(userInfo);
                    } else {
                        alert('获取在线用户信息失败，错误码：' + xhr.status);
                    }
                }
            } catch (e) {
                alert('处理在线用户信息时出错');
            }
        };
        
        xhr.send(null);
    } catch (e) {
        alert('请求在线用户信息时出错');
    }
}

function loadAudioMetadata() {
    try {
        var xhr = createXHR();
        if (!xhr) return;
        xhr.open('GET', withUUID(baseApiUrl + 'api/audio_metadata') + '&_=' + new Date().getTime(), true);
        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4 && xhr.status === 200) {
                try {
                    var metadata = JSON.parse(xhr.responseText);
                    var setText = function(id, val) {
                        var el = document.getElementById(id);
                        if (el) {
                            if (el.textContent !== undefined) el.textContent = val;
                            else el.innerText = val;
                        }
                    };
                    setText('title', metadata.title || '未知标题');
                    setText('artist', metadata.artist || '未知艺术家');
                    setText('album', metadata.album || '未知专辑');
                } catch (e) {}
            }
        };
        xhr.send(null);
    } catch (e) {}
}

function updateProgress() {
    try {
        var xhr = createXHR();
        if (!xhr) return;
        xhr.open('GET', withUUID(baseApiUrl + 'api/progress') + '&_=' + new Date().getTime(), true);
        xhr.onreadystatechange = function() {
            try {
                if (xhr.readyState !== 4) return;
                var btn = document.getElementById('playPauseButton');
                if (xhr.status === 200) {
                    var data = JSON.parse(xhr.responseText);
                    
                    // 只更新refresh_token，不再刷新整个页面
                    if (data.refresh_token && data.refresh_token !== lastRefreshToken) {
                        lastRefreshToken = data.refresh_token;
                        // 当refresh_token变化时，局部刷新关键信息
                        refreshAllInfo(); // 局部刷新图片和音频元数据
                    }
                    // 更新lastRefreshToken（如果这是第一次获取）
                    if (data.refresh_token && lastRefreshToken === null) {
                        lastRefreshToken = data.refresh_token;
                    }
                    
                    // 更新进度条
                    var fill = document.getElementById('progressFill');
                    if (fill) fill.style.width = (data.progress || 0) + '%';
                    // 更新时间
                    var td = document.getElementById('timeDisplay');
                    if (td) {
                        var txt = formatTime(data.current_time || 0) + ' / ' + formatTime(data.total_time || 0);
                        if (td.textContent !== undefined) td.textContent = txt;
                        else td.innerText = txt;
                    }
                    // 更新在线人数
                    var oc = document.getElementById('onlineCount');
                    if (oc) {
                        if (oc.textContent !== undefined) oc.textContent = data.online_users || 0;
                        else oc.innerText = data.online_users || 0;
                    }
                    
                    // 更新当前歌词
                    var lyricsEl = document.getElementById('current-lyrics');
                    if (lyricsEl) {
                        var lyricsText = data.current_lyrics || '暂无歌词';
                        if (lyricsEl.textContent !== undefined) lyricsEl.textContent = lyricsText;
                        else lyricsEl.innerText = lyricsText;
                    }
                    
                    // 更新播放暂停按钮状态
                    if (btn) btn.innerHTML = '暂停';
                } else {
                    if (btn) btn.innerHTML = '播放';
                    var oc = document.getElementById('onlineCount');
                    if (oc && oc.textContent !== undefined) oc.textContent = '0';
                    
                    // 重置歌词显示
                    var lyricsEl = document.getElementById('current-lyrics');
                    if (lyricsEl) {
                        if (lyricsEl.textContent !== undefined) lyricsEl.textContent = '暂无歌词';
                        else lyricsEl.innerText = '暂无歌词';
                    }
                }
            } catch (e) {}
        };
        xhr.send(null);
    } catch (e) {}
}

function refreshAllInfo() {
    var albumImg = document.images[0];
    if (albumImg) {
        albumImg.src = '';
        albumImg.src = baseApiUrl + '/api/album_cover?_=' + new Date().getTime();
    }
    loadAudioMetadata();
    updateProgress();
}

function startProgressUpdates() {
    try { updateProgress(); } catch (e) {}
    window.setTimeout(startProgressUpdates, 1000);
}

// ==================== 页面加载入口 ====================
window.onload = function() {
    initUUID(); // 先初始化UUID

    var albumImg = document.images[0];
    if (albumImg) {
        albumImg.src = '';
        albumImg.src = baseApiUrl + 'album_cover?_=' + new Date().getTime();
    }

    loadAudioMetadata();
    setTimeout(startProgressUpdates, 500);
};