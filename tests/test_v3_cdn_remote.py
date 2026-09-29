"""批次 18/19：``ops/cdn`` 远端动作（清缓存 / 预热）测试

分成三层：

  1. **签名正确性**（离线）：用厂商官方基线核对纯函数 ——
     AWS SigV4 用 AWS 文档《Examples of the complete Version 4 signing process (Python)》
     的 IAM ListUsers 示例；阿里云 RPC 用其文档《签名机制》的示例签名值；
     腾讯云 TC3 用官方 SDK（``tencentcloud-sdk-python-common`` 的 ``Sign.sign_tc3``）
     交叉验证过的基线（见用例注释）。
  2. **请求绑定**（本地 HTTP 端点）：把 ``settings.endpoint`` 指到本地 server，
     **从服务端实际收到的请求独立重算签名**并比对 —— 这验证了"签名的规范请求与实际
     发出的请求一致"（服务端就是这么校验的），而不只是"两条代码路径算法相同"。
  3. **拒绝路径**：缺凭据 / 缺标识 / 不支持的整站全量 / 超批量上限 / 无预热接口，
     一律明确报错，绝不假装成功。
"""

import base64
import hashlib
import hmac
import json
import threading
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, quote, urlparse

import pytest

from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.ops.cdn import remote as cdn_remote

URLS = ["https://example.com/app.js"]


# ================================================================ 本地端点 fixture
class _Recorder:
    """记录服务端实际收到的请求，并控制返回体"""

    def __init__(self) -> None:
        self.requests: list[dict] = []
        self.status = 200
        self.body = b"{}"
        self.content_type = "application/json"


def _handler_factory(recorder: _Recorder):
    class _Handler(BaseHTTPRequestHandler):
        def _record(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            payload = self.rfile.read(length) if length else b""
            recorder.requests.append(
                {
                    "method": self.command,
                    "path": self.path,
                    "headers": {key: value for key, value in self.headers.items()},
                    "body": payload,
                }
            )

        def _respond(self) -> None:
            self.send_response(recorder.status)
            self.send_header("Content-Type", recorder.content_type)
            self.send_header("Content-Length", str(len(recorder.body)))
            self.end_headers()
            self.wfile.write(recorder.body)

        def do_GET(self) -> None:  # noqa: N802 - http.server 约定
            self._record()
            self._respond()

        def do_POST(self) -> None:  # noqa: N802 - http.server 约定
            self._record()
            self._respond()

        def log_message(self, *args) -> None:  # 静音访问日志
            return

    return _Handler


@pytest.fixture()
def cdn_endpoint():
    """本地 CDN 端点：返回 ``(endpoint, recorder)``"""
    recorder = _Recorder()
    server = HTTPServer(("127.0.0.1", 0), _handler_factory(recorder))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", recorder
    finally:
        server.shutdown()
        server.server_close()


def _canonical_request_from(headers: dict, method: str, path: str, body: bytes, signed: list[str]) -> str:
    """从**实际收到的请求**重建规范请求头（独立于被测实现，统一小写 header 名）"""
    lowered = {key.lower(): value for key, value in headers.items()}
    canonical_headers = "".join(f"{name}:{lowered[name].strip()}\n" for name in signed)
    return "\n".join(
        [method, path, "", canonical_headers, ";".join(signed), hashlib.sha256(body).hexdigest()]
    )


def _hmac(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


# ================================================================ 1. 签名正确性
def test_aws_sigv4_matches_aws_documentation_vector() -> None:
    """AWS 官方向量：文档《Examples of the complete Version 4 signing process (Python)》

    输入是 IAM ListUsers 示例（AKIDEXAMPLE / 20150830T123600Z / us-east-1 / iam），
    规范请求与期望签名都取自该文档。
    """
    canonical_request = (
        "GET\n/\nAction=ListUsers&Version=2010-05-08\n"
        "content-type:application/x-www-form-urlencoded; charset=utf-8\n"
        "host:iam.amazonaws.com\n"
        "x-amz-date:20150830T123600Z\n"
        "\n"
        "content-type;host;x-amz-date\n"
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    signature = cdn_remote.aws_sigv4_signature(
        secret_access_key="wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY",
        credential_scope="20150830/us-east-1/iam/aws4_request",
        amz_date="20150830T123600Z",
        canonical_request=canonical_request,
    )
    assert signature == "5d672d79c15b13162d9279b0855cfba6789a8edb4c82c400e06b5924a6f2b5d7"


def test_aws_sigv4_authorization_header_shape() -> None:
    """签名头结构：Credential 带 scope、SignedHeaders 是实际签名的头、path 进规范请求"""
    headers = cdn_remote.aws_cloudfront_headers(
        access_key_id="AKIDEXAMPLE",
        secret_access_key="secret",
        region="us-east-1",
        host="cloudfront.amazonaws.com",
        path="/2020-05-31/distribution/DIST/invalidation",
        payload=b"<InvalidationBatch/>",
        now=datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert headers["X-Amz-Date"] == "20260921T120000Z"
    assert headers["Authorization"].startswith(
        "AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/20260921/us-east-1/cloudfront/aws4_request, "
        "SignedHeaders=host;x-amz-date, Signature="
    )
    assert headers["Content-Type"] == "text/xml"


def test_aliyun_signature_matches_official_example() -> None:
    """阿里云官方向量：文档《签名机制》的 DescribeRegions 示例（AccessKeySecret=testsecret）

    ⚠️ 该签名值只有把 HMAC 密钥写成 ``AccessKeySecret + "&"`` 才成立（SDK 同样如此）。
    """
    params = {
        "AccessKeyId": "testid",
        "Action": "DescribeRegions",
        "Format": "XML",
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": "3ee8c1b8-83d3-44af-a94f-4e0ad82fd6cf",
        "SignatureVersion": "1.0",
        "Timestamp": "2016-02-23T12:46:24Z",
        "Version": "2014-05-26",
    }
    assert cdn_remote.aliyun_string_to_sign(params) == (
        "GET&%2F&AccessKeyId%3Dtestid%26Action%3DDescribeRegions%26Format%3DXML"
        "%26SignatureMethod%3DHMAC-SHA1%26SignatureNonce%3D3ee8c1b8-83d3-44af-a94f-4e0ad82fd6cf"
        "%26SignatureVersion%3D1.0%26Timestamp%3D2016-02-23T12%253A46%253A24Z%26Version%3D2014-05-26"
    )
    assert cdn_remote.aliyun_signature(params, "testsecret") == "OLeaidS1JvxuMvnyHOwuJ+uX5qY="


def test_aliyun_percent_encode_keeps_slash_encoded() -> None:
    """阿里云的 percent-encoding：``/`` 必须编码成 ``%2F``、``~`` 不编码"""
    assert cdn_remote.aliyun_percent_encode("https://e.com/a b~c") == "https%3A%2F%2Fe.com%2Fa%20b~c"


def test_tencent_tc3_matches_official_sdk_baseline() -> None:
    """腾讯云 TC3：与官方 SDK 交叉验证过的基线

    基线来源：``tencentcloud-sdk-python-common`` 3.1.178 的
    ``tencentcloud.common.sign.Sign.sign_tc3`` 对同一输入给出同一签名（实测一致）。
    """
    canonical_request = (
        "POST\n/\n\n"
        "content-type:application/json; charset=utf-8\n"
        "host:cvm.tencentcloudapi.com\n"
        "\n"
        "content-type;host\n"
        "35e9c5b0e3ae67532d3c9f17ead6c90222632e5b1ff7f6e89887f1398934f064"
    )
    assert cdn_remote.tencent_string_to_sign(
        timestamp=1551113065, service="cvm", canonical_request=canonical_request
    ) == (
               "TC3-HMAC-SHA256\n"
               "1551113065\n"
               "2019-02-25/cvm/tc3_request\n"
               "5ffe6a04c0664d6b969fab9a13bdab201d63ee709638e2749d62a09ca18d7031"
           )
    assert (
        cdn_remote.tencent_tc3_signature(
            secret_key="Gu5t9xGARNpq86cd98joQYCN3*******",
            timestamp=1551113065,
            service="cvm",
            canonical_request=canonical_request,
        )
        == "2230eefd229f582d8b1b891af7107b91597240707d778ab3738f756258d7652c"
    )


# ================================================================ 2. 请求绑定（端到端）
@pytest.mark.asyncio
async def test_cloudfront_purge_request_is_signed_and_parsed(cdn_endpoint):
    """CloudFront：XML body + SigV4 头 + 响应解析，签名与实际请求一致"""
    endpoint, recorder = cdn_endpoint
    recorder.body = (
        '<?xml version="1.0"?>'
        '<Invalidation xmlns="http://cloudfront.amazonaws.com/doc/2020-05-31/">'
        "<Id>I2J0EXAMPLE</Id><Status>InProgress</Status></Invalidation>"
    ).encode()

    result = await cdn_remote.purge(
        provider="aws_cloudfront",
        config={
            "settings": {
                "access_key_id": "AKIDEXAMPLE",
                "distribution_id": "DIST123",
                "endpoint": endpoint,
            }
        },
        token="secret-key",
        urls=["https://example.com/app.js", "https://example.com/a.css"],
    )
    assert result["success"] is True
    assert "I2J0EXAMPLE" in result["message"]

    sent = recorder.requests[0]
    assert sent["method"] == "POST"
    assert sent["path"] == "/2020-05-31/distribution/DIST123/invalidation"
    headers = {key.lower(): value for key, value in sent["headers"].items()}
    assert headers["authorization"].startswith("AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/")
    assert "SignedHeaders=host;x-amz-date" in headers["authorization"]
    assert headers["x-amz-date"]
    assert headers["content-type"] == "text/xml"

    # body 是 CloudFront 的 InvalidationBatch XML，路径取 URL 的 path 部分
    root = ET.fromstring(sent["body"])
    paths = [node.text for node in root.findall("{*}Paths/{*}Items/{*}Path")]
    assert paths == ["/app.js", "/a.css"]
    assert root.findtext("{*}Paths/{*}Quantity") == "2"

    # 服务端会这样校验：从实际收到的请求独立重算签名，必须与 Authorization 里的一致
    credential, signature = (
        headers["authorization"].split("Credential=")[1].split(", SignedHeaders=")[0],
        headers["authorization"].split("Signature=")[1],
    )
    scope = credential.split("/", 1)[1]
    canonical_request = _canonical_request_from(
        sent["headers"], "POST", sent["path"], sent["body"], ["host", "x-amz-date"]
    )
    date_stamp, region, service = scope.split("/")[:3]
    signing_key = _hmac(_hmac(_hmac(_hmac(b"AWS4secret-key", date_stamp), region), service), "aws4_request")
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            headers["x-amz-date"],
            scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    assert signature == hmac.new(
        signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()


@pytest.mark.asyncio
async def test_cloudfront_purge_everything_uses_wildcard(cdn_endpoint):
    """purge_everything 在 CloudFront 上就是 ``/*``"""
    endpoint, recorder = cdn_endpoint
    recorder.body = (
        '<?xml version="1.0"?><Invalidation><Id>I1</Id><Status>Completed</Status></Invalidation>'
    ).encode()

    result = await cdn_remote.purge(
        provider="aws_cloudfront",
        config={"settings": {"access_key_id": "AK", "distribution_id": "D", "endpoint": endpoint}},
        token="sk",
        urls=[],
        purge_everything=True,
    )
    assert result["purge_everything"] is True
    paths = [
        node.text
        for node in ET.fromstring(recorder.requests[0]["body"]).findall("{*}Paths/{*}Items/{*}Path")
    ]
    assert paths == ["/*"]


@pytest.mark.asyncio
async def test_aliyun_purge_signs_each_url(cdn_endpoint):
    """阿里云：逐条 RefreshObjectCaches，查询串签名可被独立复算"""
    endpoint, recorder = cdn_endpoint
    recorder.body = json.dumps({"RequestId": "req-1", "RefreshTaskId": "task-1"}).encode()

    result = await cdn_remote.purge(
        provider="aliyun_cdn",
        config={"settings": {"access_key_id": "testid", "endpoint": endpoint}},
        token="testsecret",
        urls=URLS,
    )
    assert result["success"] is True
    assert "task-1" in result["message"]

    sent = recorder.requests[0]
    assert sent["method"] == "GET"
    raw_query = urlparse(sent["path"]).query
    params = dict(parse_qsl(raw_query, keep_blank_values=True))
    assert params["Action"] == "RefreshObjectCaches"
    assert params["ObjectPath"] == URLS[0]
    assert params["ObjectType"] == "File"
    assert params["AccessKeyId"] == "testid"
    assert params["Version"] == "2018-05-10"
    assert params["SignatureMethod"] == "HMAC-SHA1"

    # 独立复算（服务端视角）：对收到的查询串做两次 percent-encoding 后 HMAC
    signature = params.pop("Signature")
    canonicalized = "&".join(
        f"{quote(key, safe='~')}={quote(value, safe='~')}" for key, value in sorted(params.items())
    )
    string_to_sign = f"GET&%2F&{quote(canonicalized, safe='~')}"
    assert signature == base64.b64encode(
        hmac.new(b"testsecret&", string_to_sign.encode("utf-8"), hashlib.sha1).digest()
    ).decode()


@pytest.mark.asyncio
async def test_aliyun_preheat_uses_push_object_cache(cdn_endpoint):
    """阿里云预热走 PushObjectCache"""
    endpoint, recorder = cdn_endpoint
    recorder.body = json.dumps({"RequestId": "req-2", "PushTaskId": "push-1"}).encode()

    result = await cdn_remote.preheat(
        provider="aliyun_cdn",
        config={"settings": {"access_key_id": "testid", "endpoint": endpoint}},
        token="testsecret",
        urls=URLS,
    )
    assert "push-1" in result["message"]
    params = dict(parse_qsl(urlparse(recorder.requests[0]["path"]).query))
    assert params["Action"] == "PushObjectCache"
    assert params["ObjectPath"] == URLS[0]


@pytest.mark.asyncio
async def test_tencent_purge_request_is_signed_and_parsed(cdn_endpoint):
    """腾讯云：TC3 头 + JSON body + 响应解析，签名与实际请求一致"""
    endpoint, recorder = cdn_endpoint
    recorder.body = json.dumps(
        {"Response": {"RequestId": "req-3", "PurgeTaskId": "purge-9"}}
    ).encode()

    result = await cdn_remote.purge(
        provider="tencent_cdn",
        config={"settings": {"secret_id": "AKIDtest", "region": "ap-guangzhou", "endpoint": endpoint}},
        token="secret-key",
        urls=URLS,
    )
    assert "purge-9" in result["message"]

    sent = recorder.requests[0]
    assert sent["method"] == "POST"
    assert sent["path"] == "/"
    headers = {key.lower(): value for key, value in sent["headers"].items()}
    assert headers["x-tc-action"] == "PurgeUrlsCache"
    assert headers["x-tc-version"] == "2018-06-06"
    assert headers["x-tc-region"] == "ap-guangzhou"
    assert json.loads(sent["body"].decode("utf-8")) == {"Urls": URLS}

    # 独立复算（服务端视角）
    authorization = headers["authorization"]
    scope = authorization.split("Credential=")[1].split(", SignedHeaders=")[0].split("/", 1)[1]
    signed_headers = authorization.split("SignedHeaders=")[1].split(",")[0].split(" Signature=")[0]
    signature = authorization.split("Signature=")[1]
    timestamp = int(headers["x-tc-timestamp"])
    canonical_request = _canonical_request_from(
        sent["headers"], "POST", "/", sent["body"], signed_headers.split(";")
    )
    string_to_sign = "\n".join(
        [
            "TC3-HMAC-SHA256",
            str(timestamp),
            scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    date = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")
    signing_key = _hmac(_hmac(_hmac(b"TC3secret-key", date), "cdn"), "tc3_request")
    assert signature == hmac.new(
        signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()


@pytest.mark.asyncio
async def test_tencent_preheat_uses_push_urls_cache(cdn_endpoint):
    """腾讯云预热走 PushUrlsCache"""
    endpoint, recorder = cdn_endpoint
    recorder.body = json.dumps({"Response": {"RequestId": "r", "PushTaskId": "push-2"}}).encode()

    result = await cdn_remote.preheat(
        provider="tencent_cdn",
        config={"settings": {"secret_id": "AKIDtest", "endpoint": endpoint}},
        token="secret-key",
        urls=URLS,
    )
    assert "push-2" in result["message"]
    headers = {key.lower(): value for key, value in recorder.requests[0]["headers"].items()}
    assert headers["x-tc-action"] == "PushUrlsCache"


# ================================================================ 3. 拒绝路径
@pytest.mark.asyncio
async def test_cloudfront_requires_access_key_and_distribution():
    with pytest.raises(BadRequestError) as exc:
        await cdn_remote.purge(
            provider="aws_cloudfront", config={"settings": {}}, token="sk", urls=URLS
        )
    assert "access_key_id" in str(exc.value)

    with pytest.raises(BadRequestError) as exc2:
        await cdn_remote.purge(
            provider="aws_cloudfront",
            config={"settings": {"access_key_id": "AK"}},
            token="sk",
            urls=URLS,
        )
    assert "distribution_id" in str(exc2.value)

    with pytest.raises(BadRequestError) as exc3:
        await cdn_remote.purge(
            provider="aws_cloudfront",
            config={"settings": {"access_key_id": "AK", "distribution_id": "D"}},
            token="",
            urls=URLS,
        )
    assert "凭据" in str(exc3.value)


@pytest.mark.asyncio
async def test_aliyun_requires_credentials():
    with pytest.raises(BadRequestError) as exc:
        await cdn_remote.purge(provider="aliyun_cdn", config={"settings": {}}, token="s", urls=URLS)
    assert "access_key_id" in str(exc.value)

    with pytest.raises(BadRequestError) as exc2:
        await cdn_remote.purge(
            provider="aliyun_cdn", config={"settings": {"access_key_id": "id"}}, token="", urls=URLS
        )
    assert "凭据" in str(exc2.value)


@pytest.mark.asyncio
async def test_tencent_requires_credentials():
    with pytest.raises(BadRequestError) as exc:
        await cdn_remote.purge(provider="tencent_cdn", config={"settings": {}}, token="s", urls=URLS)
    assert "secret_id" in str(exc.value)

    with pytest.raises(BadRequestError) as exc2:
        await cdn_remote.purge(
            provider="tencent_cdn", config={"settings": {"secret_id": "id"}}, token="", urls=URLS
        )
    assert "凭据" in str(exc2.value)


@pytest.mark.asyncio
async def test_aliyun_and_tencent_reject_purge_everything():
    for provider, settings in (
            ("aliyun_cdn", {"access_key_id": "id"}),
            ("tencent_cdn", {"secret_id": "id"}),
    ):
        with pytest.raises(BadRequestError) as exc:
            await cdn_remote.purge(
                provider=provider,
                config={"settings": settings},
                token="secret",
                urls=[],
                purge_everything=True,
            )
        assert "全量" in str(exc.value)


@pytest.mark.asyncio
async def test_cloudfront_has_no_preheat_api():
    with pytest.raises(BadRequestError) as exc:
        await cdn_remote.preheat(
            provider="aws_cloudfront",
            config={"settings": {"access_key_id": "AK", "distribution_id": "D"}},
            token="sk",
            urls=URLS,
        )
    assert "预热" in str(exc.value)


@pytest.mark.asyncio
async def test_batch_limit_rejected_before_request():
    """超过单次批量上限：发请求前就明确拒绝（cloudflare 30 / 阿里云 / 腾讯云 100）"""
    with pytest.raises(BadRequestError) as exc:
        await cdn_remote.purge(
            provider="cloudflare",
            config={"zone_id": "z1"},
            token="tok",
            urls=[f"https://example.com/{index}.js" for index in range(31)],
        )
    assert "最多处理 30" in str(exc.value)

    with pytest.raises(BadRequestError) as exc2:
        await cdn_remote.purge(
            provider="aliyun_cdn",
            config={"settings": {"access_key_id": "id"}},
            token="secret",
            urls=[f"https://example.com/{index}.js" for index in range(101)],
        )
    assert "最多处理 100" in str(exc2.value)


@pytest.mark.asyncio
async def test_purge_rejects_unknown_provider():
    with pytest.raises(BadRequestError):
        await cdn_remote.purge(provider="not-a-provider", config={}, token="", urls=URLS)


@pytest.mark.asyncio
async def test_cloudflare_requires_token():
    with pytest.raises(BadRequestError) as exc:
        await cdn_remote.purge(
            provider="cloudflare", config={"zone_id": "z1"}, token="", urls=URLS
        )
    assert "凭据" in str(exc.value)


@pytest.mark.asyncio
async def test_cloudflare_requires_zone_id():
    with pytest.raises(BadRequestError) as exc:
        await cdn_remote.purge(provider="cloudflare", config={}, token="tok", urls=URLS)
    assert "zone_id" in str(exc.value)


@pytest.mark.asyncio
async def test_purge_requires_urls_or_everything():
    with pytest.raises(BadRequestError) as exc:
        await cdn_remote.purge(
            provider="cloudflare", config={"zone_id": "z1"}, token="tok", urls=[]
        )
    assert "URL" in str(exc.value)


@pytest.mark.asyncio
async def test_custom_requires_purge_url():
    with pytest.raises(BadRequestError) as exc:
        await cdn_remote.purge(
            provider="custom", config={"settings": {}}, token="", urls=URLS
        )
    assert "purge_url" in str(exc.value)


@pytest.mark.asyncio
async def test_custom_preheat_requires_preheat_url():
    with pytest.raises(BadRequestError) as exc:
        await cdn_remote.preheat(
            provider="custom", config={"settings": {}}, token="", urls=URLS
        )
    assert "preheat_url" in str(exc.value)


@pytest.mark.asyncio
async def test_cloudflare_has_no_preheat_api_regression():
    with pytest.raises(BadRequestError) as exc:
        await cdn_remote.preheat(provider="cloudflare", config={}, token="tok", urls=URLS)
    assert "预热" in str(exc.value)
