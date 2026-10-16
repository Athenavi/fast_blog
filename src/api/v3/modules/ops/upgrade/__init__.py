"""ops.upgrade 模块：在线升级管理 + **真实升级执行**（2026-09-21 批次 18 整合）

模块定位
========
管理面板侧的升级运维入口：看版本与历史、检查有没有新版本、预演会替换哪些文件，
并且**真实执行升级**（替换代码 → alembic 迁移 → 清缓存 → 可选重启；失败自动回滚）。
无独立数据库表，版本读 ``version.txt``，历史读 ``logs/update_history.json``，
备份在 ``backups/update_backups/<old_ver>_<ts>/``。

能力基座
========
- ``shared/utils/version_manager.py`` —— 当前版本与项目根（**文件格式已统一为 INI**）
- ``shared/utils/auto_update_checker.py`` —— 远端（GitHub Releases）检查、本地
  ``releases/update_*.zip`` 扫描、版本号比较
- ``shared/utils/update_history.py`` —— 升级历史（每次执行/回滚收尾都会写入）
- ``executor.py`` —— **真实替换执行器**（原仓库根 ``updater/updater.py`` 的能力，
  2026-09-21 整合进 src；原目录已删除）

端点
====

::

    GET    /api/v3/ops/upgrade/status    升级状态（版本 / 进行中 / 最近结果 / 历史）
    POST   /api/v3/ops/upgrade/check     检查更新（远端优先，回退本地 releases）
    POST   /api/v3/ops/upgrade/apply     升级干跑预检（只体检、不替换，保留兼容）
    GET    /api/v3/ops/upgrade/paths     路径策略（会替换哪些代码、绝不动哪些数据）
    POST   /api/v3/ops/upgrade/plan      执行预演（列出将替换/跳过的文件，只读）
    POST   /api/v3/ops/upgrade/execute   真实升级（需 confirm=true）
    GET    /api/v3/ops/upgrade/backups   升级备份列表
    POST   /api/v3/ops/upgrade/rollback  按备份回滚代码（需 confirm=true）
    GET/PUT /api/v3/ops/upgrade/settings 升级设置（重启命令）

权限码：``module_ops:upgrade:view``（status / paths / backups / settings 读）、
``module_ops:upgrade:execute``（check / apply / plan / execute / rollback / settings 写）。

与旧实现（``updater/updater.py``）的三点关键差异
==============================================
旧实现被刻意排除在 API 之外，理由是"会停掉正在服务本请求的进程 + 整套流程没有重启逻辑 +
整目录替换"。整合时逐条解决，而不是照搬：

1. **不自杀进程**：执行器不终止后端进程；替换完成后由配置的 ``restart_command``
   （system_settings 的 ``upgrade.restart_command``，如 ``docker compose restart backend``）
   真实执行，未配置则如实返回"需人工重启生效"。
2. **不阻塞事件循环**：所有文件 IO / 子进程都在 ``asyncio.to_thread`` 里跑，
   且默认**后台任务**执行，``GET /status`` 查看 ``in_progress`` 与最近结果。
3. **替换范围白名单 + 保护清单**：只覆盖代码路径（``src/ shared/ cli/ ...``），
   ``media/ uploads/ storage/ logs/ backups/ releases/ .env ...`` 永不触碰；
   替换前逐文件备份并写 ``manifest.json``，回滚按清单精确还原（新增文件会被删除）。
   旧实现用 ``shutil.move/rmtree(项目根)`` 做"原子替换"，会连数据一起动掉 —— 这条路径不存在了。
"""
