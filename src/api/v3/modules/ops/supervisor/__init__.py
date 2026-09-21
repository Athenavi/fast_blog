"""ops.supervisor：进程监督（登记 / 状态 / 受控启停 / 日志）

2026-09-21 批次 18 由仓库根的原 ``process_supervisor/`` 整合而来（原目录删除）：

  - **登记**存 ``system_settings`` 的 ``supervisor.config``（JSON，非公开）；
  - **状态**用三层健康检查（pid 存活 / 端口 / HTTP）判定，指标在登记了 ``pid_file``
    且 psutil 可用时采集，否则**如实标注不可用**；
  - **动作**只执行登记命令（``start_command`` / ``stop_command`` / ``restart_command``），
    需 ``confirm=true`` + 权限码 ``module_ops:supervisor:execute``（写操作会进审计日志）；
  - **日志**只允许读 ``logs/`` 与 ``storage/logs/`` 下的文件。

进程生命周期归部署层（Docker / systemd）；本模块不 `Popen` 托管主应用自己。
"""
