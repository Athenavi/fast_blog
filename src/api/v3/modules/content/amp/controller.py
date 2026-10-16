"""amp 模块路由（AMP 文档生成 / HTML 转换 / 规范校验）

::

    GET  /api/v3/content/amp/article/{article_id}  按文章生成 AMP 文档（需 article:view）
    POST /api/v3/content/amp/convert               把 HTML 转成 AMP 文档（需 article:edit）
    POST /api/v3/content/amp/validate              校验 HTML 是否符合 AMP 规范（需 article:view）

生成与转换都是**真实转换器**（基于 ``html.parser`` 的元素级处理），正文从真表
``articles`` + ``article_content`` 读取；转换端点需要 ``article:edit``（编辑器提交前转换/自检）。
"""

from fastapi import APIRouter

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.content.amp.schema import AmpConvertRequest, AmpValidateRequest
from src.api.v3.modules.content.amp.service import amp_service

router = APIRouter(prefix="/amp", tags=["content-amp"], route_class=OperationLogRoute)


@router.get("/article/{article_id}", response_model=ResponseModel, summary="生成文章的 AMP 文档")
async def amp_for_article(
    article_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_VIEW),
) -> dict:
    """从 ``articles`` / ``article_content`` / ``article_seo`` 读数据并生成完整 AMP 文档"""
    return resp.success(await amp_service.generate_for_article(db, article_id))


@router.post("/convert", response_model=ResponseModel, summary="把 HTML 转换成 AMP 文档")
async def convert_to_amp(
    payload: AmpConvertRequest,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_EDIT),
) -> dict:
    """元素级转换（img→amp-img、video→amp-video、剥离禁用标签与 on* 属性、内联 CSS）"""
    return resp.success(
        amp_service.convert_to_amp(
            html=payload.html,
            title=payload.title or "",
            author_name=payload.author_name or "",
            canonical_url=payload.canonical_url or "",
            site_name=payload.site_name or "",
            featured_image=payload.featured_image or "",
            published_at=payload.published_at,
            extra_css=payload.extra_css or "",
        ),
        msg="已转换",
    )


@router.post("/validate", response_model=ResponseModel, summary="校验 HTML 是否符合 AMP 规范")
async def validate_amp(
    payload: AmpValidateRequest,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_VIEW),
) -> dict:
    """返回违规项：禁用标签 / 内联事件属性 / CSS 超限 / 缺 canonical / 缺 ``<html amp>``"""
    return resp.success(amp_service.validate_amp(payload.html))
