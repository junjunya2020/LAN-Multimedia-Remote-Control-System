# app/core/logging.py
import logging
import os
import time
from logging.handlers import RotatingFileHandler

class LoggerManager:
    """
    日志管理器类
    提供统一的日志配置和访问接口
    """
    
    # 默认日志级别
    DEFAULT_LOG_LEVEL = logging.INFO
    
    # 日志格式
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    DETAILED_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(module)s:%(funcName)s:%(lineno)d] - %(message)s'
    
    # 日志目录
    LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs')
    
    _loggers = {}
    _initialized = False
    
    @classmethod
    def initialize(cls, log_level=None):
        """
        初始化日志系统
        
        Args:
            log_level: 日志级别，可以是字符串('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')或logging模块的常量
        """
        if cls._initialized:
            return
        
        # 确保日志目录存在
        os.makedirs(cls.LOG_DIR, exist_ok=True)
        
        # 设置根日志级别
        root_level = log_level if log_level is not None else cls.DEFAULT_LOG_LEVEL
        if isinstance(root_level, str):
            root_level = getattr(logging, root_level.upper(), cls.DEFAULT_LOG_LEVEL)
        
        logging.basicConfig(level=root_level, format=cls.LOG_FORMAT)
        
        cls._initialized = True
    
    @classmethod
    def get_logger(cls, name, log_file=None, log_level=None):
        """
        获取指定名称的日志记录器
        
        Args:
            name: 日志记录器名称
            log_file: 日志文件名称，如果为None则只输出到控制台
            log_level: 该日志记录器的日志级别
            
        Returns:
            logging.Logger: 配置好的日志记录器
        """
        # 如果日志系统未初始化，先初始化
        if not cls._initialized:
            cls.initialize()
        
        # 如果该名称的日志记录器已存在，直接返回
        if name in cls._loggers:
            return cls._loggers[name]
        
        # 创建新的日志记录器
        logger = logging.getLogger(name)
        
        # 设置日志级别
        if log_level is not None:
            if isinstance(log_level, str):
                log_level = getattr(logging, log_level.upper(), cls.DEFAULT_LOG_LEVEL)
            logger.setLevel(log_level)
        
        # 添加文件处理器（如果指定了日志文件）
        if log_file:
            log_path = os.path.join(cls.LOG_DIR, log_file)
            
            # 创建RotatingFileHandler，支持日志文件滚动
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            
            # 设置文件处理器的格式和级别
            file_handler.setFormatter(logging.Formatter(cls.DETAILED_LOG_FORMAT))
            if log_level is not None:
                file_handler.setLevel(log_level)
            
            logger.addHandler(file_handler)
        
        # 添加控制台处理器（如果还没有）
        if not any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(cls.LOG_FORMAT))
            if log_level is not None:
                console_handler.setLevel(log_level)
            logger.addHandler(console_handler)
        
        # 保存日志记录器
        cls._loggers[name] = logger
        
        return logger

# 创建默认的日志记录器
def get_logger(name='app', log_file=None, log_level=None):
    """
    获取日志记录器的便捷函数
    
    Args:
        name: 日志记录器名称
        log_file: 日志文件名称
        log_level: 日志级别
        
    Returns:
        logging.Logger: 日志记录器
    """
    return LoggerManager.get_logger(name, log_file, log_level)

# 预定义常用的日志记录器
error_logger = get_logger('app.error', 'error.log', logging.ERROR)
info_logger = get_logger('app.info', 'info.log', logging.INFO)
debug_logger = get_logger('app.debug', 'debug.log', logging.DEBUG)
player_logger = get_logger('app.player', 'player.log')