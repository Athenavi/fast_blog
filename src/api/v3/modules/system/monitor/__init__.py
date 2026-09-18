"""monitor 模块：系统监控（服务器信息 + 在线会话）

**无数据库表**（会话数据读的是既有的 `user_sessions` 表），因此没有 `crud.py` / `model.py`。

对应原 astro 后台的「系统总览」聚合页（`admin/system-hub`、`admin/system`）——
它们同属「无接口页面」清单，React 原实现已随 `archive/` 删除。

功能设计参考官方 FastApiAdmin 的 `modules/monitor/{server,online,health,cache}`；
其中 **cache 部分已由本目录的 `system/cache` 模块覆盖**，所以这里只补
「服务器信息」与「在线会话」两块，再加一个给首页用的 `overview` 聚合端点。

数据源：
  - 服务器信息 → `psutil`（已在 requirements）
  - 在线会话   → `user_sessions` 表 + `SessionManagementService`

权限码：``module_system:monitor:view`` / ``:kick``
"""
