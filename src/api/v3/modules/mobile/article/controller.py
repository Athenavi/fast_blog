"""mobile/article：移动端文章浏览 + 用户投稿

路由前缀：``/api/v3/mobile/article``

**公开部分**（无需鉴权）复用 ``modules/content/article`` 的
``article_service.public_list`` / ``public_detail``（同一套可见性规则：已发布、
未隐藏、定时发布未到不算、软删除排除）。

**投稿部分**（仅需登录）复用 ``article_service`` 的写方法，并追加归属与状态约束，
详见 ``mobile/article/service.py``：只能操作自己的文章，且**只能存草稿**——
发布走后台 ``/content/article/{id}/publish``，形成"投稿 → 审核 → 发布"的分离。

legacy 缺陷修复：旧实现里 ``GET /{article_id}``（:139）注册在 ``GET /search``（:231）之前，
导致 ``/api/v3/articles/search`` 永远被路径参数吞掉并返回 422。v3 把静态路径
（``/list``、``/search``、``/mine``）统一前置，并由 ``assert_no_shadowed_routes`` 在启动期强制。
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import DBSession, PageDep
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.content.article.service import article_service
from src.api.v3.modules.mobile.article.schema import (
    MobileArticleCreate,
    MobileArticleQuery,
    MobileArticleUpdate,
)
from src.api.v3.modules.mobile.article.service import mobile_article_service
from src.auth.auth_deps import jwt_optional_dependency, jwt_required_dependency

router = APIRouter(prefix="/article", tags=["mobile-article"], route_class=OperationLogRoute)


# ---------------------------------------------------------------- 公开读
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


# ---------------------------------------------------------------- 我的投稿
@router.get("/mine", response_model=ResponseModel, summary="我的文章（需登录，含草稿）")
async def list_my_articles(
    db: DBSession,
    page: PageDep,
    user=Depends(jwt_required_dependency),
    status: Optional[int] = Query(default=None, description="0 草稿 / 1 已发布"),
    keyword: Optional[str] = Query(default=None),
) -> dict:
    query = MobileArticleQuery(
        page=page.page, page_size=page.page_size, status=status, keyword=keyword
    )
    items, total = await mobile_article_service.list_mine(
        db,
        user,
        page=query.page,
        page_size=query.page_size,
        status=query.status,
        keyword=query.keyword,
    )
    return resp.success_page(items, total, query.page, query.page_size)


@router.post("", response_model=ResponseModel, summary="投稿（创建草稿，需登录）")
async def create_my_article(
    payload: MobileArticleCreate,
    db: DBSession,
    user=Depends(jwt_required_dependency),
) -> dict:
    """创建草稿。

    状态、置顶、加精、VIP 等**管理字段由服务端强制设定**，请求体里也不接受这些字段，
    因此前台无法自行发布。
    """
    return resp.success(await mobile_article_service.create_draft(db, user, payload), msg="草稿已保存")


# ---------------------------------------------------------------- 详情与自己的写操作
@router.get("/{article_id}", response_model=ResponseModel, summary="文章详情（无需鉴权）")
async def get_article(
    article_id: int,
    db: DBSession,
    language_code: Optional[str] = Query(default=None),
) -> dict:
    return resp.success(
        await article_service.public_detail(db, article_id, language_code=language_code)
    )


@router.get("/{article_id}/mine", response_model=ResponseModel, summary="我的文章详情（需登录，含草稿）")
async def get_my_article(
    article_id: int,
    db: DBSession,
    user=Depends(jwt_required_dependency),
) -> dict:
    return resp.success(await mobile_article_service.get_mine(db, user, article_id))


@router.put("/{article_id}", response_model=ResponseModel, summary="编辑我的文章（需登录）")
async def update_my_article(
    article_id: int,
    payload: MobileArticleUpdate,
    db: DBSession,
    user=Depends(jwt_required_dependency),
) -> dict:
    return resp.success(
        await mobile_article_service.update_mine(db, user, article_id, payload), msg="已保存"
    )


@router.delete("/{article_id}", response_model=ResponseModel, summary="删除我的文章（需登录）")
async def delete_my_article(
    article_id: int,
    db: DBSession,
    user=Depends(jwt_required_dependency),
) -> dict:
    await mobile_article_service.delete_mine(db, user, article_id)
    return resp.success(None, msg="已删除")


# ---------------------------------------------------------------- 点赞
@router.get("/{article_id}/like/status", response_model=ResponseModel, summary="点赞状态（匿名可查）")
async def get_like_status(
    article_id: int,
    db: DBSession,
    user=Depends(jwt_optional_dependency),
) -> dict:
    """文章详情页用：匿名返回 ``liked=false`` + 计数，登录返回当前用户是否已点赞。"""
    return resp.success(await mobile_article_service.like_status(db, user, article_id))


@router.post("/{article_id}/like", response_model=ResponseModel, summary="点赞 / 取消点赞（需登录）")
async def toggle_like(
    article_id: int,
    db: DBSession,
    user=Depends(jwt_required_dependency),
) -> dict:
    """per-user 幂等切换（ArticleLike 表去重），计数同步到 ``Article.likes``。"""
    return resp.success(await mobile_article_service.toggle_like(db, user, article_id))
