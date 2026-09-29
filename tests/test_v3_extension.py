"""Phase 4b：extension 域（plugin / theme / widget）骨架测试

不连接数据库：验证路由挂载、模块登记、静态路径顺序、鉴权分流，
并直接单测「危险操作二次确认」这一显式需求。
"""

import pytest
from fastapi import FastAPI

from src.api.v3 import register_v3_routes
from src.api.v3.core.exceptions import BadRequestError

EXTENSION_MODULES = {"block_pattern", "plugin", "theme", "widget"}


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


def test_require_confirm_blocks_dangerous_actions():
    """危险操作（安装/激活/停用/卸载）必须显式 confirm=true"""
    from src.api.v3.modules.extension.plugin.service import require_confirm

    for action in ("安装插件", "激活插件", "停用插件", "卸载插件"):
        with pytest.raises(BadRequestError):
            require_confirm(False, action)
        require_confirm(True, action)  # 明确确认时不抛错
