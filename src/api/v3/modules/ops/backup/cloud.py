"""ops.backup 的云存储：把备份上传到 AWS S3 / 阿里云 OSS（**真实调用**）

这是原 `shared/utils/backup_manager.py` 那条死代码链里"云上传"能力的重建版：
旧实现有两处硬伤（`Path.with_suffix('.tar.gz')` 直接抛 ``ValueError``、把已经归档的备份再打一层 tar），
**从未成功上传过一次**。这里重写为真实可用的实现：

  - ``s3``：用 ``aioboto3``（依赖已在 ``requirements.txt``）走标准 S3 API，
    region / endpoint 可覆盖（S3 兼容存储、MinIO、内网私有云都行）；
  - ``oss``：用 ``httpx`` + OSS V1 签名（``HMAC-SHA1``）直接 ``PUT``，
    不引入 ``oss2`` 依赖，且签名可被离线复算验证（见测试）。

配置存 ``system_settings`` 的 ``backup.cloud``（见 ``service.py``）：
``provider`` / ``bucket`` / ``region`` / ``endpoint`` / ``prefix`` / ``access_key_id``
是非敏感项；**密钥单独加密**（``core/secret_box.py``，AES-256-GCM），读接口只回 ``has_secret``。
"""

import asyncio
import base64
import hashlib
import hmac
import os
from datetime import datetime, timezone
from email.utils import formatdate
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from src.api.v3.core import sigv4
from src.api.v3.core.exceptions import BadRequestError

#: 云存储配置在 ``system_settings`` 里的键
CLOUD_SETTING_KEY = "backup.cloud"

#: 支持的云存储
SUPPORTED_CLOUD_PROVIDERS = ("s3", "oss")

#: object key 默认前缀 / 各 provider 的默认 region
DEFAULT_PREFIX = "backups"
DEFAULT_REGIONS = {"s3": "us-east-1", "oss": "oss-cn-hangzhou"}

#: 上传超时（秒）
UPLOAD_TIMEOUT = 600.0

#: S3 单次 PUT 的对象上限（5GB，S3 硬限制；更大的备份需要 multipart，当前如实不支持）
MAX_SINGLE_PUT_BYTES = 5 * 1024 * 1024 * 1024


def default_endpoint(provider: str, region: str) -> Optional[str]:
    """OSS 必须显式给 endpoint（由 region 推导）；S3 交给 botocore 解析（配置可覆盖）"""
    if provider == "oss":
        return f"https://{region or DEFAULT_REGIONS['oss']}.aliyuncs.com"
    return None


def build_object_key(prefix: str, filename: str) -> str:
    """云端 object key：``{prefix}/{filename}``（``prefix`` 留空或未配置时用默认 ``backups``）"""
    clean = str(prefix or DEFAULT_PREFIX).strip("/")
    return f"{clean}/{filename}" if clean else str(filename)


def mask(config: dict[str, Any]) -> dict[str, Any]:
    """响应脱敏：密钥永不回传，只回 ``has_secret``"""
    out = {key: value for key, value in (config or {}).items() if key != "secret_encrypted"}
    out["has_secret"] = bool((config or {}).get("secret_encrypted"))
    return out


# ---------------------------------------------------------------- OSS 签名（V1）
def oss_string_to_sign(
    *, method: str, content_type: str, date: str, resource: str, content_md5: str = ""
) -> str:
    """OSS V1 签名的 StringToSign

    ``VERB + "\\n" + Content-MD5 + "\\n" + Content-Type + "\\n" + Date + "\\n" + CanonicalizedResource``
    （没有 ``x-oss-*`` 头时 CanonicalizedOSSHeaders 为空串）
    """
    return "\n".join([method.upper(), content_md5 or "", content_type or "", date or "", resource])


def oss_authorization(
    *,
    access_key_id: str,
    secret: str,
    method: str,
    content_type: str,
    date: str,
    resource: str,
    content_md5: str = "",
) -> str:
    """``Authorization: OSS {AccessKeyId}:{Base64(HMAC-SHA1(secret, StringToSign))}``（纯函数）"""
    string_to_sign = oss_string_to_sign(
        method=method,
        content_type=content_type,
        date=date,
        resource=resource,
        content_md5=content_md5,
    )
    signature = base64.b64encode(
        hmac.new(secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha1).digest()
    ).decode("utf-8")
    return f"OSS {access_key_id}:{signature}"


# ---------------------------------------------------------------- 上传
def _require(config: dict[str, Any], key: str, message: str) -> str:
    value = str(config.get(key) or "").strip()
    if not value:
        raise BadRequestError(message)
    return value


async def upload_backup(
    *, provider: str, config: dict[str, Any], secret: str, path: str, key: str
) -> dict[str, Any]:
    """按 provider 上传一个备份文件（返回云端位置信息）"""
    if provider == "s3":
        return await _upload_s3(config=config, secret=secret, path=path, key=key)
    if provider == "oss":
        return await _upload_oss(config=config, secret=secret, path=path, key=key)
    raise BadRequestError(
        f"不支持的云存储提供商：{provider}（可选 {list(SUPPORTED_CLOUD_PROVIDERS)}）"
    )


async def _upload_s3(*, config: dict[str, Any], secret: str, path: str, key: str) -> dict[str, Any]:
    """S3 上传：httpx + SigV4（**单次 PUT**，path-style 寻址；endpoint 可覆盖 → MinIO / 私有云）

    用 ``core/sigv4.py``（与 CloudFront 同一份、经 AWS 官方向量验证）自己签名，
    而不是 ``aioboto3``：后者在本机环境（Windows + Proactor + 本地端点）会挂住，
    且签名无法离线复核。代价是只做单次 PUT —— S3 单对象上限 5GB，更大的备份需要 multipart，
    当前会如实报错而不是悄悄失败。
    """
    access_key_id = _require(config, "access_key_id", "S3 需要配置 access_key_id")
    bucket = _require(config, "bucket", "S3 需要配置 bucket")
    region = str(config.get("region") or DEFAULT_REGIONS["s3"])
    endpoint = str(config.get("endpoint") or f"https://s3.{region}.amazonaws.com").rstrip("/")
    if not secret:
        raise BadRequestError("S3 密钥（secret access key）未配置，无法上传")

    size = os.path.getsize(path)
    if size > MAX_SINGLE_PUT_BYTES:
        raise BadRequestError(
            f"备份文件 {size} 字节超过单次 PUT 上限（{MAX_SINGLE_PUT_BYTES}）；"
            "S3 大文件需要 multipart 上传，当前未实现"
        )

    host = urlparse(endpoint).netloc
    uri = sigv4.canonical_uri(bucket, key)
    payload_hash = await asyncio.to_thread(sigv4.sha256_file, path)
    signed = sigv4.signing_headers(
        method="PUT",
        canonical_uri=uri,
        headers={"host": host, "x-amz-content-sha256": payload_hash},
        payload_hash=payload_hash,
        access_key_id=access_key_id,
        secret_access_key=secret,
        region=region,
        service="s3",
        now=datetime.now(timezone.utc),
    )
    headers = {
        "Host": host,
        "X-Amz-Date": signed["X-Amz-Date"],
        "X-Amz-Content-Sha256": payload_hash,
        "Content-Type": "application/octet-stream",
        "Content-Length": str(size),
        "Authorization": signed["Authorization"],
    }

    try:
        def _put_file() -> httpx.Response:
            with httpx.Client(timeout=UPLOAD_TIMEOUT) as client:
                with open(path, 'rb') as handle:
                    return client.put(f"{endpoint}{uri}", content=handle, headers=headers)

        resp = await asyncio.to_thread(_put_file)
    except (httpx.HTTPError, OSError) as exc:
        raise BadRequestError(f"上传到 S3 失败（bucket={bucket}）：{exc}") from exc

    if resp.status_code >= 400:
        raise BadRequestError(
            f"S3 拒绝上传（HTTP {resp.status_code}）：{(resp.text or '')[:200]}"
        )

    return {
        "provider": "s3",
        "bucket": bucket,
        "key": key,
        "size": size,
        "endpoint": endpoint,
        "location": f"s3://{bucket}/{key}",
        "status_code": resp.status_code,
    }


async def _upload_oss(*, config: dict[str, Any], secret: str, path: str, key: str) -> dict[str, Any]:
    """阿里云 OSS 上传（httpx + OSS V1 签名，路径风格 URL）"""
    access_key_id = _require(config, "access_key_id", "阿里云 OSS 需要配置 access_key_id")
    bucket = _require(config, "bucket", "阿里云 OSS 需要配置 bucket")
    region = str(config.get("region") or DEFAULT_REGIONS["oss"])
    endpoint = str(config.get("endpoint") or default_endpoint("oss", region) or "").rstrip("/")
    if not secret:
        raise BadRequestError("阿里云 OSS 密钥（access key secret）未配置，无法上传")

    resource = f"/{bucket}/{key}"
    url = f"{endpoint}{resource}"
    date = formatdate(usegmt=True)
    content_type = "application/octet-stream"
    headers = {
        "Date": date,
        "Content-Type": content_type,
        "Content-Length": str(os.path.getsize(path)),
        "Authorization": oss_authorization(
            access_key_id=access_key_id,
            secret=secret,
            method="PUT",
            content_type=content_type,
            date=date,
            resource=resource,
        ),
    }

    try:
        # 注意：httpx 的 AsyncClient 不接受同步文件对象（会抛 "Attempted to send
        # an sync request with an AsyncClient instance"），所以放到工作线程里用同步
        # client 流式上传 —— 既不把大备份读进内存，也不阻塞事件循环。
        def _put_file() -> httpx.Response:
            with httpx.Client(timeout=UPLOAD_TIMEOUT) as client:
                with open(path, 'rb') as handle:
                    return client.put(url, content=handle, headers=headers)

        resp = await asyncio.to_thread(_put_file)
    except (httpx.HTTPError, OSError) as exc:
        raise BadRequestError(f"上传到 OSS 失败（{endpoint}）：{exc}") from exc

    if resp.status_code >= 400:
        raise BadRequestError(
            f"OSS 拒绝上传（HTTP {resp.status_code}）：{(resp.text or '')[:200]}"
        )

    return {
        "provider": "oss",
        "bucket": bucket,
        "key": key,
        "size": os.path.getsize(path),
        "endpoint": endpoint,
        "location": f"oss://{bucket}/{key}",
        "status_code": resp.status_code,
    }
