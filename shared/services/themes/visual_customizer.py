"""
可视化主题定制器服务 - 增强版

提供实时预览、配置项扩展、CSS变量管理等功能
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class VisualThemeCustomizer:
    """
    可视化主题定制器
    
    功能:
    1. 实时预览引擎 - 生成预览HTML和CSS
    2. 配置项扩展 - 颜色、字体、布局、动画
    3. CSS变量管理 - 自动生成和管理CSS变量
    4. 深色模式适配
    5. 品牌色预设
    6. 设备预览（桌面/平板/手机）
    7. 配置导入/导出
    8. 版本历史管理
    """

    def __init__(self, themes_dir: str = "themes"):
        self.themes_dir = Path(themes_dir)
        self.history_dir = Path("storage/theme_history")
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def generate_preview_html(
            self,
            theme_slug: str,
            config: Dict[str, Any],
            preview_type: str = "article"
    ) -> str:
        """
        生成预览HTML
        
        Args:
            theme_slug: 主题标识
            config: 主题配置
            preview_type: 预览类型（article, homepage, category）
            
        Returns:
            HTML字符串
        """
        css = self.generate_css_variables(config)

        if preview_type == "article":
            html = self._generate_article_preview(theme_slug, config, css)
        elif preview_type == "homepage":
            html = self._generate_homepage_preview(theme_slug, config, css)
        else:
            html = self._generate_article_preview(theme_slug, config, css)

        return html

    def generate_css_variables(self, config: Dict[str, Any]) -> str:
        """
        根据配置生成CSS变量
        
        Args:
            config: 主题配置
            
        Returns:
            CSS变量字符串
        """
        css_lines = [":root {"]

        # 颜色变量
        colors = config.get('colors', {})
        for key, value in colors.items():
            if self._is_valid_color(value):
                css_lines.append(f"  --color-{key}: {value};")

        # 字体变量
        typography = config.get('typography', {})
        if 'fontFamily' in typography:
            css_lines.append(f"  --font-family: {typography['fontFamily']};")
        if 'headingFont' in typography:
            css_lines.append(f"  --font-heading: {typography['headingFont']};")
        if 'fontSize' in typography:
            css_lines.append(f"  --font-size-base: {typography['fontSize']};")
        if 'lineHeight' in typography:
            css_lines.append(f"  --line-height: {typography['lineHeight']};")

        # 布局变量
        layout = config.get('layout', {})
        if 'contentWidth' in layout:
            css_lines.append(f"  --content-width: {layout['contentWidth']};")
        if 'sidebarPosition' in layout:
            css_lines.append(f"  --sidebar-position: {layout['sidebarPosition']};")

        # 组件变量
        components = config.get('components', {})
        if 'borderRadius' in components:
            css_lines.append(f"  --border-radius: {components['borderRadius']};")
        if 'shadowStyle' in components:
            shadow_value = self._get_shadow_value(components['shadowStyle'])
            css_lines.append(f"  --shadow-style: {shadow_value};")

        css_lines.append("}")

        # 深色模式
        dark_colors = config.get('darkColors', {})
        if dark_colors:
            css_lines.append("\n@media (prefers-color-scheme: dark) {")
            css_lines.append("  :root {")
            for key, value in dark_colors.items():
                if self._is_valid_color(value):
                    css_lines.append(f"    --color-{key}: {value};")
            css_lines.append("  }")
            css_lines.append("}")

        return "\n".join(css_lines)

    def get_color_presets(self) -> List[Dict[str, Any]]:
        """
        获取颜色预设方案
        
        Returns:
            颜色预设列表
        """
        presets = [
            {
                "name": "默认蓝色",
                "id": "default-blue",
                "colors": {
                    "primary": "#3b82f6",
                    "secondary": "#64748b",
                    "accent": "#f59e0b",
                    "background": "#ffffff",
                    "foreground": "#1f2937"
                },
                "category": "light"
            },
            {
                "name": "深紫色",
                "id": "deep-purple",
                "colors": {
                    "primary": "#7c3aed",
                    "secondary": "#6b7280",
                    "accent": "#ec4899",
                    "background": "#ffffff",
                    "foreground": "#111827"
                },
                "category": "light"
            },
            {
                "name": "森林绿",
                "id": "forest-green",
                "colors": {
                    "primary": "#059669",
                    "secondary": "#6b7280",
                    "accent": "#f59e0b",
                    "background": "#ffffff",
                    "foreground": "#1f2937"
                },
                "category": "light"
            },
            {
                "name": "日落橙",
                "id": "sunset-orange",
                "colors": {
                    "primary": "#ea580c",
                    "secondary": "#64748b",
                    "accent": "#06b6d4",
                    "background": "#ffffff",
                    "foreground": "#1f2937"
                },
                "category": "light"
            },
            {
                "name": "暗夜黑",
                "id": "midnight-dark",
                "colors": {
                    "primary": "#3b82f6",
                    "secondary": "#9ca3af",
                    "accent": "#f59e0b",
                    "background": "#111827",
                    "foreground": "#f9fafb"
                },
                "category": "dark"
            },
            {
                "name": "深海蓝",
                "id": "ocean-deep",
                "colors": {
                    "primary": "#0ea5e9",
                    "secondary": "#94a3b8",
                    "accent": "#f43f5e",
                    "background": "#0f172a",
                    "foreground": "#f1f5f9"
                },
                "category": "dark"
            }
        ]

        return presets

    def get_font_options(self) -> List[Dict[str, Any]]:
        """
        获取字体选项
        
        Returns:
            字体选项列表
        """
        fonts = [
            {
                "name": "Inter (现代无衬线)",
                "family": "'Inter', system-ui, -apple-system, sans-serif",
                "category": "sans-serif",
                "google_font": True
            },
            {
                "name": "Roboto (经典无衬线)",
                "family": "'Roboto', sans-serif",
                "category": "sans-serif",
                "google_font": True
            },
            {
                "name": "Merriweather (优雅衬线)",
                "family": "'Merriweather', Georgia, serif",
                "category": "serif",
                "google_font": True
            },
            {
                "name": "Playfair Display (标题专用)",
                "family": "'Playfair Display', serif",
                "category": "serif",
                "google_font": True,
                "recommended_for": "headings"
            },
            {
                "name": "Source Sans Pro (清晰易读)",
                "family": "'Source Sans Pro', sans-serif",
                "category": "sans-serif",
                "google_font": True
            },
            {
                "name": "Lato (友好圆润)",
                "family": "'Lato', sans-serif",
                "category": "sans-serif",
                "google_font": True
            },
            {
                "name": "系统默认",
                "family": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                "category": "system",
                "google_font": False
            }
        ]

        return fonts

    def get_layout_options(self) -> Dict[str, Any]:
        """
        获取布局选项
        
        Returns:
            布局选项字典
        """
        return {
            "sidebar_positions": [
                {"value": "left", "label": "左侧边栏"},
                {"value": "right", "label": "右侧边栏"},
                {"value": "none", "label": "无边栏"}
            ],
            "content_widths": [
                {"value": "max-w-3xl", "label": "窄 (768px)"},
                {"value": "max-w-4xl", "label": "中等 (896px)"},
                {"value": "max-w-5xl", "label": "宽 (1024px)"},
                {"value": "max-w-7xl", "label": "超宽 (1280px)"},
                {"value": "full", "label": "全宽"}
            ],
            "header_styles": [
                {"value": "centered", "label": "居中"},
                {"value": "left-aligned", "label": "左对齐"},
                {"value": "magazine", "label": "杂志风格"},
                {"value": "minimal", "label": "极简"}
            ],
            "footer_styles": [
                {"value": "simple", "label": "简单"},
                {"value": "multi-column", "label": "多列"},
                {"value": "minimal", "label": "极简"}
            ]
        }

    def save_config_version(
            self,
            theme_slug: str,
            config: Dict[str, Any],
            note: str = ""
    ) -> bool:
        """
        保存配置版本
        
        Args:
            theme_slug: 主题标识
            config: 主题配置
            note: 版本说明
            
        Returns:
            是否成功
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            version_file = self.history_dir / f"{theme_slug}_{timestamp}.json"

            version_data = {
                "theme_slug": theme_slug,
                "timestamp": datetime.now().isoformat(),
                "note": note,
                "config": config
            }

            with open(version_file, 'w', encoding='utf-8') as f:
                json.dump(version_data, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            print(f"[ThemeCustomizer] Failed to save version: {e}")
            return False

    def get_config_history(
            self,
            theme_slug: str,
            limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取配置历史
        
        Args:
            theme_slug: 主题标识
            limit: 返回数量
            
        Returns:
            历史记录列表
        """
        history_files = sorted(
            self.history_dir.glob(f"{theme_slug}_*.json"),
            reverse=True
        )[:limit]

        history = []
        for file_path in history_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    history.append({
                        "timestamp": data["timestamp"],
                        "note": data.get("note", ""),
                        "file": file_path.name
                    })
            except Exception:
                continue

        return history

    def restore_config_version(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        恢复配置版本
        
        Args:
            filename: 版本文件名
            
        Returns:
            配置数据，失败返回None
        """
        try:
            version_file = self.history_dir / filename

            if not version_file.exists():
                return None

            with open(version_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("config")

        except Exception as e:
            print(f"[ThemeCustomizer] Failed to restore version: {e}")
            return None

    def export_config(self, config: Dict[str, Any]) -> str:
        """
        导出配置为JSON字符串
        
        Args:
            config: 主题配置
            
        Returns:
            JSON字符串
        """
        return json.dumps(config, ensure_ascii=False, indent=2)

    def import_config(self, json_str: str) -> Optional[Dict[str, Any]]:
        """
        从JSON字符串导入配置
        
        Args:
            json_str: JSON字符串
            
        Returns:
            配置字典，失败返回None
        """
        try:
            config = json.loads(json_str)

            # 验证基本结构
            if not isinstance(config, dict):
                return None

            return config

        except Exception as e:
            print(f"[ThemeCustomizer] Failed to import config: {e}")
            return None

    def _is_valid_color(self, color: str) -> bool:
        """验证颜色值是否有效"""
        if not color or not isinstance(color, str):
            return False

        # Hex颜色
        if re.match(r'^#[0-9A-Fa-f]{6}$', color):
            return True
        if re.match(r'^#[0-9A-Fa-f]{3}$', color):
            return True

        # RGB/RGBA
        if re.match(r'^rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+', color):
            return True

        # HSL/HSLA
        if re.match(r'^hsla?\(\s*\d+\s*,\s*\d+%', color):
            return True

        # 命名颜色
        named_colors = {
            'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink',
            'white', 'black', 'gray', 'grey', 'brown', 'cyan', 'magenta'
        }
        if color.lower() in named_colors:
            return True

        return False

    def _get_shadow_value(self, style: str) -> str:
        """获取阴影值"""
        shadows = {
            "none": "none",
            "small": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
            "medium": "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
            "large": "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
            "xl": "0 20px 25px -5px rgba(0, 0, 0, 0.1)"
        }
        return shadows.get(style, shadows["medium"])

    def _generate_article_preview(
            self,
            theme_slug: str,
            config: Dict[str, Any],
            css: str
    ) -> str:
        """生成文章预览HTML"""
        layout = config.get('layout', {})
        sidebar_pos = layout.get('sidebarPosition', 'right')
        content_width = layout.get('contentWidth', 'max-w-4xl')

        sidebar_class = ""
        if sidebar_pos == "left":
            sidebar_class = "flex-row-reverse"
        elif sidebar_pos == "none":
            sidebar_class = ""

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>主题预览</title>
    <style>
        {css}
        
        body {{
            font-family: var(--font-family, system-ui);
            font-size: var(--font-size-base, 16px);
            line-height: var(--line-height, 1.6);
            color: var(--color-foreground, #1f2937);
            background-color: var(--color-background, #ffffff);
            margin: 0;
            padding: 0;
        }}
        
        .preview-container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .content-wrapper {{
            display: flex;
            gap: 2rem;
            {sidebar_class}
        }}
        
        .main-content {{
            flex: 1;
            max-width: {content_width if content_width != 'full' else '100%'};
        }}
        
        .sidebar {{
            width: 300px;
            flex-shrink: 0;
        }}
        
        .article-header {{
            margin-bottom: 2rem;
        }}
        
        .article-title {{
            font-family: var(--font-heading, inherit);
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
            color: var(--color-foreground);
        }}
        
        .article-meta {{
            color: var(--color-secondary, #64748b);
            font-size: 0.9rem;
        }}
        
        .article-content {{
            line-height: 1.8;
        }}
        
        .article-content p {{
            margin-bottom: 1.5rem;
        }}
        
        .article-content h2 {{
            font-family: var(--font-heading, inherit);
            font-size: 1.8rem;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }}
        
        .widget {{
            background: var(--color-muted, #f3f4f6);
            padding: 1.5rem;
            border-radius: var(--border-radius, 0.5rem);
            margin-bottom: 1.5rem;
        }}
        
        .widget-title {{
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: var(--color-primary, #3b82f6);
        }}
    </style>
</head>
<body>
    <div class="preview-container">
        <div class="content-wrapper">
            <main class="main-content">
                <article>
                    <header class="article-header">
                        <h1 class="article-title">示例文章标题</h1>
                        <div class="article-meta">
                            <span>作者：管理员</span> · 
                            <span>2024年1月1日</span> · 
                            <span>阅读时间：5分钟</span>
                        </div>
                    </header>
                    
                    <div class="article-content">
                        <p>这是一篇示例文章的预览内容。您可以在左侧面板中调整各种设置，实时查看效果。</p>
                        
                        <h2>副标题示例</h2>
                        <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
                        
                        <p>Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.</p>
                    </div>
                </article>
            </main>
            
            {self._generate_sidebar_html() if sidebar_pos != 'none' else ''}
        </div>
    </div>
</body>
</html>"""

        return html

    def _generate_homepage_preview(
            self,
            theme_slug: str,
            config: Dict[str, Any],
            css: str
    ) -> str:
        """生成首页预览HTML"""
        # 简化实现，与文章预览类似
        return self._generate_article_preview(theme_slug, config, css)

    def _generate_sidebar_html(self) -> str:
        """生成侧边栏HTML"""
        return """
            <aside class="sidebar">
                <div class="widget">
                    <h3 class="widget-title">关于本站</h3>
                    <p>这是一个博客网站的侧边栏示例。</p>
                </div>
                
                <div class="widget">
                    <h3 class="widget-title">分类目录</h3>
                    <ul style="list-style: none; padding: 0;">
                        <li style="margin-bottom: 0.5rem;">技术教程</li>
                        <li style="margin-bottom: 0.5rem;">生活随笔</li>
                        <li style="margin-bottom: 0.5rem;">读书笔记</li>
                    </ul>
                </div>
                
                <div class="widget">
                    <h3 class="widget-title">标签云</h3>
                    <div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">
                        <span style="background: var(--color-primary); color: white; padding: 0.25rem 0.75rem; border-radius: 1rem; font-size: 0.85rem;">Python</span>
                        <span style="background: var(--color-primary); color: white; padding: 0.25rem 0.75rem; border-radius: 1rem; font-size: 0.85rem;">JavaScript</span>
                        <span style="background: var(--color-primary); color: white; padding: 0.25rem 0.75rem; border-radius: 1rem; font-size: 0.85rem;">Web开发</span>
                    </div>
                </div>
            </aside>
        """


# 全局实例
visual_customizer = VisualThemeCustomizer()
