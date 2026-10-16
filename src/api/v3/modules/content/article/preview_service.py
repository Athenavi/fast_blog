"""文章草稿预览令牌（v3 真实实现）

替代 v2 的 ``shared/services/articles/draft_preview_service.py``：

  - v2 把令牌写进 ``data/preview_tokens.json``（重启会丢、多 worker 各一份、并发写文件不安全），
    v3 落到 ``article_preview_tokens`` 表（迁移 ``50dc796822dc``）
  - v2 用自制 salted-SHA256 存访问密码，v3 复用项目的 Argon2（``password_validator``）
  - 生成/撤销走**与其他写路径一致**的权限判定：他人文章需 ``article:edit_others``
    且数据范围允许（``ensure_write_in_scope``）

安全要点：

  - 令牌为 32 字节 URL 安全随机串（``secrets.token_urlsafe``）
  - 失败一律返回同一句文案（不区分"不存在 / 已过期 / 密码错"），避免枚举探测
  - 访问计数用**原子 UPDATE ... RETURNING**，并发下不丢计数、不超额放行
  - ``password_hash`` 绝不出现在任何响应里（``_token_out`` 只给 ``has_password``）
"""

import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.article.article_preview_token import ArticlePreviewToken
from src.api.v3.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.core.permission import codes as C
from src.api.v3.core.permission.scope import ensure_write_in_scope
from src.api.v3.modules.content.article.crud import article_crud
from src.api.v3.modules.content.article.schema import STATUS_DELETED
from src.api.v3.modules.content.article.service import article_service
from src.utils.security.password_validator import hash_password, verify_password

logger = get_logger("article.preview")

#: 有效期上限（小时）：30 天；访问上限：10000 次
MAX_EXPIRES_HOURS = 720
MAX_VIEWS_LIMIT = 10000
#: 统一失败文案（不区分具体原因，避免探测）
INVALID_MESSAGE = "预览链接无效或已过期"
#: 预览返回的字段白名单（不把管理端全量字段暴露给持链接者）
_PREVIEW_FIELDS = (
    "id", "title", "slug", "excerpt", "cover_image", "category", "tags",
    "content", "language_code", "status", "published_at", "created_at", "updated_at",
)


def _token_out(row: ArticlePreviewToken) -> Dict[str, Any]:
    """令牌对外结构（**绝不包含 ``password_hash``**）"""
    return {
        "id": row.id,
        "article_id": row.article_id,
        "token": row.token,
        "max_views": row.max_views,
        "view_count": int(row.view_count or 0),
        "is_active": bool(row.is_active),
        "has_password": row.password_hash is not None,
        "expires_at": row.expires_at,
        "created_by": row.created_by,
        "created_at": row.created_at,
    }


class ArticlePreviewService:
    """草稿预览令牌的生成 / 校验 / 撤销 / 清理"""

    async def _load_article_for_write(
        self, db: AsyncSession, article_id: int, user: Any
    ) -> Article:
        article = await article_crud.get(db, article_id)
        if article is None or article.status == STATUS_DELETED:
            raise NotFoundError("文章不存在")
        if user is not None:
            await ensure_write_in_scope(
                db, Article, article, user=user, others_code=C.ARTICLE_EDIT_OTHERS
            )
        return article

    async def create_token(
        self,
        db: AsyncSession,
        article_id: int,
        *,
        user: Any = None,
        expires_hours: int = 24,
        password: Optional[str] = None,
        max_views: Optional[int] = None,
    ) -> Dict[str, Any]:
        """为文章生成一枚预览令牌（返回结构含 token 明文，调用方负责只展示给创建者）"""
        if expires_hours < 1 or expires_hours > MAX_EXPIRES_HOURS:
            raise BadRequestError(f"有效期需在 1~{MAX_EXPIRES_HOURS} 小时之间")
        if max_views is not None and (max_views < 1 or max_views > MAX_VIEWS_LIMIT):
            raise BadRequestError(f"访问上限需在 1~{MAX_VIEWS_LIMIT} 之间")

        await self._load_article_for_write(db, article_id, user)

        now = datetime.now()
        row = ArticlePreviewToken(
            article_id=article_id,
            token=secrets.token_urlsafe(32),
            password_hash=hash_password(password) if password else None,
            max_views=max_views,
            view_count=0,
            is_active=True,
            expires_at=now + timedelta(hours=expires_hours),
            created_by=getattr(user, "id", None),
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        logger.info(
            "生成预览令牌 article=%s token=%s... 有效期=%sh 密码=%s",
            article_id, row.token[:8], expires_hours, bool(password),
        )
        return _token_out(row)

    async def list_tokens(self, db: AsyncSession, article_id: int) -> List[Dict[str, Any]]:
        rows = (
            await db.execute(
                select(ArticlePreviewToken)
                .where(ArticlePreviewToken.article_id == article_id)
                .order_by(ArticlePreviewToken.id.desc())
            )
        ).scalars().all()
        return [_token_out(row) for row in rows]

    async def revoke_token(
        self, db: AsyncSession, token_id: int, *, user: Any = None
    ) -> None:
        row = (
            await db.execute(
                select(ArticlePreviewToken).where(ArticlePreviewToken.id == token_id)
            )
        ).scalar_one_or_none()
        if row is None:
            raise NotFoundError("预览令牌不存在")
        await self._load_article_for_write(db, row.article_id, user)

        row.is_active = False
        row.updated_at = datetime.now()
        await db.commit()

    async def resolve_preview(
        self, db: AsyncSession, token: str, *, password: Optional[str] = None
    ) -> Dict[str, Any]:
        """校验令牌（含密码与访问上限）并**原子计数**，返回可预览的文章内容

        校验失败一律抛同一句 ``INVALID_MESSAGE``；成功时返回
        ``{"article": {...}, "preview": {...}}``。
        """
        row = (
            await db.execute(
                select(ArticlePreviewToken).where(ArticlePreviewToken.token == token)
            )
        ).scalar_one_or_none()
        if row is None or not row.is_active:
            raise ForbiddenError(INVALID_MESSAGE)

        now = datetime.now()
        if row.expires_at is None or row.expires_at < now:
            raise ForbiddenError(INVALID_MESSAGE)
        if row.max_views is not None and int(row.view_count or 0) >= int(row.max_views):
            raise ForbiddenError(INVALID_MESSAGE)
        if row.password_hash:
            if not password or not verify_password(password, row.password_hash):
                raise ForbiddenError(INVALID_MESSAGE)

        article_row = await article_crud.get(db, row.article_id)
        if article_row is None or article_row.status == STATUS_DELETED:
            # 文章已被（软）删除：链接立即失效，避免"删了还能看"
            raise ForbiddenError(INVALID_MESSAGE)

        # 原子自增：并发访问下计数不丢失
        new_count = (
            await db.execute(
                update(ArticlePreviewToken)
                .where(ArticlePreviewToken.id == row.id)
                .values(view_count=ArticlePreviewToken.view_count + 1, updated_at=now)
                .returning(ArticlePreviewToken.view_count)
            )
        ).scalar_one_or_none()
        if row.max_views is not None and new_count is not None and int(new_count) > int(row.max_views):
            # 刚好越过上限：立即失效，避免后续继续放行
            await db.execute(
                update(ArticlePreviewToken)
                .where(ArticlePreviewToken.id == row.id)
                .values(is_active=False)
            )
            await db.commit()
            raise ForbiddenError(INVALID_MESSAGE)
        await db.commit()

        try:
            detail = await article_service.get_article(db, row.article_id)
        except Exception:  # noqa: BLE001 - 文章被删等情况一律按"链接失效"处理
            logger.warning("预览令牌指向的文章不可读 article=%s", row.article_id, exc_info=True)
            raise ForbiddenError(INVALID_MESSAGE) from None

        article = {key: detail.get(key) for key in _PREVIEW_FIELDS}
        return {
            "article": article,
            "preview": {
                "view_count": int(new_count or 0),
                "max_views": row.max_views,
                "expires_at": row.expires_at,
            },
        }

    async def cleanup_expired(self, db: AsyncSession) -> int:
        """清理已过期或已失效的令牌，返回删除条数"""
        result = await db.execute(
            delete(ArticlePreviewToken).where(
                or_(
                    ArticlePreviewToken.expires_at < datetime.now(),
                    ArticlePreviewToken.is_active.is_(False),
                )
            )
        )
        await db.commit()
        count = int(result.rowcount or 0)
        if count:
            logger.info("清理预览令牌 %s 条", count)
        return count


article_preview_service = ArticlePreviewService()
