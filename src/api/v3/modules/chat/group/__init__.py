"""chat.group 模块（T5-11 批次 4）：群聊会话与成员管理，表 ``chat_groups``/``chat_group_members``。

注意：成员表列名是 ``group``/``user``（代码生成器产物，非 group_id/user_id）。
消息收发不在本模块（无 chat_messages 表，站内信见 chat/private_message）；
成员增删会同步群主表的 ``member_count``。
"""
