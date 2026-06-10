"""
MCP (Model Context Protocol) Server 实现

提供 FastBlog 内容与 AI 模型的集成接口，支持 Claude Desktop、Cursor IDE 等客户端连接

功能:
1. 资源暴露 (articles, users, media, categories)
2. 工具调用 (create/update/delete/search articles, manage categories etc.)
3. 认证和权限控制
4. 实时数据同步

参考: Model Context Protocol 规范
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Callable, Optional

# 引入 FastBlog 核心依赖以实现真正的 AI 代理功能
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article import Article, ArticleContent
from shared.models.category import Category
from shared.models.user import User
from shared.models.media import Media
from shared.models.system import SystemSettings
from src.utils.database.main import get_async_session_context

logger = logging.getLogger('mcp_server')


class MCPServer:
    """
    MCP Server 核心实现

    遵循 Model Context Protocol 规范，提供标准化的 AI 集成接口
    """

    def __init__(self, name: str = "fastblog-mcp", version: str = "1.0.0"):
        self.name = name
        self.version = version

        # 资源注册表 {resource_uri: resource_handler}
        self.resources: Dict[str, Callable] = {}

        # 工具注册表 {tool_name: tool_handler}
        self.tools: Dict[str, Callable] = {}

        # 提示词模板
        self.prompts: Dict[str, str] = {}

        # 服务器状态
        self.is_running = False
        self.connected_clients: List[str] = []

        # 初始化内置资源和工具
        self._register_builtin_resources()
        self._register_builtin_tools()
        self._register_builtin_prompts()

    def _register_builtin_resources(self):
        """注册内置资源"""
        self.register_resource(
            uri="fastblog://articles",
            name="Articles",
            description="访问博客文章列表和内容",
            handler=self._get_articles_resource
        )
        self.register_resource(
            uri="fastblog://categories",
            name="Categories",
            description="访问文章分类",
            handler=self._get_categories_resource
        )
        self.register_resource(
            uri="fastblog://users",
            name="Users",
            description="访问用户信息",
            handler=self._get_users_resource
        )
        self.register_resource(
            uri="fastblog://media",
            name="Media Library",
            description="访问媒体文件库",
            handler=self._get_media_resource
        )
        self.register_resource(
            uri="fastblog://settings",
            name="Site Settings",
            description="访问站点配置信息",
            handler=self._get_settings_resource
        )

    def _register_builtin_tools(self):
        """注册内置工具"""
        # 内容管理工具
        self.register_tool(
            name="create_article",
            description="创建新文章",
            parameters={
                "title": {"type": "string", "description": "文章标题", "required": True},
                "content": {"type": "string", "description": "文章内容 (Markdown)", "required": True},
                "category_id": {"type": "integer", "description": "分类ID", "required": False},
                "tags": {"type": "string", "description": "标签列表（逗号分隔）", "required": False},
                "status": {"type": "string", "description": "状态 (draft/published)", "required": False, "enum": ["draft", "published"]},
            },
            handler=self._create_article_tool
        )
        self.register_tool(
            name="update_article",
            description="更新现有文章",
            parameters={
                "article_id": {"type": "integer", "description": "文章ID", "required": True},
                "title": {"type": "string", "description": "新标题", "required": False},
                "content": {"type": "string", "description": "新内容 (Markdown)", "required": False},
                "status": {"type": "string", "description": "新状态 (draft/published)", "required": False},
            },
            handler=self._update_article_tool
        )
        self.register_tool(
            name="delete_article",
            description="删除文章",
            parameters={
                "article_id": {"type": "integer", "description": "文章ID", "required": True},
            },
            handler=self._delete_article_tool
        )
        self.register_tool(
            name="search_articles",
            description="搜索文章（关键词搜索）",
            parameters={
                "query": {"type": "string", "description": "搜索关键词", "required": True},
                "limit": {"type": "integer", "description": "返回数量", "required": False},
            },
            handler=self._search_articles_tool
        )

        # 分类管理工具
        self.register_tool(
            name="list_categories",
            description="获取所有分类列表",
            parameters={},
            handler=self._list_categories_tool
        )
        self.register_tool(
            name="create_category",
            description="创建新分类",
            parameters={
                "name": {"type": "string", "description": "分类名称", "required": True},
                "slug": {"type": "string", "description": "分类别名", "required": False},
                "description": {"type": "string", "description": "分类描述", "required": False},
            },
            handler=self._create_category_tool
        )

        # 评论管理工具
        self.register_tool(
            name="list_comments",
            description="获取评论列表，支持按状态筛选（pending/approved/rejected）",
            parameters={
                "status": {"type": "string", "description": "筛选状态: pending=待审核, approved=已通过, rejected=已拒绝", "required": False, "enum": ["pending", "approved", "rejected"]},
                "limit": {"type": "integer", "description": "返回数量（默认 20，最多 50）", "required": False},
            },
            handler=self._list_comments_tool
        )
        self.register_tool(
            name="approve_comment",
            description="审核通过评论",
            parameters={
                "comment_id": {"type": "integer", "description": "评论ID", "required": True},
            },
            handler=self._approve_comment_tool
        )
        self.register_tool(
            name="reject_comment",
            description="拒绝评论",
            parameters={
                "comment_id": {"type": "integer", "description": "评论ID", "required": True},
            },
            handler=self._reject_comment_tool
        )
        self.register_tool(
            name="delete_comment",
            description="删除评论（管理员）",
            parameters={
                "comment_id": {"type": "integer", "description": "评论ID", "required": True},
            },
            handler=self._delete_comment_tool
        )

        # 统计工具
        self.register_tool(
            name="get_system_stats",
            description="获取系统统计信息（文章数、用户数等）",
            parameters={},
            handler=self._get_system_stats_tool
        )

        # SEO 优化工具
        self.register_tool(
            name="generate_seo_description",
            description="为文章生成 SEO 描述",
            parameters={
                "article_id": {"type": "integer", "description": "文章ID", "required": True},
            },
            handler=self._generate_seo_description_tool
        )

    def _register_builtin_prompts(self):
        """注册内置提示词模板"""
        self.prompts["write_blog_post"] = """
你是一个专业的博客作者。请根据以下主题撰写一篇博客文章：

主题: {topic}
目标读者: {audience}
文章长度: {length}
语气风格: {tone}

要求:
1. 包含引人入胜的开头
2. 使用清晰的小标题组织内容
3. 提供实用的建议和示例
4. 以有力的结论结尾
5. 字数控制在 {length} 字左右
"""
        self.prompts["seo_optimize"] = """
请为以下文章优化 SEO：

标题: {title}
内容摘要: {excerpt}

请提供:
1. 优化的 Meta 描述（150-160字符）
2. 5-8个相关关键词
3. 建议的内部链接
4. 可读性改进建议
"""
        self.prompts["content_audit"] = """
请对以下内容进行审计：

{content}

检查项目:
1. 语法和拼写错误
2. 内容结构和逻辑
3. 可读性评分
4. SEO 优化建议
5. 改进建议
"""

    def register_resource(
            self,
            uri: str,
            name: str,
            description: str,
            handler: Callable,
            mime_type: str = "application/json"
    ):
        """注册资源"""
        self.resources[uri] = {
            "uri": uri,
            "name": name,
            "description": description,
            "handler": handler,
            "mime_type": mime_type,
        }

    def register_tool(
            self,
            name: str,
            description: str,
            parameters: Dict[str, Any],
            handler: Callable
    ):
        """注册工具"""
        self.tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": handler,
        }

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理 MCP 请求"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "resources/read":
                return await self._handle_resource_read(params, request_id)
            elif method == "tools/call":
                return await self._handle_tool_call(params, request_id)
            elif method == "prompts/get":
                return await self._handle_prompt_get(params, request_id)
            elif method == "resources/list":
                return await self._handle_resources_list(request_id)
            elif method == "tools/list":
                return await self._handle_tools_list(request_id)
            elif method == "prompts/list":
                return await self._handle_prompts_list(request_id)
            else:
                return self._error_response(request_id, f"Unknown method: {method}")
        except Exception as e:
            logger.exception(f"MCP request failed: {e}")
            return self._error_response(request_id, str(e))

    async def _handle_resource_read(self, params: Dict, request_id: Any) -> Dict:
        """处理资源读取请求"""
        uri = params.get("uri")
        if uri not in self.resources:
            return self._error_response(request_id, f"Resource not found: {uri}")
        resource = self.resources[uri]
        try:
            data = await resource["handler"](params)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "contents": [{
                        "uri": uri,
                        "mime_type": resource["mime_type"],
                        "text": json.dumps(data, ensure_ascii=False, indent=2, default=str)
                    }]
                }
            }
        except Exception as e:
            logger.exception(f"Resource read failed: {uri}")
            return self._error_response(request_id, f"Failed to read resource: {str(e)}")

    async def _handle_tool_call(self, params: Dict, request_id: Any) -> Dict:
        """处理工具调用请求"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        if tool_name not in self.tools:
            return self._error_response(request_id, f"Tool not found: {tool_name}")
        tool = self.tools[tool_name]
        try:
            result = await tool["handler"](arguments)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False, indent=2, default=str)
                    }]
                }
            }
        except Exception as e:
            logger.exception(f"Tool execution failed: {tool_name}")
            return self._error_response(request_id, f"Tool execution failed: {str(e)}")

    async def _handle_prompt_get(self, params: Dict, request_id: Any) -> Dict:
        """处理提示词获取请求"""
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})
        if prompt_name not in self.prompts:
            return self._error_response(request_id, f"Prompt not found: {prompt_name}")
        template = self.prompts[prompt_name]
        try:
            prompt_text = template.format(**arguments)
        except KeyError as e:
            return self._error_response(request_id, f"Missing argument: {str(e)}")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "description": f"Prompt: {prompt_name}",
                "messages": [{"role": "user", "content": {"type": "text", "text": prompt_text}}]
            }
        }

    async def _handle_resources_list(self, request_id: Any) -> Dict:
        """列出所有资源"""
        resources_list = [
            {"uri": res["uri"], "name": res["name"], "description": res["description"], "mime_type": res["mime_type"]}
            for res in self.resources.values()
        ]
        return {"jsonrpc": "2.0", "id": request_id, "result": {"resources": resources_list}}

    async def _handle_tools_list(self, request_id: Any) -> Dict:
        """列出所有工具（用 OpenAI function-calling 格式）"""
        tools_list = []
        for tool in self.tools.values():
            props = {}
            required = []
            for pname, pdef in tool["parameters"].items():
                ptype = pdef.get("type", "string")
                props[pname] = {
                    "type": ptype,
                    "description": pdef.get("description", ""),
                }
                if ptype == "array":
                    props[pname]["items"] = {"type": "string"}
                if "enum" in pdef:
                    props[pname]["enum"] = pdef["enum"]
                if pdef.get("required", False):
                    required.append(pname)
            tools_list.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": {
                    "type": "object",
                    "properties": props,
                    "required": required,
                },
            })
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools_list}}

    async def _handle_prompts_list(self, request_id: Any) -> Dict:
        """列出所有提示词"""
        prompts_list = [{"name": name, "description": f"Template for {name}"} for name in self.prompts.keys()]
        return {"jsonrpc": "2.0", "id": request_id, "result": {"prompts": prompts_list}}

    # ==================== 资源处理器（真实数据库查询） ====================

    async def _get_articles_resource(self, params: Dict) -> List[Dict]:
        """获取文章列表"""
        limit = params.get("limit", 20)
        async with get_async_session_context() as db:
            query = select(Article).where(Article.status == 1).order_by(Article.created_at.desc()).limit(limit)
            result = await db.execute(query)
            articles = result.scalars().all()
            return [a.to_dict() for a in articles]

    async def _get_categories_resource(self, params: Dict) -> List[Dict]:
        """获取分类列表"""
        async with get_async_session_context() as db:
            query = select(Category).order_by(Category.sort_order.asc(), Category.id.asc())
            result = await db.execute(query)
            categories = result.scalars().all()
            return [{"id": c.id, "name": c.name, "slug": c.slug, "description": c.description}
                    for c in categories]

    async def _get_users_resource(self, params: Dict) -> List[Dict]:
        """获取用户列表"""
        async with get_async_session_context() as db:
            query = select(User).limit(50)
            result = await db.execute(query)
            users = result.scalars().all()
            return [{
                "id": u.id, "username": u.username, "email": u.email,
                "role": "admin" if getattr(u, 'is_superuser', False) else "user",
                "is_active": getattr(u, 'is_active', True),
            } for u in users]

    async def _get_media_resource(self, params: Dict) -> List[Dict]:
        """获取媒体列表"""
        async with get_async_session_context() as db:
            try:
                query = select(Media).order_by(Media.created_at.desc()).limit(50)
                result = await db.execute(query)
                media_list = result.scalars().all()
                return [{"id": m.id, "filename": m.filename or m.original_name or "unknown",
                         "url": m.url or f"/media/{m.filename or ''}", "mime_type": getattr(m, 'mime_type', ''),
                         "size": getattr(m, 'file_size', 0), "alt_text": getattr(m, 'alt_text', '')}
                        for m in media_list]
            except Exception:
                pass
        # Fallback: 扫描 media 目录
        media_dir = Path("static/uploads")
        if media_dir.exists():
            files = []
            for f in list(media_dir.iterdir())[:50]:
                if f.is_file():
                    files.append({"filename": f.name, "url": f"/static/uploads/{f.name}", "size": f.stat().st_size})
            return files
        return []

    async def _get_settings_resource(self, params: Dict) -> Dict:
        """获取站点设置"""
        async with get_async_session_context() as db:
            try:
                query = select(SystemSettings).limit(50)
                result = await db.execute(query)
                settings = result.scalars().all()
                site_settings = {s.setting_key: s.setting_value for s in settings if hasattr(s, 'setting_key')}
                return {
                    "site_name": site_settings.get("site_name", "FastBlog"),
                    "site_url": site_settings.get("site_url", "http://localhost:9421"),
                    "language": site_settings.get("default_language", "zh-CN"),
                    "description": site_settings.get("site_description", ""),
                }
            except Exception:
                pass
        return {"site_name": "FastBlog", "site_url": "http://localhost:9421", "language": "zh-CN"}

    # ==================== 工具处理器（真实数据库操作） ====================

    async def _create_article_tool(self, arguments: Dict) -> Dict:
        """创建文章工具"""
        title = arguments.get("title", "").strip()
        content = arguments.get("content", "").strip()
        status_str = arguments.get("status", "draft")
        category_id = arguments.get("category_id")
        tags = arguments.get("tags", "")

        if not title:
            raise ValueError("文章标题不能为空")
        if not content:
            raise ValueError("文章内容不能为空")

        now = datetime.now(timezone.utc)
        slug = title.lower().replace(" ", "-")[:200]

        async with get_async_session_context() as db:
            try:
                # 创建文章
                new_article = Article(
                    title=title,
                    slug=slug,
                    excerpt=content[:200],
                    user=1,  # 默认管理员
                    category=category_id if category_id else None,
                    tags_list=tags,
                    status=1 if status_str == "published" else 0,
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_article)
                await db.flush()

                # 保存内容
                article_content = ArticleContent(
                    article_id=new_article.id,
                    content=content,
                    created_at=now,
                    updated_at=now,
                )
                db.add(article_content)
                await db.commit()

                return {
                    "success": True,
                    "message": f"文章「{title}」创建成功",
                    "article_id": new_article.id,
                    "status": status_str,
                }
            except Exception as e:
                await db.rollback()
                logger.exception("创建文章失败")
                raise ValueError(f"创建文章失败: {str(e)}")

    async def _update_article_tool(self, arguments: Dict) -> Dict:
        """更新文章工具"""
        article_id = arguments.get("article_id")
        if not article_id:
            raise ValueError("文章ID不能为空")

        now = datetime.now(timezone.utc)
        async with get_async_session_context() as db:
            query = select(Article).where(Article.id == int(article_id))
            result = await db.execute(query)
            article = result.scalar_one_or_none()
            if not article:
                raise ValueError(f"文章 #{article_id} 不存在")

            if "title" in arguments:
                article.title = arguments["title"].strip()
            if "status" in arguments:
                article.status = 1 if arguments["status"] == "published" else 0
            if "content" in arguments:
                content_text = arguments["content"].strip()
                content_q = select(ArticleContent).where(ArticleContent.article_id == int(article_id))
                content_r = await db.execute(content_q)
                ac = content_r.scalar_one_or_none()
                if ac:
                    ac.content = content_text
                    ac.updated_at = now
                else:
                    db.add(ArticleContent(article_id=int(article_id), content=content_text, created_at=now, updated_at=now))

            article.updated_at = now
            await db.commit()

            return {
                "success": True,
                "message": f"文章 #{article_id} 更新成功",
                "article_id": article_id,
            }

    async def _delete_article_tool(self, arguments: Dict) -> Dict:
        """删除文章（软删除）"""
        article_id = arguments.get("article_id")
        if not article_id:
            raise ValueError("文章ID不能为空")

        async with get_async_session_context() as db:
            query = select(Article).where(Article.id == int(article_id))
            result = await db.execute(query)
            article = result.scalar_one_or_none()
            if not article:
                raise ValueError(f"文章 #{article_id} 不存在")

            article.status = -1  # 软删除
            article.updated_at = datetime.now(timezone.utc)
            await db.commit()

            return {
                "success": True,
                "message": f"文章 #{article_id} 已删除",
                "article_id": article_id,
            }

    async def _search_articles_tool(self, arguments: Dict) -> List[Dict]:
        """搜索文章工具"""
        query_text = arguments.get("query", "").strip()
        limit = min(arguments.get("limit", 10), 50)

        if not query_text:
            raise ValueError("搜索关键词不能为空")

        # 尝试 MeiliSearch
        try:
            from shared.services.integrations.meilisearch_service import meilisearch_service
            result = await meilisearch_service.search(query=query_text, page=1, per_page=limit)
            if result and 'articles' in result:
                hits = result['articles']
                return [{
                    "id": h.get("id"), "title": h.get("title", ""),
                    "excerpt": h.get("excerpt", ""), "slug": h.get("slug", ""),
                    "category_name": h.get("category_name", ""),
                    "author_name": h.get("author_name", ""),
                } for h in hits]
        except Exception as e:
            logger.warning(f"MeiliSearch 不可用，回退到数据库搜索: {e}")

        # 回退：数据库 LIKE 搜索
        async with get_async_session_context() as db:
            pattern = f"%{query_text}%"
            query = (
                select(Article)
                .where(Article.status == 1)
                .where(Article.title.ilike(pattern) | (Article.excerpt.ilike(pattern)))
                .order_by(Article.views.desc())
                .limit(limit)
            )
            result = await db.execute(query)
            articles = result.scalars().all()
            return [{"id": a.id, "title": a.title, "excerpt": a.excerpt or "", "slug": a.slug or ""}
                    for a in articles]

    async def _list_categories_tool(self, arguments: Dict) -> List[Dict]:
        """获取分类列表"""
        async with get_async_session_context() as db:
            query = select(Category).order_by(Category.sort_order.asc(), Category.id.asc())
            result = await db.execute(query)
            categories = result.scalars().all()
            return [{"id": c.id, "name": c.name, "slug": c.slug or "",
                     "description": c.description or "", "articles_count": getattr(c, 'articles_count', 0)}
                    for c in categories]

    async def _create_category_tool(self, arguments: Dict) -> Dict:
        """创建新分类"""
        name = arguments.get("name", "").strip()
        if not name:
            raise ValueError("分类名称不能为空")

        slug = arguments.get("slug") or name.lower().replace(" ", "-")
        description = arguments.get("description", "")

        now = datetime.now(timezone.utc)
        async with get_async_session_context() as db:
            try:
                new_cat = Category(
                    name=name, slug=slug, description=description,
                    created_at=now, updated_at=now,
                )
                db.add(new_cat)
                await db.commit()
                return {
                    "success": True,
                    "message": f"分类「{name}」创建成功",
                    "category_id": new_cat.id,
                }
            except Exception as e:
                await db.rollback()
                raise ValueError(f"创建分类失败: {str(e)}")

    # ==================== 评论管理工具 ====================

    async def _list_comments_tool(self, arguments: Dict) -> Dict:
        """获取评论列表（支持状态筛选）"""
        status = arguments.get("status", "").strip().lower()
        limit = min(arguments.get("limit", 20), 50)

        async with get_async_session_context() as db:
            try:
                query = select(Comment).order_by(Comment.created_at.desc()).limit(limit)

                if status == "pending":
                    query = query.where(Comment.is_approved == False)
                elif status == "approved":
                    query = query.where(Comment.is_approved == True)
                # rejected 通过 is_approved=False + spam_score 判断（简化：is_approved=False 且 spam_score > 0.5）
                # 实际用 status 字段判断，这里简单处理

                result = await db.execute(query)
                comments = result.scalars().all()

                return {
                    "success": True,
                    "comments": [
                        {
                            "id": c.id,
                            "article_id": c.article_id,
                            "author": c.author_name or f"用户 #{c.user_id}" if c.user_id else "匿名",
                            "content": c.content[:500] if c.content else "",
                            "is_approved": c.is_approved,
                            "likes": c.likes or 0,
                            "created_at": c.created_at.isoformat() if c.created_at else "",
                        }
                        for c in comments
                    ],
                    "total": len(comments),
                }
            except Exception as e:
                logger.exception("获取评论列表失败")
                return {"success": False, "error": f"获取评论列表失败: {str(e)}"}

    async def _approve_comment_tool(self, arguments: Dict) -> Dict:
        """审核通过评论"""
        comment_id = arguments.get("comment_id")
        if not comment_id:
            raise ValueError("评论ID不能为空")

        async with get_async_session_context() as db:
            try:
                query = select(Comment).where(Comment.id == int(comment_id))
                result = await db.execute(query)
                comment = result.scalar_one_or_none()
                if not comment:
                    raise ValueError(f"评论 #{comment_id} 不存在")

                comment.is_approved = True
                comment.updated_at = datetime.now(timezone.utc)
                await db.commit()

                return {
                    "success": True,
                    "message": f"评论 #{comment_id} 已审核通过",
                    "comment_id": comment_id,
                }
            except ValueError:
                raise
            except Exception as e:
                await db.rollback()
                logger.exception(f"审核评论失败: {e}")
                raise ValueError(f"审核评论失败: {str(e)}")

    async def _reject_comment_tool(self, arguments: Dict) -> Dict:
        """拒绝评论"""
        comment_id = arguments.get("comment_id")
        if not comment_id:
            raise ValueError("评论ID不能为空")

        async with get_async_session_context() as db:
            try:
                query = select(Comment).where(Comment.id == int(comment_id))
                result = await db.execute(query)
                comment = result.scalar_one_or_none()
                if not comment:
                    raise ValueError(f"评论 #{comment_id} 不存在")

                comment.is_approved = False
                comment.updated_at = datetime.now(timezone.utc)
                await db.commit()

                return {
                    "success": True,
                    "message": f"评论 #{comment_id} 已拒绝",
                    "comment_id": comment_id,
                }
            except ValueError:
                raise
            except Exception as e:
                await db.rollback()
                logger.exception(f"拒绝评论失败: {e}")
                raise ValueError(f"拒绝评论失败: {str(e)}")

    async def _delete_comment_tool(self, arguments: Dict) -> Dict:
        """删除评论（管理员）"""
        comment_id = arguments.get("comment_id")
        if not comment_id:
            raise ValueError("评论ID不能为空")

        async with get_async_session_context() as db:
            try:
                query = select(Comment).where(Comment.id == int(comment_id))
                result = await db.execute(query)
                comment = result.scalar_one_or_none()
                if not comment:
                    raise ValueError(f"评论 #{comment_id} 不存在")

                await db.delete(comment)
                await db.commit()

                return {
                    "success": True,
                    "message": f"评论 #{comment_id} 已删除",
                    "comment_id": comment_id,
                }
            except ValueError:
                raise
            except Exception as e:
                await db.rollback()
                logger.exception(f"删除评论失败: {e}")
                raise ValueError(f"删除评论失败: {str(e)}")

    async def _get_system_stats_tool(self, arguments: Dict) -> Dict:
        """获取系统统计信息"""
        async with get_async_session_context() as db:
            try:
                article_count_q = select(func.count(Article.id)).where(Article.status == 1)
                article_count = (await db.execute(article_count_q)).scalar() or 0

                draft_count_q = select(func.count(Article.id)).where(Article.status == 0)
                draft_count = (await db.execute(draft_count_q)).scalar() or 0

                user_count_q = select(func.count(User.id))
                user_count = (await db.execute(user_count_q)).scalar() or 0

                category_count_q = select(func.count(Category.id))
                category_count = (await db.execute(category_count_q)).scalar() or 0

                total_views_q = select(func.coalesce(func.sum(Article.views), 0)).where(Article.status == 1)
                total_views = (await db.execute(total_views_q)).scalar() or 0

                return {
                    "published_articles": article_count,
                    "draft_articles": draft_count,
                    "total_articles": article_count + draft_count,
                    "total_users": user_count,
                    "total_categories": category_count,
                    "total_views": total_views,
                }
            except Exception as e:
                logger.exception("获取统计数据失败")
                return {"error": str(e)}

    async def _generate_seo_description_tool(self, arguments: Dict) -> Dict:
        """生成 SEO 描述（从文章摘要生成）"""
        article_id = arguments.get("article_id")
        if not article_id:
            raise ValueError("文章ID不能为空")

        async with get_async_session_context() as db:
            query = select(Article).where(Article.id == int(article_id))
            result = await db.execute(query)
            article = result.scalar_one_or_none()
            if not article:
                raise ValueError(f"文章 #{article_id} 不存在")

            title = article.title or ""
            excerpt = article.excerpt or ""
            # 从摘要生成 Meta Description（截取前160字符）
            meta_desc = excerpt[:160] if excerpt else title[:160]
            # 提取关键词（从标题和标签）
            keywords = []
            if title:
                keywords.extend([w.strip() for w in title.replace(" ", ",").split(",") if w.strip()])
            if article.tags_list:
                keywords.extend([t.strip() for t in article.tags_list.split(",") if t.strip()])

            return {
                "success": True,
                "article_id": article_id,
                "seo_description": meta_desc,
                "keywords": list(set(keywords))[:8],
                "title": title,
            }

    # ==================== 辅助方法 ====================

    def _error_response(self, request_id: Any, error_message: str) -> Dict:
        """生成错误响应"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32000, "message": error_message},
        }

    def get_server_info(self) -> Dict:
        """获取服务器信息"""
        return {
            "name": self.name,
            "version": self.version,
            "resources_count": len(self.resources),
            "tools_count": len(self.tools),
            "prompts_count": len(self.prompts),
        }

    def get_openai_tools(self) -> List[Dict]:
        """获取 OpenAI function-calling 格式的工具列表"""
        tools = []
        for tool in self.tools.values():
            props = {}
            required = []
            for pname, pdef in tool["parameters"].items():
                ptype = pdef.get("type", "string")
                desc = pdef.get("description", "")
                props[pname] = {"type": ptype, "description": desc}
                if ptype == "array":
                    props[pname]["items"] = {"type": "string"}
                if "enum" in pdef:
                    props[pname]["enum"] = pdef["enum"]
                if pdef.get("required", False):
                    required.append(pname)
            tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": {
                        "type": "object",
                        "properties": props,
                        "required": required,
                    },
                },
            })
        return tools


# 全局实例
mcp_server = MCPServer()
