"""
certification 子模块 - 模型定义（T5-11 批次 13：专家认证）
手写模型，写法对齐代码生成器产物。

> v2 的专家认证是**进程内内存单例**（`services/advanced_features/expert_certification.py`），
> 重启即失、多 worker 各一份，也没有任何审核记录。这里是真表：
> 主表 + 证明材料 + 审核流水，审核状态机 ``pending → approved / rejected``，
> 通过后 ``approved → revoked``（撤销），有效期两年。
"""
from .certification_document import CertificationDocument
from .certification_review import CertificationReview
from .expert_certification import ExpertCertification

__all__ = [
    'CertificationDocument',
    'CertificationReview',
    'ExpertCertification',
]
