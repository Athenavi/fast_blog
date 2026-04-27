"""
主题模板层级加载器
类似WordPress Template Hierarchy,实现智能模板查找
"""
from pathlib import Path
from typing import Dict, Any, Optional, List

# 常量定义
DEFAULT_THEME = 'default'
TEMPLATE_EXT = '.html'
FALLBACK_TEMPLATE = 'index.html'


class TemplateLoader:
    """模板加载器服务"""
    
    def __init__(self):
        self.themes_dir = Path(__file__).parent.parent.parent / "django_blog" / "themes"
        self._path_cache = {}  # 缓存路径检查结果

    def _get_theme_dir(self, theme: str) -> Optional[Path]:
        """
        获取主题目录（带缓存）
        
        Args:
            theme: 主题名称
            
        Returns:
            主题目录路径或None
        """
        if theme not in self._path_cache:
            theme_dir = self.themes_dir / theme
            self._path_cache[theme] = theme_dir if theme_dir.exists() else None
        return self._path_cache[theme]

    def _find_template(self, theme_dir: Path, *names: str) -> Optional[Path]:
        """
        在主题目录中查找第一个存在的模板
        
        Args:
            theme_dir: 主题目录
            *names: 模板名称列表
            
        Returns:
            找到的第一个模板路径或None
        """
        for name in names:
            if name:  # 跳过空字符串
                template_file = theme_dir / f"{name}{TEMPLATE_EXT}"
                if template_file.exists():
                    return template_file
        return None

    def find_template(self, template_name: str, theme: str = DEFAULT_THEME) -> Optional[Path]:
        """
        查找模板文件
        
        Args:
            template_name: 模板名称(如 single, archive, page等)
            theme: 主题名称
            
        Returns:
            模板文件路径或None
        """
        theme_dir = self._get_theme_dir(theme)
        if not theme_dir:
            return None

        return self._find_template(theme_dir, template_name)

    def resolve_article_template(self, article: Dict[str, Any], theme: str = DEFAULT_THEME) -> Optional[Path]:
        """
        解析文章详情页模板(按WordPress层级)
        
        查找顺序:
        1. single-{post_type}-{slug}.html
        2. single-{post_type}.html
        3. single-{id}.html
        4. single.html
        5. index.html
        
        Args:
            article: 文章数据
            theme: 主题名称
            
        Returns:
            匹配的模板路径
        """
        theme_dir = self._get_theme_dir(theme)
        if not theme_dir:
            return self._fallback_to_index(theme)
        
        post_type = article.get('post_type', 'post')
        slug = article.get('slug', '')
        article_id = article.get('id', 0)

        # 构建候选模板列表
        candidates = [
            f"single-{post_type}-{slug}" if slug else None,
            f"single-{post_type}",
            f"single-{article_id}" if article_id else None,
            "single",
        ]

        # 查找第一个存在的模板
        template = self._find_template(theme_dir, *candidates)
        if template:
            return template

        # Fallback到index.html
        return self._fallback_to_index(theme)

    def resolve_page_template(self, page: Dict[str, Any], theme: str = DEFAULT_THEME) -> Optional[Path]:
        """
        解析页面模板
        
        查找顺序:
        1. page-{slug}.html
        2. page-{id}.html
        3. page.html
        4. index.html
        
        Args:
            page: 页面数据
            theme: 主题名称
            
        Returns:
            匹配的模板路径
        """
        theme_dir = self._get_theme_dir(theme)
        if not theme_dir:
            return self._fallback_to_index(theme)
        
        slug = page.get('slug', '')
        page_id = page.get('id', 0)

        # 构建候选模板列表
        candidates = [
            f"page-{slug}" if slug else None,
            f"page-{page_id}" if page_id else None,
            "page",
        ]

        template = self._find_template(theme_dir, *candidates)
        if template:
            return template
        
        return self._fallback_to_index(theme)
    
    def resolve_archive_template(self, archive_type: str, term_slug: str = '',
                                 theme: str = DEFAULT_THEME) -> Optional[Path]:
        """
        解析归档页模板
        
        查找顺序:
        - category: category-{slug}.html → category.html → archive.html → index.html
        - tag: tag-{slug}.html → tag.html → archive.html → index.html
        - author: author-{id}.html → author.html → archive.html → index.html
        - date: date.html → archive.html → index.html
        
        Args:
            archive_type: 归档类型(category/tag/author/date)
            term_slug: 术语slug(分类/标签slug或作者ID)
            theme: 主题名称
            
        Returns:
            匹配的模板路径
        """
        theme_dir = self._get_theme_dir(theme)
        if not theme_dir:
            return self._fallback_to_index(theme)

        # 定义各类型的模板前缀和回退链
        type_configs = {
            'category': ([f"category-{term_slug}" if term_slug else None, "category"], "archive"),
            'tag': ([f"tag-{term_slug}" if term_slug else None, "tag"], "archive"),
            'author': ([f"author-{term_slug}" if term_slug else None, "author"], "archive"),
            'date': (["date"], "archive"),
        }

        if archive_type in type_configs:
            specific_templates, fallback = type_configs[archive_type]

            # 先查找特定模板
            template = self._find_template(theme_dir, *specific_templates)
            if template:
                return template

            # 回退到archive.html
            template = self._find_template(theme_dir, fallback)
            if template:
                return template
        
        # Final fallback: index.html
        return self._fallback_to_index(theme)

    def resolve_search_template(self, theme: str = DEFAULT_THEME) -> Optional[Path]:
        """
        解析搜索结果模板
        
        Args:
            theme: 主题名称
            
        Returns:
            模板路径
        """
        theme_dir = self._get_theme_dir(theme)
        if not theme_dir:
            return self._fallback_to_index(theme)

        template = self._find_template(theme_dir, "search")
        return template if template else self._fallback_to_index(theme)

    def resolve_404_template(self, theme: str = DEFAULT_THEME) -> Optional[Path]:
        """
        解析404页面模板
        
        Args:
            theme: 主题名称
            
        Returns:
            模板路径
        """
        theme_dir = self._get_theme_dir(theme)
        if not theme_dir:
            return None

        template = self._find_template(theme_dir, "404")
        return template if template else self._fallback_to_index(theme)

    def resolve_home_template(self, theme: str = DEFAULT_THEME) -> Optional[Path]:
        """
        解析首页模板
        
        Args:
            theme: 主题名称
            
        Returns:
            模板路径
        """
        theme_dir = self._get_theme_dir(theme)
        if not theme_dir:
            return self._fallback_to_index(theme)
        
        # home.html优先于index.html
        template = self._find_template(theme_dir, "home")
        return template if template else self._fallback_to_index(theme)

    def _fallback_to_index(self, theme: str = DEFAULT_THEME) -> Optional[Path]:
        """
        回退到index.html
        
        Args:
            theme: 主题名称
            
        Returns:
            index.html路径或None
        """
        theme_dir = self._get_theme_dir(theme)
        if not theme_dir:
            return None

        return self._find_template(theme_dir, FALLBACK_TEMPLATE)

    def get_available_templates(self, theme: str = DEFAULT_THEME) -> List[str]:
        """
        获取主题可用的所有模板
        
        Args:
            theme: 主题名称
            
        Returns:
            模板名称列表
        """
        theme_dir = self._get_theme_dir(theme)
        if not theme_dir:
            return []

        return sorted([file.stem for file in theme_dir.glob(f"*{TEMPLATE_EXT}")])
    
    def get_template_hierarchy_info(self) -> Dict[str, Any]:
        """
        获取模板层级说明信息
        
        Returns:
            层级说明
        """
        return {
            'article_detail': [
                'single-{post_type}-{slug}.html',
                'single-{post_type}.html',
                'single-{id}.html',
                'single.html',
                'index.html',
            ],
            'page_detail': [
                'page-{slug}.html',
                'page-{id}.html',
                'page.html',
                'index.html',
            ],
            'category_archive': [
                'category-{slug}.html',
                'category.html',
                'archive.html',
                'index.html',
            ],
            'tag_archive': [
                'tag-{slug}.html',
                'tag.html',
                'archive.html',
                'index.html',
            ],
            'author_archive': [
                'author-{id}.html',
                'author.html',
                'archive.html',
                'index.html',
            ],
            'search': ['search.html', 'index.html'],
            '404': ['404.html', 'index.html'],
            'home': ['home.html', 'index.html'],
        }


# 单例实例
template_loader = TemplateLoader()
