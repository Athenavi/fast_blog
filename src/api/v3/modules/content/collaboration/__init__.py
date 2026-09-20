"""content.collaboration 模块（T5-11 批次 9）：工作区 / 任务 / 团队评论 / 协作邀请 / yjs 协同。

表：``workspaces`` / ``workspace_members`` / ``tasks`` / ``team_comments``
+ 本批次新建的 ``collaboration_invites``（alembic 迁移 ``a7c1e5f9b2d4``）。

本模块是 **v3 的第一个 WebSocket 端点**所在（``/yjs/ws/{document_id}``：真 CRDT（pycrdt）
+ Redis 跨进程广播）。v2 的同名实现在四个子模块里各有硬伤，**本模块是重写而非平移**，
逐条对照见各 ``*_service.py`` 的模块 docstring。
"""
