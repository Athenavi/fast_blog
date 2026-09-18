"""search_analytics 模块：搜索行为分析

路由前缀：``/api/v3/analytics/search``

数据源：``search_history`` 表（``id, user, keyword, results_count, created_at``）。

说明：v2 **没有**这个模块（检索 ``SearchHistory`` 只命中 v3 旧实现），因此这里按
「表结构 + v3 旧实现的契约」重新实现，而不是迁移。

权限码：``settings:view``
"""
