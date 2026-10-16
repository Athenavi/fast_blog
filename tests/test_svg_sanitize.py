# -*- coding: utf-8 -*-
"""SVG 上传清洗（白名单）回归测试。

背景：``content/media`` 对 ``image/svg+xml`` 以 ``Content-Disposition: inline`` 同源下发，
原先的正则黑名单可被"未列出的元素 / 实体编码 / 命名空间混淆"绕过 → 存储型 XSS。
现改为 XML 白名单清洗：``src/utils/upload/public_upload.py::sanitize_svg_bytes``。
"""
import pytest

from src.utils.upload.svg_sanitizer import sanitize_svg_bytes

SVG_NS = "http://www.w3.org/2000/svg"


def _svg(body: str) -> bytes:
    return f'<svg xmlns="{SVG_NS}">{body}</svg>'.encode("utf-8")


class TestSanitizeSvgKeepsSafeContent:
    def test_keeps_basic_shapes(self):
        out = sanitize_svg_bytes(_svg('<rect width="10" height="10" fill="#fff"/><path d="M0 0 L5 5"/>'))
        assert b"rect" in out
        assert b"path" in out

    def test_keeps_gradients_and_text(self):
        out = sanitize_svg_bytes(
            _svg('<defs><linearGradient id="g"><stop offset="0" stop-color="#000"/></linearGradient>'
                 '</defs><text x="1" y="2">hi</text>')
        )
        assert b"linearGradient" in out
        assert b"stop" in out
        assert b"text" in out


class TestSanitizeSvgRemovesUnsafeContent:
    def test_drops_script_subtree(self):
        out = sanitize_svg_bytes(_svg('<script>alert(1)</script><rect width="1" height="1"/>'))
        assert b"script" not in out.lower()
        assert b"alert" not in out
        assert b"rect" in out

    def test_drops_foreign_object(self):
        out = sanitize_svg_bytes(
            _svg('<foreignObject><body xmlns="http://www.w3.org/1999/xhtml">x</body></foreignObject>'
                 '<rect width="1" height="1"/>')
        )
        assert b"foreignobject" not in out.lower()
        assert b"<body" not in out

    def test_drops_elements_not_in_whitelist(self):
        # animate / set / handler 等未列入白名单的元素整棵丢弃（正则黑名单时代靠枚举，易漏）
        out = sanitize_svg_bytes(_svg('<set attributeName="x" to="1"/><animate dur="1s"/>'))
        assert b"<set" not in out
        assert b"animate" not in out

    def test_strips_event_handler_attributes(self):
        out = sanitize_svg_bytes(_svg('<rect onload="alert(1)" onmouseover="alert(2)" width="1" height="1"/>'))
        assert b"onload" not in out
        assert b"onmouseover" not in out
        assert b"rect" in out

    def test_strips_javascript_href(self):
        out = sanitize_svg_bytes(_svg('<a href="javascript:alert(1)"><text>x</text></a>'))
        assert b"javascript:" not in out

    def test_strips_data_uri_href(self):
        out = sanitize_svg_bytes(_svg('<image href="data:text/html;base64,PHNjcmlwdD4="/>'))
        assert b"data:" not in out

    def test_neutralises_entity_encoded_javascript(self):
        # XML 解析会把 &#106;avascript: 还原成 javascript:，随后被协议白名单丢弃
        out = sanitize_svg_bytes(_svg('<a href="&#106;avascript:alert(1)"><text>x</text></a>'))
        assert b"javascript:" not in out

    def test_strips_style_with_javascript_url(self):
        out = sanitize_svg_bytes(_svg('<rect style="background:url(javascript:alert(1))" width="1" height="1"/>'))
        assert b"javascript:" not in out


class TestSanitizeSvgRejects:
    def test_rejects_doctype_with_entity(self):
        with pytest.raises(ValueError):
            sanitize_svg_bytes(
                b'<?xml version="1.0"?>'
                b'<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
                b'<svg xmlns="' + SVG_NS.encode() + b'"><text>&xxe;</text></svg>'
            )

    def test_rejects_non_svg_root(self):
        with pytest.raises(ValueError):
            sanitize_svg_bytes(b"<html><body>x</body></html>")

    def test_rejects_malformed_xml(self):
        with pytest.raises(Exception):
            sanitize_svg_bytes(b"<svg><rect")
