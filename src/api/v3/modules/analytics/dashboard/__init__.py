"""dashboard 模块：后台数据概览

路由前缀：``/api/v3/analytics/dashboard``

数据来源全部是既有表的聚合（``articles`` / ``users`` / ``comments``），不新增表、不引入缓存层
（后台首页调用频率低，且 v2 的 dashboard 也无缓存）。

权限码：``settings:view``（沿用 v3 旧实现与 v2 的口径）
"""
