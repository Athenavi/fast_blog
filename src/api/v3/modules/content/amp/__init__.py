"""content.amp：AMP 文档生成 / HTML 转换 / 规范校验

生成从真表读取文章正文并产出完整 AMP 文档；转换与校验都是基于 ``html.parser``
的元素级**真实处理**（不是模板拼串，也不是规则表之外的硬编码）。

导出 :data:`amp_service` 供路由与其它模块复用。
"""

from src.api.v3.modules.content.amp.service import amp_service

__all__ = ["amp_service"]
