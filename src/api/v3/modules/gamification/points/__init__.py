"""gamification.points 模块（T5-11 批次 12）：积分账户 / 流水 / 规则 / 签到 / 兑换。

表：``user_points`` / ``points_transactions`` / ``points_rules``（本批次新建）。

> v2 的同名能力是**进程内内存单例**，并暴露 `POST /record-action` 让前端自报加分（可刷分）。
> 本模块是重写：真表 + 余额校验 + 流水 + 规则可配 + **不暴露**自报加分接口。
"""
