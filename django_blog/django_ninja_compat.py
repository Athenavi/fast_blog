"""
Django Ninja 兼容性模块
提供与 FastAPI 类似的 ApiResponse 类，用于统一的 API 响应格式
"""

from typing import Optional, Any, Dict

from ninja import Schema


class ApiResponse(Schema):
    """
    通用 API 响应模型
    
    这个类提供了与 FastAPI 项目中相同的响应格式，确保前后端接口一致性。
    
    Attributes:
        success (bool): 请求是否成功
        data (Optional[Any]): 成功时返回的数据
        error (Optional[str]): 失败时返回的错误信息
        message (Optional[str]): 额外的消息
        pagination (Optional[Dict]): 分页信息
    """
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
    pagination: Optional[Dict[str, Any]] = None
