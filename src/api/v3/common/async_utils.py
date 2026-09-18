"""异步兼容小工具

项目里有些既有 service（如 ``PluginManager``）在不同版本中把方法实现成 sync 或 async，
调用方无法从签名可靠判断。``maybe_await`` 让调用方写一次代码即可兼容两种形态，
避免"忘记 await 拿到 coroutine"这类隐性错误（v2 的 widgets 端点踩过）。
"""

import inspect
from typing import Any, TypeVar

T = TypeVar("T")


async def maybe_await(value: Any) -> Any:
    """``value`` 是 awaitable 就 await，否则原样返回"""
    if inspect.isawaitable(value):
        return await value
    return value
