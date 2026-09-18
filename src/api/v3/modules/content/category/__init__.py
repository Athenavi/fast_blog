"""category 模块：分类管理

路由前缀：``/api/v3/content/category``

数据模型：``categories(id, name, slug, description, parent_id 自引用, sort_order, icon,
color, is_visible, articles_count)``；文章通过 ``articles.category`` 单分类外键关联
（**没有**中间表）。

公开读：``GET /api/v3/content/category/public``（无鉴权，供博客前台）。
权限码：``category:view`` / ``category:create`` / ``category:edit`` / ``category:delete``
"""
