"""system/screen_options：用户级「每页 UI 偏好」持久化

偏好落 ``system_settings``（每用户一行，键 ``screen_options.{user_id}``，
值为 ``{page: {option_key: value}}`` 的 JSON）。
"""

from src.api.v3.modules.system.screen_options.service import screen_options_service

__all__ = ["screen_options_service"]
