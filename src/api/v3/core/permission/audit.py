"""启动期权限审计（P4）

三件事：

  1. **写操作端点必须声明权限码** —— 否则必须出现在 ``EXEMPT_WRITE_ENDPOINTS`` 里并给出理由，
     这样"漏配权限"会被当场发现，而"有意的公开写操作"则需要被显式承认
  2. **端点用到的权限码必须已登记** —— 全部出现在 ``codes.CODE_LABELS`` 中，防止拼错或漏登记
  3. **通配码告警** —— ``*`` / ``*:*:*`` 出现在端点声明里属危险用法，单独列出

生产（``strict=True``）下发现问题直接抛 ``RuntimeError``，避免"漏配权限就上线"。
开发/测试环境只记录日志，不阻断启动。
"""

from typing import Any, Dict, Iterable, List, Tuple

from src.api.v3.core.logger import get_logger
from src.api.v3.core.permission.codes import CODE_LABELS
from src.api.v3.core.permission.constants import WILDCARD_CODES

logger = get_logger("permission.audit")

#: 写操作端点豁免清单：``(method, path) -> 理由``
#: 这些端点**故意**不声明权限码（公开接口 / 仅认证的用户端接口 / 只操作本人数据）
#:
#: 审计会校验本清单：出现"写操作无码且未豁免"会告警（strict 下拒绝启动），
#: 清单里存在但路由已不存在的条目也会告警（防止清单腐化）。
EXEMPT_WRITE_ENDPOINTS: Dict[Tuple[str, str], str] = {
    # ---- 认证流程（认证前 / 仅需认证）----
    ("POST", "/api/v3/system/auth/login"): "登录（认证前）",
    ("POST", "/api/v3/system/auth/refresh"): "刷新令牌（认证前）",
    ("POST", "/api/v3/system/auth/logout"): "登出（仅需认证，无权限码语义）",
    ("POST", "/api/v3/system/permission/check"): "权限自检（只读语义，任意登录用户查自己）",
    # ---- 前台公开接口 ----
    ("POST", "/api/v3/content/article/public/{article_id}/views"): "浏览量计数（前台公开）",
    ("POST", "/api/v3/content/comment/public"): "前台发表评论（公开接口，反垃圾在业务层）",
    ("POST", "/api/v3/content/comment/{comment_id}/like"): "评论点赞（仅需认证）",
    # ---- 通知：只操作"本人"数据 ----
    ("POST", "/api/v3/ops/notification/read-all"): "标记本人通知全部已读",
    ("POST", "/api/v3/ops/notification/{notification_id}/read"): "标记本人通知已读",
    ("DELETE", "/api/v3/ops/notification/{notification_id}"): "删除本人通知",
    ("DELETE", "/api/v3/ops/notification/clean"): "清理本人通知",
    # ---- 移动端：用户端 API，设计上仅需认证（与后台管理权限分离）----
    ("POST", "/api/v3/mobile/auth/login"): "移动端登录（认证前）",
    ("POST", "/api/v3/mobile/auth/register"): "移动端注册（认证前）",
    ("POST", "/api/v3/mobile/comment"): "移动端发表评论（仅认证）",
    ("POST", "/api/v3/mobile/comment/{comment_id}/like"): "移动端点like（仅认证）",
    ("POST", "/api/v3/mobile/media/upload/image"): "移动端上传图片（仅认证，配额在业务层）",
    ("POST", "/api/v3/mobile/media/upload/article-cover"): "移动端上传封面（仅认证）",
    ("PUT", "/api/v3/mobile/user/profile"): "修改本人资料（仅认证）",
    # ---- 前台媒体库：全部只操作"本人"数据（service 层做归属校验，越权返回 404）----
    ("POST", "/api/v3/mobile/media/folders"): "新建本人的媒体文件夹",
    ("PUT", "/api/v3/mobile/media/folders/{folder_id}"): "重命名本人的媒体文件夹",
    ("DELETE", "/api/v3/mobile/media/folders/{folder_id}"): "删除本人的媒体文件夹",
    ("PUT", "/api/v3/mobile/media/{media_id}"): "更新本人的媒体信息",
    ("DELETE", "/api/v3/mobile/media/{media_id}"): "删除本人的媒体",
    ("POST", "/api/v3/mobile/media/batch/delete"): "批量删除本人的媒体",
    # ---- 前台投稿：只能操作"本人"文章，且服务端强制为草稿（发布需后台权限）----
    ("POST", "/api/v3/mobile/article"): "投稿创建草稿（仅认证；状态等管理字段由服务端强制）",
    ("PUT", "/api/v3/mobile/article/{article_id}"): "编辑本人的文章（仅认证；改状态的企图被忽略）",
    ("DELETE", "/api/v3/mobile/article/{article_id}"): "删除本人的文章（仅认证）",
    ("POST", "/api/v3/mobile/article/{article_id}/like"): "文章点赞切换（仅认证；per-user 表去重，不可刷赞）",
    # ---- 前台站内信：仅认证且只操作"本人"数据（发送校验收件人且禁止发给自己）----
    ("POST", "/api/v3/mobile/message"): "发送站内信（仅认证；不能发给自己，收件人须存在）",
    ("POST", "/api/v3/mobile/message/{message_id}/read"): "标记本人收到的消息已读（仅认证，非收件人 404）",
    ("DELETE", "/api/v3/mobile/message/{message_id}"): "删除本人收发的消息（仅认证，双向软删）",
    # ---- 公开表单提交：匿名可用（批次 2 既有端点，防滥用由限流层兜底）----
    ("POST", "/api/v3/marketing/form/public/{slug}/submit"): "公开表单提交（无鉴权设计；服务层校验必填与 store 开关）",
    # ---- commerce 支付流程（批次 7）----
    ("POST", "/api/v3/commerce/payment/initiate"): "发起本人支付（仅认证；订单与金额交给支付插件，服务端不做本地降级）",
    ("POST",
     "/api/v3/commerce/payment/callback/{provider}"): "支付网关回调（匿名；安全性完全由插件 verify_callback 验签把守，验签失败不更新交易）",
    # ---- commerce 收益提现（批次 7）：前台用户发起，user_id 固定为登录用户 ----
    ("POST", "/api/v3/mobile/revenue/payout"): "发起本人提现（仅认证；user_id 取登录用户，不接受外部传入）",
}

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _iter_auth_permissions(route: Any) -> Iterable[Any]:
    """遍历路由依赖树，产出全部 ``AuthPermission`` 实例"""
    dependant = getattr(route, "dependant", None)
    if dependant is None:
        return
    from src.api.v3.core.permission.control import AuthPermission

    stack = list(getattr(dependant, "dependencies", []) or [])
    while stack:
        dep = stack.pop()
        call = getattr(dep, "call", None)
        if isinstance(call, AuthPermission):
            yield call
        stack.extend(getattr(dep, "dependencies", []) or [])


def collect_route_permissions(app: Any) -> List[dict]:
    """收集所有路由的权限声明"""
    rows: List[dict] = []
    for route in getattr(app, "routes", []):
        path = str(getattr(route, "path", ""))
        methods = {m.upper() for m in (getattr(route, "methods", None) or set())}
        codes: set[str] = set()
        for perm in _iter_auth_permissions(route):
            codes |= set(perm.permissions)
        rows.append({"path": path, "methods": methods, "codes": codes})
    return rows


def audit_permissions(app: Any, *, strict: bool = False) -> dict:
    """审计已注册路由的权限声明，返回报告（``strict`` 时对问题抛异常）"""
    rows = collect_route_permissions(app)

    missing: List[Tuple[str, str]] = []
    unknown: List[Tuple[str, str]] = []
    wildcards: List[Tuple[str, str]] = []
    exempt_used: List[Tuple[str, str]] = []
    with_codes = 0

    for row in rows:
        path, methods, codes = row["path"], row["methods"], row["codes"]
        if not path.startswith("/api/v3"):
            continue
        if codes:
            with_codes += 1

        for code in codes:
            if code in WILDCARD_CODES:
                wildcards.append((path, code))
            elif code not in CODE_LABELS:
                unknown.append((path, code))

        for method in sorted(methods & _WRITE_METHODS):
            if codes:
                continue
            if (method, path) in EXEMPT_WRITE_ENDPOINTS:
                exempt_used.append((method, path))
            else:
                missing.append((method, path))

    report = {
        "v3_routes": sum(1 for row in rows if row["path"].startswith("/api/v3")),
        "paths_with_codes": with_codes,
        "write_without_codes": missing,
        "exempt_matched": exempt_used,
        "exempt_unused": sorted(set(EXEMPT_WRITE_ENDPOINTS) - set(exempt_used)),
        "unknown_codes": sorted(set(unknown)),
        "wildcards": sorted(set(wildcards)),
    }

    logger.info(
        "权限审计：v3 路由 %d 条，声明权限码 %d 条；写操作未声明且未豁免 %d 条；"
        "未知权限码 %d 个；通配声明 %d 处",
        report["v3_routes"],
        report["paths_with_codes"],
        len(missing),
        len(unknown),
        len(wildcards),
    )
    for method, path in missing:
        logger.warning("  写操作缺少权限码：%s %s", method, path)
    for path, code in unknown:
        logger.warning("  未登记的权限码：%s（%s）", code, path)
    for path, code in wildcards:
        logger.warning("  端点上出现通配权限码：%s（%s）", code, path)
    for method, path in report["exempt_unused"]:
        logger.warning("  豁免清单已过期（路由不存在）：%s %s", method, path)

    problems = len(missing) + len(unknown)
    if strict and problems:
        raise RuntimeError(
            f"权限审计未通过：{len(missing)} 个写操作缺少权限码、{len(unknown)} 个未登记权限码"
        )
    return report


__all__ = ["EXEMPT_WRITE_ENDPOINTS", "audit_permissions", "collect_route_permissions"]
