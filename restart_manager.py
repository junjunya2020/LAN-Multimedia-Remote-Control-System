#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重启管理器
独立的重启脚本，用于优雅地重启音频播放系统
"""

import os
import sys
import time
import signal
import subprocess
import psutil
import requests
from datetime import datetime

def get_current_process_info():
    """获取当前进程信息"""
    current_pid = os.getpid()
    current_process = psutil.Process(current_pid)
    
    # 查找可能的播放器进程
    player_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'python' in cmdline[0].lower():
                # 检查是否是播放器进程
                for arg in cmdline:
                    if 'run.py' in arg or 'uvicorn' in arg:
                        player_processes.append(proc)
                        break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return current_pid, player_processes

def send_termination_signal(processes):
    """向进程发送终止信号"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始发送终止信号...")
    
    terminated_pids = []
    for proc in processes:
        try:
            pid = proc.info['pid']
            print(f"  - 向进程 {pid} 发送 SIGTERM 信号")
            proc.terminate()  # 发送 SIGTERM 信号
            terminated_pids.append(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"  - 无法终止进程 {proc.info['pid']}: {e}")
    
    return terminated_pids

def wait_for_process_termination(processes, timeout=30):
    """等待进程终止"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 等待进程终止 (超时: {timeout}秒)...")
    
    start_time = time.time()
    remaining_processes = processes.copy()
    
    while time.time() - start_time < timeout:
        for proc in remaining_processes[:]:
            try:
                if not proc.is_running():
                    print(f"  - 进程 {proc.info['pid']} 已终止")
                    remaining_processes.remove(proc)
            except psutil.NoSuchProcess:
                print(f"  - 进程 {proc.info['pid']} 已终止")
                remaining_processes.remove(proc)
        
        if not remaining_processes:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 所有进程已成功终止")
            return True
        
        time.sleep(1)
    
    # 超时后强制终止
    if remaining_processes:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 超时，强制终止剩余进程...")
        for proc in remaining_processes:
            try:
                proc.kill()  # 发送 SIGKILL 信号
                print(f"  - 强制终止进程 {proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                print(f"  - 无法强制终止进程 {proc.info['pid']}: {e}")
    
    return len(remaining_processes) == 0

def start_new_process():
    """启动新的播放器进程"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 启动新的播放器进程...")
    
    try:
        # 获取项目目录和绝对路径
        project_dir = os.path.dirname(os.path.abspath(__file__))
        python_exe = os.path.abspath(sys.executable)
        run_py = os.path.join(project_dir, "run.py")
        
        # 切换到项目目录
        os.chdir(project_dir)
        
        # 在Windows上使用cmd /c start启动新控制台窗口
        if os.name == 'nt':
            # 使用绝对路径，确保cmd /c start能找到正确的文件
            cmd = f'cmd /c start "音频播放器" "{python_exe}" "{run_py}"'
            process = subprocess.Popen(
                cmd,
                cwd=project_dir,
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            # 非Windows系统保持原有逻辑
            cmd = [python_exe, run_py]
            process = subprocess.Popen(cmd, cwd=project_dir)
        
        print(f"  - 新进程已启动，PID: {process.pid}")
        print(f"  - Python路径: {python_exe}")
        print(f"  - 运行文件: {run_py}")
        return process
    except Exception as e:
        print(f"  - 启动新进程失败: {e}")
        return None

def wait_for_service_ready(timeout=60):
    """等待服务启动完成"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 等待服务启动 (超时: {timeout}秒)...")
    
    start_time = time.time()
    url = "http://127.0.0.1:5000/static/default/index.html"
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 服务已成功启动并可以访问")
                return True
        except requests.exceptions.RequestException:
            # 服务还未启动，继续等待
            pass
        
        time.sleep(2)
        print(f"  - 等待服务启动... ({int(time.time() - start_time)}秒)")
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 服务启动超时")
    return False

def main():
    """主函数"""
    print("=" * 60)
    print("音频播放系统重启管理器")
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 获取当前进程信息
    current_pid, player_processes = get_current_process_info()
    
    if not player_processes:
        print("[错误] 未找到正在运行的播放器进程")
        print("启动进程")

    
    print(f"发现 {len(player_processes)} 个播放器相关进程:")
    for proc in player_processes:
        try:
            cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else 'N/A'
            print(f"  - PID {proc.info['pid']}: {cmdline}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            print(f"  - PID {proc.info['pid']}: [无法获取信息]")
    
    # 步骤1: 发送终止信号
    terminated_pids = send_termination_signal(player_processes)
    
    # 步骤2: 等待进程终止
    if not wait_for_process_termination(player_processes, timeout=30):
        print("[警告] 部分进程可能未完全终止")
    
    # 步骤3: 启动新进程
    new_process = start_new_process()
    if not new_process:
        print("[错误] 无法启动新进程")
        return False
    
    # 步骤4: 等待服务就绪
    if wait_for_service_ready(timeout=60):
        print("=" * 60)
        print("✅ 重启成功!")
        print(f"新进程PID: {new_process.pid}")
        print("服务已正常启动并可以访问")
        print("=" * 60)
        return True
    else:
        print("=" * 60)
        print("❌ 重启失败!")
        print("服务启动超时或无法访问")
        print("=" * 60)
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n重启过程被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"重启过程中发生错误: {e}")
        sys.exit(1)