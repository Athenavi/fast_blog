"""测试：GDPR / PCI 合规检查与文档生成

不需要数据库：

  - ``markdown_to_html`` / ``_inline`` 是纯函数
  - 新增端点注册与鉴权分流（``POST /consent`` 对访客开放，合规端点需 ``gdpr:view``）

真实检查（gdpr_consents / users / payment_* 聚合）与文档内容走运行时验证。
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v3 import register_v3_routes
from src.api.v3.modules.system.gdpr.compliance_service import _inline, markdown_to_html

CONSENT_POST = "/api/v3/system/gdpr/consent"
CHECK_PATH = "/api/v3/system/gdpr/compliance/check"
POLICY_PATH = "/api/v3/system/gdpr/compliance/privacy-policy"
COOKIE_PATH = "/api/v3/system/gdpr/compliance/cookie-consent"


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


# ------------------------------------------------------------------ Markdown → HTML
def test_markdown_to_html_headings_paragraphs_lists():
    html = markdown_to_html("# 标题\n\n正文一段\n\n- 项目一\n- 项目二\n")

    assert "<h1>标题</h1>" in html
    assert "<p>正文一段</p>" in html
    assert "<ul>" in html and html.count("<li>") == 2


def test_markdown_to_html_closes_list_before_next_block():
    html = markdown_to_html("- a\n\n## 小节")

    assert html.index("</ul>") < html.index("<h2>小节</h2>")


def test_inline_bold_is_converted():
    assert _inline("这是**重点**内容") == "这是<strong>重点</strong>内容"


def test_inline_leaves_odd_markers_untouched():
    assert _inline("单个 ** 星号") == "单个 ** 星号"


# ------------------------------------------------------------------ 端点


def test_consent_post_is_open_to_visitors():
    """Cookie 同意横幅首访即出现，因此上报端点不要求登录（空体应 422 而非 401）"""
    response = TestClient(_app()).post(CONSENT_POST, json={})

    assert response.status_code == 422


@pytest.mark.parametrize("payload", [{"granted": "maybe"}, {"granted": True, "details": "x" * 2001}])
def test_consent_post_validates_payload(payload):
    assert TestClient(_app()).post(CONSENT_POST, json=payload).status_code == 422
