"""
AI 配置管理 API
用户 AI 助手配置�?CRUD，每人最�?10 �?"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config.settings import settings
from shared.models import User
from shared.models.ai.ai_config import AIConfig
from shared.utils.crypto import encrypt_api_key, decrypt_api_key
from src.api.v2._helpers import ok, fail, _catch
from src.auth.auth_deps import get_current_active_user
from src.utils.database.unified_manager import get_db_session as get_async_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ai-config"])


MAX_CONFIGS_PER_USER = 10


class CreateConfigRequest(BaseModel):
    """创建 AI 配置请求（Body 传递，避免 API Key 出现�?URL 参数/日志中）"""
    name: str
    api_url: str
    api_key: str
    model: str
    provider: str = "openai"


class UpdateConfigRequest(BaseModel):
    """更新 AI 配置请求（Body 传递，避免 API Key 出现�?URL 参数/日志中）"""
    name: str | None = None
    api_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    provider: str | None = None


def _encrypt(api_key: str, user: User) -> str:
    """加密 API Key"""
    return encrypt_api_key(api_key, user.password or '', settings.SECRET_KEY)


def _decrypt(encrypted: str, user: User) -> Optional[str]:
    """解密 API Key"""
    return decrypt_api_key(encrypted, user.password or '', settings.SECRET_KEY)


@router.get("/ai/configs", summary="获取用户�?AI 配置列表")
@_catch
async def list_configs(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    """获取当前用户的所�?AI 配置（不包含加密�?API Key�?""
    result = await db.execute(
        select(AIConfig).where(AIConfig.user_id == current_user.id).order_by(AIConfig.sort_order, AIConfig.created_at.desc())
    )
    configs = result.scalars().all()
    return ok(data=[c.to_dict() for c in configs])


@router.post("/ai/configs", summary="创建 AI 配置")
@_catch
async def create_config(
    req: CreateConfigRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    创建新的
    AI
    配置（API
    Key
    加密存储，最�?10
    条）"""
    # 检查数量限�?    count = await db.scalar(
        select(func.count(AIConfig.id)).where(AIConfig.user_id == current_user.id)
    )
    if count and count >= MAX_CONFIGS_PER_USER:
        return fail(f"最多只能创�?{MAX_CONFIGS_PER_USER} 条配�?)

    # 检查名称唯一
    existing = await db.scalar(
        select(AIConfig).where(and_(AIConfig.user_id == current_user.id, AIConfig.name == req.name))
    )
    if existing:
        return fail("配置名称已存�?)

    encrypted = _encrypt(req.api_key, current_user)
    now = datetime.now()
    config = AIConfig(
        user_id=current_user.id,
        name=req.name,
        api_url=req.api_url,
        api_key_encrypted=encrypted,
        model=req.model,
        provider=req.provider,
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
    req: UpdateConfigRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    更新
    AI
    配置（只传需要修改的字段�?""
    config = await db.scalar(
        select(AIConfig).where(and_(AIConfig.id == config_id, AIConfig.user_id == current_user.id))
    )
    if not config:
        return fail("配置不存�?)

    if req.name is not None:
        # 检查名称唯一
        dup = await db.scalar(
            select(AIConfig).where(and_(AIConfig.user_id == current_user.id, AIConfig.name == req.name, AIConfig.id != config_id))
        )
        if dup:
            return fail("配置名称已存�?)
        config.name = req.name
    if req.api_url is not None:
        config.api_url = req.api_url
    if req.api_key is not None:
        config.api_key_encrypted = _encrypt(req.api_key, current_user)
    if req.model is not None:
        config.model = req.model
    if req.provider is not None:
        config.provider = req.provider
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
        return fail("配置不存�?)
    await db.delete(config)
    await db.commit()
    return ok(msg="配置已删�?)

                  @ router.post("/ai/configs/{config_id}/activate", summary="激�?AI 配置")
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
        return fail("配置不存�?)

        # 取消所有激�?    await db.execute(
        select(AIConfig).where(AIConfig.user_id == current_user.id).update({"is_active": False})
    )
        # 激活目标配�?    config.is_active = True
    config.updated_at = datetime.now()
    await db.commit()
        return ok(data=config.to_dict(), msg="配置已激�?)

                                             @ router.get("/ai/configs/active", summary="获取当前激活的 AI 配置（含解密后的 API Key�?)
@_catch
async def get_active_config(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
            """获取当前用户激活的 AI 配置，返回解密后�?api_key（用�?AI Chat 自动使用�?""
            config = await db.scalar(
                select(AIConfig).where(and_(AIConfig.user_id == current_user.id, AIConfig.is_active == True))
            )
            if not config:
                return ok(data=None)

            data = config.to_dict()
            decrypted = _decrypt(config.api_key_encrypted, current_user)
            data["api_key"] = decrypted
            return ok(data=data)
