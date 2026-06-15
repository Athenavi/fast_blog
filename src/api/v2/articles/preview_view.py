"""
草稿预览查看页面 - 后端渲染
"""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import html

from shared.models.article import Article, ArticleContent
from shared.services.articles.draft_preview_service import draft_preview_service
from src.utils.database.main import get_async_session as get_async_db

router = APIRouter(tags=["preview-view"])


def _build_html(title, content_body, cover_image, excerpt, updated_at, view_count, expires_at):
    title_safe = html.escape(title or '无标题')
    cover_image_safe = html.escape(cover_image) if cover_image else ''
    excerpt_safe = html.escape(excerpt) if excerpt else ''
    cover_html = f'<img src="{cover_image_safe}" class="w-full h-64 object-cover rounded-2xl mb-8 shadow-lg"/>' if cover_image else ''
    excerpt_html = f'<p class="text-lg text-gray-500 mb-6">{excerpt_safe}</p>' if excerpt else ''
    date_str = updated_at.strftime('%Y-%m-%d %H:%M') if updated_at else ''
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title_safe} - 预览</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
  .prose {{ max-width: 65ch; margin: 0 auto; }}
  .prose h1 {{ font-size: 1.875rem; font-weight: 700; margin-top: 2rem; margin-bottom: 1rem; }}
  .prose h2 {{ font-size: 1.5rem; font-weight: 600; margin-top: 1.75rem; margin-bottom: 0.75rem; }}
  .prose h3 {{ font-size: 1.25rem; font-weight: 600; margin-top: 1.5rem; margin-bottom: 0.5rem; }}
  .prose p {{ margin-bottom: 1rem; line-height: 1.75; }}
  .prose img {{ max-width: 100%; height: auto; border-radius: 0.5rem; margin: 1.5rem 0; }}
  .prose blockquote {{ border-left: 4px solid #3b82f6; padding-left: 1rem; color: #6b7280; font-style: italic; margin: 1.5rem 0; }}
  .prose ul, .prose ol {{ padding-left: 1.5rem; margin-bottom: 1rem; }}
  .prose li {{ margin-bottom: 0.25rem; }}
  .prose a {{ color: #2563eb; text-decoration: underline; }}
  .prose code {{ background: #f3f4f6; padding: 0.125rem 0.375rem; border-radius: 0.25rem; font-size: 0.875rem; }}
  .prose pre {{ background: #1f2937; color: #f3f4f6; padding: 1rem; border-radius: 0.5rem; overflow-x: auto; margin: 1rem 0; }}
  .prose pre code {{ background: none; padding: 0; color: inherit; }}
</style></head>
<body class="bg-gray-50 min-h-screen">
<div class="max-w-4xl mx-auto px-4 py-8">
  <div class="bg-amber-50 border border-amber-200 rounded-2xl px-6 py-3 mb-8 flex items-center justify-between">
    <div class="flex items-center gap-2 text-amber-700">
      <span class="text-lg">⚡</span>
      <span class="text-sm font-medium">预览模式</span>
      <span class="text-xs text-amber-500">| 浏览量: {view_count}</span>
    </div>
    <span class="text-xs text-amber-500">仅供预览，内容可能未发布</span>
  </div>
  {cover_html}
  <article class="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 md:p-12">
    <h1 class="text-3xl md:text-4xl font-bold text-gray-900 mb-4">{title_safe}</h1>
    {excerpt_html}
    <div class="flex items-center gap-3 text-sm text-gray-400 mb-8 pb-6 border-b border-gray-100">
      <span>预览</span>
      {f'<span>·</span><span>{date_str}</span>' if date_str else ''}
    </div>
    <div class="prose text-gray-700 leading-relaxed">
      {content_body or '<p class="text-gray-400 italic">暂无内容</p>'}
    </div>
  </article>
  <div class="text-center mt-8 text-xs text-gray-400">
    <p>由 FastBlog 生成 · 预览链接有效期至 {expires_at}</p>
  </div>
</div></body></html>"""


def _build_password_page(token):
    token_safe = html.escape(token[:12])
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>预览 - 需要密码</title>
<script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-50 flex items-center justify-center min-h-screen">
<div class="bg-white p-8 rounded-2xl shadow-lg max-w-md w-full mx-4">
  <h1 class="text-xl font-bold text-gray-900 mb-2">此预览受密码保护</h1>
  <p class="text-sm text-gray-500 mb-6">请输入密码以查看预览内容</p>
  <form method="POST" action="/preview/{token}" class="space-y-4">
    <div class="flex gap-2">
      <input type="password" name="password" required placeholder="输入密码"
             class="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"/>
      <button type="submit" class="px-6 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 font-medium">验证</button>
    </div>
  </form>
  <p class="text-xs text-gray-400 mt-4 text-center">token: {token_safe}...</p>
</div></body></html>"""


_INVALID_HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>预览 - 无效链接</title>
<script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-50 flex items-center justify-center min-h-screen">
<div class="bg-white p-8 rounded-2xl shadow-lg max-w-md w-full mx-4 text-center">
  <div class="text-6xl mb-4">🔗</div>
  <h1 class="text-xl font-bold text-gray-900 mb-2">预览链接无效或已过期</h1>
  <p class="text-sm text-gray-500 mb-6">该预览链接可能已过期、被撤销或已达到最大访问次数。</p>
  <a href="/" class="inline-block px-6 py-2.5 bg-gray-600 text-white rounded-xl hover:bg-gray-700 font-medium">返回首页</a>
</div></body></html>"""


@router.get("/preview/{token}", response_class=HTMLResponse)
async def view_preview(token: str, request: Request, db: AsyncSession = Depends(get_async_db)):
    """查看草稿预览页面"""
    password = request.query_params.get("password")
    token_info = draft_preview_service.validate_preview_token(token=token, password=password)

    if not token_info:
        stored_token = draft_preview_service.preview_tokens.get(token)
        if stored_token and stored_token.get('password_hash') and stored_token['is_active']:
            return HTMLResponse(_build_password_page(token))
        return HTMLResponse(_INVALID_HTML, status_code=404)

    row = (await db.execute(
        select(Article, ArticleContent)
        .outerjoin(ArticleContent, Article.id == ArticleContent.article)
        .where(Article.id == token_info['article_id'])
    )).first()

    if not row:
        return HTMLResponse("<html><body><h1>文章不存在</h1></body></html>", status_code=404)

    article, content_obj = row
    content = content_obj.content if content_obj else ''
    stats = draft_preview_service.get_token_stats(token)
    view_count = stats['view_count'] if stats else 0
    expires_at = stats.get('expires_at', '—') if stats else '—'

    html = _build_html(
        title=article.title,
        content_body=content,
        cover_image=article.cover_image,
        excerpt=article.excerpt,
        updated_at=article.updated_at,
        view_count=view_count,
        expires_at=expires_at,
    )
    return HTMLResponse(html)


@router.post("/preview/{token}", response_class=HTMLResponse)
async def view_preview_post(token: str, password: str = Form(...), db: AsyncSession = Depends(get_async_db)):
    """草稿预览密码验证（POST）"""
    token_info = draft_preview_service.validate_preview_token(token=token, password=password)

    if not token_info:
        stored_token = draft_preview_service.preview_tokens.get(token)
        if stored_token and stored_token.get('password_hash') and stored_token['is_active']:
            return HTMLResponse(_build_password_page(token))
        return HTMLResponse(_INVALID_HTML, status_code=404)

    row = (await db.execute(
        select(Article, ArticleContent)
        .outerjoin(ArticleContent, Article.id == ArticleContent.article)
        .where(Article.id == token_info['article_id'])
    )).first()

    if not row:
        return HTMLResponse("<html><body><h1>文章不存在</h1></body></html>", status_code=404)

    article, content_obj = row
    content = content_obj.content if content_obj else ''
    stats = draft_preview_service.get_token_stats(token)
    view_count = stats['view_count'] if stats else 0
    expires_at = stats.get('expires_at', '—') if stats else '—'

    html = _build_html(
        title=article.title,
        content_body=content,
        cover_image=article.cover_image,
        excerpt=article.excerpt,
        updated_at=article.updated_at,
        view_count=view_count,
        expires_at=expires_at,
    )
    return HTMLResponse(html)
