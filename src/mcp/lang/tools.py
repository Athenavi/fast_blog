"""
LangChain @tool wrappers for MCP tools.

Each function wraps an MCP tool call so it can be used
with langgraph's ToolNode / create_react_agent.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from src.mcp.server import mcp_server

logger = logging.getLogger('mcp.lang.tools')


async def _call_mcp(name: str, args: Dict[str, Any]) -> str:
    """Execute an MCP tool and return a readable string result."""
    req = {"method": "tools/call", "params": {"name": name, "arguments": args}, "id": "lg"}
    resp = await mcp_server.handle_request(req)
    if "error" in resp:
        return f"❌ {resp['error']['message']}"
    content = resp.get("result", {}).get("content", [])
    text = content[0].get("text", "{}") if content else "{}"
    try:
        data = json.loads(text)
        return json.dumps(data, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        return text


@tool
async def create_article(
    title: str,
    content: str,
    category_id: Optional[int] = None,
    tags: Optional[str] = None,
    status: Optional[str] = "draft",
) -> str:
    """Create a new blog article with the given title and content.

    Args:
        title: The article title
        content: The article body (Markdown)
        category_id: Optional category ID
        tags: Comma-separated tag list
        status: 'draft' or 'published'
    """
    args = {"title": title, "content": content}
    if category_id:
        args["category_id"] = category_id
    if tags:
        args["tags"] = tags
    args["status"] = status or "draft"
    return await _call_mcp("create_article", args)


@tool
async def update_article(
    article_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    status: Optional[str] = None,
) -> str:
    """Update an existing blog article.

    Args:
        article_id: The article ID
        title: New title (optional)
        content: New content (optional)
        status: 'draft' or 'published' (optional)
    """
    args = {"article_id": article_id}
    if title:
        args["title"] = title
    if content:
        args["content"] = content
    if status:
        args["status"] = status
    return await _call_mcp("update_article", args)


@tool
async def delete_article(article_id: int) -> str:
    """Delete a blog article by ID.

    Args:
        article_id: The article ID to delete
    """
    return await _call_mcp("delete_article", {"article_id": article_id})


@tool
async def search_articles(query: str, limit: int = 10) -> str:
    """Search blog articles by keyword.

    Args:
        query: Search keyword(s)
        limit: Max results (default 10)
    """
    return await _call_mcp("search_articles", {"query": query, "limit": limit})


@tool
async def list_categories() -> str:
    """List all article categories."""
    return await _call_mcp("list_categories", {})


@tool
async def create_category(
    name: str,
    slug: Optional[str] = None,
    description: Optional[str] = None,
) -> str:
    """Create a new article category.

    Args:
        name: Category name
        slug: URL slug (auto-generated from name if omitted)
        description: Optional description
    """
    args = {"name": name}
    if slug:
        args["slug"] = slug
    if description:
        args["description"] = description
    return await _call_mcp("create_category", args)


@tool
async def get_system_stats() -> str:
    """Get blog system statistics (article count, user count, etc.)."""
    return await _call_mcp("get_system_stats", {})


# ─── Tool list for ToolNode ─────────────────────────────────────────

MCP_TOOLS = [
    create_article,
    update_article,
    delete_article,
    search_articles,
    list_categories,
    create_category,
    get_system_stats,
]
