"""gamification.points 模块（T5-11 批次 12）：积分账户 / 流水 / 规则 / 等级 / 签到 / 兑换。

表：``user_points`` / ``points_transactions`` / ``points_rules``（本批次新建）。

> v2 的同名能力是**进程内内存单例**，并暴露 `POST /record-action` 让前端自报加分（可刷分）。
> 本模块是重写：真表 + 余额校验 + 流水 + 规则可配 + **不暴露**自报加分接口。

本轮补接的**真实能力**：

- **等级**：``service.level_for`` 纯函数（阈值表 ``LEVELS`` → 等级名），``GET /points/level/{score}``
  公开暴露；``GET /points/me`` 返回本人余额 + 当前等级 + 最近流水。
- **规则表**：``DEFAULT_POINT_RULES`` 常量兜底（与 ``scripts/seed_gamification.py`` 一致），
  ``points_rules`` 为空时 ``GET /points/rules`` 回退常量而非空数组。
- **排行**：``service.rank_entries`` 纯函数，对 ``user_points`` 真表聚合结果排序赋名次。
"""
