"""AWS Signature V4（SigV4）—— CloudFront 与 S3 云上传**共用的一份纯函数实现**

与 AWS 官方文档《Examples of the complete Version 4 signing process (Python)》的
IAM ListUsers 示例逐字对齐：官方向量用例在 ``tests/test_v3_cdn_remote.py``
（``test_aws_sigv4_matches_aws_documentation_vector``），端到端用例再从**服务端实际收到的
请求**独立复算一次签名。

为什么不直接用 SDK（boto3 / aioboto3）：

  - CloudFront 的 CreateInvalidation 需要手写 XML 与自定义头，SDK 的封装帮不上忙；
  - 备份的 S3 上传只需要**单次 PUT**（≤5GB），而 ``aioboto3`` 在本机环境
    （Windows + Proactor 事件循环 + 本地端点）会直接挂住，且它的签名无法离线复核；
  - 自己实现可以像 CDN 那样做**离线验签**（纯函数 + 官方向量 + 本地端点复算）。
"""

import hashlib
import hmac
from datetime import datetime
from typing import Any


def signing_key(secret_access_key: str, date_stamp: str, region: str, service: str) -> bytes:
    """派生签名密钥：``AWS4{secret}`` → date → region → service → ``aws4_request``"""
    key = f"AWS4{secret_access_key}".encode("utf-8")
    k_date = hmac.new(key, date_stamp.encode("utf-8"), hashlib.sha256).digest()
    k_region = hmac.new(k_date, region.encode("utf-8"), hashlib.sha256).digest()
    k_service = hmac.new(k_region, service.encode("utf-8"), hashlib.sha256).digest()
    return hmac.new(k_service, b"aws4_request", hashlib.sha256).digest()


def parse_credential_scope(scope: str) -> tuple[str, str, str]:
    """``{date}/{region}/{service}/aws4_request`` → ``(date, region, service)``"""
    parts = scope.split("/")
    if len(parts) != 4 or parts[3] != "aws4_request":
        raise ValueError(f"非法的 SigV4 credential scope：{scope}")
    return parts[0], parts[1], parts[2]


def signature(
    *, secret_access_key: str, credential_scope: str, amz_date: str, canonical_request: str
) -> str:
    """``HMAC-SHA256(SigningKey, StringToSign)``（纯函数）"""
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    date_stamp, region, service = parse_credential_scope(credential_scope)
    key = signing_key(secret_access_key, date_stamp, region, service)
    return hmac.new(key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()


def signing_headers(
    *,
    method: str,
    canonical_uri: str,
    headers: dict[str, str],
    payload_hash: str,
    access_key_id: str,
    secret_access_key: str,
    region: str,
    service: str,
    now: datetime,
    query: str = "",
) -> dict[str, str]:
    """构造 SigV4 请求头：返回要补到请求上的 ``X-Amz-Date`` 与 ``Authorization``

    ``headers`` 是**要纳入签名**的头（键会被规范成小写，值按原样参与），
    调用方需保证实际发出的头与之逐字一致（值不要有首尾空格）。
    """
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    sign_map = {name.lower(): str(value) for name, value in headers.items()}
    sign_map["x-amz-date"] = amz_date
    signed_headers = ";".join(sorted(sign_map))
    canonical_headers = "".join(
        f"{name}:{sign_map[name]}\n" for name in sorted(sign_map)
    )
    canonical_request = "\n".join(
        [method.upper(), canonical_uri, query, canonical_headers, signed_headers, payload_hash]
    )
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    signed = signature(
        secret_access_key=secret_access_key,
        credential_scope=credential_scope,
        amz_date=amz_date,
        canonical_request=canonical_request,
    )
    return {
        "X-Amz-Date": amz_date,
        "Authorization": (
            f"AWS4-HMAC-SHA256 Credential={access_key_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signed}"
        ),
    }


def sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    """分块算文件 sha256（S3 的 ``x-amz-content-sha256`` 用；不把文件读进内存）"""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_uri(*segments: Any) -> str:
    """把路径段拼成带前导 ``/`` 的 CanonicalURI（段内保留 ``/`` 与 ``~``，其余按 RFC3986 编码）"""
    from urllib.parse import quote

    parts = [quote(str(segment).strip("/"), safe="/~") for segment in segments if str(segment)]
    return "/" + "/".join(parts)
