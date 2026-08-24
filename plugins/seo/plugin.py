"""
SEO 插件 — 文章级 SEO 元数据驱动

职责：
1. 文章发布/更新时自动生成 SEO 元数据（seo_title / seo_description / seo_keywords / og_*），
   使每篇文章开箱即拥有完整 meta。
2. 提供 build_article_seo() 组装器，供路由/前端把文章平铺的 seo_* 字段组装为完整 meta 结构。

前端由 plugins/seo 配套的 SeoHead 组件（frontend-astro/src/components/seo/SeoHead.astro）渲染。
"""
import logging
from typing import Any, Dict, Optional

from sqlalchemy import select

from shared.services.plugins.event_bus import (
    event_bus,
    ArticlePublishedPayload,
    ArticleUpdatedPayload,
)
from shared.services.plugins.plugin_manager.core import BasePlugin

logger = logging.getLogger(__name__)


def _normalize_text(value: str, limit: int = 160) -> str:
    """清洗文本并截断（SEO 描述常用 160 字符）"""
    value = (value or "").strip().replace("\n", " ").replace("\r", " ")
    return value[:limit]


class SeoPlugin(BasePlugin):
    """文章级 SEO 元数据插件"""

    def __init__(self):
        super().__init__(
            plugin_id=3010,
            name="SEO Auto",
            slug="seo",
            version="1.0.0",
        )
        self.settings = {'enabled': True, 'auto_generate_on_publish': True}

    # ── 事件订阅：文章发布/更新时自动生成 SEO ──
    def subscribers(self) -> list:
        return [
            ("article.published", self.on_article_published),
            ("article.updated", self.on_article_updated),
        ]

    async def on_article_published(self, payload: ArticlePublishedPayload):
        await self._ensure_article_seo(payload.article_id, payload)

    async def on_article_updated(self, payload: ArticleUpdatedPayload):
        await self._ensure_article_seo(payload.article_id, payload)

    async def _ensure_article_seo(self, article_id: int, payload) -> None:
        """文章保存时，若 SEO 字段为空则自动生成（不覆盖管理员已填写的值）"""
        if not self.settings.get('enabled') or not self.settings.get('auto_generate_on_publish'):
            return
        try:
            from datetime import datetime

            from src.utils.database.unified_manager import db_manager
            from shared.models.article.article_seo import ArticleSEO

            title = getattr(payload, 'title', '') or ''
            excerpt = getattr(payload, 'excerpt', '') or ''
            tags = getattr(payload, 'tags', None) or []

            async with db_manager.get_session() as db:
                seo = (await db.execute(
                    select(ArticleSEO).where(ArticleSEO.article_id == article_id)
                )).scalar_one_or_none()

                if seo is None:
                    seo = ArticleSEO(article_id=article_id)
                    db.add(seo)

                changed = False
                if not seo.seo_title and title:
                    seo.seo_title = title[:255]
                    changed = True
                if not seo.seo_description:
                    seo.seo_description = _normalize_text(excerpt)
                    changed = True
                if not seo.og_title and title:
                    seo.og_title = title[:255]
                    changed = True
                if not seo.og_description:
                    seo.og_description = _normalize_text(excerpt)
                    changed = True
                if not seo.seo_keywords and tags:
                    seo.seo_keywords = ",".join(tags)[:500]
                    changed = True

                if changed:
                    seo.updated_at = datetime.now()
                    await db.commit()
                    logger.info(f"[SeoPlugin] 自动生成文章 {article_id} 的 SEO 元数据")
        except Exception as e:
            logger.warning(f"[SeoPlugin] 自动 SEO 生成失败: {e}")

    # ── Meta 组装器（供路由/前端使用）──
    @staticmethod
    def build_article_seo(article: Dict[str, Any], site_url: str = "") -> Dict[str, Any]:
        """
        由文章数据（含 seo_title/seo_description/og_* 等平铺字段）组装完整 SEO 结构。

        Args:
            article: 文章详情数据（GET /api/v2/articles/p/{slug} 返回结构）
            site_url: 站点根地址（用于生成 canonical/og:url）
        """
        title = article.get("seo_title") or article.get("title") or ""
        description = article.get("seo_description") or article.get("excerpt") or ""
        og_title = article.get("og_title") or title
        og_description = article.get("og_description") or description
        og_image = article.get("og_image") or article.get("cover_image") or ""
        slug = article.get("slug") or ""
        canonical = article.get("canonical_url") or (
            f"{site_url.rstrip('/')}/blog/p/{slug}" if site_url and slug else ""
        )

        return {
            "title": title,
            "description": description,
            "keywords": article.get("seo_keywords") or "",
            "og": {
                "type": article.get("og_type") or "article",
                "title": og_title,
                "description": og_description,
                "image": og_image,
                "url": canonical,
            },
            "twitter": {
                "card": article.get("twitter_card") or "summary_large_image",
                "title": article.get("twitter_title") or og_title,
                "description": article.get("twitter_description") or og_description,
                "image": article.get("twitter_image") or og_image,
            },
            "canonical": canonical,
            "robots": article.get("robots_meta") or "index,follow",
            "schema_enabled": article.get("schema_org_enabled", True),
            "schema_type": article.get("schema_org_type") or "BlogPosting",
        }


plugin_instance = SeoPlugin()
