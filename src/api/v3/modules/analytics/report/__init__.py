"""analytics.report 模块（T5-11 批次 8）：真实报表聚合、导出、定时报表与报表历史。

表：``scheduled_reports`` / ``report_history``。

> **本模块没有沿用 v2 的实现**：v2 的 `user-activity` / `traffic` / `custom` 三类报表
> 全部返回硬编码的 0 与空结构，`content` 报表还查了不存在的列（`articles.view_count`、
> `article_likes.like_type`）。这里全部改为对现有表做**真实聚合**（见 `service.py`）。
"""
