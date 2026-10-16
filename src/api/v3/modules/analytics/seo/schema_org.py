"""JSON-LD 结构化数据（schema.org）—— 任务 14a

v2 的 ``shared/services/system/schema_generator.py``（11.2KB）是一套**真实的** JSON-LD 生成器
（Article / Breadcrumb / Organization / Person / Website / FAQ / Image / Video），
因此 v3 **直接复用它的生成逻辑**，只把"站点信息从哪来"接到真表：

  - v2 的 ``SchemaGenerator._get_site_name()`` 读的是 v2 的 ``SystemSetting.get_value``
    （同步类方法，v3 不适用）→ v3 改从 ``sites``（当前站点，优先）与 ``system_settings``
    读站点名 / URL / logo，读不到再回退默认值，并把结果**覆盖**进生成的 schema

与文章联动：``article_seo.schema_org_enabled`` 为真时按 ``schema_org_type``（默认 Article）
生成对应类型；未启用时仍可预览，但响应里会标注 ``enabled=False``（前端据此决定是否注入）。
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.article.article_content import ArticleContent
from shared.models.article.article_seo import ArticleSEO
from shared.models.category.category import Category
from shared.services.system.schema_generator import SchemaGenerator
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger

logger = get_logger("analytics.seo.schema_org")

#: v2 生成器支持的类型 → 中文说明（前端下拉用）
SCHEMA_TYPES: Dict[str, str] = {
    "Article": "文章",
    "BreadcrumbList": "面包屑导航",
    "Organization": "组织 / 站点主体",
    "Person": "作者 / 人物",
    "WebSite": "网站（含站内搜索）",
    "FAQPage": "常见问题",
    "ImageObject": "图片",
    "VideoObject": "视频",
}

DEFAULT_SITE_NAME = "FastBlog"


class SchemaOrgService:
    """结构化数据生成（复用 v2 生成器 + v3 真表站点信息）"""

    def __init__(self) -> None:
        self._generator = SchemaGenerator()

    # ------------------------------------------------------------------ 站点信息
    async def site_context(self, db: AsyncSession, *, base_url: Optional[str] = None) -> Dict[str, Any]:
        """站点名 / 站点 URL / logo：``sites``（当前站点优先）→ ``system_settings`` → 默认值"""
        from shared.models.multisite.site import Site
        from shared.models.system.system_settings import SystemSettings

        name = ""
        site_url = ""
        logo = ""

        site = (
            await db.execute(
                select(Site).where(Site.is_active.is_(True)).order_by(Site.is_default.desc(), Site.id.asc()).limit(1)
            )
        ).scalars().first()
        if site is not None:
            name = str(site.name or "").strip()
            logo = str(site.logo_url or "").strip()
            domain = str(site.domain or "").strip()
            if domain:
                site_url = domain if domain.startswith("http") else f"https://{domain}"

        if not name or not site_url:
            rows = (
                await db.execute(
                    select(SystemSettings).where(
                        SystemSettings.setting_key.in_(["site_name", "site_url", "site_logo"])
                    )
                )
            ).scalars().all()
            settings = {
                str(row.setting_key): (row.setting_value or "") for row in rows
            }
            name = name or str(settings.get("site_name") or "").strip()
            site_url = site_url or str(settings.get("site_url") or "").strip()
            logo = logo or str(settings.get("site_logo") or "").strip()

        resolved_base = (base_url or site_url or "").rstrip("/")
        return {
            "name": name or DEFAULT_SITE_NAME,
            "base_url": resolved_base,
            "logo": logo,
            "source": "sites" if site is not None else "system_settings",
        }

    # ------------------------------------------------------------------ 生成
    @staticmethod
    def types() -> List[Dict[str, str]]:
        return [{"type": key, "label": label} for key, label in SCHEMA_TYPES.items()]

    def build(self, schema_type: str, **kwargs: Any) -> Dict[str, Any]:
        """按类型调用 v2 生成器（``schema_type`` 不在支持列表时 400）"""
        if schema_type not in SCHEMA_TYPES:
            raise BadRequestError(
                f"不支持的结构化数据类型「{schema_type}」（可选：{sorted(SCHEMA_TYPES)}）"
            )
        # v2 生成器的方法名统一是 generate_<suffix>_schema
        builder = getattr(
            self._generator, f"generate_{self._method_suffix(schema_type)}_schema", None
        )
        if builder is None:
            raise BadRequestError(f"生成器缺少 {schema_type} 的实现")
        try:
            return builder(**kwargs)
        except TypeError as exc:
            # 参数不匹配要如实报出来（而不是抛 500）
            raise BadRequestError(f"{schema_type} 生成参数不正确：{exc}") from None

    async def for_article(
        self, db: AsyncSession, article_id: int, *, base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """为文章生成结构化数据：Article（或 ``schema_org_type``）+ BreadcrumbList"""
        article = await db.get(Article, article_id)
        if article is None:
            raise NotFoundError("文章不存在")

        seo = (
            await db.execute(select(ArticleSEO).where(ArticleSEO.article_id == article_id).limit(1))
        ).scalars().first()
        content_row = (
            await db.execute(
                select(ArticleContent)
                .where(ArticleContent.article == article_id)
                .order_by(ArticleContent.id.asc())
                .limit(1)
            )
        ).scalars().first()

        context = await self.site_context(db, base_url=base_url)
        base = context["base_url"] or ""

        author = await self._author_name(db, article.user)
        category_name, category_slug = await self._category_info(db, article.category)
        canonical = (seo.canonical_url if seo is not None else None) or (
            f"{base}/article/{article.slug}" if base and article.slug else ""
        )
        description = (
            (seo.seo_description if seo is not None else None)
            or article.excerpt
            or (content_row.content[:160] if content_row is not None else "")
            or ""
        )

        schema_type = (seo.schema_org_type if seo is not None else None) or "Article"
        if schema_type not in SCHEMA_TYPES:
            schema_type = "Article"

        if schema_type == "FAQPage":
            # FAQ 需要问答对，本批没有来源 → 明确报错而不是生成空壳
            raise BadRequestError("FAQ 结构化数据需要问答对，请用 /schema/preview 手工生成")
        if schema_type not in ("Article", "Person"):
            raise BadRequestError(
                f"文章只支持 Article / Person 类型（当前 schema_org_type={schema_type}）"
            )

        if schema_type == "Person":
            person = self.build(
                "Person",
                name=author or context["name"],
                url=f"{base}/author/{article.user}" if base else "",
                description=description,
            )
            blocks = [person]
        else:
            article_schema = self.build(
                "Article",
                title=article.title or "",
                description=description,
                url=canonical,
                author_name=author or context["name"],
                author_url=f"{base}/author/{article.user}" if base else "",
                publish_date=article.published_at.isoformat() if article.published_at else None,
                modified_date=article.updated_at.isoformat() if article.updated_at else None,
                image_url=(seo.og_image if seo is not None else None) or context["logo"] or "",
                keywords=[item.strip() for item in str(article.tags_list or "").strip("[]").split(",") if item.strip()]
                if article.tags_list
                else None,
                category=category_name or "",
            )
            blocks = [article_schema]

        blocks.append(
            self.build(
                "BreadcrumbList",
                items=self._breadcrumb_items(
                    base=base,
                    category_name=category_name,
                    category_slug=category_slug,
                    article_title=article.title or "",
                    article_slug=article.slug or "",
                ),
            )
        )

        self._apply_site(blocks, context)
        return {
            "article_id": article_id,
            "enabled": bool(seo.schema_org_enabled) if seo is not None else False,
            "schema_type": schema_type,
            "site": context,
            "blocks": blocks,
            "json_ld": self.to_json_ld(blocks[0]),
            "script_tag": self.to_script_tag(blocks[0]),
        }

    # ------------------------------------------------------------------ 输出
    @staticmethod
    def to_json_ld(schema: Dict[str, Any]) -> str:
        return SchemaGenerator().to_json_ld(schema)

    @staticmethod
    def to_script_tag(schema: Dict[str, Any]) -> str:
        return SchemaGenerator().to_script_tag(schema)

    # ------------------------------------------------------------------ 内部
    @staticmethod
    def _method_suffix(schema_type: str) -> str:
        mapping = {
            "Article": "article",
            "BreadcrumbList": "breadcrumb",
            "Organization": "organization",
            "Person": "person",
            "WebSite": "website",
            "FAQPage": "faq",
            "ImageObject": "image",
            "VideoObject": "video",
        }
        return mapping[schema_type]

    @staticmethod
    def _apply_site(blocks: List[Dict[str, Any]], context: Dict[str, Any]) -> None:
        """把真表读到的站点信息覆盖进 schema（v2 生成器用的是它自己的默认值）"""
        for block in blocks:
            block["@context"] = "https://schema.org"
            if context["name"] and isinstance(block.get("publisher"), dict):
                block["publisher"]["name"] = context["name"]
            if context["logo"] and isinstance(block.get("publisher"), dict):
                block["publisher"].setdefault("logo", {"@type": "ImageObject", "url": context["logo"]})

    @staticmethod
    async def _author_name(db: AsyncSession, user_id: Any) -> str:
        if user_id in (None, ""):
            return ""
        from shared.models.user import User

        row = await db.get(User, int(user_id))
        if row is None:
            return ""
        return str(getattr(row, "nickname", None) or getattr(row, "username", "") or "")

    @staticmethod
    async def _category_info(db: AsyncSession, category_id: Any) -> tuple:
        if category_id in (None, ""):
            return "", ""
        row = await db.get(Category, int(category_id))
        if row is None:
            return "", ""
        return str(row.name or ""), str(row.slug or "")

    @staticmethod
    def _breadcrumb_items(
        *,
        base: str,
        category_name: str,
        category_slug: str,
        article_title: str,
        article_slug: str,
    ) -> List[Dict[str, str]]:
        items = [{"name": "首页", "url": f"{base}/" if base else "/"}]
        if category_name:
            items.append(
                {
                    "name": category_name,
                    "url": f"{base}/category/{category_slug}" if base and category_slug else "",
                }
            )
        items.append(
            {
                "name": article_title,
                "url": f"{base}/article/{article_slug}" if base and article_slug else "",
            }
        )
        return items


schema_org_service = SchemaOrgService()
