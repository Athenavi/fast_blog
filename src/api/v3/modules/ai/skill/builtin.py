"""内置技能：每个技能都调用 v3 的真实能力，没有空壳

  - ``content_creator``：真实 LLM（复用 ``ai/config`` + ``ai/llm`` + ``workflow/tasks`` 的提示词）
  - ``seo_optimizer``：复用 ``analytics/seo`` 的分析与生成（可落 ``article_seo``）
  - ``keyword_extract``：无分词库时的真实算法（n-gram 频次 + 停用词 + 长度/位置加权 + 长词优先）
  - ``content_stats``：真表聚合（articles / comments / categories）
  - ``migration_preview``：复用 ``ops/migration`` 的解析器，**只解析不落库**
  - ``ops_health``：复用 ``system/monitor`` 的告警统计与异常检测阈值
"""

import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import func, select

from shared.models.article.article import Article
from shared.models.category.category import Category
from shared.models.comment.comment import Comment
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.permission import codes
from src.api.v3.modules.ai import llm
from src.api.v3.modules.ai.config.crud import ai_config_crud
from src.api.v3.modules.ai.config.service import ai_config_service
from src.api.v3.modules.ai.skill.registry import SkillContext, skill
from src.api.v3.modules.ai.workflow import tasks

#: 内容创作动作 → 提示词任务类型（任务类型定义在 workflow/tasks.py，与前端同源）
CONTENT_ACTIONS: Dict[str, str] = {
    "outline": "outline",
    "expand": "smart_continue",
    "title": "generate_titles",
    "polish": "polish",
    "summary": "summarize",
}

_TAG = re.compile(r"<[^>]+>")
_CJK = re.compile(r"[\u4e00-\u9fff]+")
_LATIN = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")

#: 中文停用词/高频虚词（用于 n-gram 过滤；不追求语言学完备，够用且可读）
_STOPWORDS = frozenset(
    "的 了 和 是 在 我 有 就 不 人 都 一 上 也 很 到 说 要 去 你 会 着 没 看 好 这 那 与 及 或 等 "
    "被 把 让 从 但 而 中 对 为 以 之 其 于 则 因 所 能 可 可以 我们 他们 你们 它们 以及 一个 一些 "
    "这个 那个 这些 那些 什么 怎么 如果 因为 所以 但是 然后 还是 已经 自己 时候 现在 需要 应该 "
    "进行 通过 使用 表示 出现 提供 支持 实现 包括 由于 对于 关于 根据 按照 只是 可能 一定 非常 比较 "
    "以及 并且 或者 不过 只是 如此 这样 那样 如何 为何 是否 其中 以上 以下 之后 之前 目前 同时".split()
)


async def _resolve_settings(ctx: SkillContext):
    """取可用 LLM 配置（``config_id`` 留空则用第一条配置）"""
    config_id = ctx.config_id
    if config_id is None:
        rows, _total = await ai_config_crud.list(ctx.db, page=1, page_size=1)
        if not rows:
            raise NotFoundError("还没有可用的 AI 配置，请先在「AI 配置」里添加并测试连接")
        config_id = int(rows[0].id)
    return await ai_config_service.resolve_llm_settings(ctx.db, config_id)


def extract_keywords(
    text: str, *, limit: int = 15, min_len: int = 2, max_len: int = 6, min_count: int = 2
) -> List[Dict[str, Any]]:
    """中文关键词提取（无分词库依赖的真实算法）

    1. 去 HTML 标签，中文取 2-6 字滑窗 n-gram、英文取单词
    2. 停用词过滤 + 频次统计
    3. **最小频次剪枝**：只保留出现 ≥ ``min_count`` 次的候选 —— 没有分词库时，
       只出现一次的 n-gram 绝大多数是**跨词边界**的拼接噪声（如「容营销策略需」），
       把它们当关键词会明显污染结果；需要长尾词时把 ``min_count`` 设为 1
    4. 打分 = 频次 × 长度权重 × 位置权重（前 20% 出现的词加权）
    5. 长词包含短词时保留长词（避免「数据」与「数据分析」并列）
    """
    plain = _TAG.sub(" ", text or "")
    if not plain.strip():
        raise BadRequestError("待提取的文本为空")

    counts: Counter = Counter()
    first_seen: Dict[str, int] = {}

    for match in _LATIN.finditer(plain):
        word = match.group(0).lower()
        if word in _STOPWORDS:
            continue
        counts[word] += 1
        first_seen.setdefault(word, match.start())

    for block in _CJK.finditer(plain):
        chars = block.group(0)
        for size in range(min_len, max_len + 1):
            for start in range(0, max(0, len(chars) - size + 1)):
                gram = chars[start : start + size]
                if gram in _STOPWORDS or any(ch in _STOPWORDS for ch in gram):
                    continue
                counts[gram] += 1
                first_seen.setdefault(gram, block.start() + start)

    if not counts:
        raise BadRequestError("未从文本中提取到候选关键词（内容过短或全是停用词）")

    threshold = max(1, min_count)
    total_len = max(len(plain), 1)
    scored: List[tuple] = []
    for gram, freq in counts.items():
        if freq < threshold:
            continue
        length_bonus = 1 + 0.15 * (len(gram) - min_len)
        position_bonus = 1.2 if first_seen.get(gram, total_len) < total_len * 0.2 else 1.0
        scored.append((gram, freq, freq * length_bonus * position_bonus))

    if not scored:
        raise BadRequestError(
            f"没有出现次数达到 {threshold} 次的候选关键词（可把 min_count 调低，或提供更长的文本）"
        )

    scored.sort(key=lambda item: (-item[2], -len(item[0]), item[0]))

    picked: List[tuple] = []
    for gram, freq, score in scored:
        if any(gram != longer and gram in longer for longer, _f, _s in picked):
            continue
        picked.append((gram, freq, score))
        if len(picked) >= limit:
            break

    return [
        {"keyword": gram, "count": int(freq), "score": round(float(score), 2)}
        for gram, freq, score in picked
    ]


@skill(
    "keyword_extract",
    label="关键词提取",
    description="从正文中提取候选关键词（n-gram 频次 + 停用词过滤 + 长度/位置加权，不调用模型）",
    category="seo_optimization",
    required_permission=codes.SEO_VIEW,
    params=(
        {"name": "text", "type": "text", "required": False, "description": "待提取文本；与 article_id 二选一"},
        {"name": "article_id", "type": "int", "required": False, "description": "从该文章的正文提取"},
        {"name": "limit", "type": "int", "required": False, "default": 15, "description": "返回条数上限"},
        {"name": "min_count", "type": "int", "required": False, "default": 2,
         "description": "最小出现次数（无分词库时低于该次数的 n-gram 多为跨词噪声；要长尾词可设为 1）"},
    ),
)
async def keyword_extract(ctx: SkillContext) -> Dict[str, Any]:
    text = ctx.param("text")
    article_id = ctx.int_param("article_id")
    if not text and article_id is None:
        raise BadRequestError("需要 text 或 article_id 之一")

    if not text:
        article = await ctx.db.get(Article, int(article_id))
        if article is None:
            raise NotFoundError("文章不存在")
        from shared.models.article.article_content import ArticleContent

        row = (
            await ctx.db.execute(
                select(ArticleContent)
                .where(ArticleContent.article == int(article_id))
                .order_by(ArticleContent.id.asc())
                .limit(1)
            )
        ).scalars().first()
        text = (row.content if row is not None else "") or article.title or ""

    limit = ctx.int_param("limit", default=15) or 15
    min_count = ctx.int_param("min_count", default=2) or 2
    keywords = extract_keywords(
        str(text), limit=max(1, min(limit, 100)), min_count=max(1, min(min_count, 20))
    )
    return {
        "source": "article" if article_id is not None and not ctx.param("text") else "text",
        "article_id": article_id,
        "total": len(keywords),
        "keywords": keywords,
    }


@skill(
    "content_creator",
    label="内容创作助手",
    description="大纲 / 扩写 / 标题 / 润色 / 摘要（真实调用 LLM，提示词与工作流任务同源）",
    category="content_creation",
    required_permission=codes.AI_WORKFLOW_EXECUTE,
    params=(
        {"name": "action", "type": "str", "required": True, "default": "outline",
         "description": f"动作：{', '.join(sorted(CONTENT_ACTIONS))}"},
        {"name": "text", "type": "text", "required": True, "description": "要处理的正文"},
        {"name": "target_lang", "type": "str", "required": False, "description": "风格/语言提示（style_transform 等用）"},
        {"name": "max_tokens", "type": "int", "required": False, "description": "输出上限"},
    ),
)
async def content_creator(ctx: SkillContext) -> Dict[str, Any]:
    action = str(ctx.param("action", "outline")).strip().lower()
    task_type = CONTENT_ACTIONS.get(action)
    if task_type is None:
        raise BadRequestError(f"未知动作「{action}」（可选：{sorted(CONTENT_ACTIONS)}）")
    text = ctx.require("text", label="text（要处理的正文）")

    settings = await _resolve_settings(ctx)
    system, prompt = tasks.render(
        task_type, input_text=str(text), target_lang=str(ctx.param("target_lang", "英文"))
    )
    result = await llm.complete(
        settings, system=system or None, prompt=prompt, max_tokens=ctx.int_param("max_tokens")
    )
    return {
        "action": action,
        "task_type": task_type,
        "model": settings.model,
        "output": result.text,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
    }


@skill(
    "seo_optimizer",
    label="SEO 优化",
    description="文章 SEO 规则分析，或用 AI 生成 SEO 元信息（可选直接落库 article_seo）",
    category="seo_optimization",
    required_permission=codes.SEO_EDIT,
    params=(
        {"name": "article_id", "type": "int", "required": True, "description": "文章 ID"},
        {"name": "action", "type": "str", "required": False, "default": "analyze",
         "description": "analyze（规则分析）/ meta（AI 生成元信息）"},
        {"name": "apply", "type": "bool", "required": False, "default": False,
         "description": "meta 动作：是否写入 article_seo"},
    ),
)
async def seo_optimizer(ctx: SkillContext) -> Dict[str, Any]:
    from src.api.v3.modules.analytics.seo.assistant_service import seo_assistant_service
    from src.api.v3.modules.analytics.seo.service import seo_service

    article_id = int(ctx.require("article_id", label="article_id（文章 ID）"))
    action = str(ctx.param("action", "analyze")).strip().lower()

    if action == "analyze":
        return await seo_service.analyze_article(ctx.db, article_id)
    if action == "meta":
        return await seo_assistant_service.generate_for_article(
            ctx.db,
            article_id,
            config_id=ctx.config_id,
            apply=bool(ctx.param("apply", False)),
            max_tokens=ctx.int_param("max_tokens"),
        )
    raise BadRequestError(f"未知动作「{action}」（可选：analyze / meta）")


@skill(
    "content_stats",
    label="内容统计",
    description="已发布 / 草稿 / 回收站文章数、评论数、分类数、窗口内新增（真表聚合）",
    category="data_analysis",
    required_permission=codes.ARTICLE_VIEW,
    params=(
        {"name": "days", "type": "int", "required": False, "default": 7, "description": "统计窗口（天）"},
    ),
)
async def content_stats(ctx: SkillContext) -> Dict[str, Any]:
    days = ctx.int_param("days", default=7) or 7
    days = max(1, min(days, 365))
    since = datetime.now() - timedelta(days=days)

    async def _count(model, *conditions) -> int:
        return int(
            (await ctx.db.execute(select(func.count()).select_from(model).where(*conditions))).scalar() or 0
        )

    top_rows = (
        await ctx.db.execute(
            select(Category.name, func.count(Article.id))
            .join(Article, Article.category == Category.id)
            .where(Article.status == 1)
            .group_by(Category.name)
            .order_by(func.count(Article.id).desc())
            .limit(5)
        )
    ).all()

    return {
        "window_days": days,
        "articles": {
            "published": await _count(Article, Article.status == 1),
            "draft": await _count(Article, Article.status == 0),
            "deleted": await _count(Article, Article.status == -1),
            "created_in_window": await _count(Article, Article.created_at >= since),
        },
        "comments": await _count(Comment),
        "categories": await _count(Category),
        "top_categories": [{"name": name, "published": int(count)} for name, count in top_rows],
    }


@skill(
    "migration_preview",
    label="迁移预检",
    description="解析 wordpress/markdown/ghost/json/csv 源文件并给出条目预览（只解析，不落库）",
    category="data_migration",
    required_permission=codes.MIGRATION_VIEW,
    params=(
        {"name": "platform", "type": "str", "required": True, "description": "wordpress / markdown / ghost / json / csv…"},
        {"name": "file_path", "type": "str", "required": True, "description": "服务端文件或目录路径"},
        {"name": "preview_size", "type": "int", "required": False, "default": 5, "description": "预览条数"},
    ),
)
async def migration_preview(ctx: SkillContext) -> Dict[str, Any]:
    from src.api.v3.modules.ops.migration.importers import IMPORTER_KINDS, load_feed

    platform = str(ctx.require("platform", label="platform（来源平台）")).strip().lower()
    raw_path = str(ctx.require("file_path", label="file_path（服务端路径）")).strip()
    kind = IMPORTER_KINDS.get(platform)
    if kind is None and platform != "wordpress":
        raise BadRequestError(
            f"来源平台「{platform}」的解析器尚未实现（可用：wordpress、{', '.join(sorted(IMPORTER_KINDS))}）"
        )

    path = Path(raw_path)
    if not path.exists():
        raise BadRequestError(f"源文件不存在：{path}")

    preview_size = max(1, min(ctx.int_param("preview_size", default=5) or 5, 50))
    if kind is None:
        from src.api.v3.modules.ops.migration.wxr_importer import parse_wxr

        feed = parse_wxr(path.read_bytes())
        importable = feed.importable_items
        preview = [
            {"title": item.title, "slug": item.slug, "status": item.status, "type": item.post_type}
            for item in importable[:preview_size]
        ]
        total = len(importable)
    else:
        article_feed = load_feed(kind, path, {})
        preview = [
            {"title": item.title, "slug": item.slug, "status": item.status, "type": "article"}
            for item in article_feed.items[:preview_size]
        ]
        total = len(article_feed.items)

    return {
        "platform": platform,
        "file": str(path),
        "total_items": total,
        "preview": preview,
        "note": "预检只解析源文件，不写入任何表",
    }


@skill(
    "ops_health",
    label="运维健康",
    description="告警统计 + 异常检测阈值（复用 system/monitor 的真实聚合）",
    category="system_ops",
    required_permission=codes.MONITOR_VIEW,
    params=(),
)
async def ops_health(ctx: SkillContext) -> Dict[str, Any]:
    from src.api.v3.modules.system.monitor.monitoring_service import monitoring_alert_service
    from src.api.v3.modules.system.security.anomaly_service import anomaly_detection_service

    return {
        "alerts": await monitoring_alert_service.stats(ctx.db),
        "anomaly_thresholds": await anomaly_detection_service.load_thresholds(ctx.db),
        "checked_at": datetime.now().isoformat(),
    }
