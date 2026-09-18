"""article 模块：文章管理 + 公开读

路由前缀：``/api/v3/content/article``

数据模型（``shared/models/article``）::

    articles           文章主体（title/slug/status/tags_list/... ，**没有 content 字段**）
    article_content    正文，按 ``language_code`` 多语言，一篇文章可多行
    article_seo        1:1 SEO 字段（独立表）

关键约定：

  - **软删除**：``status = -1`` + ``deleted_at``（``status`` 语义：-1 删除 / 0 草稿 / 1 已发布）
  - **定时发布**：``scheduled_publish_at``；到点由 ``src/scheduler.py`` 的
    ``ScheduledPublishService`` 置为已发布（v3 不重复实现调度）
  - **公开读与后台读显式分流**：公开走 ``/article/public/**``（无鉴权、可独立缓存），
    后台走 ``/article/**``（需权限码），避免同一 URL 因登录态返回不同内容而污染缓存
  - 写操作后调用 ``article_cache_service.invalidate_public_caches()``，保证与前台的公开
    读缓存一致（读缓存本身在 Phase 4/6 再补，先保证「写后必失效」）

权限码：``article:view`` / ``article:create`` / ``article:edit`` / ``article:delete`` / ``article:publish``
"""
