"""
草稿预览查看页面 - 后端渲染
"""
import html

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article import Article, ArticleContent
from shared.services.articles.draft_preview_service import draft_preview_service
from src.utils.database.main import get_async_session as get_async_db

router = APIRouter(tags=["preview-view"])

# 公共 CSS 样式常量（非 f-string，避免 Python 3.12+ 花括号解析问题）
_PREVIEW_STYLES = """\
  *,::before,::after{box-sizing:border-box;border-width:0;border-style:solid}
  html{line-height:1.5;-webkit-text-size-adjust:100%;tab-size:4}
  body{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,"Noto Sans",sans-serif}
  .min-h-screen{min-height:100vh}.bg-gray-50{--tw-bg-opacity:1;background-color:rgb(249 250 251/var(--tw-bg-opacity))}
  .max-w-4xl{max-width:56rem}.mx-auto{margin-left:auto;margin-right:auto}.px-4{padding-left:1rem;padding-right:1rem}.py-8{padding-top:2rem;padding-bottom:2rem}
  .px-6{padding-left:1.5rem;padding-right:1.5rem}.py-3{padding-top:.75rem;padding-bottom:.75rem}
  .mb-8{margin-bottom:2rem}.flex{display:flex}.items-center{align-items:center}.justify-between{justify-content:space-between}
  .gap-2{gap:.5rem}.text-lg{font-size:1.125rem;line-height:1.75rem}.text-sm{font-size:.875rem;line-height:1.25rem}
  .text-xs{font-size:.75rem;line-height:1rem}.font-medium{font-weight:500}.font-bold{font-weight:700}
  .text-3xl{font-size:1.875rem;line-height:2.25rem}.text-4xl{font-size:2.25rem;line-height:2.5rem}
  .text-gray-900{--tw-text-opacity:1;color:rgb(17 24 39/var(--tw-text-opacity))}
  .text-gray-700{--tw-text-opacity:1;color:rgb(55 65 81/var(--tw-text-opacity))}
  .text-gray-500{--tw-text-opacity:1;color:rgb(107 114 128/var(--tw-text-opacity))}
  .text-gray-400{--tw-text-opacity:1;color:rgb(156 163 175/var(--tw-text-opacity))}
  .text-amber-700{--tw-text-opacity:1;color:rgb(180 83 9/var(--tw-text-opacity))}
  .text-amber-500{--tw-text-opacity:1;color:rgb(217 119 6/var(--tw-text-opacity))}
  .bg-amber-50{--tw-bg-opacity:1;background-color:rgb(255 251 235/var(--tw-bg-opacity))}
  .border-amber-200{--tw-border-opacity:1;border-color:rgb(253 230 138/var(--tw-border-opacity))}
  .rounded-2xl{border-radius:1rem}.border{border-width:1px}
  .border-gray-200{--tw-border-opacity:1;border-color:rgb(229 231 235/var(--tw-border-opacity))}
  .border-gray-100{--tw-border-opacity:1;border-color:rgb(243 244 246/var(--tw-border-opacity))}
  .bg-white{--tw-bg-opacity:1;background-color:rgb(255 255 255/var(--tw-bg-opacity))}
  .shadow-sm{box-shadow:0 1px 2px 0 rgb(0 0 0/.05)}.p-8{padding:2rem}.md\\:p-12{padding:3rem}
  .pb-6{padding-bottom:1.5rem}.mb-4{margin-bottom:1rem}.leading-relaxed{line-height:1.625}
  .italic{font-style:italic}.text-center{text-align:center}.mt-8{margin-top:2rem}
  .w-full{width:100%}.h-64{height:16rem}.object-cover{object-fit:cover}.shadow-lg{box-shadow:0 10px 15px -3px rgb(0 0 0/.1),0 4px 6px -4px rgb(0 0 0/.1)}
  .mb-6{margin-bottom:1.5rem}.gap-3{gap:.75rem}.border-b{border-bottom-width:1px}
  .hidden{display:none}.max-w-md{max-width:28rem}.justify-center{justify-content:center}.space-y-4>:not([hidden])~:not([hidden]){--tw-space-y-reverse:0;margin-top:calc(1rem*(1 - var(--tw-space-y-reverse)));margin-bottom:calc(1rem*var(--tw-space-y-reverse))}
  .flex-1{flex:1 1 0%}.px-4{padding-left:1rem;padding-right:1rem}.py-2\\.5{padding-top:.625rem;padding-bottom:.625rem}
  .border-gray-300{--tw-border-opacity:1;border-color:rgb(209 213 219/var(--tw-border-opacity))}
  .rounded-xl{border-radius:.75rem}.focus\\:ring-2:focus{--tw-ring-offset-shadow:var(--tw-ring-inset) 0 0 0 var(--tw-ring-offset-width) var(--tw-ring-offset-color);--tw-ring-shadow:var(--tw-ring-inset) 0 0 0 calc(2px + var(--tw-ring-offset-width)) var(--tw-ring-color);box-shadow:var(--tw-ring-offset-shadow),var(--tw-ring-shadow),var(--tw-shadow,0 0 transparent)}
  .focus\\:ring-blue-500:focus{--tw-ring-opacity:1;--tw-ring-color:rgb(59 130 246/var(--tw-ring-opacity))}
  .focus\\:border-blue-500:focus{--tw-border-opacity:1;border-color:rgb(59 130 246/var(--tw-border-opacity))}
  .outline-none{outline:2px solid transparent;outline-offset:2px}
  .bg-blue-600{--tw-bg-opacity:1;background-color:rgb(37 99 235/var(--tw-bg-opacity))}
  .hover\\:bg-blue-700:hover{--tw-bg-opacity:1;background-color:rgb(29 78 216/var(--tw-bg-opacity))}
  .text-white{--tw-text-opacity:1;color:rgb(255 255 255/var(--tw-text-opacity))}
  .mt-4{margin-top:1rem}.bg-gray-600{--tw-bg-opacity:1;background-color:rgb(75 85 99/var(--tw-bg-opacity))}
  .hover\\:bg-gray-700:hover{--tw-bg-opacity:1;background-color:rgb(55 65 81/var(--tw-bg-opacity))}
  .inline-block{display:inline-block}.text-6xl{font-size:3.75rem;line-height:1}
  .mx-4{margin-left:1rem;margin-right:1rem}"""

_PREVIEW_STYLES_PASSWORD = """\
  *,::before,::after{box-sizing:border-box;border-width:0;border-style:solid}
  html{line-height:1.5;-webkit-text-size-adjust:100%;tab-size:4}
  body{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,"Noto Sans",sans-serif}
  .min-h-screen{min-height:100vh}.bg-gray-50{--tw-bg-opacity:1;background-color:rgb(249 250 251/var(--tw-bg-opacity))}
  .flex{display:flex}.items-center{align-items:center}.justify-center{justify-content:center}
  .bg-white{--tw-bg-opacity:1;background-color:rgb(255 255 255/var(--tw-bg-opacity))}
  .p-8{padding:2rem}.rounded-2xl{border-radius:1rem}.shadow-lg{box-shadow:0 10px 15px -3px rgb(0 0 0/.1),0 4px 6px -4px rgb(0 0 0/.1)}
  .max-w-md{max-width:28rem}.w-full{width:100%}.mx-4{margin-left:1rem;margin-right:1rem}
  .text-xl{font-size:1.25rem;line-height:1.75rem}.font-bold{font-weight:700}
  .text-gray-900{--tw-text-opacity:1;color:rgb(17 24 39/var(--tw-text-opacity))}
  .text-gray-500{--tw-text-opacity:1;color:rgb(107 114 128/var(--tw-text-opacity))}
  .text-gray-400{--tw-text-opacity:1;color:rgb(156 163 175/var(--tw-text-opacity))}
  .text-xs{font-size:.75rem;line-height:1rem}.text-sm{font-size:.875rem;line-height:1.25rem}
  .mb-2{margin-bottom:.5rem}.mb-6{margin-bottom:1.5rem}.mt-4{margin-top:1rem}
  .space-y-4>:not([hidden])~:not([hidden]){--tw-space-y-reverse:0;margin-top:calc(1rem*(1 - var(--tw-space-y-reverse)));margin-bottom:calc(1rem*var(--tw-space-y-reverse))}
  .flex-1{flex:1 1 0%}.px-4{padding-left:1rem;padding-right:1rem}.py-2\\.5{padding-top:.625rem;padding-bottom:.625rem}
  .border{border-width:1px}.border-gray-300{--tw-border-opacity:1;border-color:rgb(209 213 219/var(--tw-border-opacity))}
  .rounded-xl{border-radius:.75rem}.outline-none{outline:2px solid transparent;outline-offset:2px}
  .focus\\:ring-2:focus{--tw-ring-offset-shadow:var(--tw-ring-inset) 0 0 0 var(--tw-ring-offset-width) var(--tw-ring-offset-color);--tw-ring-shadow:var(--tw-ring-inset) 0 0 0 calc(2px + var(--tw-ring-offset-width)) var(--tw-ring-color);box-shadow:var(--tw-ring-offset-shadow),var(--tw-ring-shadow),var(--tw-shadow,0 0 transparent)}
  .focus\\:ring-blue-500:focus{--tw-ring-opacity:1;--tw-ring-color:rgb(59 130 246/var(--tw-ring-opacity))}
  .focus\\:border-blue-500:focus{--tw-border-opacity:1;border-color:rgb(59 130 246/var(--tw-border-opacity))}
  .bg-blue-600{--tw-bg-opacity:1;background-color:rgb(37 99 235/var(--tw-bg-opacity))}
  .hover\\:bg-blue-700:hover{--tw-bg-opacity:1;background-color:rgb(29 78 216/var(--tw-bg-opacity))}
  .text-white{--tw-text-opacity:1;color:rgb(255 255 255/var(--tw-text-opacity))}
  .px-6{padding-left:1.5rem;padding-right:1.5rem}.py-2\\.5{padding-top:.625rem;padding-bottom:.625rem}
  .font-medium{font-weight:500}.text-center{text-align:center}
  .gap-2{gap:.5rem}"""


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
<style>
  /* tailwindcss v3.4 minimal subset */
  {_PREVIEW_STYLES}
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
<style>
  {_PREVIEW_STYLES_PASSWORD}
</style></head>
<body class="bg-gray-50 flex items-center justify-center min-h-screen">
<div class="bg-white p-8 rounded-2xl shadow-lg max-w-md w-full mx-4">
  <h1 class="text-xl font-bold text-gray-900 mb-2">此预览受密码保护</h1>
  <p class="text-sm text-gray-500 mb-6">请输入密码以查看预览内容</p>
  <form method="POST" action="/api/v2/articles/preview/{token}" class="space-y-4">
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
<style>
  *,::before,::after{box-sizing:border-box;border-width:0;border-style:solid}
  html{line-height:1.5;-webkit-text-size-adjust:100%;tab-size:4}
  body{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,"Noto Sans",sans-serif}
  .min-h-screen{min-height:100vh}.bg-gray-50{--tw-bg-opacity:1;background-color:rgb(249 250 251/var(--tw-bg-opacity))}
  .flex{display:flex}.items-center{align-items:center}.justify-center{justify-content:center}
  .bg-white{--tw-bg-opacity:1;background-color:rgb(255 255 255/var(--tw-bg-opacity))}
  .p-8{padding:2rem}.rounded-2xl{border-radius:1rem}.shadow-lg{box-shadow:0 10px 15px -3px rgb(0 0 0/.1),0 4px 6px -4px rgb(0 0 0/.1)}
  .max-w-md{max-width:28rem}.w-full{width:100%}.mx-4{margin-left:1rem;margin-right:1rem}
  .text-center{text-align:center}.text-6xl{font-size:3.75rem;line-height:1}.mb-4{margin-bottom:1rem}.mb-6{margin-bottom:1.5rem}
  .text-xl{font-size:1.25rem;line-height:1.75rem}.font-bold{font-weight:700}
  .text-gray-900{--tw-text-opacity:1;color:rgb(17 24 39/var(--tw-text-opacity))}
  .text-gray-500{--tw-text-opacity:1;color:rgb(107 114 128/var(--tw-text-opacity))}
  .text-sm{font-size:.875rem;line-height:1.25rem}.inline-block{display:inline-block}
  .px-6{padding-left:1.5rem;padding-right:1.5rem}.py-2\\.5{padding-top:.625rem;padding-bottom:.625rem}
  .bg-gray-600{--tw-bg-opacity:1;background-color:rgb(75 85 99/var(--tw-bg-opacity))}
  .hover\\:bg-gray-700:hover{--tw-bg-opacity:1;background-color:rgb(55 65 81/var(--tw-bg-opacity))}
  .text-white{--tw-text-opacity:1;color:rgb(255 255 255/var(--tw-text-opacity))}
  .rounded-xl{border-radius:.75rem}.font-medium{font-weight:500}
</style></head>
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
