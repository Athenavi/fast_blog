"""mobile.follow 模块（T5-11 批次 11）：前台关注关系（fans）。

表：``user_follows``（本批次新建，alembic 迁移 ``b3d7f1a5c8e2``）。

> v2 的 6 个关注端点在 ``users/unified_users.py`` 里读写**模块级内存字典**
> （重启即丢、多 worker 各一份，注释自承"后续应迁移到数据库表"），且**没有 follow 表**；
> 本模块是重写：真表 + 分页 + 目标存在性校验 + 拉黑校验 + ``is_following`` / ``is_mutual`` 标记。
"""
