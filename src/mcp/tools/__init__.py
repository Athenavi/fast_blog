"""
MCP 工具定义注册表

所有工具的名称、描述、参数模式和处理器函数集中定义在此。
MCPServer 初始化时调用 register_all() 一次性注册全部工具。
"""
from src.mcp.tools import article, content, analytics, media


# 工具定义列表：(name, description, parameters_dict, handler_func)
# parameters_dict: {param_name: {type, description, required, enum?}, ...}
_TOOL_DEFS = [
    # ─── 文章管理 ───
    ("create_article", "创建新文章", {
        "title": {"type": "string", "description": "文章标题", "required": True},
        "content": {"type": "string", "description": "文章内容 (Markdown)", "required": True},
        "category_id": {"type": "integer", "description": "分类ID"},
        "tags": {"type": "string", "description": "标签列表（逗号分隔）"},
        "status": {"type": "string", "description": "状态 (draft/published)", "enum": ["draft", "published"]},
    }, article.create_article),

    ("update_article", "更新现有文章", {
        "article_id": {"type": "integer", "description": "文章ID", "required": True},
        "title": {"type": "string", "description": "新标题"},
        "content": {"type": "string", "description": "新内容 (Markdown)"},
        "status": {"type": "string", "description": "新状态 (draft/published)"},
    }, article.update_article),

    ("delete_article", "删除文章（软删除）", {
        "article_id": {"type": "integer", "description": "文章ID", "required": True},
    }, article.delete_article),

    ("search_articles", "搜索文章（关键词搜索，支持 MeiliSearch）", {
        "query": {"type": "string", "description": "搜索关键词", "required": True},
        "limit": {"type": "integer", "description": "返回数量（默认 10，最多 50）"},
    }, article.search_articles),

    # ─── 分类管理 ───
    ("list_categories", "获取所有分类列表", {}, content.list_categories),
    ("create_category", "创建新分类", {
        "name": {"type": "string", "description": "分类名称", "required": True},
        "slug": {"type": "string", "description": "分类别名"},
        "description": {"type": "string", "description": "分类描述"},
    }, content.create_category),
    ("update_category", "更新分类信息", {
        "category_id": {"type": "integer", "description": "分类ID", "required": True},
        "name": {"type": "string", "description": "新分类名称"},
        "description": {"type": "string", "description": "新分类描述"},
    }, content.update_category),
    ("delete_category", "删除分类", {
        "category_id": {"type": "integer", "description": "分类ID", "required": True},
    }, content.delete_category),

    # ─── 标签 ───
    ("list_tags", "获取所有标签列表（从文章中聚合）", {}, content.list_tags),

    # ─── 评论管理 ───
    ("list_comments", "获取评论列表，支持按状态筛选", {
        "status": {"type": "string", "description": "筛选状态: pending/approved/rejected",
                    "enum": ["pending", "approved", "rejected"]},
        "limit": {"type": "integer", "description": "返回数量（默认 20，最多 50）"},
    }, content.list_comments),
    ("approve_comment", "审核通过评论", {
        "comment_id": {"type": "integer", "description": "评论ID", "required": True},
    }, content.approve_comment),
    ("reject_comment", "拒绝评论", {
        "comment_id": {"type": "integer", "description": "评论ID", "required": True},
    }, content.reject_comment),
    ("delete_comment", "删除评论（管理员）", {
        "comment_id": {"type": "integer", "description": "评论ID", "required": True},
    }, content.delete_comment),

    # ─── 分析工具 ───
    ("get_analytics", "获取博客分析概况（文章数/用户数/评论数/浏览量等）", {}, analytics.get_analytics),
    ("get_trending_articles", "获取热门文章排行", {
        "limit": {"type": "integer", "description": "返回数量（默认 10，最多 30）"},
        "days": {"type": "integer", "description": "统计天数（默认 7）"},
    }, analytics.get_trending_articles),
    ("get_system_stats", "获取系统统计信息", {}, analytics.get_system_stats),

    # ─── 媒体管理 ───
    ("list_media", "获取媒体文件列表", {
        "limit": {"type": "integer", "description": "返回数量（默认 20，最多 50）"},
        "media_type": {"type": "string", "description": "筛选类型: image/video/audio/document"},
    }, media.list_media),
    ("delete_media", "删除媒体文件", {
        "media_id": {"type": "integer", "description": "媒体ID", "required": True},
    }, media.delete_media),

    # ─── SEO ───
    ("generate_seo_description", "为文章生成 SEO 描述（从摘要截取前 160 字符）", {
        "article_id": {"type": "integer", "description": "文章ID", "required": True},
    }, analytics.generate_seo_description),
]


def register_all(mcp_server: "MCPServer") -> None:
    """向 MCPServer 实例注册所有工具"""
    for name, desc, params, handler in _TOOL_DEFS:
        mcp_server.register_tool(name=name, description=desc, parameters=params, handler=handler)
