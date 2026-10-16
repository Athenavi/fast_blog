"""自定义内容类型的**字段定义**与**取值**校验。

字段定义存 ``custom_post_types.fields``（JSON 数组文本），形如::

    [{"key": "price",  "type": "number",   "label": "价格", "required": true, "min": 0},
     {"key": "cover",  "type": "media",    "label": "封面"},
     {"key": "tags",   "type": "relation", "label": "标签", "target": "tag", "multiple": true}]

取值仍落既有的 ``custom_fields.field_value``（字符串列，宽 255），写入前由
:func:`validate_values` 按定义做**类型与必填校验并规范化**：

  - 不合法的输入**显式报错**（含字段 key 与原因），不静默截断、不静默丢弃；
  - 未在定义里出现的 key 也报错 —— 否则前端拼错字段名会静默丢数据。
"""

import json
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.api.v3.core.exceptions import BadRequestError

#: 支持的字段类型（首批；够覆盖绝大多数内容型需求）
FIELD_TYPES: Tuple[str, ...] = (
    "text",
    "textarea",
    "richtext",
    "number",
    "boolean",
    "select",
    "date",
    "media",
    "relation",
    "json",
)

#: 字段 key：小写字母开头，允许数字与下划线
KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,49}$")

MAX_FIELDS = 50
#: 与 ``custom_fields.field_value`` 列宽一致
MAX_VALUE_LENGTH = 255


# ---------------------------------------------------------------- 定义解析

def parse_fields(raw: Optional[str]) -> List[dict]:
    """解析定义文本；空或非法返回空列表（是否报错由调用方决定）。"""
    if not raw:
        return []
    if isinstance(raw, list):  # 容忍直接传数组
        return [item for item in raw if isinstance(item, dict)]
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def dump_fields(fields: Iterable[dict]) -> str:
    """规范化序列化（排序 key，便于比对与审计）"""
    return json.dumps(list(fields), ensure_ascii=False, sort_keys=True)


def _as_number(value: Any, key: str, bound: str) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise BadRequestError(f"字段 {key} 的 {bound} 必须是数字") from exc


def validate_field_definitions(raw: Any) -> List[dict]:
    """校验字段定义，返回**规范化副本**；不合法抛 ``BadRequestError``。"""
    if raw in (None, "", []):
        return []

    if isinstance(raw, (str, bytes)):
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError) as exc:
            raise BadRequestError("fields 不是合法 JSON（应为字段定义数组）") from exc
    else:
        parsed = raw

    if not isinstance(parsed, list):
        raise BadRequestError("fields 必须是数组")
    if len(parsed) > MAX_FIELDS:
        raise BadRequestError(f"字段数量超过上限 {MAX_FIELDS}")

    normalized: List[dict] = []
    seen: set[str] = set()
    for index, item in enumerate(parsed):
        if not isinstance(item, dict):
            raise BadRequestError(f"第 {index + 1} 个字段定义必须是对象")

        key = str(item.get("key") or "").strip()
        if not KEY_PATTERN.match(key):
            raise BadRequestError(
                f"字段 key 非法（{key or '空'}）：须小写字母开头，只含小写字母/数字/下划线"
            )
        if key in seen:
            raise BadRequestError(f"字段 key 重复：{key}")
        seen.add(key)

        ftype = str(item.get("type") or "").strip()
        if ftype not in FIELD_TYPES:
            raise BadRequestError(
                f"字段 {key} 的类型 {ftype or '空'} 不支持（可选：{'/'.join(FIELD_TYPES)}）"
            )

        spec: Dict[str, Any] = {"key": key, "type": ftype}
        label = str(item.get("label") or "").strip()
        if label:
            spec["label"] = label[:100]
        if bool(item.get("required")):
            spec["required"] = True
        if item.get("help"):
            spec["help"] = str(item["help"])[:200]

        if ftype == "select":
            options = item.get("options")
            if not isinstance(options, list) or not options:
                raise BadRequestError(f"字段 {key} 是 select，必须提供非空 options")
            spec["options"] = [str(option)[:100] for option in options]
        if ftype == "relation":
            target = str(item.get("target") or "").strip()
            if not target:
                raise BadRequestError(f"字段 {key} 是 relation，必须提供 target（如 tag/category）")
            spec["target"] = target[:50]
            if bool(item.get("multiple")):
                spec["multiple"] = True
        if ftype == "number":
            if item.get("min") is not None:
                spec["min"] = _as_number(item["min"], key, "min")
            if item.get("max") is not None:
                spec["max"] = _as_number(item["max"], key, "max")

        normalized.append(spec)

    return normalized


# ---------------------------------------------------------------- 取值校验

def _coerce(spec: dict, value: Any) -> str:
    """按字段定义把单个取值规范化成可入库的字符串。"""
    key = spec["key"]
    ftype = spec["type"]

    if ftype == "number":
        number = _as_number(value, key, "值")
        if "min" in spec and number < spec["min"]:
            raise BadRequestError(f"字段 {key} 不能小于 {spec['min']}")
        if "max" in spec and number > spec["max"]:
            raise BadRequestError(f"字段 {key} 不能大于 {spec['max']}")
        text = str(int(number)) if float(number).is_integer() else str(number)
        return text

    if ftype == "boolean":
        if isinstance(value, bool):
            return "true" if value else "false"
        text = str(value).strip().lower()
        if text in ("true", "1", "yes", "on"):
            return "true"
        if text in ("false", "0", "no", "off"):
            return "false"
        raise BadRequestError(f"字段 {key} 必须是布尔值")

    if ftype == "date":
        from datetime import date, datetime

        text = str(value).strip()
        try:
            if "T" in text or " " in text:
                datetime.fromisoformat(text.replace("Z", "+00:00"))
            else:
                date.fromisoformat(text)
        except ValueError as exc:
            raise BadRequestError(f"字段 {key} 必须是 ISO 日期（YYYY-MM-DD）") from exc
        return text

    if ftype == "select":
        text = str(value).strip()
        options = spec.get("options") or []
        if text not in options:
            raise BadRequestError(f"字段 {key} 的取值不在允许选项中：{text}")
        return text

    if ftype == "relation":
        raw_items = value if isinstance(value, (list, tuple)) else str(value).split(",")
        items = [str(item).strip() for item in raw_items if str(item).strip()]
        if not items:
            raise BadRequestError(f"字段 {key} 至少需要一个关联对象")
        if not spec.get("multiple") and len(items) > 1:
            raise BadRequestError(f"字段 {key} 只允许单个关联对象")
        for item in items:
            # 关联对象只接受数字 id 或 slug 形态，避免把任意字符串塞进来
            if not re.match(r"^[A-Za-z0-9_-]{1,64}$", item):
                raise BadRequestError(f"字段 {key} 的关联值非法：{item}")
        return ",".join(items)

    if ftype == "json":
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        try:
            json.loads(text)
        except (ValueError, TypeError) as exc:
            raise BadRequestError(f"字段 {key} 必须是合法 JSON") from exc
        return text

    # text / textarea / richtext / media
    text = str(value)
    if len(text) > MAX_VALUE_LENGTH:
        raise BadRequestError(
            f"字段 {key} 的值超过 {MAX_VALUE_LENGTH} 字符（长文本请用 richtext 并另行存储）"
        )
    return text


def validate_values(definitions: Iterable[dict], values: Dict[str, Any]) -> Dict[str, str]:
    """按定义校验并规范化全部取值，返回 ``{key: 可入库字符串}``。

    规则：必填缺失 → 报错；未定义的 key → 报错（防拼错字段名静默丢数据）；
    值为 ``None`` 或空串视为"未填"。
    """
    specs = {str(spec.get("key")): spec for spec in definitions if isinstance(spec, dict)}

    unknown = sorted(set(values) - set(specs))
    if unknown:
        raise BadRequestError(f"存在未定义的字段：{', '.join(unknown)}")

    result: Dict[str, str] = {}
    for key, spec in specs.items():
        raw = values.get(key)
        blank = raw is None or (isinstance(raw, str) and not raw.strip())
        if blank:
            if spec.get("required"):
                raise BadRequestError(f"缺少必填字段：{key}")
            continue
        result[key] = _coerce(spec, raw)
    return result
