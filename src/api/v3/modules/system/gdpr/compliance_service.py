"""合规检查与文档生成（GDPR / PCI DSS）

替代 v2 的 ``shared/services/payment/tax_compliance.py`` 里的 ``ComplianceManager``：

  - v2 把 GDPR/PCI 配置**硬编码在 __init__**（`data_retention_days=365` 等布尔开关），
    检查函数只对**传入的 dict** 做判断，不查库；隐私政策与 Cookie 同意是英文模板。
  - v3 改为：配置读 ``system_settings``（可后台维护）、检查项基于**真表聚合**
    （``gdpr_consents`` / ``users`` / ``payment_transactions``），文档用**真实站点配置**
    生成中文内容，Cookie 横幅直接给出可嵌入的 HTML（含 v3 的同意上报端点）。

三块能力：

  - ``checklist``：GDPR（同意覆盖率、超期数据、权利出口）+ PCI DSS（支付是否网关托管、
    是否出现疑似卡号字段）逐项给出 ``ok / warn / fail`` 与证据
  - ``privacy_policy``：按真实站点信息生成隐私政策（Markdown，可转 HTML）
  - ``cookie_consent_html``：生成 Cookie 同意横幅 HTML（前端可直接嵌入）
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config.settings import app_config
from shared.models.payment.payment_gateway import PaymentGateway
from shared.models.payment.payment_transaction import PaymentTransaction
from shared.models.security import GDPRConsent
from shared.models.user.user import User
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.system.setting.crud import setting_crud

logger = get_logger("system.gdpr.compliance")

#: 合规配置持久化键（``system_settings``，JSON）
SETTINGS_KEY = "gdpr.compliance.settings"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "retention_days": 365,
    "require_consent": True,
    "allow_data_export": True,
    "allow_data_deletion": True,
    "contact_email": "",
    "privacy_policy_url": "/privacy",
}


def markdown_to_html(markdown: str) -> str:
    """极简 Markdown→HTML（只处理本项目会产出的语法：# 标题、- 列表、**粗体**、空行分段）"""
    html_lines: List[str] = []
    in_list = False
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue
        if line.startswith("#"):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            level = min(len(line) - len(line.lstrip("#")), 6)
            text = line[level:].strip()
            html_lines.append(f"<h{level}>{_inline(text)}</h{level}>")
        elif line.lstrip().startswith(("- ", "* ")):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{_inline(line.lstrip()[2:].strip())}</li>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p>{_inline(line)}</p>")
    if in_list:
        html_lines.append("</ul>")
    return "\n".join(html_lines)


def _inline(text: str) -> str:
    """粗体 ``**x**`` → ``<strong>x</strong>``（其余原样，避免引入模板引擎）"""
    parts = text.split("**")
    if len(parts) % 2 == 0:
        return text
    return "".join(
        f"<strong>{part}</strong>" if index % 2 else part for index, part in enumerate(parts)
    )


class ComplianceService:
    """合规检查与文档生成"""

    # ------------------------------------------------------------------ 配置
    async def load_settings(self, db: AsyncSession) -> Dict[str, Any]:
        """读合规配置（``system_settings``；缺失/损坏回退默认）"""
        row = await setting_crud.get_by(db, setting_key=SETTINGS_KEY)
        stored: Dict[str, Any] = {}
        if row is not None and row.setting_value:
            try:
                parsed = json.loads(row.setting_value)
                if isinstance(parsed, dict):
                    stored = parsed
            except (TypeError, ValueError):
                logger.warning("合规配置不是合法 JSON，已回退默认值")
        return {**DEFAULT_SETTINGS, **stored}

    async def save_settings(self, db: AsyncSession, values: Dict[str, Any]) -> Dict[str, Any]:
        """增量更新合规配置（未知键拒绝）"""
        unknown = set(values) - set(DEFAULT_SETTINGS)
        if unknown:
            from src.api.v3.core.exceptions import BadRequestError

            raise BadRequestError(f"不支持的配置项：{', '.join(sorted(unknown))}")
        merged = {**(await self.load_settings(db)), **values}
        payload = json.dumps(merged, ensure_ascii=False)
        row = await setting_crud.get_by(db, setting_key=SETTINGS_KEY)
        if row is None:
            await setting_crud.create(
                db,
                {
                    "setting_key": SETTINGS_KEY,
                    "setting_value": payload,
                    "setting_type": "json",
                    "description": "GDPR / PCI 合规配置（JSON）",
                    "is_public": False,
                },
            )
        else:
            await setting_crud.update(db, row, {"setting_value": payload})
        logger.info("合规配置已更新：%s", list(values))
        return merged

    # ------------------------------------------------------------------ 检查
    async def checklist(self, db: AsyncSession) -> Dict[str, Any]:
        """GDPR / PCI DSS 逐项检查（全部基于真表与真配置）"""
        settings = await self.load_settings(db)
        now = datetime.now()
        retention_days = int(settings["retention_days"])
        retention_cutoff = now - timedelta(days=retention_days)

        total_users = int(
            (await db.execute(select(func.count()).select_from(User))).scalar() or 0
        )
        consented_users = int(
            (
                await db.execute(
                    select(func.count(func.distinct(GDPRConsent.user_id))).where(
                        GDPRConsent.granted.is_(True)
                    )
                )
            ).scalar()
            or 0
        )
        coverage = round(consented_users / total_users, 4) if total_users else 0.0
        stale_consents = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(GDPRConsent)
                    .where(GDPRConsent.created_at < retention_cutoff)
                )
            ).scalar()
            or 0
        )

        gdpr: List[Dict[str, Any]] = [
            {
                "key": "consent_coverage",
                "status": "ok" if (coverage >= 0.5 or total_users == 0) else "warn",
                "message": f"已同意用户覆盖 {consented_users}/{total_users}（{coverage:.1%}）",
                "evidence": {"consented_users": consented_users, "total_users": total_users},
            },
            {
                "key": "consent_required",
                "status": "ok" if settings["require_consent"] else "warn",
                "message": "已开启“需先同意再采集”"
                if settings["require_consent"]
                else "未要求用户同意即采集（建议开启）",
                "evidence": {"require_consent": settings["require_consent"]},
            },
            {
                "key": "data_retention",
                "status": "ok" if stale_consents == 0 else "warn",
                "message": f"保留期 {retention_days} 天，超期同意记录 {stale_consents} 条",
                "evidence": {"retention_days": retention_days, "stale_records": stale_consents},
            },
            {
                "key": "right_to_export",
                "status": "ok" if settings["allow_data_export"] else "fail",
                "message": "已开放数据导出" if settings["allow_data_export"] else "未开放数据导出（GDPR 第 20 条要求）",
                "evidence": {"allow_data_export": settings["allow_data_export"]},
            },
            {
                "key": "right_to_erasure",
                "status": "ok" if settings["allow_data_deletion"] else "fail",
                "message": "已开放数据删除" if settings["allow_data_deletion"] else "未开放数据删除（GDPR 第 17 条要求）",
                "evidence": {"allow_data_deletion": settings["allow_data_deletion"]},
            },
        ]

        gateways = int(
            (
                await db.execute(
                    select(func.count()).select_from(PaymentGateway).where(PaymentGateway.is_active.is_(True))
                )
            ).scalar()
            or 0
        )
        suspicious = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(PaymentTransaction)
                    .where(PaymentTransaction.extra_metadata.ilike("%card_number%"))
                )
            ).scalar()
            or 0
        )
        pci: List[Dict[str, Any]] = [
            {
                "key": "no_card_storage",
                "status": "ok" if suspicious == 0 else "fail",
                "message": "未发现疑似卡号字段落库"
                if suspicious == 0
                else f"发现 {suspicious} 条交易元数据含 card_number（严禁存储卡号）",
                "evidence": {"suspicious_transactions": suspicious},
            },
            {
                "key": "gateway_offload",
                "status": "ok" if gateways > 0 else "warn",
                "message": f"已启用 {gateways} 个支付网关（支付敏感数据由网关托管）"
                if gateways > 0
                else "未配置支付网关；若开展支付需接入网关以避开卡号落地",
                "evidence": {"active_gateways": gateways},
            },
        ]

        def _summary(items: List[Dict[str, Any]]) -> Dict[str, int]:
            result = {"ok": 0, "warn": 0, "fail": 0}
            for item in items:
                result[item["status"]] = result.get(item["status"], 0) + 1
            return result

        return {
            "generated_at": now.isoformat(),
            "settings": settings,
            "gdpr": {"items": gdpr, "summary": _summary(gdpr)},
            "pci_dss": {"items": pci, "summary": _summary(pci)},
        }

    # ------------------------------------------------------------------ 文档
    async def site_info(self, db: AsyncSession) -> Dict[str, str]:
        """站点信息（优先 ``system_settings``，回退 ``shared/config/settings.py``）"""
        settings = await self.load_settings(db)
        return {
            "name": getattr(app_config, "sitename", "") or "本站",
            "url": getattr(app_config, "domain", "/") or "/",
            "contact_email": settings.get("contact_email") or "support@example.com",
            "privacy_policy_url": settings.get("privacy_policy_url") or "/privacy",
            "retention_days": str(settings.get("retention_days") or 365),
        }

    async def privacy_policy(self, db: AsyncSession, *, as_html: bool = False) -> Dict[str, Any]:
        """生成隐私政策（中文，内容由真实站点配置与合规开关决定）"""
        info = await self.site_info(db)
        settings = await self.load_settings(db)
        updated = datetime.now().strftime("%Y-%m-%d")

        rights = []
        if settings["allow_data_export"]:
            rights.append("- 数据导出：可通过后台导出你的个人数据副本")
        if settings["allow_data_deletion"]:
            rights.append("- 数据删除：可申请删除账号与相关内容")
        rights.append("- 撤回同意：可随时在 Cookie 设置中撤回同意")

        markdown = f"""# {info['name']} 隐私政策

**最后更新：{updated}**

## 1. 引言

{info['name']}（{info['url']}）尊重并保护你的个人信息。本政策说明我们收集哪些信息、如何使用、保留多久，以及你拥有哪些权利。

## 2. 我们收集的信息

- 账号信息：用户名、邮箱等注册与登录所需的最小信息
- 内容与互动：你发布的文章、评论、点赞等
- 访问数据：页面访问记录、设备与浏览器类型、IP 地址（用于统计与安全防护）

## 3. 信息的使用

- 提供并维护博客服务
- 统计访问情况、改进内容与体验
- 安全防护（登录风控、异常行为识别）

## 4. Cookie 与本地存储

我们使用必要的 Cookie 维持登录状态，并在你同意后使用统计类 Cookie。你可以随时在 Cookie 设置中调整或撤回同意。

## 5. 数据保留

个人数据默认保留 **{info['retention_days']} 天**，超期数据将被清理或匿名化。

## 6. 你的权利

{chr(10).join(rights)}

## 7. 联系方式

如对本政策或你的数据有任何疑问，请联系：{info['contact_email']}
"""
        return {
            "site": info,
            "format": "html" if as_html else "markdown",
            "content": markdown_to_html(markdown) if as_html else markdown,
        }

    async def cookie_consent_html(self, db: AsyncSession) -> Dict[str, Any]:
        """生成 Cookie 同意横幅 HTML（含 v3 的同意上报端点，前端可直接嵌入）"""
        info = await self.site_info(db)
        html = f"""<!-- Cookie 同意横幅（由 {info['name']} 后台生成；嵌入到页面底部即可） -->
<div id="cookie-consent-banner" role="dialog" aria-live="polite" style="position:fixed;left:0;right:0;bottom:0;z-index:9999;background:#1a1a1a;color:#fff;padding:16px 20px;box-shadow:0 -2px 10px rgba(0,0,0,.3);display:none">
  <div style="max-width:1100px;margin:0 auto;display:flex;gap:16px;align-items:center;flex-wrap:wrap">
    <div style="flex:1;min-width:280px">
      <strong>{info['name']}</strong> 使用 Cookie 维持登录状态，并在你同意后用于访问统计。
      详见 <a href="{info['privacy_policy_url']}" style="color:#7cc4ff">隐私政策</a>。
    </div>
    <div style="display:flex;gap:8px">
      <button id="cookie-consent-reject" style="padding:8px 16px;border-radius:6px;border:1px solid #888;background:transparent;color:#fff;cursor:pointer">仅必要</button>
      <button id="cookie-consent-accept" style="padding:8px 16px;border-radius:6px;border:0;background:#2563eb;color:#fff;cursor:pointer">全部同意</button>
    </div>
  </div>
</div>
<script>
(function () {{
  var KEY = 'fb_cookie_consent';
  var banner = document.getElementById('cookie-consent-banner');
  function report(granted) {{
    fetch('/api/v3/system/gdpr/consent', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      credentials: 'same-origin',
      body: JSON.stringify({{ consent_type: 'cookies', granted: granted }})
    }}).catch(function () {{}});
  }}
  if (!localStorage.getItem(KEY)) {{ banner.style.display = 'block'; }}
  document.getElementById('cookie-consent-accept').onclick = function () {{
    localStorage.setItem(KEY, 'all'); banner.style.display = 'none'; report(true);
  }};
  document.getElementById('cookie-consent-reject').onclick = function () {{
    localStorage.setItem(KEY, 'necessary'); banner.style.display = 'none'; report(false);
  }};
}})();
</script>
"""
        return {"site": info, "content": html}


compliance_service = ComplianceService()
