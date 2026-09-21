"""
third_party_publish 子模块 - 模型定义（2026-09-21 批次 18）

> 三个模型都是**手写模型**（写法对齐代码生成器产物），对应 ``config/models.yaml``
> 里同名条目的 ``module: third_party_publish``。
> 覆盖"多平台发布"底座的渠道配置 / 发布任务 / 尝试记录（平台适配器分期实现）。
"""
from .publish_channel import PublishChannel
from .publish_log import PublishLog
from .publish_task import PublishTask

__all__ = ['PublishChannel', 'PublishLog', 'PublishTask']
