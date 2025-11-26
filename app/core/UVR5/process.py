import asyncio
import os
import shutil
import tempfile  # 用于获取临时目录
import multiprocessing
from multiprocessing import Pool, Manager, current_process
import signal
import threading
import psutil
import time
from pydub import AudioSegment
from audio_separator.separator import Separator

class VocalSeparationAsync:
    def __init__(self, max_workers=None):
        self.input_path = None                    # 源文件路径
        self.model_name = None                    # 要加载的模型名称（如 "UVR-MDX-NET-HQ"）
        self.vocal_output_path = None             # 人声音轨输出
        self.instrumental_output_path = None      # 伴奏输出
        self.save_format = ".mp3"                 # 默认保存格式
        
        # 进程池相关
        self.max_workers = max_workers or multiprocessing.cpu_count()  # 最大进程数
        self.process_pool = None                  # 进程池对象
        self.is_converting = False                # 转换状态标记
        self.worker_process = None                 # 工作进程对象

    # ---------------------------
    #       配置方法
    # ---------------------------
    def set_source_path(self, source_path: str):
        self.input_path = source_path

    def set_model(self, model_name: str):
        """设置模型名称（不是文件路径！）"""
        self.model_name = model_name

    def set_vocal_output_path(self, output_path: str):
        self.vocal_output_path = output_path

    def set_instrumental_output_path(self, output_path: str):
        self.instrumental_output_path = output_path

    def set_save_format(self, save_format: str):
        self.save_format = save_format

    def set_max_workers(self, max_workers: int):
        """设置进程池大小"""
        self.max_workers = max_workers

    # ---------------------------
    #       进程池处理函数（静态方法）
    # ---------------------------
    @staticmethod
    def _separation_process(params):
        """在独立进程中执行音频分离的静态方法"""
        input_path = params['input_path']
        model_name = params['model_name']
        vocal_output_path = params['vocal_output_path']
        instrumental_output_path = params['instrumental_output_path']
        save_format = params['save_format']
        
        try:
            # 初始化 Separator
            separator = Separator()
            
            # 默认模型加载
            if not model_name:
                separator.load_model()
            else:
                separator.load_model(model_name)

            # 获取源目录
            input_dir = os.path.dirname(input_path)
            base_name = os.path.splitext(os.path.basename(input_path))[0]

            # 默认输出路径
            if not vocal_output_path:
                vocal_output_path = os.path.join(input_dir, base_name + "_Vocal" + save_format)

            if not instrumental_output_path:
                instrumental_output_path = os.path.join(input_dir, base_name + "_Instrumental" + save_format)

            # 获取临时目录
            temp_dir = tempfile.gettempdir()
            vocal_temp_path = os.path.join(temp_dir, base_name + "_Vocal_temp.wav")
            instrumental_temp_path = os.path.join(temp_dir, base_name + "_Instrumental_temp.wav")

            # 开始分离
            print("开始分离……")
            output = separator.separate(input_path)

            # 临时 WAV 输出路径
            vocal_temp_path = output[0]
            instrumental_temp_path = output[1]

            # 转换为目标格式并保存
            print("正在保存人声和伴奏为 MP3...")

            # 使用 pydub 保存为 mp3 格式
            AudioSegment.from_file(vocal_temp_path).export(vocal_output_path, format="mp3")
            AudioSegment.from_file(instrumental_temp_path).export(instrumental_output_path, format="mp3")

            # 删除临时 WAV 文件
            os.remove(vocal_temp_path)
            os.remove(instrumental_temp_path)

            # 打印输出路径
            print(f"人声保存为: {vocal_output_path}")
            print(f"伴奏保存为: {instrumental_output_path}")
            
            return {
                "status": "success", 
                "vocal_path": vocal_output_path, 
                "instrumental_path": instrumental_output_path
            }
            
        except KeyboardInterrupt:
            return {"status": "stopped", "message": "用户中断了转换"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ---------------------------
    #       全局信号处理器
    # ---------------------------
    @staticmethod
    def _setup_signal_handlers(instance):
        """设置全局信号处理器"""
        original_handler = {}
        
        def signal_handler(signum, frame):
            print(f"\n收到中断信号 {signum}，正在停止转换...")
            if instance:
                instance.stop_conversion()
            # 调用原始信号处理器
            if signum in original_handler:
                original_handler[signum](signum, frame)
        
        # 保存原始处理器并设置新的
        for sig in [signal.SIGINT, signal.SIGTERM]:
            try:
                original_handler[sig] = signal.signal(sig, signal_handler)
            except (OSError, ValueError):
                # 在某些系统上可能不支持某些信号
                pass
        
        return original_handler

    @staticmethod
    def _restore_signal_handlers(original_handlers):
        """恢复原始信号处理器"""
        for sig, handler in original_handlers.items():
            try:
                signal.signal(sig, handler)
            except (OSError, ValueError):
                pass

    # ---------------------------
    #       转换入口（同步，阻塞式）
    # ---------------------------
    def start_conversion_sync(self, input_path, model_name=None, 
                             vocal_output_path=None, instrumental_output_path=None,
                             save_format=".mp3"):
        """
        同步阻塞式音频分离 - 使用多进程池阻塞当前请求直到完成
        这个方法会创建独立进程执行分离任务，只阻塞当前请求线程
        """
        print(f"[多进程同步模式] 开始处理音频文件: {input_path}")
        
        # 准备参数
        params = {
            'input_path': input_path,
            'model_name': model_name,
            'vocal_output_path': vocal_output_path,
            'instrumental_output_path': instrumental_output_path,
            'save_format': save_format,
        }
        
        # 使用多进程池执行任务，阻塞当前线程直到完成
        try:
            # 创建独立的进程池（每个请求独立）
            with multiprocessing.Pool(processes=1) as pool:
                # 使用apply方法阻塞当前线程直到任务完成
                result = pool.apply(VocalSeparationAsync._separation_process, (params,))
                return result
            
        except Exception as e:
            print(f"[多进程同步模式] 转换过程中发生错误: {str(e)}")
            return {"status": "error", "message": str(e)}

    # ---------------------------
    #       转换入口（异步）
    # ---------------------------
    async def start_conversion_async(self, input_path, model_name=None, 
                                    vocal_output_path=None, instrumental_output_path=None,
                                    save_format=".mp3", callback=None):
        if self.is_converting:
            return {"status": "error", "message": "转换已在进行中"}
        
        self.is_converting = True
        
        # 设置全局信号处理器
        original_handler = self._setup_signal_handlers(self)
        
        # 准备参数
        params = {
            'input_path': input_path,
            'model_name': model_name,
            'vocal_output_path': vocal_output_path,
            'instrumental_output_path': instrumental_output_path,
            'save_format': save_format,
        }
        
        print(f"[异步模式] 开始处理音频文件: {input_path}")
        
        try:
            # 使用 asyncio 的事件循环来运行多进程任务
            loop = asyncio.get_event_loop()
            
            # 在单独的线程中运行多进程任务，避免阻塞事件循环
            with multiprocessing.Pool(processes=1) as pool:
                self.worker_process = pool._pool[0] if pool._pool else None
                
                # 使用 run_in_executor 来异步执行多进程任务
                result = await loop.run_in_executor(
                    None, 
                    lambda: pool.apply(VocalSeparationAsync._separation_process, (params,))
                )
                
                return result
            
        except KeyboardInterrupt:
            print("检测到用户中断，正在停止转换...")
            # 直接终止正在运行的进程
            await self.stop_conversion()
            return {"status": "stopped", "message": "用户中断了转换"}
            
        except Exception as e:
            print(f"转换过程中发生错误: {str(e)}")
            return {"status": "error", "message": str(e)}
            
        finally:
            # 清理资源
            self.is_converting = False
            self.worker_process = None
            
            # 恢复信号处理器
            self._restore_signal_handlers(original_handler)

    # ---------------------------
    #       停止转换
    # ---------------------------
    async def stop_conversion(self):
        """
        停止当前音频转换任务
        """
        print("正在停止转换...")
        
        try:
            # 直接终止正在运行的进程
            if self.worker_process and self.worker_process.is_alive():
                print(f"正在终止进程 {self.worker_process.pid}...")
                try:
                    # 获取所有子进程并终止
                    parent = psutil.Process(self.worker_process.pid)
                    children = parent.children(recursive=True)
                    
                    # 终止所有子进程
                    for child in children:
                        try:
                            child.terminate()
                            child.wait(timeout=3)
                        except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                            child.kill()
                    
                    # 终止主进程
                    parent.terminate()
                    parent.wait(timeout=5)
                    
                    print(f"进程 {self.worker_process.pid} 已终止")
                    
                except psutil.NoSuchProcess:
                    print(f"进程 {self.worker_process.pid} 已不存在")
                except Exception as e:
                    print(f"终止进程时出错: {e}")
                    # 强制终止
                    try:
                        parent.kill()
                        parent.wait()
                    except:
                        pass
        
        except Exception as e:
            print(f"停止转换时发生错误: {e}")
        
        finally:
            self.worker_process = None
            self.is_converting = False
            print("转换已停止")

    # ---------------------------
    #       状态检查
    # ---------------------------
    def get_conversion_status(self):
        """获取当前转换状态"""
        return {
            "is_converting": self.is_converting,
            "input_path": self.input_path,
            "model_name": self.model_name,
            "output_paths": {
                "vocal": self.vocal_output_path,
                "instrumental": self.instrumental_output_path
            }
        }

    # ---------------------------
    #       清理资源
    # ---------------------------
    async def cleanup(self):
        """清理资源"""
        await self.stop_conversion()

    def __del__(self):
        """析构函数"""
        # 在析构函数中无法使用async，需要同步处理
        try:
            if self.is_converting and self.worker_process:
                if hasattr(self.worker_process, 'terminate'):
                    self.worker_process.terminate()
        except:
            pass


# ---------------------------
#       测试代码
# ---------------------------
if __name__ == "__main__":
    async def test_conversion():
        v = VocalSeparationAsync(max_workers=2)
        
        try:
            # 设置源路径
            v.set_source_path("C:/MUSIC/远程音频/Music/30年前，50年后 - 精卫.mp3")
            
            # 设置要使用的模型名称
            v.set_model("UVR-MDX-NET-Inst_HQ_3.onnx")
            
            # 设置保存格式
            v.set_save_format(".mp3")
            
            print("启动音频分离...")
            print("按 Ctrl+C 可以随时停止转换")
            
            # 启动转换
            result = await v.start_conversion_async(
                input_path=v.input_path,
                model_name=v.model_name,
                vocal_output_path=v.vocal_output_path,
                instrumental_output_path=v.instrumental_output_path,
                save_format=v.save_format
            )
            print(f"转换结果: {result}")
            
        except KeyboardInterrupt:
            print("\n主程序收到键盘中断...")
            await v.stop_conversion()
        except Exception as e:
            print(f"转换出错: {e}")
        finally:
            print("清理资源...")
            await v.cleanup()
            print("程序结束")

    # 运行测试
    try:
        asyncio.run(test_conversion())
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序异常: {e}")