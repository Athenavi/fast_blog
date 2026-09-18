"""tag 模块路由

::

    GET    /api/v3/content/tag                              标签聚合列表
    GET    /api/v3/content/tag/public/{tag}/articles        按标签查文章（无鉴权）
    POST   /api/v3/content/tag/rename                       标签重命名（合并）
    POST   /api/v3/content/tag/delete                       删除标签（从所有文章移除）

权限码：``article:view``（查询）/ ``article:edit``（重命名、删除）
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.content.tag.schema import TagDeleteRequest, TagRenameRequest
from src.api.v3.modules.content.tag.service import tag_service

router = APIRouter(prefix="/tag", tags=["content-tag"], route_class=OperationLogRoute)


def _article_brief(article) -> dict:
    return {
        "id": article.id,
        "title": article.title,
        "slug": article.slug,
        "excerpt": article.excerpt,
        "cover_image": article.cover_image,
        "category_id": article.category,
        "tags": article.tags_list,
        "views": article.views,
        "likes": article.likes,
        "status": article.status,
        "is_featured": bool(article.is_featured),
        "created_at": article.created_at,
        "published_at": article.published_at,
    }


# ─────────────────────────── 公开：按标签查文章 ───────────────────────────
@router.get(
    "/public/{tag}/articles",
    response_model=ResponseModel,
    summary="按标签查文章（无需鉴权）",
)
async def public_articles_by_tag(
    tag: str,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    articles, total = await tag_service.articles_by_tag(
        db, tag, page=page, page_size=page_size, published_only=True
    )
    return resp.success_page([_article_brief(a) for a in articles], total, page, page_size)


# ─────────────────────────── 聚合列表 ───────────────────────────
@router.get("", response_model=ResponseModel, summary="标签列表（聚合）")
@router.get(
    "/list",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 标签列表",
)
async def list_tags(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("article:view"),
    limit: int = Query(default=200, ge=1, le=1000),
    min_count: int = Query(default=1, ge=1),
    keyword: Optional[str] = Query(default=None),
) -> dict:
    items, total = await tag_service.list_tags(
        db, limit=limit, keyword=keyword, min_count=min_count
    )
    return resp.success_page(items, total, 1, limit)


# ─────────────────────────── 重命名 / 删除 ───────────────────────────
@router.post("/rename", response_model=ResponseModel, summary="标签重命名")
async def rename_tag(
    payload: TagRenameRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("article:edit"),
) -> dict:
    result = await tag_service.rename_tag(db, payload.old_name, payload.new_name)
    return resp.success(result, msg="重命名完成")


@router.post("/delete", response_model=ResponseModel, summary="删除标签")
async def delete_tag(
    payload: TagDeleteRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("article:edit"),
) -> dict:
    result = await tag_service.delete_tag(db, payload.name)
    return resp.success(result, msg="已从文章中移除")


@router.get("/{tag}/articles", response_model=ResponseModel, summary="按标签查文章（管理端）")
async def articles_by_tag(
    tag: str,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl("article:view"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    published_only: bool = Query(default=False),
) -> dict:
    articles, total = await tag_service.articles_by_tag(
        db, tag, page=page, page_size=page_size, published_only=published_only
    )
    return resp.success_page([_article_brief(a) for a in articles], total, page, page_size)
