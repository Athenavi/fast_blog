"""GraphQL schema：**以查询为主 + 少量写**（文章创建/更新）。

设计取舍（用户确认「读 + 少量写」）：

  - 写操作只做文章 create/update，且内部仍调用既有 ``article_service``，
    不另起一套写语义；其余写操作继续走 REST，避免双 API 长期分叉。
  - 权限与 REST 完全同源：``GraphQLContext.require`` 复用
    ``permission.control.satisfies`` / ``token_scopes``，因此 API 令牌的 scopes 收窄
    与用户会话语义在 GraphQL 上同样生效。
  - 业务异常（NotFound/Conflict/Forbidden…）统一转成 GraphQL 错误，不泄露堆栈。
"""

from typing import List, Optional

import strawberry
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.fastapi import GraphQLRouter

from src.api.v3.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from src.api.v3.core.permission import codes
from src.api.v3.graphql.context import GraphQLContext, get_context
from src.api.v3.graphql.types import (
    Article,
    ArticleConnection,
    Category,
    Tag,
    Viewer,
    to_article,
    to_category,
    to_tag,
    to_viewer,
)
from src.api.v3.modules.content.article.schema import ArticleCreate, ArticleUpdate
from src.api.v3.modules.content.article.service import article_service
from src.api.v3.modules.content.category.service import category_service
from src.api.v3.modules.content.tag.service import tag_service
from src.auth.auth_deps import jwt_optional_dependency
from src.utils.database.unified_manager import get_db_session

#: 业务异常 → GraphQL 错误的统一映射（语义保留，不回显堆栈）
_BUSINESS_ERRORS = (BadRequestError, ConflictError, ForbiddenError, NotFoundError)


@strawberry.input
class ArticleInput:
    """创建/更新文章的输入（REST ``ArticleCreate`` 的**子集**，避免写语义漂移）"""

    title: str
    content: Optional[str] = None
    slug: Optional[str] = None
    excerpt: Optional[str] = None
    category_id: Optional[int] = None
    tags: Optional[List[str]] = None
    status: Optional[int] = None
    language_code: Optional[str] = None


@strawberry.type
class Query:
    @strawberry.field(description="当前身份；匿名返回 null")
    async def viewer(self, info: strawberry.Info[GraphQLContext]) -> Optional[Viewer]:
        ctx = info.context
        return to_viewer(ctx.viewer) if ctx.viewer is not None else None

    @strawberry.field(description="管理端文章列表（需 module_content:article:view）")
    async def articles(
        self,
        info: strawberry.Info[GraphQLContext],
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        status: Optional[int] = None,
        category_id: Optional[int] = None,
    ) -> ArticleConnection:
        ctx = info.context
        await ctx.require(codes.ARTICLE_VIEW)
        try:
            items, total = await article_service.list_articles(
                ctx.db,
                page=page,
                page_size=page_size,
                keyword=keyword,
                status=status,
                category_id=category_id,
                scope_user=ctx.viewer,
            )
        except _BUSINESS_ERRORS as exc:
            raise strawberry.exceptions.GraphQLError(str(exc)) from exc
        return ArticleConnection(
            items=[to_article(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    @strawberry.field(description="文章详情（需 view 权限；含正文与语言）")
    async def article(self, info: strawberry.Info[GraphQLContext], id: int) -> Article:  # noqa: A002
        ctx = info.context
        await ctx.require(codes.ARTICLE_VIEW)
        try:
            data = await article_service.get_article(
                ctx.db, id, with_content=True, scope_user=ctx.viewer
            )
        except _BUSINESS_ERRORS as exc:
            raise strawberry.exceptions.GraphQLError(str(exc)) from exc
        return to_article(data, with_content=True)

    @strawberry.field(description="公开文章列表（无需登录；仅已发布）")
    async def public_articles(
        self,
        info: strawberry.Info[GraphQLContext],
        page: int = 1,
        page_size: int = 20,
        category_id: Optional[int] = None,
        tag: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> ArticleConnection:
        ctx = info.context
        items, total = await article_service.public_list(
            ctx.db,
            page=page,
            page_size=page_size,
            category_id=category_id,
            tag=tag,
            keyword=keyword,
        )
        return ArticleConnection(
            items=[to_article(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    @strawberry.field(description="公开文章详情（VIP 文章只回摘要且 locked=true）")
    async def public_article(
        self,
        info: strawberry.Info[GraphQLContext],
        id: Optional[int] = None,  # noqa: A002
        slug: Optional[str] = None,
    ) -> Article:
        ctx = info.context
        if id is None and not slug:
            raise strawberry.exceptions.GraphQLError("必须提供 id 或 slug")
        try:
            if id is not None:
                data = await article_service.public_detail(ctx.db, id, viewer=ctx.viewer)
            else:
                data = await article_service.public_detail_by_slug(
                    ctx.db, str(slug), viewer=ctx.viewer
                )
        except _BUSINESS_ERRORS as exc:
            raise strawberry.exceptions.GraphQLError(str(exc)) from exc
        return to_article(data, with_content=True)

    @strawberry.field(description="分类列表（公开）")
    async def categories(
        self,
        info: strawberry.Info[GraphQLContext],
        keyword: Optional[str] = None,
    ) -> List[Category]:
        items = await category_service.list_categories(
            info.context.db, is_visible=True, keyword=keyword
        )
        return [to_category(item) for item in items]

    @strawberry.field(description="标签列表（公开）")
    async def tags(
        self,
        info: strawberry.Info[GraphQLContext],
        limit: int = 200,
        keyword: Optional[str] = None,
    ) -> List[Tag]:
        items, _total = await tag_service.list_tags(
            info.context.db, limit=limit, keyword=keyword
        )
        return [to_tag(item) for item in items]


@strawberry.type
class Mutation:
    @strawberry.mutation(description="创建文章（需 module_content:article:create）")
    async def create_article(
        self,
        info: strawberry.Info[GraphQLContext],
        input: ArticleInput,
    ) -> Article:
        ctx = info.context
        await ctx.require(codes.ARTICLE_CREATE)
        payload = ArticleCreate(
            title=input.title,
            content=input.content,
            slug=input.slug,
            excerpt=input.excerpt,
            category_id=input.category_id,
            tags=list(input.tags or []),
            **(
                {"status": input.status}
                if input.status is not None
                else {}
            ),
            **(
                {"language_code": input.language_code}
                if input.language_code is not None
                else {}
            ),
        )
        try:
            data = await article_service.create_article(
                ctx.db, payload, user_id=getattr(ctx.viewer, "id", None)
            )
        except _BUSINESS_ERRORS as exc:
            raise strawberry.exceptions.GraphQLError(str(exc)) from exc
        return to_article(data, with_content=True)

    @strawberry.mutation(description="更新文章（需 module_content:article:edit）")
    async def update_article(
        self,
        info: strawberry.Info[GraphQLContext],
        id: int,  # noqa: A002
        input: ArticleInput,
    ) -> Article:
        ctx = info.context
        await ctx.require(codes.ARTICLE_EDIT)
        payload = ArticleUpdate(
            title=input.title,
            content=input.content,
            slug=input.slug,
            excerpt=input.excerpt,
            category_id=input.category_id,
            tags=list(input.tags) if input.tags is not None else None,
            status=input.status,
            language_code=input.language_code,
        )
        try:
            data = await article_service.update_article(
                ctx.db, id, payload, scope_user=ctx.viewer
            )
        except _BUSINESS_ERRORS as exc:
            raise strawberry.exceptions.GraphQLError(str(exc)) from exc
        return to_article(data, with_content=True)


def build_schema() -> strawberry.Schema:
    """组装 schema（查询 + 少量写）"""
    return strawberry.Schema(query=Query, mutation=Mutation)


async def _context_getter(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    viewer=Depends(jwt_optional_dependency),
) -> GraphQLContext:
    """上下文：匿名可查公开字段；受保护字段由 ``require`` 逐个把关。"""
    return await get_context(request=request, db=db, viewer=viewer)


def build_router(*, graphiql: bool = False) -> GraphQLRouter:
    """构造 GraphQL 路由。

    ``graphql_ide`` 是 strawberry 的 IDE 开关（旧版本叫 ``graphiql``）；
    与 API 文档同样处理：只在本环境显式开放文档时才挂 IDE 界面。
    """
    return GraphQLRouter(
        build_schema(),
        context_getter=_context_getter,
        graphql_ide="graphiql" if graphiql else None,
    )
