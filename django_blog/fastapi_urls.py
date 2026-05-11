"""
FastAPI 路由配置 - 在 Django 中直接使用 FastAPI 的原始路由代码

此文件将 FastAPI 的路由转换为 Django URL patterns
使得同一套 FastAPI 路由代码可以在两个后台系统中运行

使用方法:
- 在 django_blog/urls.py 中包含此文件即可使用 FastAPI 路由
- FastAPI 路由将自动注册到 /api/v1/... 路径
"""

import os
# 导入 FastAPI 的 router
import sys

from .fastapi_adapter import register_fastapi_router

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

urlpatterns = []

try:
    # 直接从 FastAPI 主应用中导入总路由器
    from src.api.v1 import api_v1_router

    # api_v1_router 已经包含了 /api/v1 前缀，所以这里使用空前缀
    urlpatterns.extend(register_fastapi_router(api_v1_router, prefix='', tags=['api-v1']))

    print("OK: FastAPI router loaded successfully")

except Exception as e:
    print(f"WARNING: Failed to import FastAPI router: {e}")
    import traceback

    traceback.print_exc()
