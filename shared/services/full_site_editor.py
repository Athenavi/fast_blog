"""
全站编辑服务 - Full Site Editing (FSE)
提供类似WordPress FSE的可视化网站定制功能

功能:
1. 模板管理系统
2. 模板部件(页头/页脚/侧边栏)
3. 全局样式编辑
4. 导航菜单可视化构建
5. 实时预览
6. 版本历史
"""

import json
import shutil
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


class TemplateManager:
    """
    模板管理器
    
    管理页面模板、存档模板、单页模板等
    """

    def __init__(self, templates_dir: str = "themes/default/templates"):
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # 模板类型定义
        self.template_types = {
            'index': '首页模板',
            'single': '文章详情页模板',
            'archive': '归档页模板',
            'page': '页面模板',
            'search': '搜索结果页模板',
            '404': '404错误页模板',
            'header': '页头模板部件',
            'footer': '页脚模板部件',
            'sidebar': '侧边栏模板部件',
        }

    def get_available_templates(self) -> List[Dict[str, Any]]:
        """获取所有可用模板"""
        templates = []

        for template_type in self.template_types.keys():
            template_file = self.templates_dir / f"{template_type}.html"

            if template_file.exists():
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                templates.append({
                    'type': template_type,
                    'name': self.template_types[template_type],
                    'path': str(template_file),
                    'content': content,
                    'last_modified': datetime.fromtimestamp(
                        template_file.stat().st_mtime
                    ).isoformat(),
                })
            else:
                # 返回默认模板
                templates.append({
                    'type': template_type,
                    'name': self.template_types[template_type],
                    'path': None,
                    'content': self._get_default_template(template_type),
                    'last_modified': None,
                    'is_default': True,
                })

        return templates

    def get_template(self, template_type: str) -> Optional[Dict[str, Any]]:
        """获取指定类型的模板"""
        template_file = self.templates_dir / f"{template_type}.html"

        if not template_file.exists():
            return {
                'type': template_type,
                'name': self.template_types.get(template_type, template_type),
                'content': self._get_default_template(template_type),
                'is_default': True,
            }

        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()

        return {
            'type': template_type,
            'name': self.template_types.get(template_type, template_type),
            'path': str(template_file),
            'content': content,
            'last_modified': datetime.fromtimestamp(
                template_file.stat().st_mtime
            ).isoformat(),
        }

    def save_template(self, template_type: str, content: str) -> bool:
        """保存模板"""
        try:
            template_file = self.templates_dir / f"{template_type}.html"

            # 备份旧模板
            if template_file.exists():
                backup_file = template_file.with_suffix('.html.bak')
                shutil.copy2(template_file, backup_file)

            # 保存新模板
            with open(template_file, 'w', encoding='utf-8') as f:
                f.write(content)

            return True

        except Exception as e:
            print(f"保存模板失败: {e}")
            return False

    def reset_template(self, template_type: str) -> bool:
        """重置模板为默认值"""
        try:
            template_file = self.templates_dir / f"{template_type}.html"

            if template_file.exists():
                template_file.unlink()

            return True

        except Exception as e:
            print(f"重置模板失败: {e}")
            return False

    def _get_default_template(self, template_type: str) -> str:
        """获取默认模板内容"""
        defaults = {
            'index': '''<!-- wp:group {"layout":{"type":"constrained"}} -->
<div class="wp-block-group">
    <!-- wp:heading -->
    <h1>最新文章</h1>
    <!-- /wp:heading -->
    
    <!-- wp:query {"queryId":1,"query":{"perPage":10,"pages":0,"offset":0}} -->
    <div class="wp-block-query">
        <!-- wp:post-template -->
            <!-- wp:post-title {"isLink":true} /-->
            <!-- wp:post-excerpt /-->
            <!-- wp:post-date /-->
        <!-- /wp:post-template -->
        
        <!-- wp:query-pagination -->
            <!-- wp:query-pagination-previous /-->
            <!-- wp:query-pagination-next /-->
        <!-- /wp:query-pagination -->
    </div>
    <!-- /wp:query -->
</div>
<!-- /wp:group -->''',

            'single': '''<!-- wp:group {"layout":{"type":"constrained"}} -->
<div class="wp-block-group">
    <!-- wp:post-title /-->
    <!-- wp:post-date /-->
    <!-- wp:post-content /-->
    <!-- wp:post-terms {"term":"category"} /-->
    <!-- wp:post-terms {"term":"post_tag"} /-->
</div>
<!-- /wp:group -->''',

            'header': '''<!-- wp:group {"layout":{"type":"flex","justifyContent":"space-between"}} -->
<div class="wp-block-group">
    <!-- wp:site-title /-->
    <!-- wp:navigation /-->
</div>
<!-- /wp:group -->''',

            'footer': '''<!-- wp:group {"layout":{"type":"constrained"}} -->
<div class="wp-block-group">
    <!-- wp:paragraph {"align":"center"} -->
    <p class="has-text-align-center">© 2024 FastBlog. All rights reserved.</p>
    <!-- /wp:paragraph -->
</div>
<!-- /wp:group -->''',
        }

        return defaults.get(template_type, '<!-- Empty Template -->')


class GlobalStylesManager:
    """
    全局样式管理器
    
    管理全站的颜色、字体、间距等样式设置
    """

    def __init__(self, styles_file: str = "themes/default/global-styles.json"):
        self.styles_file = Path(styles_file)
        self.styles_file.parent.mkdir(parents=True, exist_ok=True)

        # 默认样式配置
        self.default_styles = {
            'version': 1,
            'colors': {
                'palette': [
                    {'name': 'Primary', 'slug': 'primary', 'color': '#3b82f6'},
                    {'name': 'Secondary', 'slug': 'secondary', 'color': '#64748b'},
                    {'name': 'Accent', 'slug': 'accent', 'color': '#f59e0b'},
                    {'name': 'Background', 'slug': 'background', 'color': '#ffffff'},
                    {'name': 'Foreground', 'slug': 'foreground', 'color': '#1f2937'},
                ],
                'gradients': [],
            },
            'typography': {
                'fontFamilies': [
                    {
                        'name': 'Inter',
                        'slug': 'inter',
                        'fontFamily': 'Inter, system-ui, sans-serif',
                    },
                    {
                        'name': 'Merriweather',
                        'slug': 'merriweather',
                        'fontFamily': 'Merriweather, Georgia, serif',
                    },
                ],
                'fontSizes': [
                    {'name': 'Small', 'slug': 'small', 'size': '14px'},
                    {'name': 'Medium', 'slug': 'medium', 'size': '16px'},
                    {'name': 'Large', 'slug': 'large', 'size': '20px'},
                    {'name': 'Extra Large', 'slug': 'x-large', 'size': '24px'},
                ],
            },
            'spacing': {
                'units': ['px', 'em', 'rem', '%'],
                'defaultSpacing': '16px',
            },
            'layout': {
                'contentSize': '800px',
                'wideSize': '1200px',
            },
        }

    def get_styles(self) -> Dict[str, Any]:
        """获取全局样式配置"""
        if self.styles_file.exists():
            with open(self.styles_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        return deepcopy(self.default_styles)

    def save_styles(self, styles: Dict[str, Any]) -> bool:
        """保存全局样式配置"""
        try:
            styles['version'] = styles.get('version', 1) + 1
            styles['lastModified'] = datetime.now().isoformat()

            with open(self.styles_file, 'w', encoding='utf-8') as f:
                json.dump(styles, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"保存样式失败: {e}")
            return False

    def generate_css(self, styles: Dict[str, Any] = None) -> str:
        """生成CSS变量"""
        if styles is None:
            styles = self.get_styles()

        css_lines = [':root {']

        # 颜色变量
        if 'colors' in styles and 'palette' in styles['colors']:
            for color in styles['colors']['palette']:
                slug = color['slug']
                css_var = f"--color-{slug}"
                css_lines.append(f"  {css_var}: {color['color']};")

        # 字体变量
        if 'typography' in styles and 'fontFamilies' in styles['typography']:
            for font in styles['typography']['fontFamilies']:
                slug = font['slug']
                css_var = f"--font-{slug}"
                css_lines.append(f"  {css_var}: {font['fontFamily']};")

        # 字号变量
        if 'typography' in styles and 'fontSizes' in styles['typography']:
            for size in styles['typography']['fontSizes']:
                slug = size['slug']
                css_var = f"--font-size-{slug}"
                css_lines.append(f"  {css_var}: {size['size']};")

        # 布局变量
        if 'layout' in styles:
            layout = styles['layout']
            if 'contentSize' in layout:
                css_lines.append(f"  --content-width: {layout['contentSize']};")
            if 'wideSize' in layout:
                css_lines.append(f"  --wide-width: {layout['wideSize']};")

        css_lines.append('}')

        return '\n'.join(css_lines)


class NavigationMenuManager:
    """
    导航菜单管理器
    
    管理网站的导航菜单结构
    """

    def __init__(self, menus_file: str = "config/navigation_menus.json"):
        self.menus_file = Path(menus_file)
        self.menus_file.parent.mkdir(parents=True, exist_ok=True)

        # 默认菜单
        self.default_menus = {
            'primary': {
                'name': '主导航',
                'location': 'header',
                'items': [
                    {'label': '首页', 'url': '/', 'order': 1},
                    {'label': '文章', 'url': '/blog', 'order': 2},
                    {'label': '分类', 'url': '/categories', 'order': 3},
                    {'label': '关于', 'url': '/about', 'order': 4},
                ],
            },
            'footer': {
                'name': '页脚导航',
                'location': 'footer',
                'items': [
                    {'label': '隐私政策', 'url': '/privacy', 'order': 1},
                    {'label': '使用条款', 'url': '/terms', 'order': 2},
                    {'label': '联系我们', 'url': '/contact', 'order': 3},
                ],
            },
        }

    def get_menus(self) -> Dict[str, Any]:
        """获取所有菜单"""
        if self.menus_file.exists():
            with open(self.menus_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        return deepcopy(self.default_menus)

    def get_menu(self, menu_location: str) -> Optional[Dict[str, Any]]:
        """获取指定位置的菜单"""
        menus = self.get_menus()
        return menus.get(menu_location)

    def save_menu(self, menu_location: str, menu_data: Dict[str, Any]) -> bool:
        """保存菜单"""
        try:
            menus = self.get_menus()
            menus[menu_location] = menu_data

            with open(self.menus_file, 'w', encoding='utf-8') as f:
                json.dump(menus, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"保存菜单失败: {e}")
            return False

    def add_menu_item(self, menu_location: str, item: Dict[str, Any]) -> bool:
        """添加菜单项"""
        try:
            menus = self.get_menus()

            if menu_location not in menus:
                return False

            # 添加到末尾
            max_order = max([i.get('order', 0) for i in menus[menu_location].get('items', [])], default=0)
            item['order'] = max_order + 1

            menus[menu_location]['items'].append(item)

            return self.save_menu(menu_location, menus[menu_location])

        except Exception as e:
            print(f"添加菜单项失败: {e}")
            return False

    def remove_menu_item(self, menu_location: str, item_index: int) -> bool:
        """删除菜单项"""
        try:
            menus = self.get_menus()

            if menu_location not in menus:
                return False

            items = menus[menu_location].get('items', [])
            if item_index < 0 or item_index >= len(items):
                return False

            items.pop(item_index)

            return self.save_menu(menu_location, menus[menu_location])

        except Exception as e:
            print(f"删除菜单项失败: {e}")
            return False


# 全局单例
template_manager = TemplateManager()
global_styles_manager = GlobalStylesManager()
navigation_menu_manager = NavigationMenuManager()
