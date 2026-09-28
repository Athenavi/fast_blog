"""
翻译管理服务包
提供多语言翻译、机器翻译、翻译记忆等功能
"""

# i18n 能力已合并到唯一的 TranslationService（shared/services/translation/i18n_service.py）：
# 历史上这里另有一份 I18nService 与 translation.py 的同名 TranslationService，三份实现接口
# 各不相同。现在保留同名导出，指向同一实现，调用方无需改动。
from shared.services.translation.i18n_service import (
    TranslationService as I18nService,
    translation_service as i18n_service,
)
from shared.services.translation.translation_manager.machine_translation import (
    MachineTranslationService,
    machine_translation_service
)
from shared.services.translation.translation_manager.translation_manager import (
    TranslationManager,
    translation_manager
)
from shared.services.translation.translation_manager.translation_memory import (
    TranslationMemoryService,
    translation_memory_service
)

__all__ = [
    # 核心类
    'TranslationManager',
    'I18nService',
    'MachineTranslationService',
    'TranslationMemoryService',

    # 全局实例
    'translation_manager',
    'i18n_service',
    'machine_translation_service',
    'translation_memory_service',
]
