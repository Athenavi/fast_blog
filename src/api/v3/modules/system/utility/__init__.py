"""system/utility：系统工具集（定义展开 / 命令解析 / Markdown 导出）

把 4 个"零散件"接线为 v3 只读 HTTP 能力（真实实现，非占位 / 非 mock）：

::

    GET  /api/v3/system/utility/nlp/intents            NLP 解析能力目录（公开）
    POST /api/v3/system/utility/nlp/parse              解析自然语言命令（公开）
    GET  /api/v3/system/utility/user/vip-status        当前用户 VIP 状态（仅认证）
    GET  /api/v3/system/utility/block-pattern/{id}     展开区块模式定义（需 block_pattern:view）
    GET  /api/v3/system/utility/article/{id}/markdown  导出文章 Markdown 附件（需 article:view）

数据源与复用点（**直接复用源模块，不复制逻辑**）：

- ``shared/defs/block_pattern_defs.py``  → ``to_pattern_dict`` 展开区块模式定义；
- ``shared/defs/user_defs.py``           → ``is_vip`` 判定用户 VIP；
- ``shared/services/nlp/nlp_command_parser.py`` → ``nlp_parser.parse_command`` 命令解析；
- ``src/utils/http/generate_response.py`` → ``send_chunk_md`` 流式导出 Markdown 附件。

.. note::
   本模块需要在 ``src/api/v3/__init__.py`` 的 ``DOMAIN_MODULES["/system"]`` 中登记
   ``"utility"`` 才会被路由加载；本任务受约束不得改动该文件，登记由外部完成。
"""

from src.api.v3.modules.system.utility.service import utility_service

__all__ = ["utility_service"]
