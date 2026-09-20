"""
chat 子模块 - 模型定义（2026-09-20 批次 17 增补 ``ChatMessage``）

> 前四个模型由代码生成器产出；``ChatMessage`` 是**手写模型**（写法对齐生成器产物），
> 记录群聊消息（历史落库，实时广播走 Redis）。
"""
from .chat_group import ChatGroup
from .chat_group_invite import ChatGroupInvite
from .chat_group_member import ChatGroupMember
from .chat_message import ChatMessage
from .private_message import PrivateMessage

__all__ = ['ChatGroup', 'ChatGroupInvite', 'ChatGroupMember', 'PrivateMessage', 'ChatMessage']
