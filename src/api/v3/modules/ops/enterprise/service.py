"""enterprise 模块业务逻辑：企业许可证与数据保留策略

``license_key`` 唯一（重复 → 409）；``features`` 列是 JSON 字符串，
入参 ``list[str]`` 经 ``json.dumps`` 落库，出参由 schema 还原为列表。
"""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import ConflictError, NotFoundError
from src.api.v3.modules.ops.enterprise.crud import (
    data_retention_policy_crud,
    enterprise_license_crud,
)
from src.api.v3.modules.ops.enterprise.schema import (
    DataRetentionPolicyCreate,
    DataRetentionPolicyOut,
    DataRetentionPolicyUpdate,
    EnterpriseLicenseCreate,
    EnterpriseLicenseOut,
    EnterpriseLicenseUpdate,
)


def _license_out(row) -> dict:
    return EnterpriseLicenseOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _policy_out(row) -> dict:
    return DataRetentionPolicyOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _dump_features(features: Optional[list[str]]) -> Optional[str]:
    return json.dumps(features, ensure_ascii=False) if features else None


class EnterpriseLicenseService:
    """企业版许可证（ops 域）"""

    async def list_licenses(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20, keyword: Optional[str] = None
    ) -> tuple[list[dict], int]:
        rows, total = await enterprise_license_crud.list(
            db, page=page, page_size=page_size, keyword=keyword
        )
        return [_license_out(r) for r in rows], total

    async def create_license(self, db: AsyncSession, payload: EnterpriseLicenseCreate) -> dict:
        if await enterprise_license_crud.exists(db, license_key=payload.license_key):
            raise ConflictError(f"许可证密钥已存在: {payload.license_key}")
        row = await enterprise_license_crud.create(
            db,
            payload.model_dump(exclude={"features"})
            | {
                "features": _dump_features(payload.features),
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        )
        return _license_out(row)

    async def update_license(
        self, db: AsyncSession, license_id: int, payload: EnterpriseLicenseUpdate
    ) -> dict:
        row = await enterprise_license_crud.get(db, license_id)
        if row is None:
            raise NotFoundError("许可证不存在")
        data = payload.model_dump(exclude_unset=True)
        if "license_key" in data and data["license_key"] != row.license_key:
            if await enterprise_license_crud.exists(db, license_key=data["license_key"]):
                raise ConflictError(f"许可证密钥已存在: {data['license_key']}")
        if "features" in data:
            data["features"] = _dump_features(data.pop("features"))
        updated = await enterprise_license_crud.update(
            db, row, data | {"updated_at": datetime.now()}
        )
        return _license_out(updated)

    async def delete_license(self, db: AsyncSession, license_id: int) -> None:
        row = await enterprise_license_crud.get(db, license_id)
        if row is None:
            raise NotFoundError("许可证不存在")
        await enterprise_license_crud.remove(db, row)


class DataRetentionPolicyService:
    """数据保留策略（ops 域）"""

    async def list_policies(
        self, db: AsyncSession, *, page: int = 1, page_size: int = 20, keyword: Optional[str] = None
    ) -> tuple[list[dict], int]:
        rows, total = await data_retention_policy_crud.list(
            db, page=page, page_size=page_size, keyword=keyword
        )
        return [_policy_out(r) for r in rows], total

    async def create_policy(self, db: AsyncSession, payload: DataRetentionPolicyCreate) -> dict:
        row = await data_retention_policy_crud.create(
            db,
            payload.model_dump() | {"created_at": datetime.now(), "updated_at": datetime.now()},
        )
        return _policy_out(row)

    async def update_policy(
        self, db: AsyncSession, policy_id: int, payload: DataRetentionPolicyUpdate
    ) -> dict:
        row = await data_retention_policy_crud.get(db, policy_id)
        if row is None:
            raise NotFoundError("数据保留策略不存在")
        updated = await data_retention_policy_crud.update(
            db, row, payload.model_dump(exclude_unset=True) | {"updated_at": datetime.now()}
        )
        return _policy_out(updated)

    async def delete_policy(self, db: AsyncSession, policy_id: int) -> None:
        row = await data_retention_policy_crud.get(db, policy_id)
        if row is None:
            raise NotFoundError("数据保留策略不存在")
        await data_retention_policy_crud.remove(db, row)


enterprise_license_service = EnterpriseLicenseService()
data_retention_policy_service = DataRetentionPolicyService()
