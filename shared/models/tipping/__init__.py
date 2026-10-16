"""
tipping 子模块 - 模型定义（T5-11 批次 14：打赏与提现）
手写模型，写法对齐代码生成器产物。

> v2 的 `services/advanced_features/tipping_system.py` 是**进程内内存单例**，并且引用了
> 不存在的列 ``Article.user_id``（真实列名是 ``user``）—— 那个实现连一次查询都跑不通。
> 这里是真表，且**打赏金额走真实支付链路**（批次 7 的 payment-gateway 插件）。
"""
from .tip import Tip
from .tip_withdrawal import TipWithdrawal

__all__ = [
    'Tip',
    'TipWithdrawal',
]
