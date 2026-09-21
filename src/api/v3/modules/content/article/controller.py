"""article 模块路由

**公开读（无鉴权，供博客前台 / Nuxt SSR）**::

    GET  /api/v3/content/article/public/list                 公开文章列表
    GET  /api/v3/content/article/public/detail/{article_id}  公开文章详情
    GET  /api/v3/content/article/public/slug/{slug}          按 slug 取详情
    POST /api/v3/content/article/public/{article_id}/views   浏览量 +1

**管理端（需权限码）**::

    GET    /api/v3/content/article                列表
    POST   /api/v3/content/article                新建
    POST   /api/v3/content/article/batch/delete   批量删除（软删）
    POST   /api/v3/content/article/reorder        批量重排
    GET    /api/v3/content/article/{article_id}   详情（含正文与 SEO）
    PUT    /api/v3/content/article/{article_id}   更新
    DELETE /api/v3/content/article/{article_id}   删除（软删）
    POST   /api/v3/content/article/{article_id}/publish   发布 / 撤回

别名：``/list``、``/create``、``/detail/{id}``、``/update/{id}``、``/delete``（均
``include_in_schema=False``）。静态路径（``/batch/delete``、``/reorder``、``/public/*``）
一律注册在 ``/{article_id}`` 之前，由 ``assert_no_shadowed_routes`` 强制。

权限码：``article:view`` / ``article:create`` / ``article:edit`` / ``article:delete`` / ``article:publish``
"""

from typing import List, Optional

from fastapi import APIRouter, Query

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession, OptionalUser, PageDep
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.content.article.schema import (
    ArticleBatchDeleteRequest,
    ArticleCreate,
    ArticlePublishRequest,
    ArticleUpdate,
)
from src.api.v3.modules.content.article.service import article_service

router = APIRouter(prefix="/article", tags=["content-article"], route_class=OperationLogRoute)


# ─────────────────────────── 公开读（无鉴权）───────────────────────────
@router.get("/public/list", response_model=ResponseModel, summary="公开文章列表")
async def public_articles(
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category_id: Optional[int] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    post_type: Optional[str] = Query(default=None),
    user_id: Optional[int] = Query(default=None, description="只看某位作者的公开文章"),
    exclude_vip: bool = Query(
        default=False, description="排除仅 VIP 可见的文章（作者主页文章列表用）"
    ),
) -> dict:
    items, total = await article_service.public_list(
        db,
        page=page,
        page_size=page_size,
        category_id=category_id,
        tag=tag,
        keyword=keyword,
        post_type=post_type,
        user_id=user_id,
        exclude_vip=exclude_vip,
    )
    return resp.success_page(items, total, page, page_size)


@router.get("/public/detail/{article_id}", response_model=ResponseModel, summary="公开文章详情")
async def public_article_detail(
    article_id: int,
    db: DBSession,
    viewer: OptionalUser,
    language_code: Optional[str] = Query(default=None),
) -> dict:
    """VIP 文章（`is_vip_only`）对未授权者**不返回正文**（`locked=True` + 摘要）"""
    return resp.success(
        await article_service.public_detail(
            db, article_id, language_code=language_code, viewer=viewer
        )
    )


@router.get("/public/slug/{slug}", response_model=ResponseModel, summary="按 slug 取公开详情")
async def public_article_by_slug(
    slug: str,
    db: DBSession,
    viewer: OptionalUser,
    language_code: Optional[str] = Query(default=None),
) -> dict:
    """同上：VIP 文章只给摘要，正文要走带授权的正文端点"""
    return resp.success(
        await article_service.public_detail_by_slug(
            db, slug, language_code=language_code, viewer=viewer
        )
    )


@router.post("/public/{article_id}/views", response_model=ResponseModel, summary="浏览量 +1")
async def increment_views(article_id: int, db: DBSession) -> dict:
    return resp.success({"views": await article_service.increment_views(db, article_id)})


# ─────────────────────────── 管理端：列表 ───────────────────────────
@router.get("", response_model=ResponseModel, summary="文章列表")
@router.get(
    "/list",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 文章列表",
)
async def list_articles(
    page: PageDep,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_VIEW),
    status: Optional[int] = Query(default=None, description="-1 删除 / 0 草稿 / 1 已发布"),
    category_id: Optional[int] = Query(default=None),
    user_id: Optional[int] = Query(default=None),
    post_type: Optional[str] = Query(default=None),
    is_featured: Optional[bool] = Query(default=None),
    is_sticky: Optional[bool] = Query(default=None),
) -> dict:
    items, total = await article_service.list_articles(
        db,
        page=page.page,
        page_size=page.page_size,
        keyword=page.keyword,
        status=status,
        category_id=category_id,
        user_id=user_id,
        post_type=post_type,
        is_featured=is_featured,
        is_sticky=is_sticky,
        order_by=page.order_by,
        order=page.order,
        scope_user=_current,
    )
    return resp.success_page(items, total, page.page, page.page_size)


# ─────────────────────────── 管理端：新建 ───────────────────────────
@router.post("", response_model=ResponseModel, summary="创建文章")
@router.post(
    "/create",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 创建文章",
)
async def create_article(
    payload: ArticleCreate,
    db: DBSession,
    current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_CREATE),
) -> dict:
    data = await article_service.create_article(db, payload, user_id=current.id)
    return resp.success(data, msg="创建成功")


# ─────────────────────────── 管理端：批量操作（静态路径优先）───────────
@router.post("/batch/delete", response_model=ResponseModel, summary="批量删除文章")
async def batch_delete_articles(
    payload: ArticleBatchDeleteRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_DELETE),
) -> dict:
    affected = await article_service.batch_delete(db, payload.ids)
    return resp.success({"affected": affected}, msg=f"已删除 {affected} 篇")


@router.post("/reorder", response_model=ResponseModel, summary="批量重排文章")
async def reorder_articles(
    items: List[dict],
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_EDIT),
) -> dict:
    pairs = [(int(item["id"]), int(item.get("sort_order", 0))) for item in items if "id" in item]
    affected = await article_service.reorder(db, pairs)
    return resp.success({"affected": affected}, msg="排序已更新")


# ─────────────────────────── 管理端：详情 / 更新 / 删除 ───────────────────────────
@router.get("/{article_id}", response_model=ResponseModel, summary="文章详情")
@router.get(
    "/detail/{article_id}",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 文章详情",
)
async def get_article(
    article_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_VIEW),
    language_code: Optional[str] = Query(default=None),
) -> dict:
    return resp.success(
        await article_service.get_article(
            db, article_id, language_code=language_code, scope_user=_current
        )
    )


@router.put("/{article_id}", response_model=ResponseModel, summary="更新文章")
@router.put(
    "/update/{article_id}",
    response_model=ResponseModel,
    include_in_schema=False,
    summary="[兼容 FastApiAdmin] 更新文章",
)
async def update_article(
    article_id: int,
    payload: ArticleUpdate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_EDIT),
) -> dict:
    return resp.success(await article_service.update_article(db, article_id, payload), msg="更新成功")


@router.delete("/{article_id}", response_model=ResponseModel, summary="删除文章（软删）")
async def delete_article(
    article_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_DELETE),
) -> dict:
    await article_service.delete_article(db, article_id)
    return resp.success(None, msg="已删除")


@router.post("/{article_id}/publish", response_model=ResponseModel, summary="发布 / 撤回文章")
async def publish_article(
    article_id: int,
    payload: ArticlePublishRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_PUBLISH),
) -> dict:
    data = await article_service.set_published(db, article_id, payload.publish)
    return resp.success(data, msg="已发布" if payload.publish else "已转草稿")
