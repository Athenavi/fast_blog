"""SEO 生成与写入（内容创作辅助的 SEO 部分）

v3 的 ``analytics/seo`` 已有**分析**能力（规则评分、关键词统计、内链建议、综合报告），
但只读 —— ``article_seo`` 表此前**没有任何写入路径**。本模块补上"生成 + 落库"：

  - ``generate_for_article``：用**真实 LLM**（复用 ``ai/config`` 的配置解析与 ``ai/llm`` 的调用）
    生成 SEO 元信息（JSON），``apply=True`` 时写入 ``article_seo`` 真表
  - ``save_seo``：手工保存（前端编辑后落库，与生成的字段同一套）
  - 提示词走 ``ai/workflow/tasks.py`` 的 ``seo_generate`` —— 与前端任务类型下拉同一份定义，
    不会出现"前端能选、后端没模板"的漂移

**不做**：用 LLM 改写分析评分（评分规则是确定性的，留在 ``analytics/seo`` 里）。
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.article.article_content import ArticleContent
from shared.models.article.article_seo import ArticleSEO
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.ai import llm
from src.api.v3.modules.ai.config.crud import ai_config_crud
from src.api.v3.modules.ai.config.service import ai_config_service
from src.api.v3.modules.ai.workflow import tasks

logger = get_logger("analytics.seo.assistant")

#: 可写入 ``article_seo`` 的字段（与表结构一一对应）
SEO_FIELDS = (
    "seo_title",
    "seo_description",
    "seo_keywords",
    "og_title",
    "og_description",
    "og_image",
    "og_type",
    "twitter_title",
    "twitter_description",
    "twitter_image",
    "twitter_card",
    "canonical_url",
    "robots_meta",
    "schema_org_enabled",
    "schema_org_type",
)

#: LLM 生成时喂给模型的正文长度上限（省 token，也避免超上下文）
MAX_INPUT_CHARS = 6000

#: 生成任务类型（定义在 ai/workflow/tasks.py）
GENERATE_TASK_TYPE = "seo_generate"


def parse_llm_json(text: str) -> Any:
    """解析模型返回的 JSON（容错：剥掉 ```json 代码块、截取首个 JSON 片段）

    模型不总听话 —— 因此这里只做"尽力解析"，失败就抛 ``BadRequestError`` 让调用方看到原因，
    不猜内容、不静默返回空对象。
    """
    raw = (text or "").strip()
    if not raw:
        raise BadRequestError("模型返回为空，无法解析 SEO 结果")
    if raw.startswith("```"):
        # ```json ... ``` / ``` ... ```
        raw = raw.split("```", 2)[1] if raw.count("```") >= 2 else raw.strip("`")
        if raw.lstrip().lower().startswith("json"):
            raw = raw.lstrip()[4:]
        raw = raw.strip()

    try:
        return json.loads(raw)
    except ValueError:
        pass

    for opener, closer in (("{", "}"), ("[", "]")):
        start = raw.find(opener)
        end = raw.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(raw[start: end + 1])
            except ValueError:
                continue
    raise BadRequestError("模型未返回可解析的 JSON，请重试或换用其它模型")


def normalize_keywords(value: Any) -> Optional[str]:
    """``seo_keywords`` 是 varchar：列表 → 逗号分隔；字符串原样（去空白）"""
    if value in (None, ""):
        return None
    if isinstance(value, (list, tuple, set)):
        items = [str(item).strip() for item in value if str(item).strip()]
        return ",".join(items)[:255] or None
    return str(value).strip()[:255] or None


class SEOAssistantService:
    """SEO 生成 / 保存"""

    # ------------------------------------------------------------------ 读
    async def get_seo(self, db: AsyncSession, article_id: int) -> Dict[str, Any]:
        article = await self._article_or_404(db, article_id)
        row = await self._seo_row(db, article_id)
        data = {field: (getattr(row, field) if row is not None else None) for field in SEO_FIELDS}
        return {
            "article_id": article_id,
            "article_title": article.title,
            "slug": article.slug,
            "has_seo": row is not None,
            **data,
        }

    # ------------------------------------------------------------------ 写
    async def save_seo(
        self,
        db: AsyncSession,
        article_id: int,
        payload: Dict[str, Any],
        *,
        only_fields: Optional[Tuple[str, ...]] = None,
    ) -> Dict[str, Any]:
        """保存 SEO 字段（``article_seo`` 表 upsert）"""
        await self._article_or_404(db, article_id)
        allowed = only_fields or SEO_FIELDS
        updates = {
            key: value
            for key, value in payload.items()
            if key in allowed and key in SEO_FIELDS
        }
        if not updates:
            raise BadRequestError(f"没有可保存的 SEO 字段（可选：{', '.join(allowed)}）")
        if "seo_keywords" in updates:
            updates["seo_keywords"] = normalize_keywords(updates["seo_keywords"])

        now = datetime.now()
        row = await self._seo_row(db, article_id)
        if row is None:
            row = ArticleSEO(article_id=article_id, created_at=now, updated_at=now, **updates)
            db.add(row)
        else:
            for key, value in updates.items():
                setattr(row, key, value)
            row.updated_at = now
        await db.commit()
        await db.refresh(row)
        logger.info("文章 %s 的 SEO 已保存（%s 个字段）", article_id, len(updates))
        return {
            "article_id": article_id,
            "saved_fields": sorted(updates),
            **{field: getattr(row, field) for field in SEO_FIELDS},
        }

    # ------------------------------------------------------------------ 生成
    async def generate_for_article(
        self,
        db: AsyncSession,
        article_id: int,
        *,
        config_id: Optional[int] = None,
        apply: bool = False,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """用真实 LLM 生成 SEO 元信息；``apply=True`` 时写入 ``article_seo``"""
        article = await self._article_or_404(db, article_id)
        content = await self._content_of(db, article_id)
        if not (article.title or content):
            raise BadRequestError("文章标题与正文都为空，无法生成 SEO")

        resolved_config_id = config_id if config_id is not None else await self._first_config_id(db)
        settings = await ai_config_service.resolve_llm_settings(db, resolved_config_id)

        system, prompt = tasks.render(
            GENERATE_TASK_TYPE,
            input_text=f"标题：{article.title or ''}\n\n正文：\n{content[:MAX_INPUT_CHARS]}",
        )
        result = await llm.complete(settings, system=system or None, prompt=prompt, max_tokens=max_tokens)

        parsed = parse_llm_json(result.text)
        if not isinstance(parsed, dict):
            raise BadRequestError("模型返回的不是 JSON 对象，无法作为 SEO 元信息")

        generated = {
            key: value
            for key, value in parsed.items()
            if key in SEO_FIELDS and value not in (None, "", [], {})
        }
        if not generated:
            raise BadRequestError(
                f"模型返回的 JSON 不含可用字段（期望：{', '.join(SEO_FIELDS[:5])}…）"
            )

        applied: List[str] = []
        if apply:
            saved = await self.save_seo(db, article_id, generated)
            applied = saved["saved_fields"]

        return {
            "article_id": article_id,
            "model": settings.model,
            "task_type": GENERATE_TASK_TYPE,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "generated": {**generated, "seo_keywords": normalize_keywords(generated.get("seo_keywords"))},
            "applied": applied,
        }

    # ------------------------------------------------------------------ 内部
    async def _first_config_id(self, db: AsyncSession) -> int:
        rows, _total = await ai_config_crud.list(db, page=1, page_size=1)
        if not rows:
            raise NotFoundError("还没有可用的 AI 配置，请先在「AI 配置」里添加并测试连接")
        return int(rows[0].id)

    @staticmethod
    async def _article_or_404(db: AsyncSession, article_id: int) -> Article:
        article = await db.get(Article, article_id)
        if article is None:
            raise NotFoundError("文章不存在")
        return article

    @staticmethod
    async def _content_of(db: AsyncSession, article_id: int) -> str:
        row = (
            await db.execute(
                select(ArticleContent)
                .where(ArticleContent.article == article_id)
                .order_by(ArticleContent.id.asc())
                .limit(1)
            )
        ).scalars().first()
        return (row.content or "") if row is not None else ""

    @staticmethod
    async def _seo_row(db: AsyncSession, article_id: int) -> Optional[ArticleSEO]:
        return (
            await db.execute(
                select(ArticleSEO)
                .where(ArticleSEO.article_id == article_id)
                .order_by(ArticleSEO.id.asc())
                .limit(1)
            )
        ).scalars().first()


seo_assistant_service = SEOAssistantService()
