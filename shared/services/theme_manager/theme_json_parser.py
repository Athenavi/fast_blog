"""
Theme JSON 解析器
负责解析和验证 theme.json 配置文件
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

# 常量定义
SUPPORTED_VERSIONS = {"1.0"}
THEME_JSON_FILE = "theme.json"
VALID_SIDEBAR_POSITIONS = {'left', 'right', 'none'}
NAMED_COLORS = {'red', 'blue', 'green', 'white', 'black', 'transparent'}

# 颜色验证正则表达式（编译后复用）
COLOR_PATTERNS = [
    re.compile(r'^#[0-9A-Fa-f]{6}$'),
    re.compile(r'^#[0-9A-Fa-f]{3}$'),
    re.compile(r'^rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)$'),
    re.compile(r'^rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[\d.]+\s*\)$'),
    re.compile(r'^hsl\(\s*\d+\s*,\s*\d+%\s*,\s*\d+%\s*\)$'),
    re.compile(r'^hsla\(\s*\d+\s*,\s*\d+%\s*,\s*\d+%\s*,\s*[\d.]+\s*\)$'),
]


class ThemeJsonParser:
    """
    Theme JSON 解析器
    
    功能:
    1. 解析 theme.json 文件
    2. 验证 schema
    3. 提取主题元数据
    4. 生成 CSS 变量
    5. 提供配置访问接口
    """
    
    def __init__(self):
        self.parsed_themes = {}
    
    def parse(self, theme_path: str) -> Dict[str, Any]:
        """
        解析 theme.json 文件
        
        Args:
            theme_path: 主题目录路径或 theme.json 文件路径
            
        Returns:
            解析后的配置字典
        """
        path = Path(theme_path)
        
        # 如果是目录，查找 theme.json
        json_file = path / THEME_JSON_FILE if path.is_dir() else path
        
        if not json_file.exists():
            raise FileNotFoundError(f"theme.json not found: {json_file}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 验证
            self._validate(data)
            
            # 缓存解析结果
            theme_slug = data.get('metadata', {}).get('slug', path.name)
            self.parsed_themes[theme_slug] = data
            
            return data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in theme.json: {e}")
    
    def _validate(self, data: Dict[str, Any]) -> bool:
        """
        验证 theme.json 结构
        
        Args:
            data: 解析后的 JSON 数据
            
        Returns:
            是否有效
        """
        errors = []
        
        # 检查必需字段
        if 'metadata' not in data:
            errors.append("Missing 'metadata' section")
        else:
            metadata = data['metadata']
            for field in ['name', 'slug', 'version']:
                if field not in metadata:
                    errors.append(f"Missing 'metadata.{field}'")
        
        # 检查版本
        version = data.get('version', '')
        if version not in SUPPORTED_VERSIONS:
            errors.append(f"Unsupported version: {version}. Supported: {SUPPORTED_VERSIONS}")
        
        # 检查 settings（可选但推荐）
        if 'settings' in data:
            settings = data['settings']
            
            # 验证颜色
            if 'colors' in settings:
                for color_name, color_value in settings['colors'].items():
                    if not self._is_valid_color(color_value):
                        errors.append(f"Invalid color value for '{color_name}': {color_value}")
            
            # 验证布局
            if 'layout' in settings:
                layout = settings['layout']
                sidebar_pos = layout.get('sidebarPosition')
                if sidebar_pos and sidebar_pos not in VALID_SIDEBAR_POSITIONS:
                    errors.append("Invalid sidebarPosition. Must be 'left', 'right', or 'none'")
        
        if errors:
            raise ValueError(f"Validation errors:\n" + "\n".join(f"- {e}" for e in errors))
        
        return True
    
    def _is_valid_color(self, color: str) -> bool:
        """
        验证颜色值格式
        
        Args:
            color: 颜色值（hex, rgb, rgba, hsl等）
            
        Returns:
            是否有效
        """
        # 检查预编译的正则表达式
        if any(pattern.match(color) for pattern in COLOR_PATTERNS):
            return True

        # 检查命名颜色
        return color.lower() in NAMED_COLORS
    
    def get_metadata(self, theme_slug: str) -> Optional[Dict[str, Any]]:
        """
        获取主题元数据
        
        Args:
            theme_slug: 主题标识
            
        Returns:
            元数据字典
        """
        if theme_slug in self.parsed_themes:
            return self.parsed_themes[theme_slug].get('metadata', {})
        return None
    
    def get_settings(self, theme_slug: str) -> Optional[Dict[str, Any]]:
        """
        获取主题设置
        
        Args:
            theme_slug: 主题标识
            
        Returns:
            设置字典
        """
        if theme_slug in self.parsed_themes:
            return self.parsed_themes[theme_slug].get('settings', {})
        return None
    
    def generate_css_variables(self, theme_slug: str) -> str:
        """
        从 theme.json 生成 CSS 变量
        
        Args:
            theme_slug: 主题标识
            
        Returns:
            CSS 变量字符串
        """
        settings = self.get_settings(theme_slug)
        if not settings:
            return ""
        
        css_vars = [":root {"]
        
        # 颜色变量
        if 'colors' in settings:
            for name, value in settings['colors'].items():
                css_vars.append(f"  --color-{name}: {value};")
        
        # 字体变量
        if 'typography' in settings:
            typo = settings['typography']
            if 'fontFamily' in typo:
                css_vars.append(f"  --font-family: {typo['fontFamily']};")
            if 'headingFont' in typo:
                css_vars.append(f"  --font-heading: {typo['headingFont']};")
            if 'fontSize' in typo:
                css_vars.append(f"  --font-size-base: {typo['fontSize']};")
            if 'lineHeight' in typo:
                css_vars.append(f"  --line-height: {typo['lineHeight']};")
        
        # 布局变量
        if 'layout' in settings:
            layout = settings['layout']
            if 'contentWidth' in layout:
                css_vars.append(f"  --content-width: {layout['contentWidth']};")
            if 'sidebarPosition' in layout:
                css_vars.append(f"  --sidebar-position: {layout['sidebarPosition']};")
        
        # 组件变量
        if 'components' in settings:
            components = settings['components']
            if 'borderRadius' in components:
                css_vars.append(f"  --border-radius: {components['borderRadius']};")
        
        css_vars.append("}")
        
        return "\n".join(css_vars)
    
    def get_supported_features(self, theme_slug: str) -> List[str]:
        """
        获取主题支持的功能列表
        
        Args:
            theme_slug: 主题标识
            
        Returns:
            支持的功能列表
        """
        if theme_slug in self.parsed_themes:
            return self.parsed_themes[theme_slug].get('supports', [])
        return []
    
    def supports_feature(self, theme_slug: str, feature: str) -> bool:
        """
        检查主题是否支持某个功能
        
        Args:
            theme_slug: 主题标识
            feature: 功能名称
            
        Returns:
            是否支持
        """
        supported = self.get_supported_features(theme_slug)
        return feature in supported
    
    def get_widget_areas(self, theme_slug: str) -> List[str]:
        """
        获取主题支持的 Widget 区域
        
        Args:
            theme_slug: 主题标识
            
        Returns:
            Widget 区域列表
        """
        if theme_slug in self.parsed_themes:
            widgets_config = self.parsed_themes[theme_slug].get('widgets', {})
            return widgets_config.get('areas', [])
        return []
    
    def scan_all_themes(self, themes_dir: str = "themes") -> Dict[str, Dict[str, Any]]:
        """
        扫描所有主题的 theme.json
        
        Args:
            themes_dir: 主题目录
            
        Returns:
            {theme_slug: parsed_data} 字典
        """
        themes_path = Path(themes_dir)
        if not themes_path.exists():
            return {}
        
        result = {}
        for theme_dir in themes_path.iterdir():
            if theme_dir.is_dir():
                theme_json = theme_dir / "theme.json"
                if theme_json.exists():
                    try:
                        data = self.parse(str(theme_json))
                        slug = data.get('metadata', {}).get('slug', theme_dir.name)
                        result[slug] = data
                    except Exception as e:
                        print(f"Failed to parse {theme_dir.name}: {e}")
        
        return result


# 全局实例
theme_json_parser = ThemeJsonParser()
