"""redirect：SEO 跳转规则（301/302/307/308）—— v3 真表实现

替代 v2 的 ``shared/services/seo/redirect_manager.py``（13.1KB，**redirects.json 文件存储**，
非 DB）。v3 用 ``seo_redirects`` 真表：

  - **迁移导入自动生成**：``record_from_import`` 按源站 URL（WXR 的 ``link`` /
    markdown 的 ``url`` / ghost 的 ``url``）生成「旧链接 → 新文章」跳转
  - **手工维护**：CRUD + 批量导入（对应 v2 的 ``bulk_import``）
  - **命中计数真实累加**：``resolve_path`` 命中即 ``hits + 1`` 并落库

**未做（诚实划界）**：v2 的 ``detect_404_candidates`` 依赖"最近 404 列表"，但本库的
``page_views`` 没有状态码字段、也没有独立的 404 记录表 —— 没有真实数据源，
就不做"猜一个候选出来"的功能。需要它时应先在前端/网关侧真实落 404 记录。
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.seo.seo_redirect import SeoRedirect
from src.api.v3.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.api.v3.core.logger import get_logger

logger = get_logger("content.redirect")

#: 允许的跳转状态码（301 永久 / 302 临时 / 307 / 308 保留方法）
STATUS_CODES = (301, 302, 307, 308)

#: 迁移导入生成跳转时的默认目标模板（可在迁移任务 config 里用
#: ``redirect_target_template`` 覆盖，例如 ``/post/{slug}/``）
DEFAULT_TARGET_TEMPLATE = "/article/{slug}"

_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://")


def _looks_like_host(segment: str) -> bool:
    """首段像域名（含点/端口）才当作 host 丢掉；``2020/hello`` 这种相对路径要保留"""
    return "." in segment or ":" in segment or segment.lower().startswith("localhost")


def normalize_path(value: Optional[str]) -> str:
    """把「源站 URL 或路径」归一成站点内路径（去协议/域名/查询/hash，折叠斜杠，去尾斜杠）

    ``https://old.example.com/2020/hello/?utm=x`` → ``/2020/hello``
    ``2020/hello`` → ``/2020/hello``（相对路径不被误当域名）
    """
    text = (value or "").strip()
    if not text:
        return ""
    text = _SCHEME.sub("", text)
    if text.startswith("//"):
        text = text[2:]
    text = text.split("#", 1)[0].split("?", 1)[0]
    if not text.startswith("/"):
        head, _, rest = text.partition("/")
        # 带域名（host 可能没有路径）→ 丢掉 host 段；否则视为相对路径
        text = ("/" + rest) if _looks_like_host(head) else ("/" + text)
    text = re.sub(r"/{2,}", "/", text)
    return text.rstrip("/") if len(text) > 1 else text


class RedirectService:
    """跳转规则管理 + 解析"""

    # ------------------------------------------------------------------ 查询
    async def list_redirects(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        is_active: Optional[bool] = None,
        source: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        conditions: list[Any] = []
        if keyword:
            like = f"%{keyword.strip()}%"
            conditions.append(SeoRedirect.from_path.ilike(like) | SeoRedirect.to_path.ilike(like))
        if is_active is not None:
            conditions.append(SeoRedirect.is_active.is_(bool(is_active)))
        if source:
            conditions.append(SeoRedirect.source == source)

        total = int(
            (await db.execute(select(func.count()).select_from(SeoRedirect).where(*conditions))).scalar()
            or 0
        )
        rows = (
            await db.execute(
                select(SeoRedirect)
                .where(*conditions)
                .order_by(SeoRedirect.id.desc())
                .offset((max(page, 1) - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        return [self._out(row) for row in rows], total

    async def get_redirect(self, db: AsyncSession, redirect_id: int) -> Dict[str, Any]:
        return self._out(await self._row_or_404(db, redirect_id))

    async def stats(self, db: AsyncSession) -> Dict[str, Any]:
        """总览：总数 / 启用数 / 总命中 / 按来源分组"""
        total = int((await db.execute(select(func.count()).select_from(SeoRedirect))).scalar() or 0)
        active = int(
            (
                await db.execute(
                    select(func.count()).select_from(SeoRedirect).where(SeoRedirect.is_active.is_(True))
                )
            ).scalar()
            or 0
        )
        hits = int((await db.execute(select(func.coalesce(func.sum(SeoRedirect.hits), 0)))).scalar() or 0)
        by_source = (
            await db.execute(
                select(SeoRedirect.source, func.count()).group_by(SeoRedirect.source)
            )
        ).all()
        top_rows = (
            await db.execute(
                select(SeoRedirect)
                .where(SeoRedirect.hits > 0)
                .order_by(SeoRedirect.hits.desc())
                .limit(5)
            )
        ).scalars().all()
        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "total_hits": hits,
            "by_source": {str(source or "manual"): int(count) for source, count in by_source},
            "top_hits": [
                {"from_path": row.from_path, "to_path": row.to_path, "hits": int(row.hits or 0)}
                for row in top_rows
            ],
        }

    # ------------------------------------------------------------------ 写入
    async def create_redirect(
        self, db: AsyncSession, payload: Dict[str, Any], *, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        from_path = normalize_path(payload.get("from_path"))
        if not from_path or from_path == "/":
            raise BadRequestError("from_path 不能是站点根路径")
        to_path = (payload.get("to_path") or "").strip()
        if not to_path:
            raise BadRequestError("to_path 不能为空")
        status_code = self._status_code(payload.get("status_code"))
        if normalize_path(to_path) == from_path:
            raise BadRequestError("to_path 不能与 from_path 指向同一路径（会造成自跳转）")

        existing = await self._find_by_path(db, from_path)
        if existing is not None:
            raise ConflictError(f"源路径「{from_path}」已存在跳转规则（id={existing.id}）")

        now = datetime.now()
        row = SeoRedirect(
            from_path=from_path,
            to_path=to_path,
            status_code=status_code,
            is_active=bool(payload.get("is_active", True)),
            hits=0,
            source=payload.get("source") or "manual",
            source_reference=payload.get("source_reference"),
            notes=payload.get("notes"),
            created_by=user_id,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        logger.info("新建跳转 %s → %s（%s）", from_path, to_path, status_code)
        return self._out(row)

    async def update_redirect(
        self, db: AsyncSession, redirect_id: int, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        row = await self._row_or_404(db, redirect_id)

        if payload.get("from_path") is not None:
            from_path = normalize_path(payload["from_path"])
            if not from_path or from_path == "/":
                raise BadRequestError("from_path 不能是站点根路径")
            other = await self._find_by_path(db, from_path)
            if other is not None and int(other.id) != redirect_id:
                raise ConflictError(f"源路径「{from_path}」已被规则 id={other.id} 占用")
            row.from_path = from_path

        if payload.get("to_path") is not None:
            to_path = (payload["to_path"] or "").strip()
            if not to_path:
                raise BadRequestError("to_path 不能为空")
            row.to_path = to_path

        if payload.get("status_code") is not None:
            row.status_code = self._status_code(payload["status_code"])
        if payload.get("is_active") is not None:
            row.is_active = bool(payload["is_active"])
        if payload.get("notes") is not None:
            row.notes = payload["notes"]
        if normalize_path(row.to_path) == normalize_path(row.from_path):
            raise BadRequestError("to_path 不能与 from_path 指向同一路径（会造成自跳转）")

        row.updated_at = datetime.now()
        await db.commit()
        await db.refresh(row)
        return self._out(row)

    async def delete_redirect(self, db: AsyncSession, redirect_id: int) -> None:
        row = await self._row_or_404(db, redirect_id)
        await db.delete(row)
        await db.commit()

    async def bulk_import(
        self,
        db: AsyncSession,
        items: List[Dict[str, Any]],
        *,
        user_id: Optional[int] = None,
        overwrite: bool = True,
        source: str = "manual",
        source_reference: Optional[str] = None,
    ) -> Dict[str, int]:
        """批量导入（对应 v2 的 ``bulk_import``）；``overwrite=False`` 时已存在的路径按跳过计数"""
        created = updated = skipped = 0
        now = datetime.now()
        # 本批次内重复的 from_path 必须先命中内存里的待插入对象：
        # 否则会攒成一次批量 INSERT，撞上 from_path 唯一索引直接 500
        pending: dict[str, SeoRedirect] = {}
        for entry in items:
            from_path = normalize_path(entry.get("from_path"))
            to_path = (entry.get("to_path") or "").strip()
            if not from_path or from_path == "/" or not to_path:
                skipped += 1
                continue
            try:
                status_code = self._status_code(entry.get("status_code"))
            except BadRequestError:
                skipped += 1
                continue
            if normalize_path(to_path) == from_path:
                skipped += 1
                continue

            existing = pending.get(from_path)
            if existing is None:
                existing = await self._find_by_path(db, from_path)
            if existing is None:
                row = SeoRedirect(
                    from_path=from_path,
                    to_path=to_path,
                    status_code=status_code,
                    is_active=bool(entry.get("is_active", True)),
                    hits=0,
                    source=source,
                    source_reference=source_reference,
                    notes=entry.get("notes"),
                    created_by=user_id,
                    created_at=now,
                    updated_at=now,
                )
                db.add(row)
                pending[from_path] = row
                created += 1
                continue

            if not overwrite:
                skipped += 1
                continue
            existing.to_path = to_path
            existing.status_code = status_code
            existing.is_active = bool(entry.get("is_active", existing.is_active))
            if entry.get("notes"):
                existing.notes = entry["notes"]
            existing.updated_at = now
            if from_path not in pending:
                updated += 1

        await db.commit()
        logger.info("批量导入跳转：新增 %s / 更新 %s / 跳过 %s", created, updated, skipped)
        return {"created": created, "updated": updated, "skipped": skipped}

    # ------------------------------------------------------------------ 解析
    async def resolve_path(self, db: AsyncSession, path: str) -> Dict[str, Any]:
        """按站点内路径查跳转；命中则**真实累加** ``hits``"""
        target = normalize_path(path)
        if not target:
            raise BadRequestError("path 不能为空")
        row = await self._find_by_path(db, target)
        if row is None or not row.is_active:
            return {
                "matched": False,
                "from_path": target,
                "to_path": None,
                "status_code": None,
                "hits": int(row.hits or 0) if row is not None else 0,
            }
        row.hits = int(row.hits or 0) + 1
        row.updated_at = datetime.now()
        await db.commit()
        return {
            "matched": True,
            "from_path": target,
            "to_path": row.to_path,
            "status_code": int(row.status_code or 301),
            "hits": int(row.hits),
        }

    # ------------------------------------------------------------------ 导入钩子
    async def record_from_import(
        self,
        db: AsyncSession,
        item: Any,
        article: Any,
        config: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """迁移导入的单篇钩子：源站链接 → 新文章路径

        兼容 WXR 的 ``WXRItem.link`` 与 ``importers.ImportArticle.source_url``。
        手工维护的规则**不会**被导入覆盖（人工优先），导入生成的规则可被后续导入更新。
        """
        source_url = getattr(item, "source_url", None) or getattr(item, "link", None)
        from_path = normalize_path(source_url)
        if not from_path or from_path == "/":
            return None

        config = config or {}
        template = str(config.get("redirect_target_template") or DEFAULT_TARGET_TEMPLATE)
        try:
            to_path = template.format(slug=getattr(article, "slug", "") or "", id=article.id)
        except (KeyError, IndexError, ValueError) as exc:
            logger.warning("redirect_target_template 无效（%s）：%s", template, exc)
            to_path = DEFAULT_TARGET_TEMPLATE.format(slug=getattr(article, "slug", "") or "")
        if normalize_path(to_path) == from_path:
            return None

        file_path = str(config.get("file_path") or "")
        reference = Path(file_path).name if file_path else str(config.get("task_name") or "")
        now = datetime.now()
        existing = await self._find_by_path(db, from_path)
        if existing is not None:
            if existing.source != "migration":
                return self._out(existing)
            existing.to_path = to_path
            existing.is_active = True
            existing.updated_at = now
            return self._out(existing)

        row = SeoRedirect(
            from_path=from_path,
            to_path=to_path,
            status_code=301,
            is_active=True,
            hits=0,
            source="migration",
            source_reference=reference[:500] or None,
            notes=None,
            created_by=getattr(article, "user", None),
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        return self._out(row)

    # ------------------------------------------------------------------ 内部
    @staticmethod
    def _status_code(value: Any) -> int:
        try:
            status_code = int(value if value is not None else 301)
        except (TypeError, ValueError):
            raise BadRequestError("status_code 必须是整数") from None
        if status_code not in STATUS_CODES:
            raise BadRequestError(f"status_code 只支持 {list(STATUS_CODES)}")
        return status_code

    @staticmethod
    async def _find_by_path(db: AsyncSession, from_path: str) -> Optional[SeoRedirect]:
        return (
            await db.execute(
                select(SeoRedirect).where(SeoRedirect.from_path == from_path).limit(1)
            )
        ).scalars().first()

    async def _row_or_404(self, db: AsyncSession, redirect_id: int) -> SeoRedirect:
        row = await db.get(SeoRedirect, redirect_id)
        if row is None:
            raise NotFoundError("跳转规则不存在")
        return row

    @staticmethod
    def _out(row: SeoRedirect) -> Dict[str, Any]:
        return {
            "id": row.id,
            "from_path": row.from_path,
            "to_path": row.to_path,
            "status_code": int(row.status_code or 301),
            "is_active": bool(row.is_active),
            "hits": int(row.hits or 0),
            "source": row.source,
            "source_reference": row.source_reference,
            "notes": row.notes,
            "created_by": row.created_by,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }


redirect_service = RedirectService()
