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
    POST   /api/v3/content/article/batch/publish  批量发布 / 撤回
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

from fastapi import APIRouter, Header, Query, Request

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession, OptionalUser, PageDep
from src.api.v3.core.logger import get_logger
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.content.article.preview_service import article_preview_service
from src.api.v3.modules.content.article.schema import (
    ArticleBatchDeleteRequest,
    ArticleBatchPublishRequest,
    ArticleCreate,
    ArticlePreviewTokenCreate,
    ArticlePublishRequest,
    ArticleUpdate,
)
from src.api.v3.modules.content.article.service import article_service

router = APIRouter(prefix="/article", tags=["content-article"], route_class=OperationLogRoute)

logger = get_logger("article")


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
async def increment_views(article_id: int, db: DBSession, request: Request) -> dict:
    views = await article_service.increment_views(db, article_id)
    # best-effort 埋点：把这次浏览写进 user_activities（target_type=article），失败不影响计数
    try:
        from src.api.v3.modules.analytics.tracking.service import tracking_service

        await tracking_service.record_event(
            db,
            activity_type="view",
            target_type="article",
            target_id=article_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except Exception:  # noqa: BLE001 - 埋点失败不得影响业务响应
        logger.warning("文章浏览埋点失败 article_id=%s", article_id, exc_info=True)
    return resp.success({"views": views})


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


# ─────────────────────────── 公开：草稿预览（令牌即凭证，无鉴权）───────────────────────────
@router.get("/public/preview/{token}", response_model=ResponseModel, summary="用预览令牌读取未发布草稿")
async def public_preview_article(
    token: str,
    db: DBSession,
    x_preview_password: Optional[str] = Header(
        default=None,
        alias="X-Preview-Password",
        description="预览口令（仅当令牌设置了口令时需要）",
    ),
) -> dict:
    """**无需登录**：持有令牌即可读该文章的草稿内容。口令走请求头，避免出现在 URL 与访问日志里。"""
    return resp.success(
        await article_preview_service.resolve_preview(db, token, password=x_preview_password)
    )


# ─────────────────────────── 管理端：批量操作（静态路径优先）───────────
@router.post("/batch/delete", response_model=ResponseModel, summary="批量删除文章")
async def batch_delete_articles(
    payload: ArticleBatchDeleteRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_DELETE),
) -> dict:
    affected = await article_service.batch_delete(db, payload.ids, scope_user=_current)
    return resp.success({"affected": affected}, msg=f"已删除 {affected} 篇")


@router.post("/batch/publish", response_model=ResponseModel, summary="批量发布 / 撤回文章")
async def batch_publish_articles(
    payload: ArticleBatchPublishRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_PUBLISH),
) -> dict:
    affected = await article_service.batch_set_published(
        db, payload.ids, payload.publish, scope_user=_current
    )
    action = "发布" if payload.publish else "撤回"
    return resp.success({"affected": affected}, msg=f"已{action} {affected} 篇")


@router.post("/reorder", response_model=ResponseModel, summary="批量重排文章")
async def reorder_articles(
    items: List[dict],
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_EDIT),
) -> dict:
    pairs = [(int(item["id"]), int(item.get("sort_order", 0))) for item in items if "id" in item]
    affected = await article_service.reorder(db, pairs, scope_user=_current)
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
    return resp.success(
        await article_service.update_article(db, article_id, payload, scope_user=_current),
        msg="更新成功",
    )


@router.delete("/{article_id}", response_model=ResponseModel, summary="删除文章（软删）")
async def delete_article(
    article_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_DELETE),
) -> dict:
    await article_service.delete_article(db, article_id, scope_user=_current)
    return resp.success(None, msg="已删除")


@router.post("/{article_id}/publish", response_model=ResponseModel, summary="发布 / 撤回文章")
async def publish_article(
    article_id: int,
    payload: ArticlePublishRequest,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_PUBLISH),
) -> dict:
    data = await article_service.set_published(db, article_id, payload.publish, scope_user=_current)
    return resp.success(data, msg="已发布" if payload.publish else "已转草稿")


# ─────────────────────────── 管理端：草稿预览令牌 ───────────────────────────
@router.post("/{article_id}/preview-token", response_model=ResponseModel, summary="生成草稿预览令牌")
async def create_preview_token(
    article_id: int,
    payload: ArticlePreviewTokenCreate,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_EDIT),
) -> dict:
    """为文章（含未发布草稿）生成临时预览链接

    他人文章还需 ``article:edit_others`` 且数据范围允许（与其他写路径同一套判定）。
    """
    return resp.success(
        await article_preview_service.create_token(
            db,
            article_id,
            user=_current,
            expires_hours=payload.expires_hours,
            password=payload.password,
            max_views=payload.max_views,
        ),
        msg="预览令牌已生成",
    )


@router.get("/{article_id}/preview-tokens", response_model=ResponseModel, summary="某文章的预览令牌列表")
async def list_preview_tokens(
    article_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_VIEW),
) -> dict:
    return resp.success(await article_preview_service.list_tokens(db, article_id))


@router.post("/preview-token/cleanup", response_model=ResponseModel, summary="清理过期 / 已失效的预览令牌")
async def cleanup_preview_tokens(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_EDIT),
) -> dict:
    removed = await article_preview_service.cleanup_expired(db)
    return resp.success({"removed": removed}, msg=f"已清理 {removed} 条")


@router.delete("/preview-token/{token_id}", response_model=ResponseModel, summary="撤销预览令牌")
async def revoke_preview_token(
    token_id: int,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.ARTICLE_EDIT),
) -> dict:
    await article_preview_service.revoke_token(db, token_id, user=_current)
    return resp.success(None, msg="已撤销")
