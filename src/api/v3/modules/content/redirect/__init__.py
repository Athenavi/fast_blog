"""content/redirect：SEO 跳转规则（编辑器在 /admin/content/redirect）

多格式迁移（任务 8）的 redirect map 落点：导入时按源站 URL 自动生成，
也可手工维护；命中次数由 ``/content/redirect/resolve`` 真实累加。
"""

from src.api.v3.modules.content.redirect.service import redirect_service

__all__ = ["redirect_service"]
