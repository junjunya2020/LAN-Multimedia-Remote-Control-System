// ===== Console 封装类 =====
class ConsoleWrapper {
    
    constructor() {
        // 保存原始console对象
        this.originalConsole = console;
    }

    // 显示消息的函数
    showMessage(message, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `fm-message ${type}`;
        messageDiv.textContent = message;
        
        // 尝试添加到文件管理器容器，如果不存在则添加到body
        const container = document.querySelector('.file-manager-container') || document.body;
        container.appendChild(messageDiv);
        
        // 计算所有消息的高度，实现垂直堆叠
        this.updateMessagePositions();
        
        // 3秒后自动移除
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.remove();
                // 重新调整其他消息的位置
                this.updateMessagePositions();
            }
        }, 3000);
        
        // 点击消息也可以关闭
        messageDiv.addEventListener('click', () => {
            if (messageDiv.parentNode) {
                messageDiv.remove();
                this.updateMessagePositions();
            }
        });
    }
    
    // 更新消息位置，实现垂直堆叠
    updateMessagePositions() {
        const messages = document.querySelectorAll('.fm-message');
        const baseTop = 20; // 第一个消息的top位置
        
        messages.forEach((message, index) => {
            const newTop = baseTop + (index * 80); // 每个消息间隔80px
            message.style.top = `${newTop}px`;
        });
    }

    // 封装所有console方法
    log(...args) {
        this.originalConsole.log(...args);
        // 显示消息弹窗
        const message = args.map(arg => 
            typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
        ).join(' ');
        this.showMessage(message, 'info');
        // 用户可以在此添加自定义逻辑
        this.onLog(...args);
    }

    error(...args) {
        this.originalConsole.error(...args);
        // 显示错误消息弹窗
        const message = args.map(arg => 
            typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
        ).join(' ');
        this.showMessage(message, 'error');
        // 用户可以在此添加自定义逻辑
        this.onError(...args);
    }

    warn(...args) {
        this.originalConsole.warn(...args);
        // 显示警告消息弹窗
        const message = args.map(arg => 
            typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
        ).join(' ');
        this.showMessage(message, 'warn');
        // 用户可以在此添加自定义逻辑
        this.onWarn(...args);
    }

    info(...args) {
        // show.info时调用console.log，完全复制console逻辑
        this.originalConsole.log(...args);
        // 用户可以在此添加自定义逻辑
        this.onLog(...args);
    }

    debug(...args) {
        this.originalConsole.debug(...args);
        
        // 如果debug为true，显示调试信息弹窗
        if (window.debug || debug) {
            const message = args.map(arg => 
                typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
            ).join(' ');
            this.showMessage(message, 'debug');
        }
        
        // 用户可以在此添加自定义逻辑
        this.onDebug(...args);
    }

    trace(...args) {
        this.originalConsole.trace(...args);
    }

    clear() {
        this.originalConsole.clear();
    }

    assert(assertion, ...args) {
        this.originalConsole.assert(assertion, ...args);
    }

    count(label = 'default') {
        this.originalConsole.count(label);
    }

    countReset(label = 'default') {
        this.originalConsole.countReset(label);
    }

    dir(obj) {
        this.originalConsole.dir(obj);
    }

    group(...args) {
        this.originalConsole.group(...args);
    }

    groupCollapsed(...args) {
        this.originalConsole.groupCollapsed(...args);
    }

    groupEnd() {
        this.originalConsole.groupEnd();
    }

    table(data) {
        this.originalConsole.table(data);
    }

    time(label = 'default') {
        this.originalConsole.time(label);
    }

    timeEnd(label = 'default') {
        this.originalConsole.timeEnd(label);
    }

    timeLog(label = 'default', ...args) {
        this.originalConsole.timeLog(label, ...args);
    }

    timeStamp(label) {
        this.originalConsole.timeStamp(label);
    }

    timeline(...args) {
        this.originalConsole.timeline(...args);
    }

    timelineEnd(...args) {
        this.originalConsole.timelineEnd(...args);
    }

    // 用户可重写的回调方法
    onLog(...args) {
        // 用户可以重写此方法来添加自定义逻辑
        // 例如：发送到服务器、记录到文件等
    }

    onError(...args) {
        // 用户可以重写此方法来添加自定义逻辑
    }

    onWarn(...args) {
        // 用户可以重写此方法来添加自定义逻辑
    }

    onDebug(...args) {
        // 用户可以重写此方法来添加自定义逻辑
    }
}