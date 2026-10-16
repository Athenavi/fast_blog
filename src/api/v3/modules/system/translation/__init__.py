"""system/translation：多语言词条 / 本地化 / 导入导出 / 进度 / 翻译记忆库 / 机器翻译

数据落 ``system_settings`` 的 JSON 键（无新建表）：

  - ``translation.bundles``  语言包 / 词条
  - ``translation.memory``   翻译记忆库
  - ``translation.locales``  自定义语言区域
  - ``translation.settings`` 模块设置（默认语言 / 源语言 / 相似度阈值）

机器翻译仅在配置密钥时真实调用外部 API，缺配置时如实返回 ``available=false``。
"""

from src.api.v3.modules.system.translation.service import translation_service

__all__ = ["translation_service"]
