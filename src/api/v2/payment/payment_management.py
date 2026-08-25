"""
支付系统管理 API

提供支付网关(PaymentGateway)、支付交易(PaymentTransaction)、税务配置(TaxConfig) 的 CRUD 管理接口
"""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import PaymentGateway, PaymentTransaction, TaxConfig
from src.api.v2._helpers import ok, fail, _catch
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["payment-management"])


def _is_admin(user) -> bool:
    return getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False)


# ==================== 支付网关管理 ====================


@router.get("/gateways")
@_catch
async def list_gateways(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    provider: Optional[str] = Query(None, description="提供商筛选"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """
    获取支付网关列表

    支持分页、搜索、按提供商和激活状态筛选
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    query = select(PaymentGateway)

    if search:
        query = query.where(
            or_(
                PaymentGateway.name.ilike(f"%{search}%"),
                PaymentGateway.provider.ilike(f"%{search}%"),
            )
        )

    if provider:
        query = query.where(PaymentGateway.provider == provider)

    if is_active is not None:
        query = query.where(PaymentGateway.is_active == is_active)

    query = query.order_by(PaymentGateway.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    gateways = result.scalars().all()

    return ok(data={
        "gateways": [g.to_dict() for g in gateways],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
        },
    })


@router.get("/gateways/{gateway_id}")
@_catch
async def get_gateway(
    gateway_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """获取支付网关详情"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    query = select(PaymentGateway).where(PaymentGateway.id == gateway_id)
    result = await db.execute(query)
    gateway = result.scalar_one_or_none()

    if not gateway:
        return fail("支付网关不存在")

    # 始终脱敏 config_data，避免泄露支付密钥
    result_dict = gateway.to_dict(exclude_sensitive=True)
    if result_dict.get("config_data"):
        try:
            cfg = json.loads(result_dict["config_data"])
            if isinstance(cfg, dict):
                # 脱敏所有敏感字段
                for key in cfg:
                    if any(s in key.lower() for s in ("key", "secret", "password", "token", "private", "sign")):
                        cfg[key] = "***masked***"
                result_dict["config_data"] = json.dumps(cfg, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            result_dict["config_data"] = "***masked***"
    return ok(data=result_dict)


@router.post("/gateways")
@_catch
async def create_gateway(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """创建支付网关"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    data = await request.json()

    name = data.get("name")
    provider = data.get("provider")
    if not name or not provider:
        return fail("name 和 provider 为必填字段")

    existing = await db.execute(
        select(PaymentGateway).where(
            PaymentGateway.name == name,
            PaymentGateway.provider == provider,
        )
    )
    if existing.scalar_one_or_none():
        return fail(f"网关 '{name}' (provider={provider}) 已存在")

    config_data = data.get("config_data")
    if isinstance(config_data, dict):
        config_data = json.dumps(config_data, ensure_ascii=False)

    now = datetime.utcnow()
    gateway = PaymentGateway(
        name=name,
        provider=provider,
        config_data=config_data,
        is_active=data.get("is_active", False),
        supported_currencies=data.get("supported_currencies", "USD,CNY"),
        created_at=now,
        updated_at=now,
    )

    db.add(gateway)
    try:
        await db.commit()
        await db.refresh(gateway)
    except Exception:
        await db.rollback()
        raise

    return ok(data=gateway.to_dict(), msg="支付网关创建成功")


@router.put("/gateways/{gateway_id}")
@_catch
async def update_gateway(
    gateway_id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """更新支付网关"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    query = select(PaymentGateway).where(PaymentGateway.id == gateway_id)
    result = await db.execute(query)
    gateway = result.scalar_one_or_none()

    if not gateway:
        return fail("支付网关不存在")

    data = await request.json()

    updatable_fields = ["name", "provider", "is_active", "supported_currencies"]
    for field in updatable_fields:
        if field in data:
            setattr(gateway, field, data[field])

    if "config_data" in data:
        config_data = data["config_data"]
        gateway.config_data = json.dumps(config_data, ensure_ascii=False) if isinstance(config_data, dict) else config_data

    gateway.updated_at = datetime.utcnow()

    try:
        await db.commit()
        await db.refresh(gateway)
    except Exception:
        await db.rollback()
        raise

    return ok(data=gateway.to_dict(), msg="支付网关更新成功")


@router.delete("/gateways/{gateway_id}")
@_catch
async def delete_gateway(
    gateway_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """删除支付网关"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    query = select(PaymentGateway).where(PaymentGateway.id == gateway_id)
    result = await db.execute(query)
    gateway = result.scalar_one_or_none()

    if not gateway:
        return fail("支付网关不存在")

    txn_count_query = select(func.count()).where(PaymentTransaction.gateway == gateway_id)
    txn_count_result = await db.execute(txn_count_query)
    txn_count = txn_count_result.scalar()

    if txn_count > 0:
        return fail(f"该网关下有 {txn_count} 条交易记录，请先删除或迁移交易记录后再删除网关")

    await db.delete(gateway)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return ok(msg="支付网关删除成功")


# ==================== 支付交易管理 ====================


@router.get("/transactions")
@_catch
async def list_transactions(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索订单ID/交易ID"),
    status: Optional[str] = Query(None, description="交易状态"),
    payment_method: Optional[str] = Query(None, description="支付方式"),
    currency: Optional[str] = Query(None, description="货币类型"),
    user_id: Optional[int] = Query(None, description="用户ID"),
    gateway_id: Optional[int] = Query(None, description="网关ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """
    获取支付交易列表

    支持分页、多条件筛选
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    query = select(PaymentTransaction)

    if search:
        query = query.where(
            or_(
                PaymentTransaction.order_id.ilike(f"%{search}%"),
                PaymentTransaction.transaction_id.ilike(f"%{search}%"),
            )
        )

    if status:
        query = query.where(PaymentTransaction.status == status)

    if payment_method:
        query = query.where(PaymentTransaction.payment_method == payment_method)

    if currency:
        query = query.where(PaymentTransaction.currency == currency.upper())

    if user_id:
        query = query.where(PaymentTransaction.user == user_id)

    if gateway_id:
        query = query.where(PaymentTransaction.gateway == gateway_id)

    query = query.order_by(PaymentTransaction.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    transactions = result.scalars().all()

    return ok(data={
        "transactions": [t.to_dict() for t in transactions],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
        },
    })


@router.get("/transactions/{transaction_id}")
@_catch
async def get_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """获取支付交易详情"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    query = select(PaymentTransaction).where(PaymentTransaction.id == transaction_id)
    result = await db.execute(query)
    transaction = result.scalar_one_or_none()

    if not transaction:
        return fail("交易记录不存在")

    return ok(data=transaction.to_dict(exclude_sensitive=False))


@router.post("/transactions")
@_catch
async def create_transaction(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """创建支付交易记录（管理员手动记录）"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    data = await request.json()

    user = data.get("user")
    amount = data.get("amount")
    if not user or amount is None:
        return fail("user 和 amount 为必填字段")

    gateway_id = data.get("gateway")
    if gateway_id:
        gw_query = select(PaymentGateway).where(PaymentGateway.id == gateway_id)
        gw_result = await db.execute(gw_query)
        if not gw_result.scalar_one_or_none():
            return fail(f"网关 ID={gateway_id} 不存在")

    order_id = data.get("order_id")
    if order_id:
        existing = await db.execute(
            select(PaymentTransaction).where(PaymentTransaction.order_id == order_id)
        )
        if existing.scalar_one_or_none():
            return fail(f"订单ID '{order_id}' 已存在")

    now = datetime.utcnow()
    transaction = PaymentTransaction(
        user=user,
        order_id=order_id,
        gateway=gateway_id,
        amount=amount,
        currency=data.get("currency", "USD"),
        status=data.get("status", "pending"),
        transaction_id=data.get("transaction_id"),
        payment_method=data.get("payment_method"),
        extra_metadata=json.dumps(data["extra_metadata"], ensure_ascii=False)
        if "extra_metadata" in data and isinstance(data["extra_metadata"], dict)
        else data.get("extra_metadata"),
        created_at=now,
        updated_at=now,
    )

    db.add(transaction)
    try:
        await db.commit()
        await db.refresh(transaction)
    except Exception:
        await db.rollback()
        raise

    return ok(data=transaction.to_dict(), msg="交易记录创建成功")


@router.put("/transactions/{transaction_id}")
@_catch
async def update_transaction(
    transaction_id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """更新支付交易记录"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    query = select(PaymentTransaction).where(PaymentTransaction.id == transaction_id)
    result = await db.execute(query)
    transaction = result.scalar_one_or_none()

    if not transaction:
        return fail("交易记录不存在")

    data = await request.json()

    # 成功态只能由真实网关回调/对账流程产生，禁止通过管理接口手动直改。
    SUCCESS_STATUSES = ("succeeded", "completed", "paid")
    requested_status = data.get("status")
    if requested_status is not None and str(requested_status).lower() in SUCCESS_STATUSES:
        return fail(f"不允许手动将交易状态改为 '{requested_status}'；成功态只能由真实网关回调/对账流程产生")

    updatable_fields = [
        "status", "transaction_id", "payment_method", "currency",
        "order_id",
    ]
    for field in updatable_fields:
        if field in data:
            setattr(transaction, field, data[field])

    if "amount" in data:
        transaction.amount = data["amount"]

    if "extra_metadata" in data:
        meta = data["extra_metadata"]
        transaction.extra_metadata = json.dumps(meta, ensure_ascii=False) if isinstance(meta, dict) else meta

    transaction.updated_at = datetime.utcnow()

    try:
        await db.commit()
        await db.refresh(transaction)
    except Exception:
        await db.rollback()
        raise

    return ok(data=transaction.to_dict(), msg="交易记录更新成功")


@router.delete("/transactions/{transaction_id}")
@_catch
async def delete_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """删除支付交易记录"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    query = select(PaymentTransaction).where(PaymentTransaction.id == transaction_id)
    result = await db.execute(query)
    transaction = result.scalar_one_or_none()

    if not transaction:
        return fail("交易记录不存在")

    if transaction.status not in ("pending", "failed", "cancelled"):
        return fail(f"不允许删除状态为 '{transaction.status}' 的交易记录，请先将其状态变更为 cancelled")

    await db.delete(transaction)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return ok(msg="交易记录删除成功")


# ==================== 支付网关委派（插件系统） ====================

def _get_payment_plugin():
    """查找激活的支付网关插件"""
    try:
        from shared.services.plugins.plugin_manager.core import plugin_manager
        for plugin in plugin_manager.get_active_plugins():
            if plugin.has_capability("execute:custom:payment") and hasattr(plugin, "create_payment"):
                return plugin
    except Exception as e:
        logger.warning(f"Payment plugin lookup failed: {e}")
    return None


@router.post("/create")
@_catch
async def create_payment(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """通过支付网关插件发起支付"""
    data = await request.json()
    order_id = data.get("order_id")
    amount = data.get("amount")
    subject = data.get("subject", "")

    if not order_id or amount is None:
        return fail("缺少 order_id 或 amount")

    plugin = _get_payment_plugin()
    if not plugin:
        return fail("未激活支付网关插件，请联系管理员在插件管理中激活 Payment Gateway 插件")

    result = plugin.create_payment(
        order_id=order_id,
        amount=int(amount),
        subject=subject,
        user_id=current_user.id,
        return_url=data.get("return_url", ""),
        cancel_url=data.get("cancel_url", ""),
        notify_url=data.get("notify_url", ""),
    )

    if not result.get("success"):
        return fail(result.get("error", "支付发起失败"))

    return ok(data=result, msg="支付已发起")


@router.post("/callback/{provider}")
async def payment_callback(provider: str, request: Request, db: AsyncSession = Depends(get_async_db)):
    """支付网关回调（无需认证，由签名验证保障安全）"""
    plugin = _get_payment_plugin()
    if not plugin:
        return {"code": "FAIL", "message": "Payment plugin not active"}

    body = await request.body()
    headers = dict(request.headers)
    try:
        payload = await request.json()
    except Exception:
        payload = {}
        try:
            payload = dict(request.query_params)
        except Exception:
            payload = {"raw": body.decode("utf-8", errors="replace")}

    result = plugin.verify_callback(provider, payload, headers)
    if not result.get("verified"):
        logger.warning(f"Payment callback verification failed: {result.get('error')}")
        return {"code": "FAIL", "message": result.get("error", "Verification failed")}

    # 验签通过：更新交易状态为成功（这是唯一允许设置 succeeded 的路径）
    from sqlalchemy import update as sa_update
    from datetime import datetime
    if result.get("order_id"):
        stmt = (
            sa_update(PaymentTransaction)
            .where(PaymentTransaction.order_id == result["order_id"])
            .values(
                status=result.get("status", "succeeded"),
                transaction_id=result.get("transaction_id"),
                updated_at=datetime.utcnow(),
            )
        )
        await db.execute(stmt)
        await db.commit()
        logger.info(f"Payment callback verified: order={result['order_id']}, status={result.get('status')}")

    # 各平台要求的回调响应
    if provider == "alipay":
        return "success"
    elif provider == "wechat":
        return {"code": "SUCCESS", "message": "OK"}
    else:
        return {"received": True}


# ==================== 税务配置管理 ====================


@router.get("/tax-configs")
@_catch
async def list_tax_configs(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    country: Optional[str] = Query(None, description="国家代码 (ISO 3166-1)"),
    region: Optional[str] = Query(None, description="地区"),
    tax_type: Optional[str] = Query(None, description="税种类型"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """
    获取税务配置列表

    支持分页、按国家/地区/税种/激活状态筛选
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    query = select(TaxConfig)

    if country:
        query = query.where(TaxConfig.country == country.upper())

    if region:
        query = query.where(TaxConfig.region.ilike(f"%{region}%"))

    if tax_type:
        query = query.where(TaxConfig.tax_type == tax_type)

    if is_active is not None:
        query = query.where(TaxConfig.is_active == is_active)

    query = query.order_by(TaxConfig.country, TaxConfig.region, TaxConfig.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    configs = result.scalars().all()

    return ok(data={
        "tax_configs": [c.to_dict() for c in configs],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
        },
    })


@router.get("/tax-configs/{config_id}")
@_catch
async def get_tax_config(
    config_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """获取税务配置详情"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    query = select(TaxConfig).where(TaxConfig.id == config_id)
    result = await db.execute(query)
    config = result.scalar_one_or_none()

    if not config:
        return fail("税务配置不存在")

    return ok(data=config.to_dict())


@router.post("/tax-configs")
@_catch
async def create_tax_config(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """创建税务配置"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    data = await request.json()

    country = data.get("country")
    tax_type = data.get("tax_type")
    rate = data.get("rate")
    if not country or not tax_type or rate is None:
        return fail("country、tax_type、rate 为必填字段")

    existing_query = select(TaxConfig).where(
        TaxConfig.country == country.upper(),
        TaxConfig.tax_type == tax_type,
    )
    region = data.get("region")
    if region:
        existing_query = existing_query.where(TaxConfig.region == region)
    else:
        existing_query = existing_query.where(TaxConfig.region.is_(None))

    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        region_label = f"/{region}" if region else ""
        return fail(f"国家 {country.upper()}{region_label} 的 {tax_type} 税务配置已存在")

    now = datetime.utcnow()

    effective_from = data.get("effective_from")
    if isinstance(effective_from, str):
        effective_from = datetime.fromisoformat(effective_from.replace("Z", "+00:00"))
    elif effective_from is None:
        effective_from = now

    effective_to = data.get("effective_to")
    if isinstance(effective_to, str):
        effective_to = datetime.fromisoformat(effective_to.replace("Z", "+00:00"))

    config = TaxConfig(
        country=country.upper(),
        region=region,
        tax_type=tax_type,
        rate=rate,
        description=data.get("description"),
        is_active=data.get("is_active", True),
        effective_from=effective_from,
        effective_to=effective_to,
        created_at=now,
        updated_at=now,
    )

    db.add(config)
    try:
        await db.commit()
        await db.refresh(config)
    except Exception:
        await db.rollback()
        raise

    return ok(data=config.to_dict(), msg="税务配置创建成功")


@router.put("/tax-configs/{config_id}")
@_catch
async def update_tax_config(
    config_id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """更新税务配置"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    query = select(TaxConfig).where(TaxConfig.id == config_id)
    result = await db.execute(query)
    config = result.scalar_one_or_none()

    if not config:
        return fail("税务配置不存在")

    data = await request.json()

    updatable_fields = ["country", "region", "tax_type", "rate", "description", "is_active"]
    for field in updatable_fields:
        if field in data:
            value = data[field]
            if field == "country" and value:
                value = value.upper()
            setattr(config, field, value)

    if "effective_from" in data:
        ef = data["effective_from"]
        config.effective_from = datetime.fromisoformat(ef.replace("Z", "+00:00")) if isinstance(ef, str) else ef

    if "effective_to" in data:
        et = data["effective_to"]
        config.effective_to = datetime.fromisoformat(et.replace("Z", "+00:00")) if isinstance(et, str) else et

    config.updated_at = datetime.utcnow()

    try:
        await db.commit()
        await db.refresh(config)
    except Exception:
        await db.rollback()
        raise

    return ok(data=config.to_dict(), msg="税务配置更新成功")


@router.delete("/tax-configs/{config_id}")
@_catch
async def delete_tax_config(
    config_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(jwt_required),
):
    """删除税务配置"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    query = select(TaxConfig).where(TaxConfig.id == config_id)
    result = await db.execute(query)
    config = result.scalar_one_or_none()

    if not config:
        return fail("税务配置不存在")

    await db.delete(config)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return ok(msg="税务配置删除成功")
