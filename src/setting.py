"""
应用配置 — src 入口（兼容层）
从 shared.config.settings 导入，保持旧路径兼容性。
新代码应直接从 shared.config.settings 导入。
"""
from shared.config.settings import *  # noqa: F401,F403
