"""analytics/tracking：埋点上报与阅读聚合

把 v2 遗留的四张"死表"真正用起来（写入侧 + 读侧同在 ``service``，便于字段对齐）：

  - ``page_views``：页面浏览（含 UA 解析出的设备/浏览器/系统）
  - ``user_activities``：行为事件（view/like/share/bookmark/comment/…）
  - ``ad_impressions`` / ``ad_clicks``：广告曝光与点击
  - ``search_history``：搜索关键词与结果数
"""

from src.api.v3.modules.analytics.tracking.service import tracking_service

__all__ = ["tracking_service"]
