"""content/third_party_publish（底座 / 平台适配器）

由同域多个测试文件合并（断言与注释原样保留，仅重排文件组织）。
"""

import json
import pytest
import threading
import xmlrpc.client
from fastapi import FastAPI
from http.server import BaseHTTPRequestHandler, HTTPServer
from src.api.v3 import register_v3_routes
from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.core.secret_box import decrypt_json, decrypt_secret, encrypt_json, encrypt_secret
from src.api.v3.modules.content.third_party_publish import adapters
from src.api.v3.modules.content.third_party_publish import adapters as publish_adapters
from src.api.v3.modules.content.third_party_publish.adapters import ChannelConfig, PublishPayload
from urllib.parse import parse_qsl, urlparse

# ============================================================ 来自 test_v3_publish_adapters.py（19 项）
CNBLOGS_CREDENTIALS = {
    "blog_app": "myblog",
    "username": "myblog",
    "password": "cnblogs-access-token",
}


# ================================================================ mock XML-RPC 端点
class _Recorder:
    def __init__(self) -> None:
        self.requests: list[dict] = []
        self.response_body: bytes = b""
        self.status = 200


def _handler_factory(recorder: _Recorder):
    class _Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 - http.server 约定
            length = int(self.headers.get('Content-Length') or 0)
            raw = self.rfile.read(length) if length else b''
            recorder.requests.append(
                {
                    'path': self.path,
                    'headers': {key: value for key, value in self.headers.items()},
                    'body': raw.decode('utf-8', errors='replace'),
                }
            )
            body = recorder.response_body or b''
            self.send_response(recorder.status)
            self.send_header('Content-Type', 'text/xml')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args) -> None:
            return

    return _Handler


@pytest.fixture()
def xmlrpc_endpoint():
    """本地 XML-RPC 端点：返回 ``(url, recorder)``"""
    recorder = _Recorder()
    server = HTTPServer(('127.0.0.1', 0), _handler_factory(recorder))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/metaweblog/myblog", recorder
    finally:
        server.shutdown()
        server.server_close()


def _xml_response(value) -> bytes:  # noqa: ANN001
    return xmlrpc.client.dumps((value,), encoding='utf-8').encode('utf-8')


def _fault_response(code: int, message: str) -> bytes:
    return xmlrpc.client.dumps(
        xmlrpc.client.Fault(code, message), encoding='utf-8'
    ).encode('utf-8')


def _channel(url: str, credentials: dict | None = None) -> ChannelConfig:
    return ChannelConfig(
        id=1,
        name='我的博客园',
        platform='cnblogs',
        endpoint=url,
        credentials=dict(CNBLOGS_CREDENTIALS if credentials is None else credentials),
    )


def _payload(**overrides) -> PublishPayload:  # noqa: ANN003
    data = {
        'article_id': 42,
        'title': 'FastAPI 异步实践',
        'slug': 'fastapi-async',
        'excerpt': '摘要',
        'content': '<p>正文 <b>HTML</b></p>',
        'url': 'https://example.com/articles/42',
        'author': 'athena',
        'tags': ['FastAPI', '异步'],
    }
    data.update(overrides)
    return PublishPayload(**data)


# ================================================================ 注册表
def test_cnblogs_adapter_is_registered() -> None:
    platforms = {item['platform'] for item in adapters.adapter_platforms()}
    assert 'cnblogs' in platforms
    adapter = adapters.get_adapter('cnblogs')
    assert adapter is not None
    assert adapter.display_name == '博客园'


def test_all_planned_platforms_are_registered() -> None:
    """第一批接入的平台都要在注册表里（前端下拉与 adapter_ready 都读它）"""
    platforms = {item['platform'] for item in adapters.adapter_platforms()}
    assert {'cnblogs', 'wechat_mp', 'medium', 'weibo', 'twitter'} <= platforms


def test_unknown_platform_still_fails_loudly() -> None:
    """没接入的平台（如清单里那批无公开 API 的）必须如实失败，不能有个"通用兜底"假装成功"""
    with pytest.raises(adapters.AdapterNotRegisteredError):
        adapters.require_adapter('zhihu')


# ================================================================ 自检（verify）
@pytest.mark.asyncio
async def test_verify_uses_get_users_blogs(xmlrpc_endpoint) -> None:
    url, recorder = xmlrpc_endpoint
    recorder.response_body = _xml_response(
        [{'blogid': '123', 'blogName': '雅典娜的博客', 'url': 'https://www.cnblogs.com/myblog/'}]
    )

    result = await adapters.require_adapter('cnblogs').verify(_channel(url))

    assert result.success is True
    assert '雅典娜的博客' in (result.message or '')
    sent = recorder.requests[0]
    params, _method = xmlrpc.client.loads(sent['body'])
    method_name = sent['body'].split('<methodName>')[1].split('</methodName>')[0]
    assert method_name == 'blogger.getUsersBlogs'
    # 参数顺序：(appkey, username, password)；loads 返回的是元组
    assert list(params) == ['', 'myblog', 'cnblogs-access-token']


@pytest.mark.asyncio
async def test_verify_reports_empty_blog_list_as_failure(xmlrpc_endpoint) -> None:
    url, recorder = xmlrpc_endpoint
    recorder.response_body = _xml_response([])

    result = await adapters.require_adapter('cnblogs').verify(_channel(url))

    assert result.success is False
    assert '令牌' in (result.message or '')


# ================================================================ 发布（publish）
@pytest.mark.asyncio
async def test_publish_builds_metaweblog_newpost(xmlrpc_endpoint) -> None:
    url, recorder = xmlrpc_endpoint
    recorder.response_body = _xml_response('12345678')

    result = await adapters.require_adapter('cnblogs').publish(_channel(url), _payload())

    assert result.success is True
    assert result.external_id == '12345678'
    # 博客园的文章地址规律：www.cnblogs.com/{blogApp}/p/{postid}.html
    assert result.external_url == 'https://www.cnblogs.com/myblog/p/12345678.html'

    body = recorder.requests[0]['body']
    method_name = body.split('<methodName>')[1].split('</methodName>')[0]
    assert method_name == 'metaWeblog.newPost'
    params, _method = xmlrpc.client.loads(body)
    (blog_id, username, password, struct, publish_flag) = params
    assert (blog_id, username, password) == ('', 'myblog', 'cnblogs-access-token')
    assert publish_flag is True  # 默认立即发布
    assert struct['title'] == 'FastAPI 异步实践'
    assert struct['description'] == '<p>正文 <b>HTML</b></p>'
    assert struct['mt_keywords'] == 'FastAPI,异步'
    assert '<methodCall>' in body  # 真的是 XML-RPC，不是 JSON


@pytest.mark.asyncio
async def test_publish_honours_draft_and_categories(xmlrpc_endpoint) -> None:
    url, recorder = xmlrpc_endpoint
    recorder.response_body = _xml_response('999')

    channel = _channel(url, {**CNBLOGS_CREDENTIALS, 'publish_immediately': False, 'categories': '技术,随笔'})
    result = await adapters.require_adapter('cnblogs').publish(channel, _payload(tags=[]))

    params, _method = xmlrpc.client.loads(recorder.requests[0]['body'])
    struct = params[3]
    assert params[4] is False
    assert struct['post_status'] == 'draft'
    assert struct['categories'] == ['技术', '随笔']
    assert struct['mt_keywords'] == ''
    assert result.success is True


@pytest.mark.asyncio
async def test_publish_surfaces_fault(xmlrpc_endpoint) -> None:
    """博客园返回 fault（如令牌失效）→ 抛出带 faultString 的错误，绝不返回成功"""
    url, recorder = xmlrpc_endpoint
    recorder.response_body = _fault_response(1, 'Access token is invalid')

    with pytest.raises(BadRequestError) as exc:
        await adapters.require_adapter('cnblogs').publish(_channel(url), _payload())

    assert 'Access token is invalid' in str(exc.value)


@pytest.mark.asyncio
async def test_publish_rejects_unparsable_response(xmlrpc_endpoint) -> None:
    url, recorder = xmlrpc_endpoint
    recorder.response_body = b'<html>502 Bad Gateway</html>'

    with pytest.raises(BadRequestError) as exc:
        await adapters.require_adapter('cnblogs').publish(_channel(url), _payload())

    assert 'XML-RPC' in str(exc.value)


@pytest.mark.asyncio
async def test_publish_requires_credentials(xmlrpc_endpoint) -> None:
    url, _recorder = xmlrpc_endpoint
    with pytest.raises(BadRequestError) as exc:
        await adapters.require_adapter('cnblogs').publish(
            _channel(url, {'blog_app': 'myblog'}), _payload()
        )
    assert 'username' in str(exc.value)

    with pytest.raises(BadRequestError) as exc2:
        await adapters.require_adapter('cnblogs').publish(
            _channel(url, {'username': 'myblog'}), _payload()
        )
    assert 'password' in str(exc2.value)


# ================================================================ JSON mock（微信 / Medium / 微博 / X）
class _JsonRecorder:
    def __init__(self) -> None:
        self.requests: list[dict] = []
        self.routes: dict[str, dict] = {}
        self.raw_routes: dict[str, bytes] = {}
        self.status = 200


def _json_handler_factory(recorder: _JsonRecorder):
    class _Handler(BaseHTTPRequestHandler):
        def _record(self) -> None:
            length = int(self.headers.get('Content-Length') or 0)
            body = self.rfile.read(length) if length else b''
            recorder.requests.append(
                {
                    'method': self.command,
                    'path': self.path,
                    'query': dict(parse_qsl(urlparse(self.path).query)),
                    'headers': {key: value for key, value in self.headers.items()},
                    'body': body,
                }
            )

        def _respond(self) -> None:
            path = self.path.split('?')[0]
            if path in recorder.raw_routes:
                body = recorder.raw_routes[path]
                content_type = 'image/jpeg'
                status = 200
            elif path in recorder.routes:
                body = json.dumps(recorder.routes[path], ensure_ascii=False).encode('utf-8')
                content_type = 'application/json'
                status = recorder.status
            else:
                body = json.dumps({'error': f'no mock route for {path}'}).encode()
                content_type = 'application/json'
                status = 404
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - http.server 约定
            self._record()
            self._respond()

        def do_POST(self) -> None:  # noqa: N802
            self._record()
            self._respond()

        def log_message(self, *args) -> None:
            return

    return _Handler


@pytest.fixture()
def json_endpoint():
    """本地 JSON 端点（按路径路由）：返回 ``(base_url, recorder)``"""
    recorder = _JsonRecorder()
    server = HTTPServer(('127.0.0.1', 0), _json_handler_factory(recorder))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f'http://127.0.0.1:{server.server_address[1]}', recorder
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture(autouse=True)
def _clear_wechat_token_cache():
    """access_token 是进程内缓存的，逐用例清掉才不会互相干扰"""
    from src.api.v3.modules.content.third_party_publish.builtin import wechat_mp

    wechat_mp._TOKEN_CACHE.clear()
    yield
    wechat_mp._TOKEN_CACHE.clear()


def _json_channel(url: str, platform: str, credentials: dict) -> ChannelConfig:
    return ChannelConfig(id=2, name='测试渠道', platform=platform, endpoint=url, credentials=credentials)


def _json_body(record: dict) -> dict:
    return json.loads(record['body'].decode('utf-8') or '{}')


# ---------------------------------------------------------------- 微信公众号
@pytest.mark.asyncio
async def test_wechat_publish_creates_draft(json_endpoint) -> None:
    url, recorder = json_endpoint
    recorder.routes = {
        '/cgi-bin/token': {'access_token': 'wx-token', 'expires_in': 7200},
        '/cgi-bin/draft/add': {'media_id': 'draft-media-1'},
    }
    channel = _json_channel(
        url,
        'wechat_mp',
        {'appid': 'wx-app', 'appsecret': 'wx-secret', 'thumb_media_id': 'permanent-thumb'},
    )

    result = await adapters.require_adapter('wechat_mp').publish(channel, _payload())

    assert result.success is True
    assert result.external_id == 'draft-media-1'
    assert [r['path'].split('?')[0] for r in recorder.requests] == [
        '/cgi-bin/token',
        '/cgi-bin/draft/add',
    ]
    token_call = recorder.requests[0]
    assert token_call['query']['grant_type'] == 'client_credential'
    assert token_call['query']['appid'] == 'wx-app'
    draft_call = recorder.requests[1]
    assert draft_call['query']['access_token'] == 'wx-token'
    article = _json_body(draft_call)['articles'][0]
    assert article['title'] == 'FastAPI 异步实践'
    assert article['thumb_media_id'] == 'permanent-thumb'
    assert article['content'].startswith('<p>')
    assert article['digest'] == '摘要'
    assert article['content_source_url'] == 'https://example.com/articles/42'


@pytest.mark.asyncio
async def test_wechat_publish_uploads_cover_then_submits(json_endpoint) -> None:
    """没有 thumb_media_id 时：下载封面 → 上传永久素材 → 建草稿 → 提交发布"""
    url, recorder = json_endpoint
    recorder.raw_routes = {'/cover.jpg': b'\xff\xd8\xff\xe0fake-jpeg'}
    recorder.routes = {
        '/cgi-bin/token': {'access_token': 'wx-token', 'expires_in': 7200},
        '/cgi-bin/material/add_material': {'media_id': 'uploaded-thumb', 'url': 'http://x'},
        '/cgi-bin/draft/add': {'media_id': 'draft-2'},
        '/cgi-bin/freepublish/submit': {'publish_id': 'pub-9'},
    }
    channel = _json_channel(
        url,
        'wechat_mp',
        {
            'appid': 'wx-app2',
            'appsecret': 's',
            'cover_image_url': f'{url}/cover.jpg',
            'publish_immediately': True,
        },
    )

    result = await adapters.require_adapter('wechat_mp').publish(channel, _payload())

    assert result.external_id == 'pub-9'
    paths = [r['path'].split('?')[0] for r in recorder.requests]
    assert paths == [
        '/cgi-bin/token',
        '/cover.jpg',
        '/cgi-bin/material/add_material',
        '/cgi-bin/draft/add',
        '/cgi-bin/freepublish/submit',
    ]
    upload = recorder.requests[2]
    assert upload['query']['type'] == 'image'
    assert upload['query']['access_token'] == 'wx-token'
    assert b'fake-jpeg' in upload['body']  # 真的是 multipart 上传的字节
    assert _json_body(recorder.requests[3])['articles'][0]['thumb_media_id'] == 'uploaded-thumb'
    assert _json_body(recorder.requests[4]) == {'media_id': 'draft-2'}


@pytest.mark.asyncio
async def test_wechat_requires_cover_and_surfaces_errcode(json_endpoint) -> None:
    url, recorder = json_endpoint
    recorder.routes = {'/cgi-bin/token': {'access_token': 't', 'expires_in': 7200}}

    no_cover = await adapters.require_adapter('wechat_mp').publish(
        _json_channel(url, 'wechat_mp', {'appid': 'wx-a', 'appsecret': 'b'}), _payload()
    )
    assert no_cover.success is False
    assert '封面' in (no_cover.message or '')

    # 微信的 errcode/errmsg（如 IP 白名单）必须原样带出来
    recorder.routes['/cgi-bin/draft/add'] = {
        'errcode': 40164,
        'errmsg': 'invalid ip 1.2.3.4, not in whitelist',
    }
    with pytest.raises(BadRequestError) as exc:
        await adapters.require_adapter('wechat_mp').publish(
            _json_channel(
                url, 'wechat_mp', {'appid': 'wx-b', 'appsecret': 'b', 'thumb_media_id': 't'}
            ),
            _payload(),
        )
    assert '40164' in str(exc.value)
    assert 'whitelist' in str(exc.value)


# ---------------------------------------------------------------- Medium
@pytest.mark.asyncio
async def test_medium_publish_creates_post(json_endpoint) -> None:
    url, recorder = json_endpoint
    recorder.routes = {
        '/v1/me': {'data': {'id': 'author-1', 'username': 'athena', 'name': '雅典娜'}},
        '/v1/users/author-1/posts': {
            'data': {'id': 'post-7', 'url': 'https://medium.com/@athena/x'}
        },
    }
    channel = _json_channel(
        f'{url}/v1', 'medium', {'integration_token': 'medium-token', 'publish_status': 'public'}
    )

    result = await adapters.require_adapter('medium').publish(channel, _payload())

    assert result.external_id == 'post-7'
    assert result.external_url == 'https://medium.com/@athena/x'
    assert recorder.requests[0]['path'].split('?')[0] == '/v1/me'
    sent = recorder.requests[1]
    assert sent['headers'].get('Authorization') == 'Bearer medium-token'
    body = _json_body(sent)
    assert body['title'] == 'FastAPI 异步实践'
    assert body['contentFormat'] == 'html'
    assert body['publishStatus'] == 'public'
    assert body['canonicalUrl'] == 'https://example.com/articles/42'
    assert body['tags'] == ['FastAPI', '异步']


@pytest.mark.asyncio
async def test_medium_verify_and_auth_failure(json_endpoint) -> None:
    url, recorder = json_endpoint
    recorder.routes = {'/v1/me': {'data': {'id': 'author-1', 'username': 'athena'}}}
    channel = _json_channel(f'{url}/v1', 'medium', {'integration_token': 't'})

    verified = await adapters.require_adapter('medium').verify(channel)
    assert verified.success is True

    recorder.status = 401
    recorder.routes['/v1/me'] = {'errors': [{'message': 'Token was invalid'}]}
    with pytest.raises(BadRequestError) as exc:
        await adapters.require_adapter('medium').verify(channel)
    assert '401' in str(exc.value)


# ---------------------------------------------------------------- 微博
@pytest.mark.asyncio
async def test_weibo_verify_and_share(json_endpoint) -> None:
    url, recorder = json_endpoint
    recorder.routes = {
        '/2/account/get_uid.json': {'uid': 123456},
        '/2/statuses/share.json': {
            'idstr': '5000',
            'user': {'id': 123456, 'screen_name': '雅典娜'},
        },
    }
    channel = _json_channel(f'{url}/2', 'weibo', {'access_token': 'weibo-token'})

    verified = await adapters.require_adapter('weibo').verify(channel)
    assert verified.success is True
    assert '123456' in (verified.message or '')

    result = await adapters.require_adapter('weibo').publish(channel, _payload())

    assert result.external_id == '5000'
    assert result.external_url == 'https://weibo.com/123456/5000'
    form = dict(parse_qsl(recorder.requests[1]['body'].decode('utf-8')))
    assert form['access_token'] == 'weibo-token'
    assert 'https://example.com/articles/42' in form['status']
    assert 'FastAPI 异步实践' in form['status']


@pytest.mark.asyncio
async def test_weibo_requires_link(json_endpoint) -> None:
    url, _recorder = json_endpoint
    result = await adapters.require_adapter('weibo').publish(
        _json_channel(f'{url}/2', 'weibo', {'access_token': 't'}), _payload(url=None)
    )
    assert result.success is False
    assert '链接' in (result.message or '')


# ---------------------------------------------------------------- X / Twitter
@pytest.mark.asyncio
async def test_twitter_publish_keeps_link_within_limit(json_endpoint) -> None:
    url, recorder = json_endpoint
    recorder.routes = {'/2/tweets': {'data': {'id': '175000', 'text': 'ok'}}}
    channel = _json_channel(f'{url}/2', 'twitter', {'access_token': 'x-token', 'username': 'athena'})

    result = await adapters.require_adapter('twitter').publish(
        channel, _payload(title='很长的标题' * 80)
    )

    assert result.external_id == '175000'
    assert result.external_url == 'https://x.com/athena/status/175000'
    body = _json_body(recorder.requests[0])
    assert len(body['text']) <= 280
    assert body['text'].endswith('https://example.com/articles/42')  # 截断时链接不能丢


@pytest.mark.asyncio
async def test_twitter_verify_and_error(json_endpoint) -> None:
    url, recorder = json_endpoint
    recorder.routes = {'/2/users/me': {'data': {'id': '9', 'username': 'athena'}}}
    channel = _json_channel(f'{url}/2', 'twitter', {'access_token': 'x-token'})

    verified = await adapters.require_adapter('twitter').verify(channel)
    assert verified.success is True
    assert '@athena' in (verified.message or '')

    recorder.status = 403
    recorder.routes['/2/tweets'] = {'detail': 'You are not allowed to create a Tweet with this access token.'}
    with pytest.raises(BadRequestError) as exc:
        await adapters.require_adapter('twitter').publish(channel, _payload())
    assert '403' in str(exc.value)


# ============================================================ 来自 test_v3_third_party_publish.py（6 项）
BASE = "/api/v3/content/third-party-publish"

EXPECTED_OPERATIONS = {
    ("GET", f"{BASE}/platform"),
    ("GET", f"{BASE}/channel"),
    ("POST", f"{BASE}/channel"),
    ("GET", f"{BASE}/channel/{{channel_id}}"),
    ("PUT", f"{BASE}/channel/{{channel_id}}"),
    ("DELETE", f"{BASE}/channel/{{channel_id}}"),
    ("POST", f"{BASE}/channel/{{channel_id}}/verify"),
    ("GET", f"{BASE}/task"),
    ("POST", f"{BASE}/task"),
    ("GET", f"{BASE}/task/{{task_id}}"),
    ("DELETE", f"{BASE}/task/{{task_id}}"),
    ("POST", f"{BASE}/task/{{task_id}}/retry"),
    ("GET", f"{BASE}/task/{{task_id}}/log"),
}

#: 只读端点（匿名访问必须 401）
AUTH_GET_PATHS = (
    f"{BASE}/platform",
    f"{BASE}/channel",
    f"{BASE}/channel/1",
    f"{BASE}/task",
    f"{BASE}/task/1",
    f"{BASE}/task/1/log",
)

#: 写端点（匿名访问必须 401）
AUTH_WRITE_CALLS = (
    ("POST", f"{BASE}/channel", {"name": "x", "platform": "y"}),
    ("PUT", f"{BASE}/channel/1", {"name": "x"}),
    ("DELETE", f"{BASE}/channel/1", None),
    ("POST", f"{BASE}/channel/1/verify", None),
    ("POST", f"{BASE}/task", {"article_id": 1, "channel_id": 1}),
    ("DELETE", f"{BASE}/task/1", None),
    ("POST", f"{BASE}/task/1/retry", None),
)


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ---------------------------------------------------------------- 适配器注册表
def test_unregistered_platform_fails_loudly():
    """未接入的平台必须抛 AdapterNotRegisteredError（**不能静默返回成功**）"""
    with pytest.raises(publish_adapters.AdapterNotRegisteredError):
        publish_adapters.require_adapter("definitely_not_implemented")


def test_adapter_platforms_are_real_registrations_only():
    """平台清单只来自真实注册（不伪造）：每项都能取到适配器，未接入的仍是 None"""
    listed = publish_adapters.adapter_platforms()
    assert listed, "builtin/ 包应已注册内置平台适配器"
    for item in listed:
        adapter = publish_adapters.get_adapter(item["platform"])
        assert adapter is not None
        assert item["display_name"] == adapter.display_name

    # 清单里没有公开 API、刻意不接的平台仍然是 None —— 不伪造"可用"
    assert publish_adapters.get_adapter("zhihu") is None
    assert publish_adapters.get_adapter("csdn") is None


def test_register_adapter_rejects_duplicate():
    class _Stub:
        platform = "unit_test_platform"
        display_name = "单元测试平台"

        async def verify(self, channel):  # pragma: no cover - 注册表测试用不到
            raise AssertionError("不应被调用")

        async def publish(self, channel, payload):  # pragma: no cover
            raise AssertionError("不应被调用")

    stub = _Stub()
    publish_adapters.register_adapter(stub)
    try:
        assert publish_adapters.get_adapter("unit_test_platform") is stub
        listed = {item["platform"] for item in publish_adapters.adapter_platforms()}
        assert "unit_test_platform" in listed
        with pytest.raises(ValueError):
            publish_adapters.register_adapter(_Stub())
    finally:
        publish_adapters.ADAPTERS.pop("unit_test_platform", None)


# ---------------------------------------------------------------- 凭据加密
def test_secret_roundtrip():
    token = encrypt_secret("s3cret")
    assert token and token != "s3cret"
    assert decrypt_secret(token) == "s3cret"


def test_secret_json_roundtrip_and_empty():
    blob = encrypt_json({"app_id": "a", "app_secret": "b"})
    assert decrypt_json(blob) == {"app_id": "a", "app_secret": "b"}
    assert encrypt_json({}) == ""
    assert decrypt_json("") == {}


def test_secret_rejects_broken_ciphertext():
    with pytest.raises(ValueError):
        decrypt_secret("not-base64-@@@")
