"""CDN 远端动作：清缓存 / 预热（**真实调用厂商 API**，2026-09-21 批次 18）

支持范围（**其余 provider 明确报"未实现"，绝不假装成功**）：

  - ``cloudflare``：``POST /zones/{zone_id}/purge_cache``（Bearer token；``files`` 或
    ``purge_everything``）。Cloudflare **没有预热接口**，``preheat`` 会如实报错；
  - ``custom``：调你自己配置的 ``purge_url`` / ``preheat_url``（自建网关、国内厂商的
    代理层都走这条），可带自定义 header；
  - ``aws_cloudfront`` / ``aliyun_cdn`` / ``tencent_cdn``：**需要各自的签名算法**
    （SigV4 / RPC 签名 / TC3），尚未接入 —— 调用时返回明确错误而不是"看起来成功"。

配置来源是 ``system_settings`` 的 ``cdn.config``（见 ``service.py``）：
``api_token_encrypted``（cloudflare 凭据）、``zone_id``、``settings.purge_url`` /
``settings.preheat_url`` / ``settings.headers`` / ``settings.method``。
"""

from typing import Any, Optional

import httpx

from src.api.v3.core.exceptions import BadRequestError

#: 单次远端请求超时（秒）
REMOTE_TIMEOUT = 20.0

#: 需要在实现厂商签名后才能接入的 provider
SIGNED_PROVIDERS = ("aws_cloudfront", "aliyun_cdn", "tencent_cdn")


def _settings(config: dict[str, Any]) -> dict[str, Any]:
    raw = config.get("settings")
    return raw if isinstance(raw, dict) else {}


def _require_urls(urls: list[str], *, purge_everything: bool) -> None:
    if purge_everything:
        return
    if not urls:
        raise BadRequestError("请提供要处理的 URL 列表，或显式指定 purge_everything=true")


async def purge(
    *,
    provider: str,
    config: dict[str, Any],
    token: str,
    urls: list[str],
    purge_everything: bool = False,
) -> dict[str, Any]:
    """清缓存（返回 ``{provider, success, status_code, message, urls/everything}``）"""
    if provider == "cloudflare":
        return await _cloudflare_purge(config, token, urls, purge_everything)
    if provider == "custom":
        return await _custom_call(config, "purge_url", urls, purge_everything, label="清缓存")
    if provider in SIGNED_PROVIDERS:
        raise BadRequestError(
            f"provider「{provider}」的远端清缓存需要厂商签名（SigV4/RPC/TC3），尚未接入；"
            "可先用 provider=custom 指向自建网关的清理接口"
        )
    raise BadRequestError(f"provider「{provider}」的远端清缓存尚未实现（当前支持 cloudflare / custom）")


async def preheat(*, provider: str, config: dict[str, Any], token: str, urls: list[str]) -> dict[str, Any]:
    """预热（cloudflare 无此接口 → 如实报错；custom 走 preheat_url）"""
    if provider == "cloudflare":
        raise BadRequestError("Cloudflare 不提供预热接口（其 purge 为按 URL/全量清理）")
    if provider == "custom":
        return await _custom_call(config, "preheat_url", urls, False, label="预热")
    if provider in SIGNED_PROVIDERS:
        raise BadRequestError(
            f"provider「{provider}」的预热需要厂商签名，尚未接入；可先用 provider=custom 指向自建网关"
        )
    raise BadRequestError(f"provider「{provider}」的预热尚未实现（当前支持 custom）")


# ---------------------------------------------------------------- cloudflare
async def _cloudflare_purge(
    config: dict[str, Any], token: str, urls: list[str], purge_everything: bool
) -> dict[str, Any]:
    zone_id = str(config.get("zone_id") or "").strip()
    if not token:
        raise BadRequestError("Cloudflare 凭据（api_token）未配置，无法执行远端清缓存")
    if not zone_id:
        raise BadRequestError("Cloudflare 配置缺少 zone_id，无法执行远端清缓存")
    _require_urls(urls, purge_everything=purge_everything)

    body: dict[str, Any] = {"purge_everything": True} if purge_everything else {"files": urls}
    api = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache"
    payload = await _post_json(api, body, headers={"Authorization": f"Bearer {token}"})
    success = bool(payload.get("success"))
    if not success:
        errors = payload.get("errors") or []
        detail = "；".join(str(item.get("message")) for item in errors if isinstance(item, dict))
        raise BadRequestError(f"Cloudflare 清缓存失败：{detail or '接口返回 success=false'}")
    return {
        "provider": "cloudflare",
        "success": True,
        "status_code": 200,
        "purge_everything": purge_everything,
        "urls": urls,
        "message": "已提交 Cloudflare 清缓存",
    }


# ---------------------------------------------------------------- custom
async def _custom_call(
    config: dict[str, Any],
    url_key: str,
    urls: list[str],
    purge_everything: bool,
    *,
    label: str,
) -> dict[str, Any]:
    settings = _settings(config)
    url = str(settings.get(url_key) or "").strip()
    if not url:
        raise BadRequestError(
            f"provider=custom 需要配置 settings.{url_key}（自建网关的{label}接口地址）"
        )
    _require_urls(urls, purge_everything=purge_everything)

    method = str(settings.get("method") or "POST").strip().upper()
    headers = settings.get("headers") if isinstance(settings.get("headers"), dict) else {}
    body = {
        "urls": urls,
        "purge_everything": purge_everything,
        "domain": config.get("domain"),
        "cdn_url": config.get("cdn_url"),
    }
    try:
        async with httpx.AsyncClient(timeout=REMOTE_TIMEOUT) as client:
            if method == "GET":
                resp = await client.get(url, params={"urls": ",".join(urls)}, headers=headers)
            else:
                resp = await client.request(method, url, json=body, headers=headers)
    except httpx.HTTPError as exc:
        raise BadRequestError(f"调用自定义{label}接口失败：{exc}") from exc

    if resp.status_code >= 400:
        raise BadRequestError(
            f"自定义{label}接口返回 {resp.status_code}：{(resp.text or '')[:200]}"
        )
    return {
        "provider": "custom",
        "success": True,
        "status_code": resp.status_code,
        "purge_everything": purge_everything,
        "urls": urls,
        "message": f"已调用自定义{label}接口",
    }


async def _post_json(
    url: str, body: dict[str, Any], *, headers: Optional[dict[str, str]] = None
) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=REMOTE_TIMEOUT) as client:
            resp = await client.post(url, json=body, headers=headers or {})
    except httpx.HTTPError as exc:
        raise BadRequestError(f"调用远端 CDN 接口失败：{exc}") from exc
    try:
        payload = resp.json()
    except ValueError as exc:
        raise BadRequestError(
            f"远端 CDN 接口返回了非 JSON 响应（HTTP {resp.status_code}）"
        ) from exc
    if resp.status_code >= 400 and not isinstance(payload, dict):
        raise BadRequestError(f"远端 CDN 接口返回 HTTP {resp.status_code}")
    return payload if isinstance(payload, dict) else {}
