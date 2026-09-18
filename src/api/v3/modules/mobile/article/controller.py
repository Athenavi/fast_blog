"""mobile/article：移动端文章列表 / 搜索 / 详情

路由前缀：``/api/v3/mobile/article``

本模块**不重复实现业务逻辑**，直接复用 ``modules/content/article`` 的
``article_service.public_list`` / ``public_detail``（同一套可见性规则：已发布、
未隐藏、定时发布未到不算、软删除排除）。

legacy 缺陷修复：旧实现里 ``GET /{article_id}``（:139）注册在 ``GET /search``（:231）之前，
导致 ``/api/v3/articles/search`` 永远被路径参数吞掉并返回 422。v3 把静态路径
（``/list``、``/search``）统一前置，并由 ``assert_no_shadowed_routes`` 在启动期强制。

这些接口**无需鉴权**（移动端未登录也能浏览）。
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import DBSession
from src.api.v3.modules.content.article.service import article_service

router = APIRouter(prefix="/article", tags=["mobile-article"])


@router.get("/list", response_model=ResponseModel, summary="文章列表（无需鉴权）")
async def list_articles(
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    category_id: Optional[int] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    post_type: Optional[str] = Query(default=None),
) -> dict:
    items, total = await article_service.public_list(
        db,
        page=page,
        page_size=page_size,
        category_id=category_id,
        tag=tag,
        post_type=post_type,
    )
    return resp.success_page(items, total, page, page_size)


@router.get("/search", response_model=ResponseModel, summary="文章搜索（无需鉴权）")
async def search_articles(
    db: DBSession,
    keyword: str = Query(min_length=1, max_length=100, description="搜索关键词"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
) -> dict:
    items, total = await article_service.public_list(
        db, page=page, page_size=page_size, keyword=keyword
    )
    return resp.success_page(items, total, page, page_size)


@router.get("/{article_id}", response_model=ResponseModel, summary="文章详情（无需鉴权）")
async def get_article(
    article_id: int,
    db: DBSession,
    language_code: Optional[str] = Query(default=None),
) -> dict:
    return resp.success(await article_service.public_detail(db, article_id, language_code=language_code))
