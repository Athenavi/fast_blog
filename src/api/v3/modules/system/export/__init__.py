"""system/export：真表数据导出（CSV 文件下载 / 预览 / 字段模板）

从 ``users`` / ``articles`` / ``comments`` / ``categories`` / ``page_views`` 等**真表**取数，
用标准库 ``csv`` 生成带 UTF-8 BOM 的 CSV；字段名取真实列名，表头用中文标签，统一由
``service.EXPORT_RESOURCES`` 登记表定义。Excel 导出未实现（未安装 openpyxl）。
"""

from src.api.v3.modules.system.export.service import (
    EXPORT_RESOURCES,
    export_service,
    to_csv,
)

__all__ = ["export_service", "EXPORT_RESOURCES", "to_csv"]
