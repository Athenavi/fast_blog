"""
seo 子模块 - 模型定义

手写补充（生成器按 config/models.yaml 的 ``module: seo`` 登记本目录；
既有 v2 的 redirect 管理是文件存储，v3 改为真表）。
"""
from .seo_redirect import SeoRedirect

__all__ = ['SeoRedirect']
