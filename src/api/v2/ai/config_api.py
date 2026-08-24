"""
AI 配置管理 API
用户 AI 助手配置的 CRUD，每人最多 10 条
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User
from shared.models.ai.ai_config import AIConfig
from shared.utils.crypto import encrypt_api_key, decrypt_api_key
from src.api.v2._helpers import ok, fail, _catch
from src.auth.auth_deps import jwt_required_dependency as jwt_required, get_current_active_user
from src.extensions import get_async_db_session as get_async_db
from src.setting import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ai-config"])


MAX_CONFIGS_PER_USER = 10


def _encrypt(api_key: str, user: User) -> str:
    """加密 API Key"""
    return encrypt_api_key(api_key, user.password or '', settings.SECRET_KEY)


def _decrypt(encrypted: str, user: User) -> Optional[str]:
    """解密 API Key"""
    return decrypt_api_key(encrypted, user.password or '', settings.SECRET_KEY)


@router.get("/ai/configs", summary="获取用户的 AI 配置列表")
@_catch
async def list_configs(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    """获取当前用户的所有 AI 配置（不包含加密的 API Key）"""
    result = await db.execute(
        select(AIConfig).where(AIConfig.user_id == current_user.id).order_by(AIConfig.sort_order, AIConfig.created_at.desc())
    )
    configs = result.scalars().all()
    return ok(data=[c.to_dict() for c in configs])


@router.post("/ai/configs", summary="创建 AI 配置")
@_catch
async def create_config(
    name: str = Query(...),
    api_url: str = Query(...),
    api_key: str = Query(...),
    model: str = Query(...),
    provider: str = Query("openai"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    """创建新的 AI 配置（API Key 加密存储，最多 10 条）"""
    # 检查数量限制
    count = await db.scalar(
        select(func.count(AIConfig.id)).where(AIConfig.user_id == current_user.id)
    )
    if count and count >= MAX_CONFIGS_PER_USER:
        return fail(f"最多只能创建 {MAX_CONFIGS_PER_USER} 条配置")

    # 检查名称唯一
    existing = await db.scalar(
        select(AIConfig).where(and_(AIConfig.user_id == current_user.id, AIConfig.name == name))
    )
    if existing:
        return fail("配置名称已存在")

    encrypted = _encrypt(api_key, current_user)
    now = datetime.now()
    config = AIConfig(
        user_id=current_user.id,
        name=name,
        api_url=api_url,
        api_key_encrypted=encrypted,
        model=model,
        provider=provider,
        is_active=False,
        sort_order=0,
        created_at=now,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return ok(data=config.to_dict(), msg="配置创建成功")


@router.put("/ai/configs/{config_id}", summary="更新 AI 配置")
@_catch
async def update_config(
    config_id: int,
    name: Optional[str] = Query(None),
    api_url: Optional[str] = Query(None),
    api_key: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    """更新 AI 配置（只传需要修改的字段）"""
    config = await db.scalar(
        select(AIConfig).where(and_(AIConfig.id == config_id, AIConfig.user_id == current_user.id))
    )
    if not config:
        return fail("配置不存在")

    if name is not None:
        # 检查名称唯一
        dup = await db.scalar(
            select(AIConfig).where(and_(AIConfig.user_id == current_user.id, AIConfig.name == name, AIConfig.id != config_id))
        )
        if dup:
            return fail("配置名称已存在")
        config.name = name
    if api_url is not None:
        config.api_url = api_url
    if api_key is not None:
        config.api_key_encrypted = _encrypt(api_key, current_user)
    if model is not None:
        config.model = model
    if provider is not None:
        config.provider = provider
    config.updated_at = datetime.now()

    await db.commit()
    await db.refresh(config)
    return ok(data=config.to_dict(), msg="配置更新成功")


@router.delete("/ai/configs/{config_id}", summary="删除 AI 配置")
@_catch
async def delete_config(
    config_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    """删除 AI 配置"""
    config = await db.scalar(
        select(AIConfig).where(and_(AIConfig.id == config_id, AIConfig.user_id == current_user.id))
    )
    if not config:
        return fail("配置不存在")
    await db.delete(config)
    await db.commit()
    return ok(msg="配置已删除")


@router.post("/ai/configs/{config_id}/activate", summary="激活 AI 配置")
@_catch
async def activate_config(
    config_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    """激活指定的 AI 配置（同一用户的其他配置自动取消激活）"""
    config = await db.scalar(
        select(AIConfig).where(and_(AIConfig.id == config_id, AIConfig.user_id == current_user.id))
    )
    if not config:
        return fail("配置不存在")

    # 取消所有激活
    await db.execute(
        select(AIConfig).where(AIConfig.user_id == current_user.id).update({"is_active": False})
    )
    # 激活目标配置
    config.is_active = True
    config.updated_at = datetime.now()
    await db.commit()
    return ok(data=config.to_dict(), msg="配置已激活")


@router.get("/ai/configs/active", summary="获取当前激活的 AI 配置（含解密后的 API Key）")
@_catch
async def get_active_config(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    """获取当前用户激活的 AI 配置，返回解密后的 api_key（用于 AI Chat 自动使用）"""
    config = await db.scalar(
        select(AIConfig).where(and_(AIConfig.user_id == current_user.id, AIConfig.is_active == True))
    )
    if not config:
        return ok(data=None)

    data = config.to_dict()
    decrypted = _decrypt(config.api_key_encrypted, current_user)
    data["api_key"] = decrypted
    return ok(data=data)
