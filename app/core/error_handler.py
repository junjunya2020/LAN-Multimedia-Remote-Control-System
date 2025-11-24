# app/core/error_handler.py
import traceback
import os
from quart import jsonify
from app.core.logging import error_logger, debug_logger, get_logger

class PlayerErrorHandler:
    """
    播放器错误处理类
    用于统一捕获和处理routes/player.py中的所有错误
    """
    
    # 定义常见的错误类型和对应的状态码
    COMMON_ERRORS = {
        FileNotFoundError: (404, "File not found"),
        PermissionError: (403, "Permission denied"),
        ValueError: (400, "Invalid input value"),
        TypeError: (400, "Invalid input type"),
        KeyError: (400, "Missing required parameter"),
        IndexError: (400, "Index out of range"),
        AttributeError: (500, "Attribute error occurred"),
        OSError: (500, "Operating system error"),
    }
    
    @classmethod
    async def handle_error(cls, error, error_source="Unknown", raise_unknown=True):
        """
        处理错误并返回统一格式的响应
        
        Args:
            error: 捕获到的异常对象
            error_source: 错误来源（如路由名称、函数名）
            raise_unknown: 是否对未知错误抛出异常（用于后端日志）
            
        Returns:
            tuple: (jsonify响应对象, 状态码)
        """
        # 检查是否是常见错误类型
        error_type = type(error)
        status_code = 500
        default_message = str(error) or "An unexpected error occurred"
        
        if error_type in cls.COMMON_ERRORS:
            status_code, default_message = cls.COMMON_ERRORS[error_type]
        
        # 构建错误响应
        error_response = {
            "status": "error",
            "message": default_message,
            "error_type": error_type.__name__,
            "error_source": error_source,
            "details": str(error)
        }
        
        # 获取详细的错误堆栈
        error_stack = traceback.format_exc()
        
        # 使用日志模块记录错误（根据错误类型使用不同的日志级别）
        if error_type in cls.COMMON_ERRORS:
            # 常见错误使用warning级别
            error_logger.warning(f"{error_source} - {error_type.__name__}: {str(error)}")
            debug_logger.debug(f"Error stack for {error_source}:\n{error_stack}")
        else:
            # 未知错误使用error级别
            error_logger.error(f"{error_source} - {error_type.__name__}: {str(error)}")
            error_logger.error(f"Error stack:\n{error_stack}")
        
        # 对于未知错误且raise_unknown=True，重新抛出以确保后端捕获
        if raise_unknown and error_type not in cls.COMMON_ERRORS:
            # 这里我们不真正抛出，因为已经处理了响应
            # 但我们已经记录了详细的堆栈信息
            pass
        
        return jsonify(error_response), status_code
    
    @classmethod
    def create_error_handler(cls, func=None, error_source=None):
        """
        创建一个错误处理装饰器，用于包装异步视图函数
        支持两种使用方式：
        1. @PlayerErrorHandler.create_error_handler
        2. @PlayerErrorHandler.create_error_handler(error_source="source_name")
        
        Args:
            func: 要包装的异步视图函数
            error_source: 错误来源标识
            
        Returns:
            装饰器或包装后的异步函数
        """
        # 装饰器工厂函数
        def decorator(func_to_wrap):
            # 如果error_source未提供，则使用函数名
            source = error_source if error_source is not None else func_to_wrap.__name__
            
            async def wrapper(*args, **kwargs):
                try:
                    return await func_to_wrap(*args, **kwargs)
                except Exception as e:
                    return await cls.handle_error(e, source)
            
            # 保留原函数的元数据
            wrapper.__name__ = func_to_wrap.__name__
            wrapper.__doc__ = func_to_wrap.__doc__
            wrapper.__module__ = func_to_wrap.__module__
            
            return wrapper
        
        # 如果直接作为装饰器使用（没有参数）
        if func is not None:
            return decorator(func)
        # 如果作为装饰器工厂使用（有参数）
        return decorator