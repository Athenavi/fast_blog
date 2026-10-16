"""发布前的审批闸门：让审批单真正拦得住发布（真实查库，无占位/模拟分支）。

**背景**：``approval_records`` 早已存在，``decide`` 也能真实流转多级审批，但发布路径
**完全不检查它** —— 审批单只是「被记录下来」，任何人都能绕过审批直接发布。本模块把它接进发布。

规则（按优先级，逐条可测）：

  1. 该内容**最新**一条审批单是 ``pending`` → 拒绝（有审批单待处理）；
  2. 最新一条是 ``rejected`` → 拒绝（上一次审批被驳回）；
  3. 最新一条是 ``approved`` → 允许；
  4. 没有审批单（或最新是 ``cancelled``）：
     - ``content_type`` 命中配置 ``content.approval.required_types``（JSON 数组）→ 拒绝（未走审批）；
     - 否则 → 允许 —— **默认不强制**，以免把历史内容一夜之间全部锁死。

**为什么配置读不到时不强制**：规则 1–3 完全不依赖配置，安全性不会因此下降；反之若读不到
配置就 fail-closed，配置表一异常就会把整个站点的发布锁死。两条路都不理想，取影响面小的那个，
并且每次都留下 warning。

批量校验用**一次** ``IN`` 查询 + 按时间倒序取首条，避免 N+1；批量与单条走同一实现，
保证两者判定永远一致。
"""

from __future__ import annotations

from typing import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.collaboration import ApprovalRecord
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.core.logger import get_logger

logger = get_logger("approval.guard")

#: 「必须先通过审批」的内容类型配置键（JSON 数组，如 ``["article"]``）；不存在即默认不强制
REQUIRED_TYPES_KEY = "content.approval.required_types"

#: 文章在审批单里的 ``content_type`` 取值（与 approval schema 的默认值一致）
ARTICLE_CONTENT_TYPE = "article"

#: 页面在审批单里的 ``content_type`` 取值（approval schema 注释里的 ``article/page/…``）
PAGE_CONTENT_TYPE = "page"

#: 这些状态会拦住发布（键 → 拦截原因文案）
_BLOCKING_REASONS = {
    "pending": "存在待处理的审批单",
    "rejected": "审批已被驳回",
}

#: 视为「没有有效审批」的状态：需要审批的类型此时应被拦下
_NO_APPROVAL_STATUSES = (None, "", "cancelled")


def _normalize_ids(ids: Iterable[int]) -> list[int]:
    """把入参规整为 int 列表（跳过无法转换的值，绝不因脏数据抛 500）"""
    normalized: list[int] = []
    for raw in ids:
        try:
            normalized.append(int(raw))
        except (TypeError, ValueError):  # noqa: PERF203 - 入参来自外部，需逐个兜底
            continue
    return normalized


async def _latest_status_by_content(
    db: AsyncSession, content_type: str, ids: Sequence[int]
) -> dict[int, str]:
    """每个 ``content_id`` 的**最新**审批单状态（一次 IN 查询，避免 N+1）"""
    rows = (
        await db.execute(
            select(ApprovalRecord.content_id, ApprovalRecord.status)
            .where(
                ApprovalRecord.content_type == content_type,
                ApprovalRecord.content_id.in_(list(ids)),
            )
            .order_by(
                ApprovalRecord.content_id,
                ApprovalRecord.created_at.desc(),
                ApprovalRecord.id.desc(),
            )
        )
    ).all()

    latest: dict[int, str] = {}
    for content_id, status in rows:
        if content_id is None:
            continue
        key = int(content_id)
        if key not in latest:  # 已按时间倒序 → 首条即最新
            latest[key] = (status or "").strip().lower()
    return latest


async def required_types(db: AsyncSession) -> frozenset[str]:
    """需要「必须先通过审批」的内容类型。

    读取失败或格式非法 → 空集合（不强制）并记 warning，理由见模块 docstring。
    """
    # 延迟导入：避免 article → approval → setting 的模块级依赖链
    from src.api.v3.modules.system.setting.crud import setting_crud
    from src.api.v3.modules.system.setting.service import parse_value

    try:
        row = await setting_crud.get_by(db, setting_key=REQUIRED_TYPES_KEY)
    except Exception as exc:  # noqa: BLE001 - 配置读取失败不应阻断业务
        logger.warning("读取 %s 失败，本次按「不强制审批」处理：%s", REQUIRED_TYPES_KEY, exc)
        return frozenset()

    if row is None:
        return frozenset()

    value = parse_value(getattr(row, "setting_value", None), getattr(row, "setting_type", None))
    if isinstance(value, str):
        # 兼容「逗号分隔字符串」的历史写法
        candidates = [item.strip() for item in value.split(",")]
    elif isinstance(value, (list, tuple, set)):
        candidates = [str(item).strip() for item in value]
    else:
        logger.warning(
            "%s 的值既不是数组也不是字符串（实际 %s），本次不强制审批",
            REQUIRED_TYPES_KEY,
            type(value).__name__,
        )
        return frozenset()

    return frozenset(item for item in candidates if item)


async def ensure_batch_publish_allowed(
    db: AsyncSession, *, content_type: str, ids: Sequence[int]
) -> None:
    """批量校验：任一条不通过就整体拒绝，并**列出全部原因**（便于一次改完）"""
    normalized = _normalize_ids(ids)
    if not normalized:
        return

    latest = await _latest_status_by_content(db, content_type, normalized)
    must_approve = content_type in await required_types(db)

    blocked: list[str] = []
    for content_id in normalized:
        status = latest.get(content_id)
        if status in _BLOCKING_REASONS:
            blocked.append(f"#{content_id} {_BLOCKING_REASONS[status]}")
        elif status in _NO_APPROVAL_STATUSES and must_approve:
            blocked.append(f"#{content_id} 尚未通过审批（{content_type} 已配置为必须审批）")

    if blocked:
        logger.info("发布被审批流拦截 type=%s：%s", content_type, "；".join(blocked))
        raise BadRequestError("发布被审批流拦截：" + "；".join(blocked))


async def ensure_publish_allowed(
    db: AsyncSession, *, content_type: str, content_id: int
) -> None:
    """单条校验（复用批量实现，保证两者判定一致）"""
    await ensure_batch_publish_allowed(db, content_type=content_type, ids=[content_id])


async def ensure_new_content_publish_allowed(db: AsyncSession, *, content_type: str) -> None:
    """**新建内容直接发布**时的校验。

    此刻记录还不存在（没有 id），因此不可能已经有审批单 —— 只看该类型是否被配置为
    「必须先审批后发布」。未配置则放行，保持既有「直接建草稿 / 直接发布」的行为不变。
    """
    if content_type in await required_types(db):
        raise BadRequestError(
            f"不能直接发布新建的 {content_type}：该类型已配置为「先审批后发布」，"
            "请先保存为草稿，再提交审批，通过后发布"
        )


__all__ = [
    "ARTICLE_CONTENT_TYPE",
    "PAGE_CONTENT_TYPE",
    "REQUIRED_TYPES_KEY",
    "ensure_batch_publish_allowed",
    "ensure_new_content_publish_allowed",
    "ensure_publish_allowed",
    "required_types",
]
