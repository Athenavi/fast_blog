"""comment 模块：评论管理与公开评论

路由前缀：``/api/v3/content/comment``

数据模型：``comments(id, article_id, user_id, parent_id, content, author_name,
author_email, author_url, author_ip, user_agent, is_approved, likes, spam_score,
spam_reasons, created_at, updated_at)``。

**隐私约定**：``author_email`` / ``author_ip`` / ``user_agent`` 只出现在管理端响应里，
公开读（``/public/**``）一律过滤。

垃圾检测（``spam_score`` / ``spam_reasons``）按既定范围归入二期 —— v2 的检测逻辑较重，
本次只做"通过 / 拒绝"的人工审核流。

权限码：``comment:view`` / ``comment:approve`` / ``comment:edit`` / ``comment:delete``
"""
