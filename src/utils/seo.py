"""
SEO优化工具模块
包含 sitemap 生成、slug / URL 生成、feed 发现标签等工具

## 为什么删掉了 ``get_article_meta_tags`` / ``get_page_meta_tags``

这两个函数**没有任何调用点**（全仓引用只有 ``tests/test_seo.py``，而它只导入本文件
另外三个函数），并且其中的默认配图指向**已经下线的 v2 路由**：
``/api/v2/static/images/default-cover.jpg`` —— 即使被调用也只会产出一个 404 的图。

页面级 meta 标签现在完全由 Nuxt 侧生成，见：
  - ``frontend/web/src/utils/seo.ts``（把相对资源地址补成绝对 URL）
  - ``frontend/web/src/composables/useJsonLd.ts``（JSON-LD 结构化数据）
  - 各页面里的 ``useSeoMeta``（title / description / og:* / twitter:*）
"""


def slugify(text):
    """
    将文本转换为URL友好的slug格式
    """
    import re
    # 转换为小写
    text = text.lower()
    # 替换空格和特殊字符为连字符
    text = re.sub(r'[^a-z0-9\u4e00-\u9fa5\-\s]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def generate_seo_friendly_url(title, model_type='article', id_value=None):
    """
    生成SEO友好的URL
    """
    slug = slugify(title)
    if model_type == 'article':
        return f"/p/{slug}" if slug else f"/{id_value}.html" if id_value else f"/article.html"
    elif model_type == 'category':
        return f"/category/{slug}" if slug else f"/category/{id_value}" if id_value else "/category"
    elif model_type == 'tag':
        return f"/tag/{slug}" if slug else f"/tag/{id_value}" if id_value else "/tag"
    else:
        return f"/{slug}"


def get_feed_discovery_tags(base_url: str = None) -> dict:
    """
    生成RSS/Atom Feed发现标签（用于HTML head）

    Args:
        base_url: 网站基础URL，如果为None则使用默认值

    Returns:
        包含feed link标签的字典
    """
    if not base_url:
        base_url = "http://localhost:8000"

    return {
        'rss_link': f'{base_url}/rss.xml',
        'atom_link': f'{base_url}/atom.xml',
        'rss_xml': f'<link rel="alternate" type="application/rss+xml" title="RSS 2.0" href="{base_url}/rss.xml" />',
        'atom_xml': f'<link rel="alternate" type="application/atom+xml" title="Atom 1.0" href="{base_url}/atom.xml" />'
    }
