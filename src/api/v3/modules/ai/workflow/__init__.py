"""ai.workflow 模块（T5-11 批次 4）：AI 工作流执行记录，表 ``ai_workflows``。

只做记录的查询与治理（删除）；任务的实际执行引擎为二期，
记录由后续接入的执行端写入（status: pending/processing/completed/failed）。
"""
