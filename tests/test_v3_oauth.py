"""_pending_test_oauth.py —— 待迁入 ``tests/`` 的**纯函数**单测

本任务的环境**禁止写 ``tests/`` 目录、禁止执行 shell**，因此把 OAuth 模块的纯函数单测临时
放在模块目录内（文件名以下划线开头，不会被当作业务模块导入）。恢复后应移动到
``tests/api/v3/system/test_oauth.py``（目录内约定路径：``tests/test_v3_oauth.py``）。

只覆盖**不依赖 DB / 网络 / FastAPI / 时钟真值**的纯函数（时间与密钥都以参数注入）::

  - ``get_provider`` / ``require_provider``  提供方元数据
  - ``build_authorize_url``                  授权 URL（scope/state/PKCE/微信 appid）
  - ``code_challenge_s256`` / ``generate_code_verifier``  PKCE（含 RFC 7636 附录 B 向量）
  - ``generate_state`` / ``verify_state``    state 生成与校验（签名 / 过期 / 提供方）
  - ``build_token_request``                  token 交换请求体（微信/QQ/PKCE 分支）
  - ``normalize_user_info``                  各提供方用户信息标准化
  - ``parse_providers_config`` / ``provider_credentials``  配置解析与"未配置"分支
  - ``PROVIDERS`` / ``PKCE_PROVIDERS``       常量一致性

运行（在仓库根目录，确保可 ``import src.*``）::

    python -m pytest src/api/v3/modules/system/oauth/_pending_test_oauth.py -q

**本文件尚未运行**：本任务执行环境不允许跑 pytest，故断言均来自逐行读过的实现，仅静态编写。
"""

from urllib.parse import parse_qs, urlsplit

import pytest

from src.api.v3.core.exceptions import BadRequestError
from src.api.v3.modules.system.oauth.service import (
    PKCE_PROVIDERS,
    PROVIDERS,
    build_authorize_url,
    build_token_request,
    code_challenge_s256,
    generate_code_verifier,
    generate_state,
    get_provider,
    normalize_user_info,
    parse_providers_config,
    provider_credentials,
    require_provider,
    verify_state,
)

SECRET = "unit-test-secret"


# --------------------------------------------------------------------- 提供方元数据
def test_providers_metadata_complete():
    assert set(PROVIDERS) == {"github", "google", "wechat", "qq", "weibo"}
    for key, meta in PROVIDERS.items():
        assert meta["name"] and meta["icon"]
        assert meta["authorize_url"].startswith("https://")
        assert meta["token_url"].startswith("https://")
        assert meta["user_info_url"].startswith("https://")
        assert meta["scope"]


def test_pkce_providers_subset_of_providers():
    assert PKCE_PROVIDERS == {"github", "google"}
    assert PKCE_PROVIDERS <= set(PROVIDERS)


def test_get_provider_case_and_whitespace_insensitive():
    assert get_provider(" GitHub ") is not None
    assert get_provider("github")["name"] == "GitHub"
    assert get_provider("nope") is None


def test_require_provider_rejects_unknown():
    with pytest.raises(BadRequestError):
        require_provider("nope")


# ---------------------------------------------------------------------- 授权 URL
def test_build_authorize_url_github_basic():
    url = build_authorize_url("github", "cid", "https://app/cb", "STATE")
    parts = urlsplit(url)
    assert f"{parts.scheme}://{parts.netloc}{parts.path}" == PROVIDERS["github"]["authorize_url"]
    query = parse_qs(parts.query)
    assert query["client_id"] == ["cid"]
    assert query["redirect_uri"] == ["https://app/cb"]
    assert query["response_type"] == ["code"]
    assert query["scope"] == [PROVIDERS["github"]["scope"]]
    assert query["state"] == ["STATE"]
    assert "code_challenge" not in query


def test_build_authorize_url_with_pkce_challenge():
    url = build_authorize_url("google", "cid", "https://app/cb", "STATE", code_challenge="CH")
    query = parse_qs(urlsplit(url).query)
    assert query["code_challenge"] == ["CH"]
    assert query["code_challenge_method"] == ["S256"]


def test_build_authorize_url_wechat_uses_appid_and_fragment():
    url = build_authorize_url("wechat", "WXID", "https://app/cb", "STATE")
    parts = urlsplit(url)
    assert parts.fragment == "wechat_redirect"
    query = parse_qs(parts.query)
    assert query["appid"] == ["WXID"]
    assert "client_id" not in query


def test_build_authorize_url_pkce_ignored_for_non_pkce_provider():
    # 微信不在 PKCE_PROVIDERS 内，即便传入 challenge 也不附加
    url = build_authorize_url("wechat", "WXID", "https://app/cb", "STATE", code_challenge="CH")
    assert "code_challenge" not in parse_qs(urlsplit(url).query)


# ------------------------------------------------------------------------- PKCE
def test_code_challenge_s256_rfc7636_vector():
    # RFC 7636 附录 B 的官方测试向量
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    assert code_challenge_s256(verifier) == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def test_generate_code_verifier_length_and_charset():
    verifier = generate_code_verifier()
    assert 43 <= len(verifier) <= 128
    assert verifier != generate_code_verifier()  # 每次随机，不应重复
    assert all(c.isalnum() or c in "-_" for c in verifier)
    assert ":" not in verifier  # 不能与 state 的分隔符冲突


def test_generate_code_verifier_clamps_length():
    assert len(generate_code_verifier(10)) == 43  # 低于下限被抬到 43
    assert len(generate_code_verifier(999)) == 128  # 高于上限被压到 128


# ------------------------------------------------------------------------- state
def test_state_roundtrip_valid():
    state = generate_state("github", SECRET, now=1000.0)
    assert verify_state(state, "github", SECRET, now=1000.0) is True
    # 恰好到期仍有效
    assert verify_state(state, "github", SECRET, ttl_seconds=600, now=1600.0) is True
    # 超过有效期失效
    assert verify_state(state, "github", SECRET, ttl_seconds=600, now=1601.0) is False


def test_state_rejects_wrong_provider_and_secret_and_tamper():
    state = generate_state("github", SECRET, now=1000.0)
    assert verify_state(state, "google", SECRET, now=1000.0) is False
    assert verify_state(state, "github", "other-secret", now=1000.0) is False
    tampered = state[:-1] + ("A" if state[-1] != "A" else "B")
    assert verify_state(tampered, "github", SECRET, now=1000.0) is False


def test_state_rejects_bad_structure_and_future_issue():
    assert verify_state("", "github", SECRET) is False
    assert verify_state("a:b:c", "github", SECRET) is False  # 字段数不对
    # issued 明显晚于 current（超时钟容忍）→ 拒绝
    state = generate_state("github", SECRET, now=3000.0)
    assert verify_state(state, "github", SECRET, now=1000.0) is False


# ------------------------------------------------------------------ token 请求体
def test_build_token_request_github():
    data = build_token_request("github", "CODE", "cid", "secret", "https://app/cb")
    assert data["grant_type"] == "authorization_code"
    assert data["code"] == "CODE"
    assert data["client_id"] == "cid"
    assert data["client_secret"] == "secret"
    assert data["redirect_uri"] == "https://app/cb"
    assert "code_verifier" not in data


def test_build_token_request_github_with_pkce():
    data = build_token_request(
        "github", "CODE", "cid", "secret", "https://app/cb", code_verifier="VER"
    )
    assert data["code_verifier"] == "VER"


def test_build_token_request_wechat_uses_appid_secret_no_redirect():
    data = build_token_request("wechat", "CODE", "WXID", "WXSECRET", "https://app/cb")
    assert data["appid"] == "WXID"
    assert data["secret"] == "WXSECRET"
    assert "client_id" not in data
    assert "client_secret" not in data
    assert "redirect_uri" not in data


def test_build_token_request_qq_adds_json_fmt():
    data = build_token_request("qq", "CODE", "cid", "secret", "https://app/cb")
    assert data["fmt"] == "json"
    assert data["client_id"] == "cid"


def test_build_token_request_rejects_unknown_provider():
    with pytest.raises(BadRequestError):
        build_token_request("nope", "CODE", "cid", "secret", "https://app/cb")


# ---------------------------------------------------------------- 用户信息标准化
def test_normalize_github():
    info = normalize_user_info(
        "github",
        {"id": 7, "login": "octo", "email": "o@x.com", "name": None, "avatar_url": "av", "html_url": "u"},
    )
    assert info == {
        "provider": "github",
        "provider_id": "7",
        "username": "octo",
        "email": "o@x.com",
        "name": "octo",  # name 缺省回退 login
        "avatar": "av",
        "profile_url": "u",
    }


def test_normalize_google():
    info = normalize_user_info("google", {"sub": "s1", "email": "g@x.com", "name": "G", "picture": "p"})
    assert info["provider_id"] == "s1"
    assert info["username"] == "g@x.com"
    assert info["profile_url"] is None


def test_normalize_wechat_prefers_unionid_and_no_email():
    info = normalize_user_info("wechat", {"unionid": "U", "openid": "O", "nickname": "微", "headimgurl": "h"})
    assert info["provider_id"] == "U"
    assert info["email"] is None
    assert info["username"] == "微"


def test_normalize_wechat_falls_back_to_openid():
    info = normalize_user_info("wechat", {"openid": "O", "nickname": "微"})
    assert info["provider_id"] == "O"


def test_normalize_qq_and_weibo():
    qq = normalize_user_info("qq", {"openid": "OO", "nickname": "Q", "figureurl_qq_2": "f"})
    assert qq["provider_id"] == "OO"
    assert qq["email"] is None

    wb = normalize_user_info("weibo", {"id": 42, "screen_name": "W", "email": "w@x.com", "profile_url": "wpath"})
    assert wb["provider_id"] == "42"
    assert wb["profile_url"] == "https://weibo.com/wpath"


def test_normalize_unknown_provider_passthrough():
    raw = {"a": 1}
    assert normalize_user_info("nope", raw) == raw


# --------------------------------------------------------------- 配置解析 / 未配置
def test_parse_providers_config():
    assert parse_providers_config(None) == {}
    assert parse_providers_config("") == {}
    assert parse_providers_config("{bad json") == {}
    assert parse_providers_config("[1,2]") == {}  # 非对象
    assert parse_providers_config('{"github": {"client_id": "x"}}') == {"github": {"client_id": "x"}}


def test_provider_credentials_present():
    config = {
        "github": {"client_id": "cid", "client_secret": "sec", "redirect_uri": "https://app/cb"}
    }
    creds = provider_credentials(config, "github")
    assert creds == {"client_id": "cid", "client_secret": "sec", "redirect_uri": "https://app/cb"}


def test_provider_credentials_missing_is_none():
    assert provider_credentials({}, "github") is None
    assert provider_credentials({"github": {}}, "github") is None
    assert provider_credentials({"github": {"client_id": "cid"}}, "github") is None  # 缺 secret
    assert provider_credentials({"github": {"client_secret": "sec"}}, "github") is None  # 缺 id
    assert provider_credentials("nope", "github") is None  # 非字典


def test_provider_credentials_redirect_uri_optional():
    creds = provider_credentials({"google": {"client_id": "c", "client_secret": "s"}}, "google")
    assert creds is not None
    assert creds["redirect_uri"] == ""
