"""certification 模块业务逻辑（专家认证 / 审核流）

**与 v2 的差异**：v2 的 `services/advanced_features/expert_certification.py` 是**进程内内存单例**
（重启即失、多 worker 各一份），没有任何审核记录，也没有有效期概念。这里是真表 + 真状态机：

    pending --approve--> approved --revoke--> revoked
       |                                      ^
       |--reject--> rejected                   |
       |--withdraw ----------------------------|

- 通过时写 ``issued_at`` / ``expires_at``（**两年**有效期）；
- **过期的认证不再出现在公开的「认证专家」列表里**（查询时按 ``expires_at`` 过滤，
  而不是像内存版那样假装一直有效）；
- 每次状态变更都往 ``certification_reviews`` 追加一条流水（可追溯谁在何时改成了什么）；
- ``id_number`` 只收不回显（``CertificationOut`` 根本没有这个字段）。
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.certification import ExpertCertification
from shared.models.user import User
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.gamification.certification.crud import (
    certification_document_crud,
    certification_review_crud,
    expert_certification_crud,
)
from src.api.v3.modules.gamification.certification.schema import (
    CERT_TYPES,
    VALIDITY_YEARS,
    CertTypeOut,
    CertificationActionRequest,
    CertificationApplyRequest,
    CertificationDocumentOut,
    CertificationOut,
    CertificationReviewOut,
    CertificationReviewRequest,
    CertificationUpdateRequest,
)

logger = get_logger("gamification.certification")

#: 这些状态下允许重新提交申请（被驳回 / 已撤销）
REAPPLYABLE = ("rejected", "revoked")
#: 占用中（不可重复申请）的状态
OCCUPYING = ("pending", "approved")
MAX_PAGE_SIZE = 100
EXPIRING_SOON_DAYS = 30

_TYPE_NAMES = dict(CERT_TYPES)


def _type_name(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    return _TYPE_NAMES.get(code, code)


def _is_expired(row: ExpertCertification) -> bool:
    return bool(row.expires_at is not None and row.expires_at < datetime.now())


class CertificationService:
    """专家认证"""

    # ------------------------------------------------------------ 静态
    @staticmethod
    def types() -> list[dict]:
        """认证类型（公开；与 schema 的 CERT_TYPES 保持单一来源）"""
        return [CertTypeOut(code=code, name=name).model_dump() for code, name in CERT_TYPES]

    async def _usernames(self, db: AsyncSession, user_ids: list[int]) -> dict[int, str]:
        if not user_ids:
            return {}
        rows = (
            await db.execute(select(User.id, User.username).where(User.id.in_(set(user_ids))))
        ).all()
        return {int(row.id): row.username for row in rows}

    # ------------------------------------------------------------ 拼装输出
    async def _documents(self, db: AsyncSession, cert_id: int) -> list[dict]:
        rows, _total = await certification_document_crud.list(
            db, page=1, page_size=0, filters={"certification_id": cert_id}
        )
        return [
            CertificationDocumentOut.model_validate(row, from_attributes=True).model_dump(mode="json")
            for row in sorted(rows, key=lambda row: row.id)
        ]

    async def _out(
        self,
        db: AsyncSession,
        row: ExpertCertification,
        *,
        with_documents: bool = False,
        usernames: Optional[dict[int, str]] = None,
    ) -> dict:
        names = usernames if usernames is not None else await self._usernames(db, [row.user_id])
        payload = CertificationOut(
            id=row.id,
            user_id=row.user_id,
            username=names.get(row.user_id),
            cert_type=row.cert_type,
            cert_type_name=_type_name(row.cert_type),
            status=row.status or "pending",
            real_name=row.real_name,
            organization=row.organization,
            position=row.position,
            department=row.department,
            work_years=int(row.work_years or 0),
            intro=row.intro,
            achievements=row.achievements,
            portfolio_url=row.portfolio_url,
            applied_at=row.applied_at,
            reviewed_at=row.reviewed_at,
            review_comment=row.review_comment,
            issued_at=row.issued_at,
            expires_at=row.expires_at,
            is_expired=_is_expired(row),
        )
        data = payload.model_dump(mode="json")
        if with_documents:
            data["documents"] = await self._documents(db, row.id)
        return data

    async def _log(
        self,
        db: AsyncSession,
        cert_id: int,
        action: str,
        *,
        reviewer_id: Optional[int] = None,
        comment: Optional[str] = None,
    ) -> None:
        now = datetime.now()
        await certification_review_crud.create(
            db,
            {
                "certification_id": cert_id,
                "reviewer_id": reviewer_id,
                "action": action,
                "comment": comment,
                "created_at": now,
                "updated_at": now,
            },
        )

    async def _latest(self, db: AsyncSession, user_id: int) -> Optional[ExpertCertification]:
        rows, _total = await expert_certification_crud.list(
            db, page=1, page_size=0, filters={"user_id": user_id}
        )
        if not rows:
            return None
        return max(rows, key=lambda row: (row.applied_at or datetime.min, row.id))

    # ------------------------------------------------------------ 前台
    async def mine(self, db: AsyncSession, user_id: int) -> Optional[dict]:
        row = await self._latest(db, user_id)
        if row is None:
            return None
        return await self._out(db, row, with_documents=True)

    async def apply(self, db: AsyncSession, user_id: int, payload: CertificationApplyRequest) -> dict:
        if payload.cert_type not in _TYPE_NAMES:
            raise BadRequestError(f"不支持的认证类型：{payload.cert_type}")
        current = await self._latest(db, user_id)
        if current is not None and current.status in OCCUPYING:
            raise BadRequestError(
                "已有待审核或已通过的认证" if current.status == "pending" else "已经是认证专家，无需重复申请"
            )

        now = datetime.now()
        row = await expert_certification_crud.create(
            db,
            {
                "user_id": user_id,
                "cert_type": payload.cert_type,
                "status": "pending",
                "real_name": payload.real_name,
                "id_number": payload.id_number,
                "phone": payload.phone,
                "email": payload.email,
                "organization": payload.organization,
                "position": payload.position,
                "department": payload.department,
                "work_years": payload.work_years,
                "intro": payload.intro,
                "achievements": payload.achievements,
                "portfolio_url": payload.portfolio_url,
                "applied_at": now,
                "created_at": now,
                "updated_at": now,
            },
        )
        for item in payload.documents:
            await certification_document_crud.create(
                db,
                {
                    "certification_id": row.id,
                    "user_id": user_id,
                    "file_name": item.file_name,
                    "file_url": item.file_url,
                    "file_type": item.file_type,
                    "file_size": item.file_size,
                    "created_at": now,
                    "updated_at": now,
                },
            )
        await self._log(db, row.id, "submit")
        logger.info("专家认证申请: user=%s type=%s", user_id, payload.cert_type)
        return await self._out(db, row, with_documents=True)

    async def update_mine(
        self, db: AsyncSession, user_id: int, payload: CertificationUpdateRequest
    ) -> dict:
        row = await self._latest(db, user_id)
        if row is None:
            raise NotFoundError("还没有提交过认证申请")
        if row.status != "pending":
            raise BadRequestError("只有待审核的申请才能修改")
        data = payload.model_dump(exclude_unset=True)
        if payload.cert_type is not None and payload.cert_type not in _TYPE_NAMES:
            raise BadRequestError(f"不支持的认证类型：{payload.cert_type}")
        if not data:
            return await self._out(db, row, with_documents=True)
        row = await expert_certification_crud.update(db, row, data | {"updated_at": datetime.now()})
        return await self._out(db, row, with_documents=True)

    async def withdraw(
        self, db: AsyncSession, user_id: int, payload: CertificationActionRequest
    ) -> dict:
        row = await self._latest(db, user_id)
        if row is None:
            raise NotFoundError("还没有提交过认证申请")
        if row.status != "pending":
            raise BadRequestError("只有待审核的申请才能撤回")
        now = datetime.now()
        row = await expert_certification_crud.update(
            db, row, {"status": "revoked", "updated_at": now}
        )
        await self._log(db, row.id, "withdraw", reviewer_id=None, comment=payload.comment or "申请人主动撤回")
        return await self._out(db, row, with_documents=True)

    async def experts(
        self,
        db: AsyncSession,
        *,
        cert_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """公开的认证专家列表 —— **排除已过期**（内存版没有这个概念）"""
        now = datetime.now()
        conditions = [
            ExpertCertification.status == "approved",
            or_(ExpertCertification.expires_at.is_(None), ExpertCertification.expires_at > now),
        ]
        if cert_type:
            conditions.append(ExpertCertification.cert_type == cert_type)

        total = int(
            (
                await db.execute(
                    select(func.count()).select_from(ExpertCertification).where(*conditions)
                )
            ).scalar()
            or 0
        )
        size = max(1, min(page_size, MAX_PAGE_SIZE))
        rows = (
            (
                await db.execute(
                    select(ExpertCertification)
                    .where(*conditions)
                    .order_by(ExpertCertification.issued_at.desc(), ExpertCertification.id.desc())
                    .offset((max(1, page) - 1) * size)
                    .limit(size)
                )
            )
            .scalars()
            .all()
        )
        names = await self._usernames(db, [row.user_id for row in rows])
        return [await self._out(db, row, usernames=names) for row in rows], total

    async def expert_detail(self, db: AsyncSession, user_id: int) -> dict:
        now = datetime.now()
        rows = (
            (
                await db.execute(
                    select(ExpertCertification)
                    .where(
                        ExpertCertification.user_id == user_id,
                        ExpertCertification.status == "approved",
                        or_(
                            ExpertCertification.expires_at.is_(None),
                            ExpertCertification.expires_at > now,
                        ),
                    )
                    .order_by(ExpertCertification.issued_at.desc())
                    .limit(1)
                )
            )
            .scalars()
            .all()
        )
        if not rows:
            raise NotFoundError("该用户不是（或已不是）认证专家")
        return await self._out(db, rows[0], with_documents=True)

    # ------------------------------------------------------------ 管理端
    async def pending(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]:
        rows, total = await expert_certification_crud.list(
            db,
            page=page,
            page_size=min(page_size, MAX_PAGE_SIZE),
            filters={"status": "pending"},
        )
        names = await self._usernames(db, [row.user_id for row in rows])
        return [await self._out(db, row, with_documents=True, usernames=names) for row in rows], total

    async def reviews_of(self, db: AsyncSession, cert_id: int) -> list[dict]:
        rows, _total = await certification_review_crud.list(
            db, page=1, page_size=0, filters={"certification_id": cert_id}
        )
        return [
            CertificationReviewOut.model_validate(row, from_attributes=True).model_dump(mode="json")
            for row in sorted(rows, key=lambda row: row.id)
        ]

    async def review(
        self,
        db: AsyncSession,
        cert_id: int,
        payload: CertificationReviewRequest,
        operator_id: int,
    ) -> dict:
        row = await expert_certification_crud.get(db, cert_id)
        if row is None:
            raise NotFoundError("认证申请不存在")
        if row.status != "pending":
            raise BadRequestError(f"当前状态（{row.status}）不可审核，只有待审核的申请能审核")

        now = datetime.now()
        if payload.approve:
            data: dict = {
                "status": "approved",
                "issued_at": now,
                "expires_at": now + timedelta(days=365 * VALIDITY_YEARS),
            }
        else:
            data = {"status": "rejected"}
        data.update(
            {"reviewed_at": now, "reviewer_id": operator_id, "review_comment": payload.comment, "updated_at": now})
        row = await expert_certification_crud.update(db, row, data)
        await self._log(
            db,
            row.id,
            "approve" if payload.approve else "reject",
            reviewer_id=operator_id,
            comment=payload.comment,
        )
        logger.info("专家认证审核: cert=%s approve=%s operator=%s", cert_id, payload.approve, operator_id)
        return await self._out(db, row, with_documents=True)

    async def revoke(
        self,
        db: AsyncSession,
        cert_id: int,
        payload: CertificationActionRequest,
        operator_id: int,
    ) -> dict:
        row = await expert_certification_crud.get(db, cert_id)
        if row is None:
            raise NotFoundError("认证不存在")
        if row.status != "approved":
            raise BadRequestError(f"当前状态（{row.status}）不可撤销，只有已通过的认证能撤销")
        now = datetime.now()
        row = await expert_certification_crud.update(
            db,
            row,
            {
                "status": "revoked",
                "reviewed_at": now,
                "reviewer_id": operator_id,
                "review_comment": payload.comment,
                "updated_at": now,
            },
        )
        await self._log(db, row.id, "revoke", reviewer_id=operator_id, comment=payload.comment)
        logger.info("专家认证撤销: cert=%s operator=%s", cert_id, operator_id)
        return await self._out(db, row, with_documents=True)

    async def stats(self, db: AsyncSession) -> dict:
        rows = (
            await db.execute(
                select(ExpertCertification.status, func.count(ExpertCertification.id))
                .group_by(ExpertCertification.status)
            )
        ).all()
        counts = {str(status): int(count or 0) for status, count in rows}

        now = datetime.now()
        soon = now + timedelta(days=EXPIRING_SOON_DAYS)
        expiring_soon = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(ExpertCertification)
                    .where(
                        ExpertCertification.status == "approved",
                        ExpertCertification.expires_at.is_not(None),
                        ExpertCertification.expires_at > now,
                        ExpertCertification.expires_at <= soon,
                    )
                )
            ).scalar()
            or 0
        )
        expired = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(ExpertCertification)
                    .where(
                        ExpertCertification.status == "approved",
                        ExpertCertification.expires_at.is_not(None),
                        ExpertCertification.expires_at <= now,
                    )
                )
            ).scalar()
            or 0
        )
        by_type = (
            await db.execute(
                select(ExpertCertification.cert_type, func.count(ExpertCertification.id))
                .where(ExpertCertification.status == "approved")
                .group_by(ExpertCertification.cert_type)
                .order_by(func.count(ExpertCertification.id).desc())
            )
        ).all()
        return {
            "total": sum(counts.values()),
            "pending": counts.get("pending", 0),
            "approved": counts.get("approved", 0),
            "rejected": counts.get("rejected", 0),
            "revoked": counts.get("revoked", 0),
            "expiring_soon": expiring_soon,
            "expired": expired,
            "by_type": [
                {"cert_type": code, "cert_type_name": _type_name(code), "count": int(count or 0)}
                for code, count in by_type
            ],
        }


certification_service = CertificationService()
