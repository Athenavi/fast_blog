"""
Medium 导入器 - 占位（即将支持）
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


router = APIRouter(tags=["medium-import"])


@router.get("/guide")
@_catch
async def medium_import_guide(current_user=Depends(jwt_required)):
    return ok(data={
        "platform": "Medium",
        "status": "coming_soon",
        "guide": "Medium 导入功能即将推出。目前您可以通过以下方式迁移内容：",
        "steps": [
            "登录 Medium 账号 → 设置 → 下载你的数据",
            "等待 Medium 生成并发送数据导出邮件",
            "下载包含 posts/ 目录的 ZIP 文件",
            "每个 Markdown 文件可使用 Jekyll/Hexo 导入器导入",
        ]
    })
