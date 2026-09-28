"""税务计算（真实税率来自 ``tax_configs`` 表）

替代 v2 的 ``shared/services/payment/tax_compliance.py`` 里的 ``TaxCalculator``：
v2 用 ``_initialize_tax_rates`` 把税率**硬编码在代码里**（改税率要改代码、无法按生效期管理），
v3 改为查 ``tax_configs`` 真表（后台可维护、支持生效期与启用开关）。

能力：

  - ``resolve_rate``：按国家/地区/税种匹配**当前生效**的税率（精确地区优先，其次国家级）
  - ``calculate``：不含税/含税（inclusive）两种口径计算，支持免税（有效 VAT 号）
  - ``summary``：多行项目按税率分组的税务摘要
  - ``report``：周期税务报表（税率配置 + 已成功交易总额汇总）
  - ``validate_vat_number``：EU VAT 号格式校验（纯函数）

金额口径：``amount`` 一律是**该笔金额**（不含税时是净额、含税时是总额），
返回值里 ``net`` + ``tax`` = ``total``，避免调用方自己猜。
"""

import re
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.payment.payment_transaction import PaymentTransaction
from shared.models.payment.tax_config import TaxConfig
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger

logger = get_logger("payment.tax")

#: 已成功/已支付状态的交易才计入税务报表
SETTLED_STATUSES = ("success", "paid", "completed")

#: EU VAT 号：2 位国家码 + 8~12 位字母数字
_VAT_RE = re.compile(r"^[A-Z]{2}[0-9A-Z]{8,12}$")
_VAT_PREFIXES = frozenset(
    "AT BE BG CY CZ DE DK EE EL ES FI FR GB HR HU IE IT LT LU LV MT NL PL PT RO SE SI SK".split()
)

#: 金额精度：分（两位小数）
_CENTS = Decimal("0.01")


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(_CENTS, rounding=ROUND_HALF_UP)


def validate_vat_number(vat_number: Optional[str]) -> bool:
    """校验 EU VAT 号格式（2 位国家码前缀 + 8~12 位字母数字）"""
    text = (vat_number or "").strip().upper().replace(" ", "").replace("-", "")
    if not _VAT_RE.match(text):
        return False
    return text[:2] in _VAT_PREFIXES


class TaxService:
    """税务计算与报表（全部基于 ``tax_configs`` 真表）"""

    # ------------------------------------------------------------------ 税率匹配
    async def resolve_rate(
        self,
        db: AsyncSession,
        *,
        country: str,
        region: Optional[str] = None,
        tax_type: Optional[str] = None,
        at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """按国家/地区/税种匹配当前生效税率

        优先级：精确地区匹配 > 国家级（``region`` 为空）匹配；同级取 ``effective_from`` 最新。
        未匹配到一律抛 404（宁可让调用方明确处理，也不静默按 0 计税）。
        """
        country_code = (country or "").strip().upper()
        if len(country_code) != 2:
            raise BadRequestError("country 必须是 ISO 3166-1 alpha-2 两位国家码")

        moment = at or datetime.now()
        conditions = [
            TaxConfig.country == country_code,
            TaxConfig.is_active.is_(True),
            or_(TaxConfig.effective_from.is_(None), TaxConfig.effective_from <= moment),
            or_(TaxConfig.effective_to.is_(None), TaxConfig.effective_to >= moment),
        ]
        if tax_type:
            conditions.append(TaxConfig.tax_type == tax_type)
        if region:
            conditions.append(or_(TaxConfig.region == region, TaxConfig.region.is_(None)))
        else:
            conditions.append(TaxConfig.region.is_(None))

        rows = (
            await db.execute(
                select(TaxConfig)
                .where(*conditions)
                .order_by(
                    # 精确地区优先：region 非空排前面
                    TaxConfig.region.is_(None).asc(),
                    TaxConfig.effective_from.desc().nullslast(),
                    TaxConfig.id.desc(),
                )
                .limit(1)
            )
        ).scalars().all()
        if not rows:
            scope = f"{country_code}{('/' + region) if region else ''}"
            raise NotFoundError(f"未配置 {scope} 的有效税率（tax_configs）")

        row = rows[0]
        return {
            "id": row.id,
            "country": row.country,
            "region": row.region,
            "tax_type": row.tax_type,
            "rate": float(row.rate or 0),
            "description": row.description,
        }

    # ------------------------------------------------------------------ 计算
    async def calculate(
        self,
        db: AsyncSession,
        *,
        amount: Any,
        country: str,
        region: Optional[str] = None,
        tax_type: Optional[str] = None,
        inclusive: bool = False,
        vat_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """计算一笔金额的税额

        - ``inclusive=False``（默认）：``amount`` 是**净额**，税额另加
        - ``inclusive=True``：``amount`` 是**含税总额**，税额从中拆出
        - ``vat_number`` 合法（EU 格式）时按**免税**处理（rate 记 0，并标注 exemption）
        """
        try:
            gross_input = Decimal(str(amount))
        except Exception:  # noqa: BLE001 - 非数值一律按参数错误处理
            raise BadRequestError("amount 必须是数字") from None
        if gross_input < 0:
            raise BadRequestError("amount 不能为负数")

        exempt = bool(vat_number) and validate_vat_number(vat_number)
        rate_info = await self.resolve_rate(
            db, country=country, region=region, tax_type=tax_type
        )
        rate = Decimal("0") if exempt else Decimal(str(rate_info["rate"]))

        if inclusive:
            total = _money(gross_input)
            net = _money(total / (Decimal("1") + rate / Decimal("100")) if rate else total)
            tax = _money(total - net)
        else:
            net = _money(gross_input)
            tax = _money(net * rate / Decimal("100"))
            total = _money(net + tax)

        return {
            "country": rate_info["country"],
            "region": rate_info["region"],
            "tax_type": rate_info["tax_type"],
            "rate": float(rate),
            "configured_rate": rate_info["rate"],
            "inclusive": inclusive,
            "exempt": exempt,
            "exemption_reason": "有效 VAT 号，按免税处理" if exempt else None,
            "net": float(net),
            "tax": float(tax),
            "total": float(total),
        }

    async def summary(
        self,
        db: AsyncSession,
        *,
        items: List[Dict[str, Any]],
        country: str,
        region: Optional[str] = None,
        inclusive: bool = False,
    ) -> Dict[str, Any]:
        """多行项目税务摘要（按实际命中税率分组，便于对账）"""
        if not items:
            raise BadRequestError("items 不能为空")

        groups: Dict[str, Dict[str, Any]] = {}
        net_total = Decimal("0")
        tax_total = Decimal("0")
        for item in items:
            result = await self.calculate(
                db,
                amount=item.get("amount"),
                country=country,
                region=region,
                tax_type=item.get("tax_type"),
                inclusive=inclusive,
                vat_number=item.get("vat_number"),
            )
            key = f"{result['tax_type']}@{result['rate']}"
            bucket = groups.setdefault(
                key,
                {"tax_type": result["tax_type"], "rate": result["rate"], "net": 0.0, "tax": 0.0, "items": 0},
            )
            bucket["net"] = float(_money(bucket["net"]) + Decimal(str(result["net"])))
            bucket["tax"] = float(_money(bucket["tax"]) + Decimal(str(result["tax"])))
            bucket["items"] += 1
            net_total += Decimal(str(result["net"]))
            tax_total += Decimal(str(result["tax"]))

        return {
            "country": country.upper(),
            "region": region,
            "inclusive": inclusive,
            "groups": list(groups.values()),
            "net": float(_money(net_total)),
            "tax": float(_money(tax_total)),
            "total": float(_money(net_total + tax_total)),
        }

    # ------------------------------------------------------------------ 报表
    async def report(
        self, db: AsyncSession, *, days: int = 30, currency: Optional[str] = None
    ) -> Dict[str, Any]:
        """周期税务报表：税率配置清单 + 已结算交易总额（按币种）"""
        since = datetime.now() - timedelta(days=days)

        configs = (
            await db.execute(
                select(TaxConfig)
                .where(TaxConfig.is_active.is_(True))
                .order_by(TaxConfig.country.asc(), TaxConfig.rate.desc())
            )
        ).scalars().all()

        conditions = [
            PaymentTransaction.created_at >= since,
            PaymentTransaction.status.in_(SETTLED_STATUSES),
        ]
        if currency:
            conditions.append(PaymentTransaction.currency == currency.upper())
        settled = (
            await db.execute(
                select(
                    PaymentTransaction.currency,
                    func.count().label("transactions"),
                    func.sum(PaymentTransaction.amount).label("amount"),
                )
                .where(*conditions)
                .group_by(PaymentTransaction.currency)
                .order_by(func.count().desc())
            )
        ).all()

        return {
            "period_days": days,
            "settled_statuses": list(SETTLED_STATUSES),
            "tax_configs": [
                {
                    "id": row.id,
                    "country": row.country,
                    "region": row.region,
                    "tax_type": row.tax_type,
                    "rate": float(row.rate or 0),
                    "effective_from": row.effective_from.isoformat() if row.effective_from else None,
                    "effective_to": row.effective_to.isoformat() if row.effective_to else None,
                }
                for row in configs
            ],
            "settled_transactions": [
                {
                    "currency": row.currency,
                    "transactions": int(row.transactions or 0),
                    "amount": float(row.amount or 0),
                }
                for row in settled
            ],
        }


tax_service = TaxService()
