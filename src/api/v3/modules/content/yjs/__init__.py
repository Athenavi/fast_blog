"""content/yjs：协同编辑文档的**持久化面与访问面**（快照落库 / 版本历史 / 回滚 / 协作者 / 房间视图）。

落点：正文与版本快照落真表 ``article_content`` + ``article_revisions``，协作者来自真表
``collaboration_invites``（``target_type='article'``）；实时通道（真 CRDT 房间 + Redis 跨进程
广播）由同域 ``content/collaboration`` 的 ``/collaboration/yjs/ws/{document_id}`` 提供，
本模块**不实现第二套房间注册表**（避免同一文档的房间状态分裂），只做同一注册表的只读快照视图。
"""

from src.api.v3.modules.content.yjs.service import yjs_document_service

__all__ = ["yjs_document_service"]
