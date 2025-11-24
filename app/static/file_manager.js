// 文件管理器 JavaScript 代码
// 提取自原有的 script.js 文件管理功能

let baseApiUrl = window.location.protocol + '//' + window.location.host;
let currentPage = 1; // 当前页码
const itemsPerPage = 15; // 每页显示的文件/文件夹数量
let currentPath = ''; // 当前目录路径
let selectedFiles = new Set(); // 选中的文件
let parentWindow = null; // 父窗口引用
let totalFiles = 0; // 总文件数

// ===== 本地存储管理 =====
const STORAGE_KEYS = {
    SEARCH_KEYWORD: 'file_manager_search_keyword',
    SEARCH_TYPE: 'file_manager_search_type',
    CURRENT_PATH: 'file_manager_current_path',
    FILE_LIST: 'file_manager_file_list',
    CURRENT_PAGE: 'file_manager_current_page'
};

// 保存数据到本地存储
function saveToLocalStorage(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify(data));
        return true;
    } catch (error) {
        console.error('保存到本地存储失败:', error);
        return false;
    }
}

// 从本地存储读取数据
function loadFromLocalStorage(key, defaultValue = null) {
    try {
        const data = localStorage.getItem(key);
        return data ? JSON.parse(data) : defaultValue;
    } catch (error) {
        console.error('从本地存储读取失败:', error);
        return defaultValue;
    }
}

// 清空所有本地存储数据
function clearAllLocalStorage() {
    try {
        Object.values(STORAGE_KEYS).forEach(key => {
            localStorage.removeItem(key);
        });
        return true;
    } catch (error) {
        console.error('清空本地存储失败:', error);
        return false;
    }
}

// 保存搜索状态
function saveSearchState(keyword, searchType) {
    saveToLocalStorage(STORAGE_KEYS.SEARCH_KEYWORD, keyword);
    saveToLocalStorage(STORAGE_KEYS.SEARCH_TYPE, searchType);
}

// 保存路径状态
function savePathState(path) {
    saveToLocalStorage(STORAGE_KEYS.CURRENT_PATH, path);
}

// 保存文件列表状态
function saveFileListState(files, path) {
    const fileListData = {
        path: path,
        files: files,
        timestamp: Date.now()
    };
    saveToLocalStorage(STORAGE_KEYS.FILE_LIST, fileListData);
}

// 保存页码状态
function savePageState(page) {
    saveToLocalStorage(STORAGE_KEYS.CURRENT_PAGE, page);
}

// ===== API 工具函数 =====
async function api(relativeUrl) {
    relativeUrl = relativeUrl.replace(/^\//, '');
    const fullUrl = baseApiUrl + '/' + relativeUrl;
    try {
        const res = await fetch(fullUrl);
        const data = await res.json();
        return res.ok && (!data.status || data.status !== "error")
            ? { success: true, data }
            : { success: false, data };
    } catch (err) {
        console.error('API Error:', err);
        return { success: false, data: null };
    }
}

function apiGet(endpoint, params = {}) {
    let relativeUrl = endpoint.replace(/^\//, '');
    if (Object.keys(params).length) {
        const searchParams = new URLSearchParams();
        Object.keys(params).forEach(k => params[k] !== undefined && searchParams.append(k, params[k]));
        relativeUrl += '?' + searchParams.toString();
    }
    return api(relativeUrl);
}

async function apiPost(endpoint, body = {}) {
    const relativeUrl = endpoint.replace(/^\//, '');
    const fullUrl = baseApiUrl + '/' + relativeUrl;
    try {
        const res = await fetch(fullUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body)
        });
        const data = await res.json();
        return res.ok && (!data.status || data.status !== "error")
            ? { success: true, data }
            : { success: false, data };
    } catch (err) {
        console.error('API Error:', err);
        return { success: false, data: null };
    }
}

// ===== 窗口管理 =====
function closeFileManager() {
    window.close();
}

// 清理缓存
function clearCache() {
    if (confirm('确定要清理所有本地缓存吗？这将清除搜索记录、路径状态和文件列表缓存。')) {
        const success = clearAllLocalStorage();
        if (success) {
            showSuccess('缓存清理成功！');
            // 重新加载当前页面以应用清理后的状态
            if (currentPath && currentPath !== '') {
                loadDirectory(currentPath);
            } else {
                loadRootDirectory();
            }
        } else {
            showError('缓存清理失败，请重试。');
        }
    }
}

// ===== 文件列表管理 =====

// 页面加载时初始化
window.onload = function() {
    // 获取父窗口引用
    if (window.opener) {
        parentWindow = window.opener;
    }
    
    // 恢复之前的状态
    restorePreviousState();
};

// 恢复之前的状态
function restorePreviousState() {
    // 恢复搜索状态
    const savedKeyword = loadFromLocalStorage(STORAGE_KEYS.SEARCH_KEYWORD, '');
    const savedSearchType = loadFromLocalStorage(STORAGE_KEYS.SEARCH_TYPE, 'normal');
    
    if (savedKeyword) {
        document.getElementById('searchInput').value = savedKeyword;
        // 设置搜索类型
        if (savedSearchType === 'regex') {
            useRegexSearch = true;
            document.getElementById('regexSearchBtn').textContent = '🔍 正则搜索';
        } else {
            useRegexSearch = false;
            document.getElementById('regexSearchBtn').textContent = '🔍 普通搜索';
        }
    }
    
    // 恢复路径状态
    const savedPath = loadFromLocalStorage(STORAGE_KEYS.CURRENT_PATH, '');
    const savedPage = loadFromLocalStorage(STORAGE_KEYS.CURRENT_PAGE, 1);
    
    if (savedPath) {
        currentPage = savedPage;
        loadDirectory(savedPath, false); // 不重置页码
    } else {
        // 载入根目录
        loadRootDirectory();
    }
    
    // 恢复文件列表状态（如果路径相同且数据较新）
    const fileListData = loadFromLocalStorage(STORAGE_KEYS.FILE_LIST, null);
    if (fileListData && fileListData.path === savedPath) {
        // 检查数据是否较新（5分钟内）
        const fiveMinutesAgo = Date.now() - 5 * 60 * 1000;
        if (fileListData.timestamp > fiveMinutesAgo) {
            displayFiles(fileListData.files, savedPath);
            displayPagination(totalFiles);
        }
    }
}

// 载入根目录（磁盘列表）
function loadRootDirectory() {
    apiGet('api/list_directory').then(({ success, data }) => {
        if (success) {
            displayDrivesAsRoot(data.drives);
            document.getElementById('pagination').innerHTML = '';
        } else {
            console.error('Error: ' + (data.message || 'Unknown error'));
            showError('加载驱动器列表失败: ' + (data.message || '未知错误'));
        }
    });
}

// 将磁盘列表显示为根目录内容
function displayDrivesAsRoot(drives) {
    const filesContainer = document.getElementById('files');
    document.getElementById('currentPath').textContent = '驱动器列表';
    currentPath = '';
    filesContainer.innerHTML = '';
    
    const list = document.createElement('ul');
    list.className = 'file-list';

    drives.forEach(function(drive) {
        const listItem = document.createElement('li');
        listItem.className = 'file-item drive-item';
        const link = document.createElement('a');
        link.textContent = drive + ':\\';
        link.href = 'javascript:void(0)';
        link.onclick = function() { 
            clearSelection();
            loadDirectory(drive + ':\\'); 
        };
        
        // 添加驱动器图标
        const icon = document.createElement('span');
        icon.className = 'file-icon';
        icon.textContent = '💿';
        
        listItem.appendChild(icon);
        listItem.appendChild(link);
        listItem.appendChild(document.createTextNode(" (进入磁盘)"));
        list.appendChild(listItem);
    });

    filesContainer.appendChild(list);
}

// 载入文件夹内容（分页）
function loadDirectory(path, resetPage = true) {
    if (resetPage || path !== currentPath) currentPage = 1;
    currentPath = path;
    clearSelection();

    apiGet('api/list_directory', {
        path: path,
        page: currentPage,
        page_size: itemsPerPage
    }).then(({ success, data }) => {
        if (success) {
            displayFiles(data.files, path);
            totalFiles = data.total_files; // 保存总文件数
            displayPagination(data.total_files);
            document.getElementById('currentPath').textContent = path;
            
            // 保存状态到本地存储
            savePathState(path);
            savePageState(currentPage);
            saveFileListState(data.files, path);
        } else {
            console.error('Error: ' + (data.message || 'Unknown error'));
            showError('加载目录失败: ' + (data.message || '未知错误'));
        }
    });
}

// 显示文件夹内容
function displayFiles(files, path) {
    const filesContainer = document.getElementById('files');
    filesContainer.innerHTML = '';
    const list = document.createElement('ul');
    list.className = 'file-list';

    // 添加返回上一级链接
    if (path && path !== '') {
        const backListItem = document.createElement('li');
        backListItem.className = 'file-item navigation-item';
        const backLink = document.createElement('a');
        backLink.innerHTML = '← 返回上一级';
        backLink.href = 'javascript:void(0)';
        backLink.onclick = goBack;
        
        const icon = document.createElement('span');
        icon.className = 'file-icon';
        icon.textContent = '⬆️';
        
        backListItem.appendChild(icon);
        backListItem.appendChild(backLink);
        list.appendChild(backListItem);
    }

    // 添加直达驱动器列表链接
    if (currentPath !== '') {
        const rootListItem = document.createElement('li');
        rootListItem.className = 'file-item navigation-item';
        const rootLink = document.createElement('a');
        rootLink.innerHTML = '📁 返回驱动器列表';
        rootLink.href = 'javascript:void(0)';
        rootLink.onclick = loadRootDirectory;
        
        const icon = document.createElement('span');
        icon.className = 'file-icon';
        icon.textContent = '🏠';
        
        rootListItem.appendChild(icon);
        rootListItem.appendChild(rootLink);
        list.appendChild(rootListItem);

        // 添加分隔线
        const divider = document.createElement('li');
        divider.className = 'divider';
        divider.textContent = '──────────';
        list.appendChild(divider);
    }

    // 添加文件和文件夹列表项
    files.forEach(file => {
        const listItem = document.createElement('li');
        listItem.className = 'file-item';
        listItem.dataset.filePath = file.path;
        listItem.dataset.fileName = file.name;
        
        const link = document.createElement('a');
        const icon = document.createElement('span');
        icon.className = 'file-icon';
        
        if (file.type === 'folder') {
            icon.textContent = '📁';
            link.textContent = file.name + '/';
            link.onclick = function() { 
                clearSelection();
                loadDirectory(file.path); 
            };
        } else {
            icon.textContent = getFileIcon(file.name);
            link.textContent = file.name;
            link.onclick = function() { 
                toggleFileSelection(file.path, file.name);
            };
        }
        
        link.href = 'javascript:void(0)';
        
        listItem.appendChild(icon);
        listItem.appendChild(link);
        
        // 在每个文件项右侧添加操作按钮
        const actions = document.createElement('div');
        actions.className = 'file-item-actions';
        
        if (file.type === 'file') {
            const playBtn = document.createElement('button');
            playBtn.className = 'file-action-btn play-btn';
            playBtn.innerHTML = '🎵';
            playBtn.title = '播放此文件';
            playBtn.onclick = function(e) {
                e.stopPropagation();
                playSingleFile(file.path);
            };
            
            const addBtn = document.createElement('button');
            addBtn.className = 'file-action-btn add-btn';
            addBtn.innerHTML = '➕';
            addBtn.title = '添加到播放列表';
            addBtn.onclick = function(e) {
                e.stopPropagation();
                addFileToPlaylist(file.path, file.name);
            };
            
            actions.appendChild(playBtn);
            actions.appendChild(addBtn);
        }
        
        listItem.appendChild(actions);
        list.appendChild(listItem);
    });

    filesContainer.appendChild(list);
    updateSelectedInfo();
}

// 获取文件图标
function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const audioExts = ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'wma'];
    const videoExts = ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'];
    const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp'];
    
    if (audioExts.includes(ext)) return '🎵';
    if (videoExts.includes(ext)) return '🎬';
    if (imageExts.includes(ext)) return '🖼️';
    return '📄';
}

// 返回上一级
function goBack() {
    if (currentPath && currentPath !== '') {
        const parentPath = currentPath.substring(0, currentPath.lastIndexOf('\\'));
        if (parentPath.length < 3) { // 驱动器根目录
            loadRootDirectory();
        } else {
            loadDirectory(parentPath);
        }
    }
}

// 文件选择管理
function toggleFileSelection(filePath, fileName) {
    if (selectedFiles.has(filePath)) {
        selectedFiles.delete(filePath);
    } else {
        selectedFiles.add(filePath);
    }
    
    updateFileSelectionDisplay();
    updateSelectedInfo();
}

function updateFileSelectionDisplay() {
    const fileItems = document.querySelectorAll('.file-item');
    fileItems.forEach(item => {
        const filePath = item.dataset.filePath;
        if (filePath && selectedFiles.has(filePath)) {
            item.classList.add('selected');
        } else {
            item.classList.remove('selected');
        }
    });
}

function clearSelection() {
    selectedFiles.clear();
    updateFileSelectionDisplay();
    updateSelectedInfo();
}

function updateSelectedInfo() {
    const selectedCount = document.getElementById('selectedCount');
    const count = selectedFiles.size;
    if (count === 0) {
        selectedCount.textContent = '未选择文件';
        document.getElementById('playInPlayerBtn').disabled = true;
        document.getElementById('addToPlaylistBtn').disabled = true;
    } else if (count === 1) {
        selectedCount.textContent = '已选择 1 个文件';
        document.getElementById('playInPlayerBtn').disabled = false;
        document.getElementById('addToPlaylistBtn').disabled = false;
    } else {
        selectedCount.textContent = `已选择 ${count} 个文件`;
        document.getElementById('playInPlayerBtn').disabled = true;
        document.getElementById('addToPlaylistBtn').disabled = false;
    }
}

// ===== 分页功能 =====
function displayPagination(totalFiles) {
    const paginationContainer = document.getElementById('pagination');
    const totalPages = Math.ceil(totalFiles / itemsPerPage);
    
    if (totalPages <= 1) {
        paginationContainer.innerHTML = '';
        return;
    }
    
    let paginationHTML = '';
    
    // 上一页
    if (currentPage > 1) {
        paginationHTML += `<button onclick="changePage(${currentPage - 1})">« 上一页</button>`;
    }
    
    // 页面信息和跳转输入框
    paginationHTML += `
        <span class="page-info">第 ${currentPage} 页，共 ${totalPages} 页</span>
        <input type="number" id="pageInput" min="1" max="${totalPages}" value="${currentPage}" 
               style="width: 60px; padding: 5px; margin: 0 5px;">
        <button onclick="jumpToPage()">跳转</button>
    `;
    
    // 下一页
    if (currentPage < totalPages) {
        paginationHTML += `<button onclick="changePage(${currentPage + 1})">下一页 »</button>`;
    }
    
    // 添加键盘回车支持
    setTimeout(() => {
        const pageInput = document.getElementById('pageInput');
        if (pageInput) {
            pageInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    jumpToPage();
                }
            });
        }
    }, 100);
    
    paginationContainer.innerHTML = paginationHTML;
}

function changePage(page) {
    currentPage = page;
    loadDirectory(currentPath, false);
}

function jumpToPage() {
    const pageInput = document.getElementById('pageInput');
    if (pageInput) {
        const targetPage = parseInt(pageInput.value);
        const totalPages = Math.ceil(totalFiles / itemsPerPage);
        
        if (isNaN(targetPage) || targetPage < 1 || targetPage > totalPages) {
            showError(`请输入有效的页码 (1-${totalPages})`);
            pageInput.value = currentPage; // 重置为当前页
            return;
        }
        
        currentPage = targetPage;
        loadDirectory(currentPath, false);
    }
}

// ===== 主播放器操作 =====

// 在主播放器中播放选中文件（不关闭文件管理器）
function playInMainPlayer() {
    if (selectedFiles.size === 1) {
        const filePath = Array.from(selectedFiles)[0];
        
        apiGet('api/set_file', { file: filePath }).then(({ success, data }) => {
            if (success) {
                showSuccess('已在主播放器中打开文件');
                // 立即开始播放
                apiGet('api/play').then(({ success: playSuccess }) => {
                    if (playSuccess) {
                        if (parentWindow) {
                            parentWindow.focus();
                        }
                    } else {
                        showError('开始播放失败');
                    }
                });
            } else {
                showError('打开文件失败: ' + (data.message || '未知错误'));
            }
        });
    }
}

// 播放单个文件（不关闭文件管理器）
function playSingleFile(filePath) {
    apiGet('api/set_file', { file: filePath }).then(({ success, data }) => {
        if (success) {
            showSuccess('已在主播放器中打开文件');
            // 立即开始播放
            apiGet('api/play').then(({ success: playSuccess }) => {
                if (playSuccess) {
                    if (parentWindow) {
                        parentWindow.focus();
                    }
                } else {
                    showError('开始播放失败');
                }
            });
        } else {
            showError('打开文件失败: ' + (data.message || '未知错误'));
        }
    });
}

// 添加单个文件到播放列表（不关闭文件管理器）
function addFileToPlaylist(filePath, fileName) {
    apiGet('api/add_to_playlist', { 
        name: fileName, 
        path: filePath 
    }).then(({ success, data }) => {
        if (success) {
            showSuccess(`已添加 ${fileName} 到播放列表`);
            // 通知主窗口刷新播放列表
            if (parentWindow) {
                parentWindow.postMessage({ type: 'playlistUpdated' }, '*');
            }
        } else {
            showError(`添加 ${fileName} 失败: ${data.message || '未知错误'}`);
        }
    });
}

// 添加到播放列表（不关闭文件管理器）
function addToPlaylist() {
    if (selectedFiles.size === 0) return;
    
    let successCount = 0;
    let totalCount = selectedFiles.size;
    
    selectedFiles.forEach(filePath => {
        const fileName = filePath.split('\\').pop();
        
        apiGet('api/add_to_playlist', { 
            name: fileName, 
            path: filePath 
        }).then(({ success, data }) => {
            if (success) {
                successCount++;
                
                if (successCount === totalCount) {
                    showSuccess(`成功添加 ${successCount} 个文件到播放列表`);
                    if (parentWindow) {
                        parentWindow.postMessage({ type: 'playlistUpdated' }, '*');
                    }
                }
            } else {
                showError(`添加 ${fileName} 失败: ${data.message || '未知错误'}`);
            }
        });
    });
}

// ===== 消息显示 =====
function showError(message) {
    showMessage(message, 'error');
}

function showSuccess(message) {
    showMessage(message, 'success');
}

function showMessage(message, type) {
    // 移除现有消息
    const existingMessage = document.querySelector('.fm-message');
    if (existingMessage) {
        existingMessage.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `fm-message ${type}`;
    messageDiv.textContent = message;
    
    document.querySelector('.file-manager-container').appendChild(messageDiv);
    
    // 3秒后自动移除
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.remove();
        }
    }, 3000);
}

// ===== 搜索功能 =====
let isSearching = false;
let searchTimeout = null;
let useRegexSearch = false;

// 切换搜索框显示/隐藏
function toggleSearch() {
    const searchContainer = document.getElementById('searchContainer');
    const searchBtn = document.getElementById('searchBtn');
    
    if (searchContainer.style.display === 'none') {
        searchContainer.style.display = 'block';
        searchBtn.textContent = '🔍 关闭搜索';
        document.getElementById('searchInput').focus();
    } else {
        searchContainer.style.display = 'none';
        searchBtn.textContent = '🔍 搜索';
        clearSearch();
    }
}

// 切换正则搜索模式
function toggleRegexSearch() {
    const regexBtn = document.getElementById('regexSearchBtn');
    useRegexSearch = !useRegexSearch;
    
    if (useRegexSearch) {
        regexBtn.textContent = '🔍 正则搜索';
        regexBtn.style.background = '#28a745';
        showSuccess('已启用正则搜索模式');
    } else {
        regexBtn.textContent = '🔍 普通搜索';
        regexBtn.style.background = '#17a2b8';
        showSuccess('已启用普通搜索模式');
    }
    
    // 如果当前有搜索关键词，重新执行搜索
    const searchInput = document.getElementById('searchInput');
    const keyword = searchInput.value.trim();
    if (keyword) {
        performSearch(keyword);
    }
}

// 构建索引
async function buildIndex() {
    if (!currentPath || currentPath === '') {
        showError('请先选择一个目录');
        return;
    }
    
    const buildIndexBtn = document.getElementById('buildIndexBtn');
    const searchStatus = document.getElementById('searchStatus');
    
    buildIndexBtn.disabled = true;
    buildIndexBtn.textContent = '⏳ 构建中...';
    searchStatus.textContent = '正在构建索引，请稍候...';
    searchStatus.className = 'search-status building';
    
    try {
        const { success, data } = await apiGet('api/set_index', { path: currentPath });
        
        if (success) {
            searchStatus.textContent = `索引构建成功！已索引 ${data.file_count || 0} 个文件`;
            searchStatus.className = 'search-status success';
            showSuccess(`索引构建成功，可开始搜索`);
        } else {
            searchStatus.textContent = `索引构建失败: ${data.message || '未知错误'}`;
            searchStatus.className = 'search-status error';
            showError(`索引构建失败: ${data.message || '未知错误'}`);
        }
    } catch (error) {
        searchStatus.textContent = `索引构建失败: ${error.message}`;
        searchStatus.className = 'search-status error';
        showError(`索引构建失败: ${error.message}`);
    } finally {
        buildIndexBtn.disabled = false;
        buildIndexBtn.textContent = '📊 构建索引';
    }
}

// 处理搜索输入
function handleSearch() {
    const searchInput = document.getElementById('searchInput');
    const keyword = searchInput.value.trim();
    
    // 清除之前的定时器
    if (searchTimeout) {
        clearTimeout(searchTimeout);
    }
    
    // 如果关键词为空，显示正常文件列表
    if (!keyword) {
        if (currentPath && currentPath !== '') {
            loadDirectory(currentPath);
        } else {
            loadRootDirectory();
        }
        return;
    }
    
    // 设置延迟搜索，避免频繁请求
    searchTimeout = setTimeout(() => {
        performSearch(keyword);
    }, 300);
}

// 执行搜索
async function performSearch(keyword) {
    if (isSearching) return;
    
    isSearching = true;
    const searchStatus = document.getElementById('searchStatus');
    
    try {
        searchStatus.textContent = useRegexSearch ? '正则搜索中...' : '搜索中...';
        searchStatus.className = 'search-status searching';
        
        // 如果是正则搜索，清理可能的前缀（如r"）
        let cleanedKeyword = keyword;
        if (useRegexSearch) {
            // 去除Python原始字符串前缀 r" 或 r'
            cleanedKeyword = cleanedKeyword.replace(/^r['"]/, '');
            // 去除结尾的引号
            cleanedKeyword = cleanedKeyword.replace(/['"]$/, '');
        }
        
        // 保存搜索状态到本地存储
        saveSearchState(keyword, useRegexSearch ? 'regex' : 'normal');
        
        const { success, data } = await apiPost('api/search', { 
            keyword: cleanedKeyword,
            re: useRegexSearch 
        });
        
        if (success) {
            displaySearchResults(data.files, keyword, data.match_count, data.search_type);
            searchStatus.textContent = `找到 ${data.match_count} 个匹配文件 (${data.search_type === 'regex' ? '正则' : '普通'}搜索)`;
            searchStatus.className = 'search-status success';
        } else {
            searchStatus.textContent = `搜索失败: ${data.message || '未知错误'}`;
            searchStatus.className = 'search-status error';
            showError(`搜索失败: ${data.message || '未知错误'}`);
        }
    } catch (error) {
        searchStatus.textContent = `搜索失败: ${error.message}`;
        searchStatus.className = 'search-status error';
        showError(`搜索失败: ${error.message}`);
    } finally {
        isSearching = false;
    }
}

// 显示搜索结果
function displaySearchResults(files, keyword, matchCount, searchType) {
    const filesContainer = document.getElementById('files');
    const paginationContainer = document.getElementById('pagination');
    
    filesContainer.innerHTML = '';
    paginationContainer.innerHTML = '';
    
    const searchTypeText = searchType === 'regex' ? '正则搜索' : '普通搜索';
    document.getElementById('currentPath').textContent = `${searchTypeText}结果: "${keyword}" (${matchCount} 个文件)`;
    
    if (matchCount === 0) {
        const noResults = document.createElement('div');
        noResults.className = 'no-results';
        noResults.textContent = '未找到匹配的文件';
        filesContainer.appendChild(noResults);
        return;
    }
    
    const list = document.createElement('ul');
    list.className = 'file-list';
    
    // 添加返回正常浏览的链接
    const backListItem = document.createElement('li');
    backListItem.className = 'file-item navigation-item';
    const backLink = document.createElement('a');
    backLink.innerHTML = '← 返回文件浏览';
    backLink.href = 'javascript:void(0)';
    backLink.onclick = function() {
        if (currentPath && currentPath !== '') {
            loadDirectory(currentPath);
        } else {
            loadRootDirectory();
        }
    };
    
    const icon = document.createElement('span');
    icon.className = 'file-icon';
    icon.textContent = '📁';
    
    backListItem.appendChild(icon);
    backListItem.appendChild(backLink);
    list.appendChild(backListItem);
    
    // 添加分隔线
    const divider = document.createElement('li');
    divider.className = 'divider';
    divider.textContent = '──────────';
    list.appendChild(divider);
    
    // 显示搜索结果
    files.forEach(filePath => {
        const fileName = filePath.split('\\').pop();
        const directoryPath = filePath.substring(0, filePath.lastIndexOf('\\'));
        
        const listItem = document.createElement('li');
        listItem.className = 'file-item search-result';
        listItem.dataset.filePath = filePath;
        listItem.dataset.fileName = fileName;
        
        const link = document.createElement('a');
        const icon = document.createElement('span');
        icon.className = 'file-icon';
        icon.textContent = getFileIcon(fileName);
        
        link.textContent = fileName;
        link.href = 'javascript:void(0)';
        link.onclick = function() { 
            toggleFileSelection(filePath, fileName);
        };
        
        // 显示完整路径
        const pathSpan = document.createElement('span');
        pathSpan.className = 'file-path';
        pathSpan.textContent = ` (${directoryPath})`;
        
        listItem.appendChild(icon);
        listItem.appendChild(link);
        listItem.appendChild(pathSpan);
        
        // 添加操作按钮
        const actions = document.createElement('div');
        actions.className = 'file-item-actions';
        
        const playBtn = document.createElement('button');
        playBtn.className = 'file-action-btn play-btn';
        playBtn.innerHTML = '🎵';
        playBtn.title = '播放此文件';
        playBtn.onclick = function(e) {
            e.stopPropagation();
            playSingleFile(filePath);
        };
        
        const addBtn = document.createElement('button');
        addBtn.className = 'file-action-btn add-btn';
        addBtn.innerHTML = '➕';
        addBtn.title = '添加到播放列表';
        addBtn.onclick = function(e) {
            e.stopPropagation();
            addFileToPlaylist(filePath, fileName);
        };
        
        actions.appendChild(playBtn);
        actions.appendChild(addBtn);
        listItem.appendChild(actions);
        
        list.appendChild(listItem);
    });
    
    filesContainer.appendChild(list);
    clearSelection();
}

// 清除搜索
function clearSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchStatus = document.getElementById('searchStatus');
    
    searchInput.value = '';
    searchStatus.textContent = '';
    searchStatus.className = 'search-status';
    
    // 清除本地存储中的搜索状态
    saveSearchState('', 'normal');
    
    if (searchTimeout) {
        clearTimeout(searchTimeout);
        searchTimeout = null;
    }
    
    if (currentPath && currentPath !== '') {
        loadDirectory(currentPath);
    } else {
        loadRootDirectory();
    }
}