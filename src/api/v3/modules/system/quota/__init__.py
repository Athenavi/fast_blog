"""system/quota：站点配额（读取 / 校验 / 更新）

配额落 ``sites.settings``（Text 列，里面 JSON 对象的 ``quota`` 键）；用量按真表统计，
``users`` 精确取 ``site_users``，``articles`` / ``media`` / ``storage_mb`` 走站点成员口径。
"""

from src.api.v3.modules.system.quota.service import site_quota_service

__all__ = ["site_quota_service"]
