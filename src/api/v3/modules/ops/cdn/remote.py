"""CDN 远端动作：清缓存 / 预热（**真实调用厂商 API**）

支持的 provider 与各自的**真实签名实现**：

  - ``cloudflare``：``POST /zones/{zone_id}/purge_cache``（Bearer token；``files`` 或
    ``purge_everything``）。Cloudflare **没有预热接口**，``preheat`` 会如实报错；
  - ``custom``：调你自己配置的 ``purge_url`` / ``preheat_url``（自建网关、国内厂商的
    代理层都走这条），可带自定义 header；
  - ``aws_cloudfront``：SigV4 签名的 ``CreateInvalidation``（**XML body**，路径 ``/*``
    即全量）。CloudFront **没有预热接口** → 如实报错；
  - ``aliyun_cdn``：RPC 风格 HMAC-SHA1 签名的 ``RefreshObjectCaches`` / ``PushObjectCache``
    （API 版本 ``2018-05-10``）；
  - ``tencent_cdn``：TC3-HMAC-SHA256 签名的 ``PurgeUrlsCache`` / ``PushUrlsCache``
    （API 版本 ``2018-06-06``）。

**凭据与标识的存放**（``system_settings`` 的 ``cdn.config``，见 ``service.py``）：

  - 厂商**密钥**统一放 ``api_token`` 字段 → 落库前 AES-256-GCM 加密为
    ``api_token_encrypted``，读接口只回 ``has_api_token``，**永不回传明文**；
    出参名按厂商语义不同（Cloudflare API Token / AWS Secret Access Key /
    阿里云 AccessKey Secret / 腾讯云 Secret Key），但共用同一个密文槽；
  - 其余**非敏感标识**放 ``settings``：``access_key_id``（AWS / 阿里云）、
    ``secret_id``（腾讯云）、``distribution_id``（CloudFront）、``region``、``endpoint``。

``settings.endpoint`` 可覆盖厂商默认端点（私有代理 / 国际站 / 测试本地端点）；
**端点与凭据缺失一律明确报错**，绝不假装成功。
"""

import base64
import hashlib
import hmac
import json
import secrets
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import quote, urlparse

import httpx

from src.api.v3.core import sigv4
from src.api.v3.core.exceptions import BadRequestError

#: 单次远端请求超时（秒）
REMOTE_TIMEOUT = 20.0

#: 需要厂商签名才能接入的 provider（三家云）
SIGNED_PROVIDERS = ("aws_cloudfront", "aliyun_cdn", "tencent_cdn")

#: 需要从 ``api_token`` 密文槽解密的 provider（service.py 据此按需解密）
CREDENTIAL_PROVIDERS = ("cloudflare", *SIGNED_PROVIDERS)

#: 各家云的单次批量 URL 上限（超过请分批；超限在发起请求前就明确拒绝）
MAX_URLS_PER_CALL = {
    "cloudflare": 30,  # Cloudflare purge_cache 单次最多 30 个 files
    "aws_cloudfront": 3000,  # CloudFront 单次失效最多 3000 个路径
    "aliyun_cdn": 100,
    "tencent_cdn": 100,
}

#: 厂商默认端点（可用 settings.endpoint 覆盖）
DEFAULT_ENDPOINTS = {
    "aws_cloudfront": "https://cloudfront.amazonaws.com",
    "aliyun_cdn": "https://cdn.aliyuncs.com",
    "tencent_cdn": "https://cdn.tencentcloudapi.com",
}

#: 阿里云 POP API 版本（CDN）
ALIYUN_API_VERSION = "2018-05-10"
#: 腾讯云 CDN API 版本
TENCENT_API_VERSION = "2018-06-06"
#: CloudFront REST API 版本
CLOUDFRONT_API_VERSION = "2020-05-31"


def _settings(config: dict[str, Any]) -> dict[str, Any]:
    raw = config.get("settings")
    return raw if isinstance(raw, dict) else {}


def _setting_str(settings: dict[str, Any], key: str) -> str:
    return str(settings.get(key) or "").strip()


def _endpoint(provider: str, settings: dict[str, Any]) -> str:
    """厂商端点：``settings.endpoint`` 优先，否则默认端点"""
    return _setting_str(settings, "endpoint") or DEFAULT_ENDPOINTS[provider]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_urls(urls: list[str], *, purge_everything: bool) -> None:
    if purge_everything:
        return
    if not urls:
        raise BadRequestError("请提供要处理的 URL 列表，或显式指定 purge_everything=true")


def _require_within_limit(provider: str, urls: list[str]) -> None:
    limit = MAX_URLS_PER_CALL.get(provider)
    if limit and len(urls) > limit:
        raise BadRequestError(
            f"{provider} 单次最多处理 {limit} 个 URL（收到 {len(urls)} 个），请分批提交"
        )


def _reject_everything(provider: str, label: str) -> None:
    """整站全量刷新只在 Cloudflare（整 zone）与 CloudFront（``/*``）支持"""
    raise BadRequestError(
        f"{provider} 不支持一键全量{label}：请给出要处理的 URL 列表"
        "（Cloudflare 的 purge_everything 与 CloudFront 的 /* 才代表整站）"
    )


# ---------------------------------------------------------------- 入口
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
    if provider == "aws_cloudfront":
        return await _aws_cloudfront_purge(config, token, urls, purge_everything)
    if provider == "aliyun_cdn":
        return await _aliyun_purge(config, token, urls, purge_everything)
    if provider == "tencent_cdn":
        return await _tencent_purge(config, token, urls, purge_everything)
    raise BadRequestError(
        f"provider「{provider}」的远端清缓存尚未实现（当前支持 "
        f"{['cloudflare', *SIGNED_PROVIDERS, 'custom']}）"
    )


async def preheat(*, provider: str, config: dict[str, Any], token: str, urls: list[str]) -> dict[str, Any]:
    """预热（Cloudflare / CloudFront 无此接口 → 如实报错；其余走各自接口）"""
    if provider == "cloudflare":
        raise BadRequestError("Cloudflare 不提供预热接口（其 purge 为按 URL/全量清理）")
    if provider == "custom":
        return await _custom_call(config, "preheat_url", urls, False, label="预热")
    if provider == "aws_cloudfront":
        raise BadRequestError(
            "CloudFront 不提供预热接口：边缘节点在首次请求时按需回源（可用 CreateInvalidation 清缓存）"
        )
    if provider == "aliyun_cdn":
        return await _aliyun_preheat(config, token, urls)
    if provider == "tencent_cdn":
        return await _tencent_preheat(config, token, urls)
    raise BadRequestError(f"provider「{provider}」的预热尚未实现（当前支持 custom / aliyun_cdn / tencent_cdn）")


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
    _require_within_limit("cloudflare", urls)

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
    url = _setting_str(settings, url_key)
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


# ================================================================ AWS CloudFront（SigV4）
# SigV4 的纯函数实现已抽到 ``core/sigv4.py``（与备份的 S3 上传共用同一份，避免两处实现漂移；
# 官方向量用例见 tests/test_v3_cdn_remote.py）。这里保留原名字，既有调用方与测试无需改动。
aws_signing_key = sigv4.signing_key
aws_sigv4_signature = sigv4.signature
_parse_credential_scope = sigv4.parse_credential_scope


def aws_cloudfront_headers(
    *,
    access_key_id: str,
    secret_access_key: str,
    region: str,
    host: str,
    path: str,
    payload: bytes,
    now: datetime,
    session_token: Optional[str] = None,
) -> dict[str, str]:
    """构造 CloudFront ``CreateInvalidation`` 的 SigV4 签名请求头（纯函数）"""
    service = "cloudfront"
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    payload_hash = hashlib.sha256(payload).hexdigest()

    signed: dict[str, str] = {"host": host, "x-amz-date": amz_date}
    if session_token:
        signed["x-amz-security-token"] = session_token
    signed_headers = ";".join(sorted(signed))
    # 注意：CanonicalHeaders 自身以 \n 结尾，join 再补一个 \n → 其后是空行（SigV4 规范）
    canonical_headers = "".join(f"{name}:{value}\n" for name, value in sorted(signed.items()))
    canonical_request = "\n".join(
        ["POST", path, "", canonical_headers, signed_headers, payload_hash]
    )

    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    signature = aws_sigv4_signature(
        secret_access_key=secret_access_key,
        credential_scope=credential_scope,
        amz_date=amz_date,
        canonical_request=canonical_request,
    )

    headers = {
        "Authorization": (
            f"AWS4-HMAC-SHA256 Credential={access_key_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        ),
        "X-Amz-Date": amz_date,
        "Content-Type": "text/xml",
    }
    if session_token:
        headers["X-Amz-Security-Token"] = session_token
    return headers


def cloudfront_invalidation_path(url: str) -> str:
    """把站内/绝对 URL 转成 CloudFront 失效路径（只要 path，通配符 ``*`` 允许）"""
    if url.startswith("/"):
        return url
    parsed = urlparse(url)
    return parsed.path or "/"


def cloudfront_invalidation_body(paths: list[str], caller_reference: str) -> bytes:
    """构造 ``InvalidationBatch`` 的 XML body（CloudFront 是 REST-XML 接口）"""
    root = ET.Element(
        "InvalidationBatch",
        {"xmlns": f"http://cloudfront.amazonaws.com/doc/{CLOUDFRONT_API_VERSION}/"},
    )
    paths_el = ET.SubElement(root, "Paths")
    items_el = ET.SubElement(paths_el, "Items")
    for path in paths:
        ET.SubElement(items_el, "Path").text = path
    ET.SubElement(paths_el, "Quantity").text = str(len(paths))
    ET.SubElement(root, "CallerReference").text = caller_reference
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


async def _aws_cloudfront_purge(
    config: dict[str, Any], token: str, urls: list[str], purge_everything: bool
) -> dict[str, Any]:
    settings = _settings(config)
    access_key_id = _setting_str(settings, "access_key_id")
    distribution_id = _setting_str(settings, "distribution_id")
    region = _setting_str(settings, "region") or "us-east-1"
    session_token = _setting_str(settings, "session_token") or None

    if not access_key_id:
        raise BadRequestError(
            "aws_cloudfront 需要配置 settings.access_key_id（AWS Access Key ID）"
        )
    if not token:
        raise BadRequestError(
            "aws_cloudfront 凭据（Secret Access Key）未配置，无法执行远端清缓存"
        )
    if not distribution_id:
        raise BadRequestError(
            "aws_cloudfront 需要配置 settings.distribution_id（CloudFront 分配 ID）"
        )
    _require_urls(urls, purge_everything=purge_everything)
    _require_within_limit("aws_cloudfront", urls)

    paths = ["/*"] if purge_everything else [cloudfront_invalidation_path(url) for url in urls]
    body = cloudfront_invalidation_body(paths, secrets.token_hex(16))
    path = f"/{CLOUDFRONT_API_VERSION}/distribution/{distribution_id}/invalidation"
    endpoint = _endpoint("aws_cloudfront", settings)
    host = urlparse(endpoint).netloc
    headers = aws_cloudfront_headers(
        access_key_id=access_key_id,
        secret_access_key=token,
        region=region,
        host=host,
        path=path,
        payload=body,
        now=_utcnow(),
        session_token=session_token,
    )

    try:
        async with httpx.AsyncClient(timeout=REMOTE_TIMEOUT) as client:
            resp = await client.post(f"{endpoint}{path}", content=body, headers=headers)
    except httpx.HTTPError as exc:
        raise BadRequestError(f"调用 CloudFront CreateInvalidation 失败：{exc}") from exc

    invalidation_id = _cloudfront_result(resp)
    return {
        "provider": "aws_cloudfront",
        "success": True,
        "status_code": resp.status_code,
        "purge_everything": purge_everything,
        "urls": [] if purge_everything else urls,
        "message": f"已提交 CloudFront 失效任务（Id={invalidation_id}，路径 {len(paths)} 条）",
    }


def _cloudfront_result(resp: httpx.Response) -> str:
    """解析 CloudFront 的 XML 响应；失败（含 HTTP 4xx/5xx）一律抛出带原因的异常"""
    try:
        root = ET.fromstring(resp.text or "")
    except ET.ParseError as exc:
        raise BadRequestError(
            f"CloudFront 返回了非 XML 响应（HTTP {resp.status_code}）：{(resp.text or '')[:200]}"
        ) from exc

    if resp.status_code >= 400:
        message = root.findtext("{*}Error/{*}Message") or root.findtext("{*}Message")
        code = root.findtext("{*}Error/{*}Code") or root.findtext("{*}Code") or resp.status_code
        raise BadRequestError(f"CloudFront 拒绝失效请求（{code}）：{message or resp.text[:200]}")

    invalidation_id = root.findtext("{*}Id") or root.findtext("{*}Invalidation/{*}Id")
    status = root.findtext("{*}Status") or "Unknown"
    if not invalidation_id:
        raise BadRequestError(f"CloudFront 响应缺少失效任务 Id（HTTP {resp.status_code}）")
    return f"{invalidation_id} / {status}"


# ================================================================ 阿里云 CDN（RPC HMAC-SHA1）
def aliyun_percent_encode(value: Any) -> str:
    """阿里云 RPC 签名的 percent-encoding（RFC3986；``~`` 不编码、``/`` 要编码）"""
    return quote(str(value), safe="~")


def aliyun_string_to_sign(params: dict[str, Any]) -> str:
    """阿里云 RPC 的 StringToSign：``GET&%2F&<两次编码的规范化查询串>``"""
    canonicalized = "&".join(
        f"{aliyun_percent_encode(key)}={aliyun_percent_encode(value)}"
        for key, value in sorted(params.items())
    )
    return f"GET&%2F&{aliyun_percent_encode(canonicalized)}"


def aliyun_signature(params: dict[str, Any], access_key_secret: str) -> str:
    """阿里云 RPC 签名：``Base64(HMAC-SHA1(AccessKeySecret + "&", StringToSign))``

    ⚠️ 密钥要拼一个 ``&`` 后缀 —— 这是阿里云从 ROA 时代继承下来的实际约定：
    文档公式只写 ``HMAC-SHA1(AccessKeySecret, StringToSign)``，但官方示例的签名值
    （``OLeaidS1JvxuMvnyHOwuJ+uX5qY=``）与官方 SDK
    （``aliyunsdkcore.auth.signature.rpc_signature_composer`` 的 ``secret + '&'``）
    都只有加 ``&`` 才算得出来。少了它请求会被判定为签名不匹配。
    """
    digest = hmac.new(
        f"{access_key_secret}&".encode("utf-8"),
        aliyun_string_to_sign(params).encode("utf-8"),
        hashlib.sha1,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def aliyun_signed_query(params: dict[str, Any], access_key_secret: str) -> str:
    """补上 ``Signature`` 并按同名方式编码成可直接拼到 URL 的查询串（纯函数）"""
    signed = {**params, "Signature": aliyun_signature(params, access_key_secret)}
    return "&".join(
        f"{aliyun_percent_encode(key)}={aliyun_percent_encode(value)}"
        for key, value in sorted(signed.items())
    )


def _aliyun_params(access_key_id: str, *, action: str, nonce: str, timestamp: str) -> dict[str, Any]:
    return {
        "AccessKeyId": access_key_id,
        "Action": action,
        "Format": "JSON",
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": nonce,
        "SignatureVersion": "1.0",
        "Timestamp": timestamp,
        "Version": ALIYUN_API_VERSION,
    }


def _aliyun_credentials(
    config: dict[str, Any], token: str, *, urls: list[str], purge_everything: bool, label: str
) -> tuple[dict[str, Any], str, str]:
    """取（settings, access_key_id, access_key_secret），缺什么明确报什么"""
    settings = _settings(config)
    access_key_id = _setting_str(settings, "access_key_id")
    if not access_key_id:
        raise BadRequestError("aliyun_cdn 需要配置 settings.access_key_id（阿里云 AccessKey ID）")
    if not token:
        raise BadRequestError(f"aliyun_cdn 凭据（AccessKey Secret）未配置，无法执行远端{label}")
    _require_urls(urls, purge_everything=purge_everything)
    _require_within_limit("aliyun_cdn", urls)
    return settings, access_key_id, token


async def _aliyun_call(
    settings: dict[str, Any],
    action: str,
    extra: dict[str, Any],
    access_key_id: str,
    access_key_secret: str,
    *,
    label: str,
) -> dict[str, Any]:
    """发一次阿里云 RPC 调用（GET + 查询串签名）"""
    endpoint = _endpoint("aliyun_cdn", settings)
    timestamp = _utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    params = _aliyun_params(
        access_key_id,
        action=action,
        nonce=uuid.uuid4().hex,
        timestamp=timestamp,
    )
    params.update(extra)
    query = aliyun_signed_query(params, access_key_secret)

    try:
        async with httpx.AsyncClient(timeout=REMOTE_TIMEOUT) as client:
            resp = await client.get(f"{endpoint}/?{query}")
    except httpx.HTTPError as exc:
        raise BadRequestError(f"调用阿里云 CDN {action} 失败：{exc}") from exc

    try:
        payload = resp.json()
    except ValueError as exc:
        raise BadRequestError(
            f"阿里云 CDN {action} 返回了非 JSON 响应（HTTP {resp.status_code}）"
        ) from exc
    if not isinstance(payload, dict):
        raise BadRequestError(f"阿里云 CDN {action} 返回了意外结构（HTTP {resp.status_code}）")
    if resp.status_code >= 400 or payload.get("Code"):
        code = payload.get("Code") or resp.status_code
        message = payload.get("Message") or resp.text[:200]
        raise BadRequestError(f"阿里云 CDN {label}失败（{code}）：{message}")
    return payload


async def _aliyun_purge(
    config: dict[str, Any], token: str, urls: list[str], purge_everything: bool
) -> dict[str, Any]:
    if purge_everything:
        _reject_everything("aliyun_cdn", "清缓存")
    settings, access_key_id, access_key_secret = _aliyun_credentials(
        config, token, urls=urls, purge_everything=purge_everything, label="清缓存"
    )

    # 阿里云 RefreshObjectCaches 一次只接受一个 ObjectPath → 逐条提交，逐条如实回报
    task_ids: list[str] = []
    for index, url in enumerate(urls, start=1):
        payload = await _aliyun_call(
            settings,
            "RefreshObjectCaches",
            {"ObjectPath": url, "ObjectType": "File"},
            access_key_id,
            access_key_secret,
            label=f"清缓存（第 {index}/{len(urls)} 条 {url}）",
        )
        task_ids.append(str(payload.get("RefreshTaskId") or ""))
    return {
        "provider": "aliyun_cdn",
        "success": True,
        "status_code": 200,
        "purge_everything": False,
        "urls": urls,
        "message": f"已提交阿里云刷新任务 {len(urls)} 条（TaskId: {', '.join(filter(None, task_ids)) or '-'}）",
    }


async def _aliyun_preheat(config: dict[str, Any], token: str, urls: list[str]) -> dict[str, Any]:
    settings, access_key_id, access_key_secret = _aliyun_credentials(
        config, token, urls=urls, purge_everything=False, label="预热"
    )
    task_ids: list[str] = []
    for index, url in enumerate(urls, start=1):
        payload = await _aliyun_call(
            settings,
            "PushObjectCache",
            {"ObjectPath": url},
            access_key_id,
            access_key_secret,
            label=f"预热（第 {index}/{len(urls)} 条 {url}）",
        )
        task_ids.append(str(payload.get("PushTaskId") or ""))
    return {
        "provider": "aliyun_cdn",
        "success": True,
        "status_code": 200,
        "purge_everything": False,
        "urls": urls,
        "message": f"已提交阿里云预热任务 {len(urls)} 条（TaskId: {', '.join(filter(None, task_ids)) or '-'}）",
    }


# ================================================================ 腾讯云 CDN（TC3-HMAC-SHA256）
def tencent_string_to_sign(*, timestamp: int, service: str, canonical_request: str) -> str:
    """腾讯云 TC3 的 StringToSign（纯函数）"""
    date = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")
    credential_scope = f"{date}/{service}/tc3_request"
    return "\n".join(
        [
            "TC3-HMAC-SHA256",
            str(timestamp),
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )


def tencent_tc3_signature(*, secret_key: str, timestamp: int, service: str, canonical_request: str) -> str:
    """腾讯云 TC3 签名（纯函数；四层 HMAC-SHA256：TC3+key → date → service → tc3_request）"""
    date = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")
    secret_date = hmac.new(
        f"TC3{secret_key}".encode("utf-8"), date.encode("utf-8"), hashlib.sha256
    ).digest()
    secret_service = hmac.new(secret_date, service.encode("utf-8"), hashlib.sha256).digest()
    secret_signing = hmac.new(secret_service, b"tc3_request", hashlib.sha256).digest()
    string_to_sign = tencent_string_to_sign(
        timestamp=timestamp, service=service, canonical_request=canonical_request
    )
    return hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()


def tencent_authorization(
    *,
    secret_id: str,
    secret_key: str,
    host: str,
    content_type: str,
    payload: bytes,
    timestamp: int,
) -> str:
    """构造腾讯云 TC3 的 ``Authorization`` 头（纯函数）

    参与签名的头**只有 ``content-type`` 与 ``host``** —— 与官方 SDK
    （``tencentcloud.common.abstract_client`` 的 ``_get_tc3_signature``：
    ``signed_headers = 'content-type;host'``）一致；``X-TC-Action`` 仍照常发送，
    但**不进签名**（进签名会引入大小写归一问题，官方并未这么做）。
    """
    service = "cdn"
    date = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")
    signed_headers = "content-type;host"
    canonical_headers = f"content-type:{content_type}\nhost:{host}\n"
    canonical_request = "\n".join(
        [
            "POST",
            "/",
            "",
            canonical_headers,
            signed_headers,
            hashlib.sha256(payload).hexdigest(),
        ]
    )
    signature = tencent_tc3_signature(
        secret_key=secret_key,
        timestamp=timestamp,
        service=service,
        canonical_request=canonical_request,
    )
    credential_scope = f"{date}/{service}/tc3_request"
    return (
        f"TC3-HMAC-SHA256 Credential={secret_id}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )


def _tencent_credentials(
    config: dict[str, Any], token: str, *, urls: list[str], purge_everything: bool, label: str
) -> tuple[dict[str, Any], str, str]:
    settings = _settings(config)
    secret_id = _setting_str(settings, "secret_id")
    if not secret_id:
        raise BadRequestError("tencent_cdn 需要配置 settings.secret_id（腾讯云 SecretId）")
    if not token:
        raise BadRequestError(f"tencent_cdn 凭据（SecretKey）未配置，无法执行远端{label}")
    _require_urls(urls, purge_everything=purge_everything)
    _require_within_limit("tencent_cdn", urls)
    return settings, secret_id, token


async def _tencent_call(
    settings: dict[str, Any],
    action: str,
    body: dict[str, Any],
    secret_id: str,
    secret_key: str,
    *,
    label: str,
) -> dict[str, Any]:
    """发一次腾讯云 CDN 调用（POST JSON + TC3 签名头）"""
    endpoint = _endpoint("tencent_cdn", settings)
    host = urlparse(endpoint).netloc
    region = _setting_str(settings, "region") or "ap-guangzhou"
    content_type = "application/json; charset=utf-8"
    payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    timestamp = int(_utcnow().timestamp())

    headers = {
        "Authorization": tencent_authorization(
            secret_id=secret_id,
            secret_key=secret_key,
            host=host,
            content_type=content_type,
            payload=payload,
            timestamp=timestamp,
        ),
        "Content-Type": content_type,
        "X-TC-Action": action,
        "X-TC-Version": TENCENT_API_VERSION,
        "X-TC-Timestamp": str(timestamp),
        "X-TC-Region": region,
    }

    try:
        async with httpx.AsyncClient(timeout=REMOTE_TIMEOUT) as client:
            resp = await client.post(endpoint, content=payload, headers=headers)
    except httpx.HTTPError as exc:
        raise BadRequestError(f"调用腾讯云 CDN {action} 失败：{exc}") from exc

    try:
        parsed = resp.json()
    except ValueError as exc:
        raise BadRequestError(
            f"腾讯云 CDN {action} 返回了非 JSON 响应（HTTP {resp.status_code}）"
        ) from exc
    response = (parsed or {}).get("Response") if isinstance(parsed, dict) else None
    if not isinstance(response, dict):
        raise BadRequestError(f"腾讯云 CDN {action} 返回了意外结构（HTTP {resp.status_code}）")
    error = response.get("Error")
    if isinstance(error, dict) or resp.status_code >= 400:
        code = (error or {}).get("Code") or resp.status_code
        message = (error or {}).get("Message") or resp.text[:200]
        raise BadRequestError(f"腾讯云 CDN {label}失败（{code}）：{message}")
    return response


async def _tencent_purge(
    config: dict[str, Any], token: str, urls: list[str], purge_everything: bool
) -> dict[str, Any]:
    if purge_everything:
        _reject_everything("tencent_cdn", "清缓存")
    settings, secret_id, secret_key = _tencent_credentials(
        config, token, urls=urls, purge_everything=purge_everything, label="清缓存"
    )
    response = await _tencent_call(
        settings, "PurgeUrlsCache", {"Urls": urls}, secret_id, secret_key, label="清缓存"
    )
    task_id = str(response.get("PurgeTaskId") or "")
    return {
        "provider": "tencent_cdn",
        "success": True,
        "status_code": 200,
        "purge_everything": False,
        "urls": urls,
        "message": f"已提交腾讯云刷新任务 {len(urls)} 条（TaskId: {task_id or '-'}）",
    }


async def _tencent_preheat(config: dict[str, Any], token: str, urls: list[str]) -> dict[str, Any]:
    settings, secret_id, secret_key = _tencent_credentials(
        config, token, urls=urls, purge_everything=False, label="预热"
    )
    response = await _tencent_call(
        settings, "PushUrlsCache", {"Urls": urls}, secret_id, secret_key, label="预热"
    )
    task_id = str(response.get("PushTaskId") or "")
    return {
        "provider": "tencent_cdn",
        "success": True,
        "status_code": 200,
        "purge_everything": False,
        "urls": urls,
        "message": f"已提交腾讯云预热任务 {len(urls)} 条（TaskId: {task_id or '-'}）",
    }


# ---------------------------------------------------------------- 公共 HTTP 辅助
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
