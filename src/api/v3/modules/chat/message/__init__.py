"""chat.message 模块（批次 17）：群聊消息 + WebSocket 实时通道。

表 ``chat_messages``（本批次新建，模型见 ``shared/models/chat/chat_message.py``）；
消息历史落库、实时收发走 Redis ``chat:group:{group_id}`` 频道（不可用时降级为进程内广播）。

与 ``chat/group`` 的关系：群与成员关系仍归 ``chat/group``（表 ``chat_groups`` /
``chat_group_members``）；本模块只读写消息，成员校验直接查 ``ChatGroupMember``
（列名是 ``group`` / ``user``）。

访问控制：**仅需登录**（前端用户接口），不发权限码；HTTP 写端点登记在
``src/api/v3/core/permission/audit.py`` 的 ``EXEMPT_WRITE_ENDPOINTS``，
WebSocket 端点（无 methods，审计会跳过）的准入逻辑写在 ``controller.py`` 路由体内。
"""
