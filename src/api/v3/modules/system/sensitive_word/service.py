"""sensitive_word 模块业务逻辑

管理操作直接复用共享服务 ``shared/services/security/sensitive_word_service.py``
（增删改查 / 批量导入 / 缓存刷新都在那里，评论与投稿的反垃圾也走它）。
注意：该服务**自管 DB 会话**（``db_manager.get_session()``），不接收外部会话；
本模块负责列表分页（走请求级会话）、参数校验、权限声明与统一响应。
"""

from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.security import SensitiveWord
from shared.services.security.sensitive_word_service import sensitive_word_service
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.system.sensitive_word.schema import (
    SensitiveWordBatchImport,
    SensitiveWordCreate,
    SensitiveWordUpdate,
)

logger = get_logger("sensitive_word")


def _to_out(row: Any) -> dict:
    if isinstance(row, dict):
        return row
    return {
        "id": row.id,
        "word": row.word,
        "level": row.level,
        "action": row.action,
        "replacement": row.replacement,
        "category": row.category,
        "is_active": bool(row.is_active),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


class SensitiveWordService:
    """敏感词库管理（system 域）"""

    async def list_words(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        level: Optional[int] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[list[dict], int]:
        stmt = select(SensitiveWord).order_by(
            SensitiveWord.created_at.desc(), SensitiveWord.id.desc()
        )
        count_stmt = select(func.count()).select_from(SensitiveWord)
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(SensitiveWord.word.like(like))
            count_stmt = count_stmt.where(SensitiveWord.word.like(like))
        if level is not None:
            stmt = stmt.where(SensitiveWord.level == level)
            count_stmt = count_stmt.where(SensitiveWord.level == level)
        if category:
            stmt = stmt.where(SensitiveWord.category == category)
            count_stmt = count_stmt.where(SensitiveWord.category == category)
        if is_active is not None:
            stmt = stmt.where(SensitiveWord.is_active.is_(is_active))
            count_stmt = count_stmt.where(SensitiveWord.is_active.is_(is_active))

        total = (await db.execute(count_stmt)).scalar() or 0
        rows = (await db.execute(
            stmt.offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()
        return [_to_out(r) for r in rows], int(total)

    async def create_word(self, payload: SensitiveWordCreate, *, user_id: int) -> dict:
        row = await sensitive_word_service.add_sensitive_word(
            word=payload.word.strip(),
            level=payload.level,
            action=payload.action,
            replacement=payload.replacement,
            category=payload.category,
            created_by=user_id,
        )
        if row is None:
            raise BadRequestError("敏感词添加失败（可能已存在）")
        return _to_out(row)

    async def update_word(self, word_id: int, payload: SensitiveWordUpdate) -> dict:
        data = payload.model_dump(exclude_unset=True)
        if not data:
            raise BadRequestError("没有需要更新的字段")
        updated = await sensitive_word_service.update_sensitive_word(word_id=word_id, **data)
        if updated is None:
            raise NotFoundError("敏感词不存在")
        return _to_out(updated)

    async def delete_word(self, word_id: int) -> None:
        ok = await sensitive_word_service.remove_sensitive_word(word_id=word_id)
        if not ok:
            raise NotFoundError("敏感词不存在")

    async def batch_import(self, payload: SensitiveWordBatchImport, *, user_id: int) -> dict:
        words = [w.strip() for w in payload.words if w.strip()]
        if not words:
            raise BadRequestError("导入列表为空")
        return await sensitive_word_service.batch_import_words(
            words=[
                {"word": w, "level": payload.level, "action": payload.action, "category": payload.category}
                for w in words
            ],
            created_by=user_id,
        )


sensitive_word_module_service = SensitiveWordService()
