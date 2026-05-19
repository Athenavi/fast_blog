"""
子主题服务

实现类似 WordPress 的子主题功能:
1. 主题继承系统 - 父主题/子主题关系
2. 模板覆盖机制 - 子主题可以覆盖父主题的模板
3. 样式追加/覆盖 - 子主题可以扩展或覆盖父主题样式
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from shared.services.themes.theme_manager.theme_system import theme_manager


class ChildThemeService:
    """
    子主题服务
    
    提供子主题的创建、管理和模板解析功能
    """

    def __init__(self):
        self.themes_dir = theme_manager.themes_dir

    def create_child_theme(
            self,
            parent_slug: str,
            child_name: str,
            child_slug: str = None,
            description: str = "",
            author: str = ""
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        创建子主题
        
        Args:
            parent_slug: 父主题 slug
            child_name: 子主题名称
            child_slug: 子主题 slug（可选，默认基于名称生成）
            description: 子主题描述
            author: 作者信息
            
        Returns:
            (成功标志, 消息, 子主题元数据)
        """
        try:
            # 验证父主题存在
            parent_path = self.themes_dir / parent_slug
            if not parent_path.exists():
                return False, f"父主题 '{parent_slug}' 不存在", None

            parent_metadata_file = parent_path / "metadata.json"
            if not parent_metadata_file.exists():
                return False, "父主题缺少 metadata.json 文件", None

            with open(parent_metadata_file, 'r', encoding='utf-8') as f:
                parent_metadata = json.load(f)

            # 生成子主题 slug
            if not child_slug:
                import re
                child_slug = re.sub(r'[^a-z0-9-]', '-', child_name.lower()).strip('-')

            # 检查子主题是否已存在
            child_path = self.themes_dir / child_slug
            if child_path.exists():
                return False, f"子主题 '{child_slug}' 已存在", None

            # 创建子主题目录
            child_path.mkdir(parents=True, exist_ok=True)

            # 创建子主题元数据
            child_metadata = {
                "name": child_name,
                "slug": child_slug,
                "version": "1.0.0",
                "description": description or f"{child_name} - 基于 {parent_metadata.get('name', parent_slug)} 的子主题",
                "author": author or "FastBlog User",
                "author_url": "",
                "theme_url": "",
                "screenshot": "screenshot.png",
                "parent": parent_slug,  # 关键：指定父主题
                "template": parent_slug,  # 模板继承自父主题
                "is_child_theme": True,
                "created_at": datetime.now().isoformat(),
            }

            # 写入元数据文件
            metadata_file = child_path / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(child_metadata, f, indent=2, ensure_ascii=False)

            # 创建空的 style.css（子主题必须有自己的样式文件）
            style_css = child_path / "style.css"
            style_content = f"""/*
Theme Name: {child_name}
Theme URI: 
Description: {child_metadata['description']}
Author: {child_metadata['author']}
Version: {child_metadata['version']}
Template: {parent_slug}
*/

/* 在此添加自定义样式 */
"""
            with open(style_css, 'w', encoding='utf-8') as f:
                f.write(style_content)

            # 创建 functions.php（用于加载父主题样式）
            functions_php = child_path / "functions.php"
            functions_content = """<?php
/**
 * 子主题函数文件
 * 
 * 在这里添加自定义 PHP 代码
 */

// 自动加载父主题样式
function child_theme_enqueue_styles() {
    // 加载父主题样式
    wp_enqueue_style(
        'parent-style',
        get_template_directory_uri() . '/style.css'
    );
    
    // 加载子主题样式（覆盖父主题）
    wp_enqueue_style(
        'child-style',
        get_stylesheet_directory_uri() . '/style.css',
        array('parent-style'),
        wp_get_theme()->get('Version')
    );
}
add_action('wp_enqueue_scripts', 'child_theme_enqueue_styles');
"""
            with open(functions_php, 'w', encoding='utf-8') as f:
                f.write(functions_content)

            # 创建 README 文件
            readme_file = child_path / "README.md"
            readme_content = f"""# {child_name}

{child_metadata['description']}

## 父主题

本主题是基于 **{parent_metadata.get('name', parent_slug)}** 创建的子主题。

## 自定义说明

### 模板覆盖

要覆盖父主题的模板，请在当前目录中创建同名文件。例如：
- 覆盖首页：创建 `index.html`
- 覆盖文章页：创建 `article.html`
- 覆盖分类页：创建 `category.html`

### 样式自定义

在 `style.css` 中添加您的自定义 CSS。子主题的样式会自动加载在父主题样式之后，因此可以覆盖父主题的样式。

### 函数扩展

在 `functions.php` 中添加自定义 PHP 代码。该文件会在父主题的 functions.php 之前加载。

## 更新注意事项

当父主题更新时，子主题的自定义内容不会受到影响。但请注意检查父主题的变更是否影响子主题的兼容性。
"""
            with open(readme_file, 'w', encoding='utf-8') as f:
                f.write(readme_content)

            # 创建示例截图（复制父主题的截图或创建占位符）
            parent_screenshot = parent_path / "screenshot.png"
            child_screenshot = child_path / "screenshot.png"
            if parent_screenshot.exists():
                shutil.copy2(parent_screenshot, child_screenshot)
            else:
                # 创建一个简单的占位符文本文件
                placeholder = child_path / "screenshot.txt"
                with open(placeholder, 'w', encoding='utf-8') as f:
                    f.write("请在此处放置主题截图 (screenshot.png)\n建议尺寸: 800x600 像素")

            return True, f"子主题 '{child_name}' 创建成功", child_metadata

        except Exception as e:
            # 清理可能创建的部分文件
            if child_path and child_path.exists():
                shutil.rmtree(child_path, ignore_errors=True)
            return False, f"创建子主题失败: {str(e)}", None

    def get_parent_theme_info(self, child_slug: str) -> Optional[Dict[str, Any]]:
        """
        获取子主题的父主题信息
        
        Args:
            child_slug: 子主题 slug
            
        Returns:
            父主题信息字典，如果不是子主题则返回 None
        """
        try:
            child_path = self.themes_dir / child_slug
            metadata_file = child_path / "metadata.json"

            if not metadata_file.exists():
                return None

            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            parent_slug = metadata.get('parent') or metadata.get('template')
            if not parent_slug:
                return None

            # 获取父主题信息
            parent_path = self.themes_dir / parent_slug
            parent_metadata_file = parent_path / "metadata.json"

            if not parent_metadata_file.exists():
                return {
                    "slug": parent_slug,
                    "exists": False,
                    "error": "父主题不存在"
                }

            with open(parent_metadata_file, 'r', encoding='utf-8') as f:
                parent_metadata = json.load(f)

            return {
                "slug": parent_slug,
                "exists": True,
                "name": parent_metadata.get('name', parent_slug),
                "version": parent_metadata.get('version', ''),
                "description": parent_metadata.get('description', ''),
            }

        except Exception as e:
            return {
                "error": f"获取父主题信息失败: {str(e)}"
            }

    def list_child_themes(self, parent_slug: str = None) -> List[Dict[str, Any]]:
        """
        列出所有子主题
        
        Args:
            parent_slug: 可选，只列出指定父主题的子主题
            
        Returns:
            子主题列表
        """
        child_themes = []

        for theme_dir in self.themes_dir.iterdir():
            if not theme_dir.is_dir():
                continue

            metadata_file = theme_dir / "metadata.json"
            if not metadata_file.exists():
                continue

            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                # 检查是否是子主题
                is_child = metadata.get('is_child_theme', False) or metadata.get('parent') or metadata.get('template')

                if is_child:
                    parent = metadata.get('parent') or metadata.get('template')

                    # 如果指定了父主题，过滤
                    if parent_slug and parent != parent_slug:
                        continue

                    child_themes.append({
                        "slug": metadata.get('slug', theme_dir.name),
                        "name": metadata.get('name', theme_dir.name),
                        "version": metadata.get('version', ''),
                        "description": metadata.get('description', ''),
                        "parent": parent,
                        "author": metadata.get('author', ''),
                        "created_at": metadata.get('created_at', ''),
                    })

            except Exception:
                continue

        return child_themes

    def resolve_template_with_inheritance(
            self,
            template_name: str,
            theme_slug: str
    ) -> Optional[Path]:
        """
        解析模板（支持子主题继承）
        
        查找顺序：
        1. 子主题中的模板
        2. 父主题中的模板
        
        Args:
            template_name: 模板名称（不含扩展名）
            theme_slug: 主题 slug
            
        Returns:
            模板文件路径，未找到返回 None
        """
        try:
            theme_path = self.themes_dir / theme_slug
            metadata_file = theme_path / "metadata.json"

            if not metadata_file.exists():
                return None

            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # 检查是否是子主题
            parent_slug = metadata.get('parent') or metadata.get('template')

            # 首先在子主题中查找
            child_template = theme_path / f"{template_name}.html"
            if child_template.exists():
                return child_template

            # 如果是子主题且未在子主题中找到，则在父主题中查找
            if parent_slug:
                parent_path = self.themes_dir / parent_slug
                parent_template = parent_path / f"{template_name}.html"
                if parent_template.exists():
                    return parent_template

            return None

        except Exception:
            return None

    def get_theme_hierarchy(self, theme_slug: str) -> List[Dict[str, Any]]:
        """
        获取主题继承层次结构
        
        Args:
            theme_slug: 主题 slug
            
        Returns:
            主题层次结构列表（从当前主题到根主题）
        """
        hierarchy = []
        current_slug = theme_slug
        visited = set()  # 防止循环继承

        while current_slug and current_slug not in visited:
            visited.add(current_slug)

            theme_path = self.themes_dir / current_slug
            metadata_file = theme_path / "metadata.json"

            if not metadata_file.exists():
                break

            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                hierarchy.append({
                    "slug": current_slug,
                    "name": metadata.get('name', current_slug),
                    "version": metadata.get('version', ''),
                    "is_child": bool(metadata.get('parent') or metadata.get('template')),
                })

                # 获取父主题
                current_slug = metadata.get('parent') or metadata.get('template')

            except Exception:
                break

        return hierarchy

    def validate_child_theme(self, child_slug: str) -> Tuple[bool, List[str]]:
        """
        验证子主题的完整性
        
        Args:
            child_slug: 子主题 slug
            
        Returns:
            (是否有效, 错误列表)
        """
        errors = []

        try:
            child_path = self.themes_dir / child_slug
            metadata_file = child_path / "metadata.json"

            if not metadata_file.exists():
                return False, ["缺少 metadata.json 文件"]

            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # 检查是否是子主题
            parent_slug = metadata.get('parent') or metadata.get('template')
            if not parent_slug:
                return False, ["不是子主题（缺少 parent 或 template 字段）"]

            # 检查父主题是否存在
            parent_path = self.themes_dir / parent_slug
            if not parent_path.exists():
                errors.append(f"父主题 '{parent_slug}' 不存在")

            # 检查必需文件
            style_css = child_path / "style.css"
            if not style_css.exists():
                errors.append("缺少 style.css 文件")

            # 检查元数据字段
            required_fields = ['name', 'slug', 'version']
            for field in required_fields:
                if field not in metadata:
                    errors.append(f"缺少必需字段: {field}")

            return len(errors) == 0, errors

        except Exception as e:
            return False, [f"验证失败: {str(e)}"]


# 全局实例
child_theme_service = ChildThemeService()
