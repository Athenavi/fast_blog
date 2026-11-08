"""匿名端点的轻量限流（按 IP + 作用域）。

前台有一批**无需登录**的写入接口（埋点、同意记录、评论提交）。nginx 只在
``/api/`` 上给 30r/s 的粗粒度限制，挡不住"每个 IP 每秒 30 次"持续灌数据。
这里在应用层加一层"每分钟"配额，和 nginx 的每秒限制是互补关系。

Redis 可用时用 INCR + EXPIRE（跨 worker 共享）；降级到内存缓存时退化为
get/set（单进程内有效）。**限流器自身故障时放行**：埋点断掉不该拖垮业务。
"""

from __future__ import annotations

from typing import Callable

from fastapi import HTTPException, Request, status


async def check_ip_rate_limit(
    request: Request,
    scope: str,
    limit: int,
    window_seconds: int = 60,
) -> None:
    from shared.utils.client_ip import get_client_ip
    from src.extensions import cache as ext_cache

    key = f"rl:{scope}:{get_client_ip(request)}"
    count = 0
    try:
        client = getattr(ext_cache, "_client", None)
        if client is not None and hasattr(client, "incr"):
            count = int(client.incr(key))
            if count == 1:
                client.expire(key, window_seconds)
        else:
            count = int(ext_cache.get(key) or 0) + 1
            ext_cache.set(key, str(count), ex=window_seconds)
    except Exception:  # noqa: BLE001 - 限流器故障不阻断业务
        return

    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试",
        )


def ip_rate_limit(scope: str, *, limit: int, window_seconds: int = 60) -> Callable:
    """生成 FastAPI 依赖：``_rl=Depends(ip_rate_limit("comment.create", limit=10))``"""

    async def _dependency(request: Request) -> None:
        await check_ip_rate_limit(request, scope, limit, window_seconds)

    return _dependency
