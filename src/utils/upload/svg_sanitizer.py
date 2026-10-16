# -*- coding: utf-8 -*-
"""SVG 白名单清洗器（独立模块，**不依赖 python-magic** 等原生库，便于单测）。

背景：``content/media`` 对 ``image/svg+xml`` 以 ``Content-Disposition: inline`` 同源下发，
而 SVG 可以内嵌脚本与事件处理器，因此上传时必须清洗。原先的实现是正则黑名单
（枚举 ``script``/``on*``/``javascript:`` 等），可被"未列出的元素 / 实体编码 /
命名空间前缀混淆"绕过 → 存储型 XSS。

这里改为 **XML 解析 + 白名单重建**：未知元素整棵子树丢弃，属性按规则过滤，
含 ``DOCTYPE`` / ``ENTITY`` 声明的文档直接拒绝（防实体扩展攻击）。
"""

import xml.etree.ElementTree as ET

#: 允许保留的 SVG 元素（其余元素整棵子树丢弃）；按本地名比较，命名空间前缀无关。
ALLOWED_TAGS = frozenset({
    "svg", "g", "defs", "symbol", "use", "switch", "title", "desc", "metadata",
    "a", "path", "rect", "circle", "ellipse", "line", "polyline", "polygon",
    "text", "tspan", "textpath", "image",
    "lineargradient", "radialgradient", "stop", "pattern", "clippath", "mask",
    "filter", "fegaussianblur", "feoffset", "feblend", "fecolormatrix",
    "fecomposite", "feflood", "femerge", "femergenode", "femorphology",
    "fedropshadow",
})

#: ``href`` / ``src`` 允许的协议或相对路径前缀（``javascript:`` / ``data:`` 等一律拒绝）
ALLOWED_HREF_PREFIXES = ("http://", "https://", "/", "./", "../", "#")

#: ``style`` 属性中不允许出现的片段
_FORBIDDEN_STYLE_FRAGMENTS = ("javascript:", "expression(", "url(http", "url(//")

SVG_NS = "http://www.w3.org/2000/svg"


def _local_name(tag) -> str:
    """取标签/属性的本地名并小写（``{ns}foreignObject`` → ``foreignobject``）"""
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1].lower()


def sanitize_svg_bytes(data: bytes) -> bytes:
    """白名单清洗上传的 SVG，返回清洗后的字节。

    解析失败、含 ``DOCTYPE``/``ENTITY``、根元素不是 ``svg`` 时抛 ``ValueError`` /
    ``ET.ParseError``，由调用方按"拒绝该文件"处理。
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"SVG 不是合法 UTF-8：{exc}") from exc

    lowered = text.lower()
    if "<!doctype" in lowered or "<!entity" in lowered:
        raise ValueError("SVG 含 DOCTYPE/ENTITY 声明，已拒绝")

    root = ET.fromstring(text)  # 解析失败抛 ParseError

    if _local_name(root.tag) != "svg":
        raise ValueError("根元素不是 <svg>")

    def clean(elem) -> None:
        for child in list(elem):
            if _local_name(child.tag) not in ALLOWED_TAGS:
                # 整棵子树丢弃：script / foreignObject / set / animate / handler ...
                elem.remove(child)
                continue
            clean(child)
        for attr in list(elem.attrib):
            name = _local_name(attr)
            if name.startswith("on"):
                del elem.attrib[attr]
                continue
            if name in ("href", "src") or attr.endswith("}href"):
                value = str(elem.attrib[attr]).strip().lower()
                if not value.startswith(ALLOWED_HREF_PREFIXES):
                    del elem.attrib[attr]
                continue
            if name == "style":
                value = str(elem.attrib[attr]).lower()
                if any(bad in value for bad in _FORBIDDEN_STYLE_FRAGMENTS):
                    del elem.attrib[attr]

    clean(root)
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)
