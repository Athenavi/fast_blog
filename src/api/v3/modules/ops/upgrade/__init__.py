"""ops.upgrade 模块（T5-11 批次 5）：在线升级管理。

模块定位
========
管理面板侧的升级运维入口：查看当前版本与升级历史、检查有没有新版本、
对指定目标版本做**升级前干跑预检**。无独立数据库表（无 crud/model），
版本读自 ``version.txt``，历史读自 ``logs/update_history.json``。

能力基座
========
- ``shared/utils/version_manager.py`` —— 当前版本（``release.version``）与项目根目录
- ``shared/utils/auto_update_checker.py`` —— 远端（GitHub Releases）检查、本地
  ``releases/update_*.zip`` 扫描、版本号比较
- ``shared/utils/update_history.py`` —— 升级历史（updater 每次收尾都会写入）
- ``updater/updater.py`` —— 真实替换执行器（FastBlogUpdater：下载 → 校验 → 备份 →
  停服 → 替换 → 失败回滚），本期**不**由 API 在线触发（见下）

端点
====

::

    GET    /api/v3/ops/upgrade/status   升级状态（当前版本 / app_path / 最近 10 条历史）
    POST   /api/v3/ops/upgrade/check    检查更新（远端优先，远端不可达回退本地 releases）
    POST   /api/v3/ops/upgrade/apply    升级干跑预检（不执行真实替换）

权限码：``module_ops:upgrade:view``（status）、``module_ops:upgrade:execute``
（check / apply）。check 虽为只读语义，但按契约走 POST + EXECUTE 权限。

apply 取舍：本期只做干跑预检（方案二）
=====================================
不提供「后台线程 / 子进程触发 updater」的在线执行路径，理由：

1. ``FastBlogUpdater.update()`` 内部会调用 ``stop_main_application()``——按命令行
   含 ``main.py`` 终止进程，**正是正在服务本请求的后端自身**，且全套流程没有任何
   自动重启逻辑；从 API 触发等于让服务自杀且无法自愈。
2. 下载（远端 60s 超时）与整目录替换远超「不阻塞请求线程数秒以上」的红线。
3. 真实替换涉及停服窗口，属于人工择时操作（或二期交由独立的升级编排器，
   例如复用 ``update_server`` 的子进程模式 + 进程守护重启）。

因此 ``POST /apply`` 语义为**干跑预检**：校验目标版本号、与当前版本的关系、
本地更新包是否就绪及 ZIP 完整性（与 updater 的白名单 / 1KB 下限 / ``testzip``
同口径），返回 ``{dry_run, ready, checks}``；全部通过后由人工按
``python -m updater.updater --target-version <v> --app-path <项目根>``
择时执行真实替换。请求体 ``{target_version}`` 来自 ``/check`` 的 ``latest_version``。
"""
