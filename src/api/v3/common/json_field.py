"""JSON 文本列的读写辅助

项目里有多个模型把 JSON 存在 Text 列（``widget_instances.config``、
``webhooks.events``、``articles.tags_list`` 等），读出来可能是 ``str`` 也可能是
``dict/list``。这里统一处理，避免各模块各写一遍 try/except。
"""

import json
from typing import Any


def parse_json_field(value: Any) -> Any:
    """读：把 Text(JSON) 解析成 python 对象；解析失败原样返回（不抛错）"""
    if value is None or isinstance(value, (dict, list, int, float, bool)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return value


def dump_json_field(value: Any) -> Any:
    """写：把 dict/list 序列化成字符串；已是字符串/None 时原样返回"""
    if value is None or isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)
