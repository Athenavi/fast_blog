"""media 模块：媒体库（文件与文件夹）

路由前缀：``/api/v3/content/media``

数据模型：``media(id, user, hash, filename, original_filename, file_path, file_url,
file_size, file_type, mime_type, width, height, duration, thumbnail_path, thumbnail_url,
description, alt_text, is_public, download_count, category, tags, folder_id)`` +
``media_folders(id, name, parent_id, user, description, sort_order, is_public, media_count)``。

范围说明（按既定决策）：本次做「列表 / 上传 / 详情 / 更新 / 删除 + 文件夹」核心；
分片上传（``upload_chunks``/``upload_tasks``）、下载任务（``download_tasks``）、
优化产物（``media_optimizations``）、查重（``file_hashs``）归入二期。

**隐私约定**：``file_path``（服务器磁盘路径）不出现在公开响应中，只暴露 ``file_url``。
权限码：``media:view`` / ``media:upload`` / ``media:delete``
"""
