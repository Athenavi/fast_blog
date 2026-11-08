# -*- coding: utf-8 -*-
"""多站点聚合的站点收窄 + 审批不能自审/重复审批。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


class TestSiteCondition:
    def test_returns_condition_with_site_context(self):
        from src.api.v3.core.tenancy import site_condition
        from shared.models.article.article import Article

        with patch("src.api.v3.core.tenancy.site_filter_value", return_value=3):
            condition = site_condition(Article)
        assert condition is not None
        assert "site_id" in str(condition)

    def test_returns_none_without_site_context(self):
        from src.api.v3.core.tenancy import site_condition
        from shared.models.article.article import Article

        with patch("src.api.v3.core.tenancy.site_filter_value", return_value=None):
            assert site_condition(Article) is None


class TestApprovalDecide:
    pytestmark = pytest.mark.asyncio

    def _record(self, **overrides):
        record = MagicMock()
        record.id = 1
        record.status = "pending"
        record.current_level = 1
        record.max_level = 2
        record.applicant_id = 9
        for key, value in overrides.items():
            setattr(record, key, value)
        return record

    def _db(self, steps: int = 0):
        db = AsyncMock()
        result = MagicMock()
        result.scalar.return_value = steps
        db.execute = AsyncMock(return_value=result)
        return db

    async def test_applicant_cannot_approve_self(self):
        from src.api.v3.core.exceptions import ForbiddenError
        from src.api.v3.modules.content.approval.service import approval_service

        record = self._record(applicant_id=5)
        payload = SimpleNamespace(action="approve", comment=None)
        with patch(
            "src.api.v3.modules.content.approval.service.approval_record_crud.get",
            AsyncMock(return_value=record),
        ):
            with pytest.raises(ForbiddenError):
                await approval_service.decide(self._db(), 1, payload, approver_id=5)

    async def test_same_approver_cannot_decide_twice(self):
        from src.api.v3.core.exceptions import BadRequestError
        from src.api.v3.modules.content.approval.service import approval_service

        record = self._record()
        payload = SimpleNamespace(action="approve", comment=None)
        with patch(
            "src.api.v3.modules.content.approval.service.approval_record_crud.get",
            AsyncMock(return_value=record),
        ):
            with pytest.raises(BadRequestError, match="重复审批"):
                await approval_service.decide(self._db(steps=1), 1, payload, approver_id=5)

    async def test_distinct_approver_can_decide(self):
        from src.api.v3.modules.content.approval.service import approval_service

        record = self._record()
        payload = SimpleNamespace(action="approve", comment=None)
        db = self._db(steps=0)
        db.refresh = AsyncMock()
        with patch(
            "src.api.v3.modules.content.approval.service.approval_record_crud.get",
            AsyncMock(return_value=record),
        ), patch(
            "src.api.v3.modules.content.approval.service._record_out",
            MagicMock(side_effect=lambda row: {"status": row.status}),
        ):
            result = await approval_service.decide(db, 1, payload, approver_id=5)
        assert result["status"] in ("pending", "approved")
