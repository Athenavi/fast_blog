"""
主题定制器服务 - 增强版
提供主题的实时预览和配置管理功能

功能:
1. 主题配置管理
2. 实时预览生成
3. 颜色方案管理(预设+自定义)
4. 字体配置(Google Fonts集成)
5. 布局选项
6. CSS自定义注入
7. 配置版本历史
8. 配置导入/导出
9. 草稿模式
"""

import json
import re
from pathlib import Path
from typing import Dict, Any

# 常量定义
THEMES_DIR = 'themes'
CONFIG_FILE = 'config.json'


class ThemeCustomizerService:
    """
    主题定制器服务
    
    功能:
    1. 主题配置管理
    2. 实时预览生成
    3. 颜色方案管理
    4. 字体配置
    5. 布局选项
    6. CSS自定义注入
    """

    # 颜色验证正则表达式（编译后复用）
    COLOR_PATTERNS = [
        re.compile(r'^#[0-9A-Fa-f]{6}$'),  # Hex 6位
        re.compile(r'^#[0-9A-Fa-f]{3}$'),  # Hex 3位
        re.compile(r'^rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)$'),  # RGB
        re.compile(r'^rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[\d.]+\s*\)$'),  # RGBA
        re.compile(r'^hsl\(\s*\d+\s*,\s*\d+%\s*,\s*\d+%\s*\)$'),  # HSL
        re.compile(r'^hsla\(\s*\d+\s*,\s*\d+%\s*,\s*\d+%\s*,\s*[\d.]+\s*\)$'),  # HSLA
    ]

    NAMED_COLORS = {
        'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink',
        'black', 'white', 'gray', 'grey', 'brown', 'cyan', 'magenta',
    }

    def __init__(self):
        # 默认主题配置模板
        self.default_configs = {
            'colors': {
                'primary': '#3b82f6',
                'secondary': '#64748b',
                'accent': '#f59e0b',
                'background': '#ffffff',
                'foreground': '#1f2937',
                'muted': '#f3f4f6',
                'border': '#e5e7eb',
            },
            'fonts': {
                'heading': 'Inter, system-ui, sans-serif',
                'body': 'Inter, system-ui, sans-serif',
                'mono': 'Fira Code, monospace',
            },
            'layout': {
                'sidebar_position': 'right',  # left, right, none
                'content_width': 'max-w-4xl',  # max-w-3xl, max-w-4xl, max-w-5xl, max-w-7xl
                'post_layout': 'default',  # default, wide, boxed
                'show_sidebar_on_mobile': False,
            },
            'typography': {
                'base_size': '16px',
                'scale_ratio': 1.25,
                'line_height': 1.6,
                'letter_spacing': 'normal',
            },
            'components': {
                'rounded_corners': '0.5rem',
                'shadow_style': 'medium',  # none, small, medium, large
                'button_style': 'default',  # default, rounded, pill
                'card_style': 'elevated',  # flat, elevated, outlined
            },
            'header': {
                'style': 'default',  # default, transparent, minimal
                'height': '64px',
                'sticky': True,
                'show_search': True,
                'show_social_links': True,
            },
            'footer': {
                'style': 'default',  # default, minimal, full
                'show_copyright': True,
                'show_social_links': True,
                'show_navigation': True,
                'custom_text': '',
            },
            'homepage': {
                'hero_section': True,
                'featured_posts': True,
                'featured_count': 3,
                'recent_posts': True,
                'recent_count': 6,
                'categories_display': 'grid',  # grid, list, hidden
            },
            'article': {
                'show_author': True,
                'show_date': True,
                'show_categories': True,
                'show_tags': True,
                'show_share_buttons': True,
                'show_related_posts': True,
                'show_toc': True,
                'toc_position': 'left',  # left, right
                'estimated_read_time': True,
            },
        }

        # 颜色方案预设
        self.color_presets = {
            'default': {
                'primary': '#3b82f6',
                'secondary': '#64748b',
                'accent': '#f59e0b',
            },
            'ocean': {
                'primary': '#0ea5e9',
                'secondary': '#64748b',
                'accent': '#06b6d4',
            },
            'sunset': {
                'primary': '#f97316',
                'secondary': '#64748b',
                'accent': '#ec4899',
            },
            'forest': {
                'primary': '#22c55e',
                'secondary': '#64748b',
                'accent': '#84cc16',
            },
            'purple': {
                'primary': '#a855f7',
                'secondary': '#64748b',
                'accent': '#ec4899',
            },
        }

        # 字体选项
        self.font_options = {
            'sans': [
                {'name': 'Inter', 'value': 'Inter, system-ui, sans-serif'},
                {'name': 'Roboto', 'value': 'Roboto, sans-serif'},
                {'name': 'Open Sans', 'value': 'Open Sans, sans-serif'},
                {'name': 'Lato', 'value': 'Lato, sans-serif'},
            ],
            'serif': [
                {'name': 'Merriweather', 'value': 'Merriweather, Georgia, serif'},
                {'name': 'Playfair Display', 'value': 'Playfair Display, serif'},
                {'name': 'Lora', 'value': 'Lora, serif'},
            ],
            'mono': [
                {'name': 'Fira Code', 'value': 'Fira Code, monospace'},
                {'name': 'JetBrains Mono', 'value': 'JetBrains Mono, monospace'},
                {'name': 'Source Code Pro', 'value': 'Source Code Pro, monospace'},
            ],
        }

    def get_theme_config(self, theme_slug: str) -> Dict[str, Any]:
        """
        获取主题配置
        
        Args:
            theme_slug: 主题标识
            
        Returns:
            主题配置对象
        """
        config_file = Path(THEMES_DIR) / theme_slug / CONFIG_FILE
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load theme config: {e}")
        
        return self.default_configs.copy()

    def update_theme_config(self, theme_slug: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新主题配置
        
        Args:
            theme_slug: 主题标识
            updates: 要更新的配置(支持嵌套路径,如 'colors.primary')
            
        Returns:
            更新后的完整配置
        """
        config = self.get_theme_config(theme_slug)

        # 递归更新配置
        for key_path, value in updates.items():
            keys = key_path.split('.')
            self._set_nested_value(config, keys, value)

        # 保存到配置文件
        config_file = Path(THEMES_DIR) / theme_slug / CONFIG_FILE
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save theme config: {e}")

        return config

    def generate_preview_css(self, config: Dict[str, Any]) -> str:
        """
        根据配置生成CSS
        
        Args:
            config: 主题配置
            
        Returns:
            CSS字符串
        """
        css_parts = []

        # 颜色和字体变量
        for section, prefix in [('colors', 'color'), ('fonts', 'font')]:
            if section in config:
                css_parts.append(':root {')
                for name, value in config[section].items():
                    css_parts.append(f'  --{prefix}-{name}: {value};')
                css_parts.append('}')

        # 布局样式
        if 'layout' in config:
            layout = config['layout']
            css_parts.append(f'.content-container {{ max-width: {layout.get("content_width", "max-w-4xl")}; }}')

            if layout.get('sidebar_position') == 'none':
                css_parts.append('.sidebar { display: none; }')

        # 圆角
        if 'components' in config and 'rounded_corners' in config['components']:
            radius = config['components']['rounded_corners']
            css_parts.append(f':root {{ --border-radius: {radius}; }}')
            css_parts.append(f'.card, .button, .input {{ border-radius: {radius}; }}')

        # 阴影
        if 'components' in config and 'shadow_style' in config['components']:
            shadow_map = {
                'none': 'none',
                'small': '0 1px 2px 0 rgb(0 0 0 / 0.05)',
                'medium': '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                'large': '0 10px 15px -3px rgb(0 0 0 / 0.1)',
            }
            shadow = shadow_map.get(config['components']['shadow_style'], 'none')
            css_parts.append(f'.card {{ box-shadow: {shadow}; }}')

        # 自定义CSS
        if 'custom_css' in config and config['custom_css']:
            css_parts.append(config['custom_css'])

        return '\n'.join(css_parts)

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证配置的有效性
        
        Args:
            config: 待验证的配置
            
        Returns:
            验证结果 {valid: bool, errors: list}
        """
        errors = []

        # 验证颜色格式
        if 'colors' in config:
            for color_name, color_value in config['colors'].items():
                if not self._is_valid_color(color_value):
                    errors.append(f'Invalid color format for {color_name}: {color_value}')

        # 验证布局选项
        if 'layout' in config:
            valid_positions = ['left', 'right', 'none']
            if config['layout'].get('sidebar_position') not in valid_positions:
                errors.append(f'Invalid sidebar position. Must be one of: {valid_positions}')

        # 验证字体
        if 'fonts' in config:
            for font_name, font_value in config['fonts'].items():
                if not font_value or len(font_value) > 200:
                    errors.append(f'Invalid font specification for {font_name}')

        return {'valid': len(errors) == 0, 'errors': errors}

    def export_config(self, theme_slug: str) -> str:
        """
        导出主题配置为JSON
        
        Args:
            theme_slug: 主题标识
            
        Returns:
            JSON字符串
        """
        config = self.get_theme_config(theme_slug)
        return json.dumps(config, indent=2, ensure_ascii=False)

    def import_config(self, theme_slug: str, config_json: str) -> Dict[str, Any]:
        """
        从JSON导入主题配置
        
        Args:
            theme_slug: 主题标识
            config_json: JSON配置字符串
            
        Returns:
            导入结果
        """
        try:
            config = json.loads(config_json)

            # 验证配置
            validation = self.validate_config(config)
            if not validation['valid']:
                return {
                    'success': False,
                    'errors': validation['errors'],
                }

            # 保存配置
            updated_config = self.update_theme_config(theme_slug, self._flatten_dict(config))

            return {
                'success': True,
                'config': updated_config,
            }

        except json.JSONDecodeError as e:
            return {
                'success': False,
                'errors': [f'Invalid JSON: {str(e)}'],
            }

    def _set_nested_value(self, d: Dict, keys: list, value: Any):
        """设置嵌套字典的值"""
        for key in keys[:-1]:
            if key not in d:
                d[key] = {}
            d = d[key]
        d[keys[-1]] = value

    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """将嵌套字典展平为单层字典"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def _is_valid_color(self, color: str) -> bool:
        """验证颜色格式"""
        # 检查预编译的正则表达式
        if any(pattern.match(color) for pattern in self.COLOR_PATTERNS):
            return True

        # 检查命名颜色
        return color.lower() in self.NAMED_COLORS
