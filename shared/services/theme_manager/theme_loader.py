"""
主题加载引擎
负责动态加载和应用主题配置
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional

from shared.services.theme_manager.theme_json_parser import theme_json_parser
from shared.services.theme_manager.theme_system import theme_manager

# 常量定义
METADATA_FILE = 'metadata.json'
THEME_JSON_FILE = 'theme.json'
THEME_CONFIG_JS = 'theme.config.js'
STYLES_FILE = 'styles.css'


class ThemeLoader:
    """
    主题加载器
    
    功能:
    1. 加载主题配置文件
    2. 生成主题CSS变量
    3. 提供主题资源路径
    4. 缓存主题配置
    """

    def __init__(self):
        # 主题配置缓存 {slug: config}
        self.config_cache: Dict[str, Dict[str, Any]] = {}

    def load_theme_config(self, theme_slug: str) -> Optional[Dict[str, Any]]:
        """
        加载主题配置（优先使用 theme.json）
        
        Args:
            theme_slug: 主题slug
            
        Returns:
            主题配置字典,失败返回None
        """
        # 检查缓存
        if theme_slug in self.config_cache:
            return self.config_cache[theme_slug]

        try:
            theme_path = theme_manager.themes_dir / theme_slug

            if not theme_path.exists():
                print(f"主题目录不存在: {theme_slug}")
                return None

            # 优先尝试加载 theme.json
            theme_json_file = theme_path / THEME_JSON_FILE
            if theme_json_file.exists():
                try:
                    theme_data = theme_json_parser.parse(str(theme_json_file))
                    config = {
                        'metadata': theme_data.get('metadata', {}),
                        'config': theme_data.get('settings', {}),
                        'supports': theme_data.get('supports', []),
                        'source': 'theme.json'
                    }
                    self.config_cache[theme_slug] = config
                    return config
                except Exception as e:
                    print(f"解析 theme.json 失败，回退到 metadata.json: {e}")

            # 回退到 metadata.json
            metadata_file = theme_path / METADATA_FILE
            if not metadata_file.exists():
                print(f"主题元数据不存在: {theme_slug}")
                return None

            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # 加载theme.config.js (如果存在)
            config_file = theme_path / THEME_CONFIG_JS
            theme_config = {}
            if config_file.exists():
                theme_config = self._parse_js_config(config_file)

            # 合并配置并缓存
            full_config = {
                'metadata': metadata,
                'config': theme_config,
                'path': str(theme_path),
                'slug': theme_slug
            }

            self.config_cache[theme_slug] = full_config
            return full_config

        except Exception as e:
            print(f"加载主题配置失败 {theme_slug}: {e}")
            return None

    def _parse_js_config(self, config_file: Path) -> Dict[str, Any]:
        """
        解析JS配置文件(简化版,仅提取JSON部分)
        
        Args:
            config_file: 配置文件路径
            
        Returns:
            配置字典
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 简单提取export const themeConfig = {...} 中的对象
            start = content.find('{')
            end = content.rfind('}')

            if start != -1 and end != -1:
                json_str = content[start:end + 1]
                
                # 1. 移除单行注释 (// ...)
                json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)
                
                # 2. 移除多行注释 (/* ... */)
                json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
                
                # 3. 处理单引号：将键和字符串值的单引号替换为双引号
                json_str = re.sub(r"'([^']*)'", r'"\1"', json_str)
                
                # 4. 给没有引号的键添加双引号（匹配 pattern: key: value）
                #    这会匹配像 colors: { 这样的模式并转换为 "colors": {
                json_str = re.sub(r'(\w+)\s*:', r'"\1":', json_str)
                
                # 5. 移除尾随逗号 (在 } 或 ] 之前的逗号)
                json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
                
                # 调试：打印处理后的 JSON 字符串
                import sys
                print(f"[DEBUG] 处理后的 JSON 前300字符:\n{json_str[:300]}", file=sys.stderr)
                
                return json.loads(json_str)

            return {}

        except Exception as e:
            import traceback
            print(f"解析JS配置失败: {e}")
            print(f"文件路径: {config_file}")
            print(f"错误详情: {traceback.format_exc()}")
            return {}

    def generate_css_variables(self, theme_slug: str) -> str:
        """
        生成CSS变量字符串
        
        Args:
            theme_slug: 主题slug
            
        Returns:
            CSS变量字符串
        """
        config = self.load_theme_config(theme_slug)
        if not config:
            return ""

        theme_config = config.get('config', {})
        colors = theme_config.get('colors', {})
        typography = theme_config.get('typography', {})
        layout = theme_config.get('layout', {})
        components = theme_config.get('components', {})

        css_vars = [":root {"]

        # 颜色变量
        for key, value in colors.items():
            css_vars.append(f"  --color-{key}: {value};")

        # 排版变量
        if typography:
            css_vars.append(f"  --font-family: {typography.get('fontFamily', 'system-ui')};")
            css_vars.append(f"  --font-size-base: {typography.get('fontSize', '16px')};")
            css_vars.append(f"  --line-height: {typography.get('lineHeight', 1.6)};")

        # 布局变量
        if layout:
            css_vars.append(f"  --content-width: {layout.get('contentWidth', 'max-w-4xl')};")
            css_vars.append(f"  --sidebar-position: {layout.get('sidebarPosition', 'right')};")

        # 组件变量
        if components:
            css_vars.append(f"  --border-radius: {components.get('borderRadius', '0.5rem')};")

        css_vars.append("}")
        return "\n".join(css_vars)

    def get_theme_stylesheet_url(self, theme_slug: str) -> str:
        """
        获取主题样式表URL
        
        Args:
            theme_slug: 主题slug
            
        Returns:
            样式表URL
        """
        theme_path = theme_manager.themes_dir / theme_slug
        styles_file = theme_path / STYLES_FILE

        return f"/themes/{theme_slug}/{STYLES_FILE}" if styles_file.exists() else ""

    async def get_active_theme_config(self) -> Optional[Dict[str, Any]]:
        """
        获取当前激活主题的完整配置
        
        Returns:
            主题配置
        """
        active_slug = await self._get_active_theme_async()
        if not active_slug:
            return None

        return self.load_theme_config(active_slug)
    
    async def _get_active_theme_async(self) -> str:
        """
        异步获取当前激活的主题slug
        
        Returns:
            激活的主题slug，默认返回'default'
        """
        from shared.models.theme import Theme
        from sqlalchemy import select
        from src.utils.database.unified_manager import db_manager
        
        try:
            async with db_manager.get_session() as db:
                query = select(Theme).where(Theme.is_active == True)
                result = await db.execute(query)
                theme = result.scalar_one_or_none()
                return theme.slug if theme else 'default'
        except Exception as e:
            print(f"[ThemeLoader] 获取激活主题失败: {e}")
            import traceback
            traceback.print_exc()
            return 'default'

    def clear_cache(self, theme_slug: Optional[str] = None):
        """
        清除主题配置缓存
        
        Args:
            theme_slug: 指定主题slug,为空则清除所有
        """
        if theme_slug:
            self.config_cache.pop(theme_slug, None)
        else:
            self.config_cache.clear()


# 全局实例
theme_loader = ThemeLoader()
