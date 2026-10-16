"""content.team_comment 模块：团队 / 内部评论（协作讨论、@提及、解决、统计）。

路由前缀：``/api/v3/content/team_comment``

**落点表（如实说明，未新建任何表 / ORM 模型）**：复用既有 ``team_comments`` 表
（alembic 初始全量 schema ``8b7ecb6d053c`` 创建；ORM ``shared.models.comment.team_comment.TeamComment``）。
真实列（已逐列核对 alembic 与模型）：``id`` / ``content_type`` / ``content_id`` /
``author_id`` / ``parent_id`` / ``text`` / ``mentions`` / ``is_resolved`` /
``resolved_by`` / ``resolved_at`` / ``created_at`` / ``updated_at``。

**为什么不是 ``comments`` 表**：任务提示优先用 ``comments`` 表并以既有列区分「内部评论」，
但逐列核对后 ``comments``（alembic ``8b7ecb6d053c`` 与模型一致）只有
``article_id/user_id/parent_id/content/author_name/author_email/author_url/author_ip/
user_agent/is_approved/likes/spam_score/spam_reasons/created_at/updated_at`` —— **没有任何
type / status / 可见性 / 内部标记列**。硬用它要么需要一个不存在的列（造假），要么退化成
「文章评论」而与 ``content/comment``（公开评论）职责完全重叠。因此本模块改用任务允许的
「其它既有表」：``team_comments`` —— 它正是 v2 服务
``shared/services/comments/team_comments.py`` 的落点，天然表达团队 / 内部评论语义。

**职责边界（三个评论相关模块互不重叠）**：

  - ``content/comment``：**公开**文章评论（访客可评、审核 ``is_approved``、点赞、隐私字段）。
  - ``content/collaboration``：**工作区协作**场景下的内容对象评论入口
    （``/collaboration/comment``，权限码 ``module_content:collaboration:*``）。
  - ``content/team_comment``（本模块）：content 域下**团队 / 内部评论**的完整入口，
    必须登录 + 协作权限，支持评论树、@提及、解决（resolve）、统计。

  collaboration 与本模块**共用同一张既有 ``team_comments`` 表**（以 ``content_type`` +
  ``content_id`` 区分内容对象）；本模块是 v2 ``team_comments`` 服务的独立、完整接线。

**与 v2 的差异 / 修复**（v2 服务 ``shared/services/comments/team_comments.py``）：

  - v2 的 ``resolve_comment`` **没有任何权限校验**（任何登录用户可「解决」任意评论）；
    本模块要求**作者或管理员**。
  - v2 的 ``get_user_mentions`` 用 ``TeamComment.mentions.contains(str(user_id))`` 做**子串匹配**
    （``user_id=1`` 会误命中 ``[11,21]``）；本模块改为「SQL ``like`` 粗筛 + 应用层精确解析 JSON 列表」。
  - v2 的 ``create_comment`` 接收 ``author_name`` 参数却未落库（``team_comments`` 无该列），
    作者名改由 ``author_id`` 关联 ``users.username`` 在读取时补齐。

**未接线项（既有表无法真实表达，故不做端点，绝不造假）**：

  - **指派（assignee）**：``team_comments`` 无 assignee 列 → 不做。
  - **独立已读 / 未读状态**：无 read 状态列（v2 ``unread_only`` 是拿 ``is_resolved == False``
    近似，语义并不等价）；本模块保留 ``unread_only`` 参数但**语义 = 未解决**，已如实标注。
  - **逐评论可见性 / 内部可见性列**：无 visibility 列；「内部」由「必须登录 + 协作权限码」保证。
  - **通知推送**：源服务无通知能力，本模块亦不做。

**权限**：``module_content:collaboration:{view,create,edit,delete}``（既有协作权限码，
``codes.py`` 描述即「查看 / 创建 / 编辑 / 删除 工作区 / 评论 / 邀请」）。

> 注册说明：本模块需在 ``src/api/v3/__init__.py`` 的 ``DOMAIN_MODULES['/content']`` 中登记
> ``team_comment`` 才会被加载；该文件为本次任务的**禁改项**，故未登记（见最终说明）。
"""
