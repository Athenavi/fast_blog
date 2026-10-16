"""backup 模块：数据库 / 文件 / 全量备份

路由前缀：``/api/v3/ops/backup``

复用 ``shared/services/system/backup_service.py`` 的 ``BackupService``（项目里唯一实现），
不重写任何备份逻辑。

两点工程处理：

  1. ``BackupService`` 的 ``list_backups`` / ``delete_backup`` / ``get_backup_stats`` /
     ``get_backup_schedule`` / ``update_backup_schedule`` 是**同步**方法（文件 I/O），
     v3 用 ``asyncio.to_thread`` 包装，避免在协程里阻塞事件循环。
  2. 备份/恢复是长任务（异步子进程）；v3 沿用 v2 的"请求内等待"行为，但这是**已知限制**：
     生产环境建议改成后台任务 + 任务状态查询（记入 Phase 6 待办）。

权限码：``backup:create`` / ``backup:restore`` / ``backup:delete``；查看类用 ``settings:view``。
"""
