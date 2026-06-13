"""
Ghost 导入器 - 占位（即将支持）
"""
from functools import wraps
from fastapi import APIRouter, Depends
from src.api.v2._helpers import ok, fail
from src.auth import jwt_required_dependency as jwt_required


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try: return await func(*args, **kwargs)
        except Exception as e: return fail(str(e))
    return wrapper


router = APIRouter(tags=["ghost-import"])


@router.get("/guide")
@_catch
async def ghost_import_guide(current_user=Depends(jwt_required)):
    return ok(data={
        "platform": "Ghost",
        "status": "coming_soon",
        "guide": "Ghost 导入功能即将推出。目前您可以通过 Ghost 的 JSON 导出功能导出内容，然后使用 WordPress 导入器（Ghost 支持导出为 WordPress WXR 格式）",
        "steps": [
            "登录 Ghost 管理后台 → 设置 → 导出内容",
            "选择「导出为 WordPress」格式",
            "下载导出的 XML 文件",
            "使用 WordPress 导入器导入到 FastBlog",
        ]
    })
