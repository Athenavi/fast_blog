"""system/workflow：通用工作流引擎（定义注册 / 实例执行 / 审批 / 执行历史）

把 v2 的 ``shared/services/system/workflow_engine.py`` 接线到 v3：保留引擎语义
（逐节点推进、条件分支、审批暂停、执行历史），但把 v2 的进程内存态换成真表——
统一落 ``system_settings``（不新建表），定义存键 ``workflow.definitions``，实例与执行
记录存键 ``workflow.instances``（最多保留最近 200 条）。

本模块**未登记进** ``src/api/v3/__init__.py`` 的 ``DOMAIN_MODULES``（该文件是共享文件，
本任务不改）；``controller.py`` 的 router 已按 ``/workflow`` 前缀就绪，登记后即可挂到
``/api/v3/system/workflow``。
"""

from src.api.v3.modules.system.workflow.service import workflow_engine_service

__all__ = ["workflow_engine_service"]
