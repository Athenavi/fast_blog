"""``python -m src.mcp`` —— 以 stdio 方式运行 MCP 服务（本地客户端接入）。

用法::

    # 1) 先在后台「API 令牌」页签一个令牌（权限按需勾选）
    # 2) 在 MCP 客户端配置里这样启动：
    FASTBLOG_MCP_TOKEN=fbk_xxxxxxxx_yyyy python -m src.mcp

HTTP 方式不需要这个入口 —— 直接 ``POST /api/v3/mcp``（见 ``src/mcp/http.py``），
鉴权走平台统一的 JWT / ``X-API-Key``。
"""

import asyncio
import sys

from src.mcp.transport import serve_stdio


def main() -> int:
    try:
        return asyncio.run(serve_stdio())
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
