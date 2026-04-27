"""
主题管理服务包

提供完整的主题管理功能:
- 主题发现、安装、激活和卸载
- 模板层级解析(WordPress-style)
- 主题配置管理和定制
- theme.json 解析和验证
- CSS变量生成

使用示例:
    from shared.services.theme_manager import (
        theme_manager,
        template_loader,
        theme_customizer,
        theme_installer,
        theme_loader,
        theme_json_parser
    )
"""

from shared.services.theme_manager.template_loader import TemplateLoader, template_loader
from shared.services.theme_manager.theme_customizer import ThemeCustomizerService
from shared.services.theme_manager.theme_installer import ThemeInstaller, theme_installer
from shared.services.theme_manager.theme_json_parser import ThemeJsonParser, theme_json_parser
from shared.services.theme_manager.theme_loader import ThemeLoader, theme_loader
from shared.services.theme_manager.theme_system import ThemeManager, theme_manager

__all__ = [
    # 类
    'ThemeManager',
    'TemplateLoader',
    'ThemeCustomizerService',
    'ThemeInstaller',
    'ThemeLoader',
    'ThemeJsonParser',

    # 全局实例
    'theme_manager',
    'template_loader',
    'theme_installer',
    'theme_loader',
    'theme_json_parser',
]

__version__ = '1.0.0'
