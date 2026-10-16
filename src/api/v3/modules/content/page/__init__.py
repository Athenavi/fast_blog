"""page 模块：CMS 页面管理

路由前缀：``/api/v3/content/page``

数据模型：``pages(id, title, slug, content, excerpt, template, status, author_id,
parent_id, order_index, meta_title, meta_description, meta_keywords, published_at)``。

说明：``pages.content`` 直接内联在表里（不像文章正文在 ``article_content``）；
另一个 ``page_builder`` 表（可视化区块）按既定范围归入二期。

``status`` 约定沿用 0=草稿 / 1=已发布（与 ``articles.status`` 一致的语义）。
权限码：``page:view`` / ``page:create`` / ``page:edit`` / ``page:delete`` / ``page:publish``
"""
