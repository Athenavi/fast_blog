"""seo 模块业务逻辑（真实实现）

复用项目既有的两个真实实现，不再使用 v2 的硬编码占位数据：

  - ``SEOAnalyzer.analyze_seo``：8 项加权评分（标题/描述/关键词/可读性/内容长度/
    标题层级/内链/图片 alt）
  - ``InternalLinkService``：关键词提取、相关文章、内链建议、孤立文章、链接分布

v3 补齐的部分（v2 缺失）：

  - 用 BeautifulSoup 从正文解析 ``headings`` / ``images`` / 站内链接，喂给分析器
    （bs4 不可用时回退正则），而不是传空结构
  - 维护「href → 文章 id」映射，从而能算出真实的入链数、孤立文章与链接分布
  - SEO 字段优先取 ``article_seo`` 表，回退到文章自身的 title/excerpt
"""

import re
from collections import Counter
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.article.article_content import ArticleContent
from shared.models.article.article_seo import ArticleSEO
from src.api.v3.core.exceptions import NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.analytics.seo.schema import BulkCheckRequest

logger = get_logger("seo")

STATUS_DELETED = -1
STATUS_PUBLISHED = 1

MAX_KEYWORD_SOURCE = 200_000  # 关键词统计时正文的总截断长度（防止超长内容拖慢）
_ID_PATTERNS = (
    re.compile(r"/articles?/(\d+)(?:\.html)?/?$"),
    re.compile(r"/article/(\d+)(?:\.html)?/?$"),
    re.compile(r"/p/(\d+)/?$"),
)
_HREF_RE = re.compile(r"""href=["']([^"']+)["']""", re.IGNORECASE)


# ---------------------------------------------------------------------- HTML 解析
def parse_content_structure(content: str) -> Dict[str, Any]:
    """从正文解析标题层级、图片、站内链接

    优先用 BeautifulSoup；不可用时用正则兜底（保证功能可用，只是精度下降）。
    """
    headings: Dict[str, List[str]] = {"h1": [], "h2": [], "h3": []}
    images: List[Dict[str, str]] = []
    hrefs: List[str] = []

    if not content:
        return {"headings": headings, "images": images, "hrefs": hrefs}

    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(content, "html.parser")
        for level in ("h1", "h2", "h3"):
            headings[level] = [el.get_text(strip=True) for el in soup.find_all(level)][:50]
        images = [
            {"src": img.get("src", ""), "alt": img.get("alt", "")}
            for img in soup.find_all("img")
        ][:200]
        hrefs = [a["href"] for a in soup.find_all("a", href=True)][:500]
    except Exception:  # noqa: BLE001 - bs4 缺失或解析失败时回退
        logger.warning("BeautifulSoup 不可用或解析失败，回退正则解析")
        for level in ("h1", "h2", "h3"):
            headings[level] = [
                re.sub(r"<[^>]+>", "", match).strip()
                for match in re.findall(rf"<{level}[^>]*>(.*?)</{level}>", content, re.S | re.I)
            ][:50]
        images = [
            {"src": src or "", "alt": alt or ""}
            for src, alt in re.findall(r'<img[^>]*src=["\']([^"\']*)["\'][^>]*alt=["\']([^"\']*)["\']', content, re.I)
        ][:200]
        hrefs = _HREF_RE.findall(content)[:500]

    return {"headings": headings, "images": images, "hrefs": hrefs}


def is_internal_href(href: str) -> bool:
    """站内链接判定：以 / 开头且不是协议相对地址、不是锚点/JS"""
    if not href:
        return False
    href = href.strip()
    if href.startswith(("//", "#", "mailto:", "tel:", "javascript:")):
        return False
    return href.startswith("/")


def resolve_article_id(
    href: str,
    slug_to_id: Dict[str, int],
    id_set: Iterable[int],
) -> Optional[int]:
    """把站内 href 解析成文章 id（支持 /articles/12、/article/12.html、/p/12、/{slug}）"""
    if not is_internal_href(href):
        return None

    path = href.split("?")[0].split("#")[0]
    for pattern in _ID_PATTERNS:
        match = pattern.search(path)
        if match:
            candidate = int(match.group(1))
            if candidate in set(id_set):
                return candidate

    slug = path.strip("/")
    # 允许 /p/{slug}、/{slug}
    slug = re.sub(r"^(p|articles?|post)/", "", slug)
    return slug_to_id.get(slug)


# ---------------------------------------------------------------------- 服务
class SEOService:
    """SEO 分析与内链优化"""

    # ------------------------------------------------------------------ 加载
    async def _articles(
        self,
        db: AsyncSession,
        *,
        ids: Optional[Sequence[int]] = None,
        only_published: bool = False,
        limit: int = 200,
    ) -> List[Article]:
        stmt = select(Article).where(Article.status != STATUS_DELETED)
        if ids:
            stmt = stmt.where(Article.id.in_(list(ids)))
        elif only_published:
            stmt = stmt.where(Article.status == STATUS_PUBLISHED)
        stmt = stmt.order_by(Article.id.desc()).limit(max(1, limit))
        return list((await db.execute(stmt)).scalars().all())

    async def _contents_map(self, db: AsyncSession, article_ids: Sequence[int]) -> Dict[int, str]:
        if not article_ids:
            return {}
        stmt = (
            select(ArticleContent)
            .where(ArticleContent.article.in_(list(article_ids)))
            .order_by(ArticleContent.id.asc())
        )
        contents: Dict[int, str] = {}
        for row in (await db.execute(stmt)).scalars().all():
            contents.setdefault(row.article, row.content or "")
        return contents

    async def _seo_map(self, db: AsyncSession, article_ids: Sequence[int]) -> Dict[int, dict]:
        if not article_ids:
            return {}
        stmt = select(ArticleSEO).where(ArticleSEO.article_id.in_(list(article_ids)))
        result: Dict[int, dict] = {}
        for row in (await db.execute(stmt)).scalars().all():
            try:
                result[row.article_id] = row.to_dict()
            except Exception:  # noqa: BLE001
                result[row.article_id] = {}
        return result

    @staticmethod
    def _analyzer():
        from shared.services.seo.seo_analyzer import SEOAnalyzer

        return SEOAnalyzer()

    @staticmethod
    def _link_service():
        from shared.services.seo.internal_link_service import internal_link_service

        return internal_link_service

    @staticmethod
    def _resolve_seo_fields(article: Article, seo: Optional[dict]) -> Tuple[str, str, List[str]]:
        """标题/描述/关键词：优先 article_seo，回退文章字段（键名做了兼容）"""
        seo = seo or {}
        title = (
            seo.get("meta_title") or seo.get("seo_title") or seo.get("title") or article.title or ""
        )
        description = (
            seo.get("meta_description")
            or seo.get("seo_description")
            or seo.get("description")
            or article.excerpt
            or ""
        )
        raw_keywords = seo.get("meta_keywords") or seo.get("seo_keywords") or seo.get("keywords")
        if isinstance(raw_keywords, str):
            keywords = [item.strip() for item in raw_keywords.split(",") if item.strip()]
        elif isinstance(raw_keywords, (list, tuple)):
            keywords = [str(item).strip() for item in raw_keywords if str(item).strip()]
        else:
            keywords = []
        return title, description, keywords

    # ------------------------------------------------------------------ 分析
    async def analyze_article(self, db: AsyncSession, article_id: int) -> dict:
        article = (await db.execute(select(Article).where(Article.id == article_id))).scalars().first()
        if article is None or article.status == STATUS_DELETED:
            raise NotFoundError("文章不存在")

        contents = await self._contents_map(db, [article_id])
        seo_map = await self._seo_map(db, [article_id])
        return self._analyze_one(article, contents.get(article_id, ""), seo_map.get(article_id))

    def _analyze_one(self, article: Article, content: str, seo: Optional[dict]) -> dict:
        title, description, keywords = self._resolve_seo_fields(article, seo)
        structure = parse_content_structure(content)
        internal_links = sum(1 for href in structure["hrefs"] if is_internal_href(href))

        report = self._analyzer().analyze_seo(
            title=title,
            description=description,
            content=content or "",
            keywords=keywords,
            headings=structure["headings"],
            images=structure["images"],
            internal_links=internal_links,
        )
        suggestions = list(report.get("suggestions") or [])
        return {
            "article_id": article.id,
            "title": article.title,
            "slug": article.slug,
            "status": article.status,
            "score": float(report.get("overall_score") or 0),
            "grade": report.get("grade"),
            "metrics": report.get("metrics") or {},
            "suggestions": suggestions,
            "suggestion_count": len(suggestions),
            "top_suggestions": suggestions[:3],
        }

    async def bulk_check(self, db: AsyncSession, payload: BulkCheckRequest) -> dict:
        articles = await self._articles(
            db,
            ids=payload.ids or None,
            only_published=payload.only_published if not payload.ids else False,
            limit=payload.limit,
        )
        if not articles:
            return {"checked": 0, "average_score": 0.0, "grade_distribution": {}, "items": []}

        ids = [article.id for article in articles]
        contents = await self._contents_map(db, ids)
        seo_map = await self._seo_map(db, ids)

        items = [
            self._analyze_one(article, contents.get(article.id, ""), seo_map.get(article.id))
            for article in articles
        ]
        scores = [item["score"] for item in items]
        distribution = Counter(item.get("grade") or "unknown" for item in items)

        return {
            "checked": len(items),
            "average_score": round(sum(scores) / len(scores), 2),
            "grade_distribution": dict(distribution),
            "items": items,
        }

    # ------------------------------------------------------------------ 关键词
    async def keywords(self, db: AsyncSession, *, limit: int = 50, scan_limit: int = 300) -> dict:
        articles = await self._articles(db, only_published=True, limit=scan_limit)
        contents = await self._contents_map(db, [article.id for article in articles])
        link_service = self._link_service()

        counter: Counter = Counter()
        for article in articles:
            text = " ".join(
                filter(None, [article.title or "", contents.get(article.id, "")[:5000]])
            )[:10000]
            try:
                extracted = link_service.extract_keywords(text, top_n=20) or []
            except Exception:  # noqa: BLE001
                logger.exception("关键词提取失败 article_id=%s", article.id)
                continue
            for item in extracted:
                keyword = item.get("keyword") if isinstance(item, dict) else str(item)
                if keyword:
                    counter[str(keyword)] += 1

        items = [
            {"keyword": keyword, "count": count, "article_count": count}
            for keyword, count in counter.most_common(max(1, min(limit, 500)))
        ]
        return {"keywords": items, "total": len(counter)}

    # ------------------------------------------------------------------ 内链
    async def _link_graph(
        self, db: AsyncSession, *, scan_limit: int = 500
    ) -> Tuple[List[dict], List[dict], Dict[int, dict]]:
        """构建文章列表 + 内链图（source_article_id / target_article_id）"""
        articles = await self._articles(db, only_published=True, limit=scan_limit)
        contents = await self._contents_map(db, [article.id for article in articles])

        all_articles = [
            {
                "id": article.id,
                "title": article.title,
                "slug": article.slug,
                "content": contents.get(article.id, ""),
            }
            for article in articles
        ]
        slug_to_id = {a["slug"]: a["id"] for a in all_articles if a.get("slug")}
        id_set = {a["id"] for a in all_articles}

        links: List[dict] = []
        for article in all_articles:
            for href in parse_content_structure(article["content"])["hrefs"]:
                target = resolve_article_id(href, slug_to_id, id_set)
                if target and target != article["id"]:
                    links.append({"source_article_id": article["id"], "target_article_id": target})
        return all_articles, links, {a["id"]: a for a in all_articles}

    async def orphan_articles(self, db: AsyncSession, *, limit: int = 100) -> dict:
        articles, links, _by_id = await self._link_graph(db)
        inbound = Counter(link["target_article_id"] for link in links)
        try:
            orphans = self._link_service().detect_orphan_articles(articles, links) or []
        except Exception:  # noqa: BLE001
            logger.exception("孤立文章检测失败，回退本地计算")
            orphans = [a for a in articles if inbound.get(a["id"], 0) == 0]

        items = [
            {
                "article_id": item.get("id"),
                "title": item.get("title"),
                "slug": item.get("slug"),
                "inbound_links": inbound.get(item.get("id"), 0),
            }
            for item in orphans[: max(1, min(limit, 500))]
        ]
        return {"items": items, "total": len(orphans), "total_articles": len(articles)}

    async def link_distribution(self, db: AsyncSession) -> dict:
        articles, links, _by_id = await self._link_graph(db)
        try:
            return self._link_service().analyze_link_distribution(articles, links)
        except Exception:  # noqa: BLE001
            logger.exception("链接分布分析失败，回退本地计算")
            return {"total_articles": len(articles), "total_links": len(links), "distribution": {}}

    async def internal_link_suggestions(self, db: AsyncSession, article_id: int) -> dict:
        articles, _links, by_id = await self._link_graph(db)
        current = by_id.get(article_id)
        if current is None:
            raise NotFoundError("文章不存在或未发布")
        try:
            return self._link_service().suggest_internal_links(current, articles)
        except Exception:  # noqa: BLE001
            logger.exception("内链建议生成失败 article_id=%s", article_id)
            return {"success": False, "suggestions": [], "keywords": [], "link_density": 0}

    # ------------------------------------------------------------------ 报告
    async def report(self, db: AsyncSession, *, limit: int = 100) -> dict:
        bulk = await self.bulk_check(
            db, BulkCheckRequest(ids=[], limit=limit, only_published=True)
        )
        orphans = await self.orphan_articles(db, limit=20)
        keywords = await self.keywords(db, limit=10)

        suggestion_counter: Counter = Counter()
        for item in bulk["items"]:
            for suggestion in item.get("suggestions") or []:
                suggestion_counter[suggestion] += 1

        return {
            "generated_at": datetime.now(),
            "total_articles": len(bulk["items"]),
            "analyzed_articles": bulk["checked"],
            "average_score": bulk["average_score"],
            "grade_distribution": bulk["grade_distribution"],
            "common_suggestions": [
                {"suggestion": text, "count": count}
                for text, count in suggestion_counter.most_common(10)
            ],
            "orphan_count": orphans["total"],
            "top_keywords": keywords["keywords"],
        }

    async def analyze_content(self, payload: Any) -> dict:
        """对任意内容做分析（不落库，供编辑器实时提示）"""
        structure = parse_content_structure(payload.content or "")
        internal_links = payload.internal_links or sum(
            1 for href in structure["hrefs"] if is_internal_href(href)
        )
        return self._analyzer().analyze_seo(
            title=payload.title or "",
            description=payload.description or "",
            content=payload.content or "",
            keywords=list(payload.keywords or []),
            headings=structure["headings"],
            images=structure["images"],
            internal_links=internal_links,
        )


seo_service = SEOService()
