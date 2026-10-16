"""推荐服务：相关文章 / 热门 / 个性化 / 标签建议（真表 + 可解释算法）

对齐 v2 的 ``shared/services/advanced_features/recommendation_service.py``（16.1KB）与
``ai_tag_recommendation.py``（10.5KB）。v2 把「用户画像」与「文章特征」存在**进程内存**里
（重启即丢、多进程还不一致）；v3 全部从真表实时计算：

  - 行为信号：``article_likes``（点赞）+ ``page_views``（阅读，URL 归一后匹配文章 slug）
  - 内容信号：``articles.tags_list`` / ``category`` / ``title`` / ``views`` / ``likes`` / ``published_at``
  - **打分可解释**：返回每个候选的分项得分，不做黑盒排序

算法（沿用 v2 的权重取向，但把公式写清楚）：

  兴趣权重：点赞 3.0、阅读 1.0；时间衰减 ``max(0.1, 1 - days/30)``；按标签归一化
  候选得分：标签匹配 ×0.4 + 分类匹配 ×0.2 + 时效 ×0.2 + 热度 ×0.2

**不做**：协同过滤的离线训练/向量召回（需要额外存储与任务调度，本批不引入）；
"看过同篇的人还看" 这类共现推荐需要全量行为矩阵，属于后续独立课题。
"""

import json
import re
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.article.article_content import ArticleContent
from shared.models.article.article_like import ArticleLike
from src.api.v3.core.exceptions import NotFoundError
from src.api.v3.core.logger import get_logger

logger = get_logger("content.recommend")

#: 行为权重（点赞比阅读更能表达偏好）
ACTION_WEIGHTS: Dict[str, float] = {"like": 3.0, "view": 1.0}

#: 兴趣时间衰减天数（超过后衰减到 0.1）
DECAY_DAYS = 30

#: 候选集上限（避免全表扫描；按发布时间倒序取最近的）
CANDIDATE_LIMIT = 500

#: 用户行为读取上限
BEHAVIOR_LIMIT = 300

#: 得分权重
WEIGHTS = {"tag": 0.4, "category": 0.2, "recency": 0.2, "popularity": 0.2}

_SLUG_IN_URL = re.compile(r"/([A-Za-z0-9\u4e00-\u9fff][A-Za-z0-9\u4e00-\u9fff_-]*)/?$")


def split_tags(raw: Any) -> List[str]:
    """``tags_list`` 可能是 JSON 数组字符串、逗号分隔文本或已是列表"""
    if raw in (None, "", [], {}):
        return []
    if isinstance(raw, (list, tuple, set)):
        items: Iterable[Any] = raw
    else:
        text = str(raw).strip()
        if text.startswith("["):
            try:
                parsed = json.loads(text)
            except ValueError:
                parsed = None
            items = parsed if isinstance(parsed, list) else [text]
        else:
            items = re.split(r"[,;，；]+", text)
    result: List[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in result:
            result.append(text)
    return result


def jaccard(left: Sequence[str], right: Sequence[str]) -> float:
    """集合相似度（空集按 0 处理，不做"都为空所以相似"的误判）"""
    a, b = set(left), set(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def recency_score(published_at: Optional[datetime], *, now: Optional[datetime] = None) -> float:
    """时效分：30 天半衰期，0..1"""
    if published_at is None:
        return 0.3
    now = now or datetime.now()
    days = max((now - published_at).total_seconds() / 86400.0, 0.0)
    return round(1.0 / (1.0 + days / 30.0), 4)


def popularity_score(views: Any, likes: Any) -> float:
    """热度分：``min(1, (views + likes*10) / 1000)``（点赞比浏览更稀缺，放大 10 倍）"""
    try:
        total = float(views or 0) + float(likes or 0) * 10.0
    except (TypeError, ValueError):
        return 0.0
    return round(min(1.0, total / 1000.0), 4)


def interest_weights(
    actions: Sequence[Dict[str, Any]], *, now: Optional[datetime] = None
) -> Dict[str, float]:
    """用户兴趣画像：``{标签: 归一化权重}``

    ``actions`` 每项形如 ``{"tags": [...], "action": "like"|"view", "at": datetime|None}``。
    """
    now = now or datetime.now()
    raw: Counter = Counter()
    for action in actions:
        weight = ACTION_WEIGHTS.get(str(action.get("action") or "view"), 1.0)
        at = action.get("at")
        if isinstance(at, datetime):
            days = max((now - at).total_seconds() / 86400.0, 0.0)
            weight *= max(0.1, 1.0 - days / DECAY_DAYS)
        for tag in split_tags(action.get("tags")):
            raw[tag] += weight
    total = sum(raw.values())
    if total <= 0:
        return {}
    return {tag: round(value / total, 6) for tag, value in raw.items()}


def category_affinity(
    actions: Sequence[Dict[str, Any]], *, now: Optional[datetime] = None
) -> Dict[int, float]:
    """用户对分类的偏好（与标签画像同样的衰减与权重）"""
    now = now or datetime.now()
    raw: Counter = Counter()
    for action in actions:
        category = action.get("category")
        if category in (None, ""):
            continue
        weight = ACTION_WEIGHTS.get(str(action.get("action") or "view"), 1.0)
        at = action.get("at")
        if isinstance(at, datetime):
            days = max((now - at).total_seconds() / 86400.0, 0.0)
            weight *= max(0.1, 1.0 - days / DECAY_DAYS)
        raw[int(category)] += weight
    total = sum(raw.values())
    if total <= 0:
        return {}
    return {int(key): round(value / total, 6) for key, value in raw.items()}


def score_candidate(
    *,
    interests: Dict[str, float],
    candidate_tags: Sequence[str],
    category_score: float,
    published_at: Optional[datetime],
    views: Any,
    likes: Any,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """候选打分（返回分项，便于前端解释「为什么推荐」）"""
    tag_score = sum(interests.get(tag, 0.0) for tag in candidate_tags)
    tag_score = min(1.0, tag_score)
    recency = recency_score(published_at, now=now)
    popularity = popularity_score(views, likes)

    total = (
        tag_score * WEIGHTS["tag"]
        + max(0.0, min(1.0, category_score)) * WEIGHTS["category"]
        + recency * WEIGHTS["recency"]
        + popularity * WEIGHTS["popularity"]
    )
    return {
        "score": round(total, 6),
        "tag_score": round(tag_score, 6),
        "category_score": round(max(0.0, min(1.0, category_score)), 6),
        "recency_score": recency,
        "popularity_score": popularity,
    }


def slug_from_page_url(url: Optional[str]) -> Optional[str]:
    """从 ``page_views.page_url`` 里取末段 slug（``/article/hello`` → ``hello``）"""
    if not url:
        return None
    path = str(url).split("#", 1)[0].split("?", 1)[0].rstrip("/")
    match = _SLUG_IN_URL.search(path)
    return match.group(1) if match else None


class RecommendService:
    """推荐：相关文章 / 热门 / 个性化 / 标签建议"""

    # ------------------------------------------------------------------ 相关文章
    async def related(self, db: AsyncSession, article_id: int, *, limit: int = 8) -> Dict[str, Any]:
        """相关文章：同分类优先 + 标签 Jaccard 相似度 + 热度微调（真表计算）"""
        article = await db.get(Article, article_id)
        if article is None:
            raise NotFoundError("文章不存在")

        base_tags = split_tags(article.tags_list)
        rows = await self._candidates(db, exclude_ids=[article_id])
        scored: List[Tuple[float, Article, float]] = []
        for candidate in rows:
            tag_similarity = jaccard(base_tags, split_tags(candidate.tags_list))
            same_category = (
                article.category is not None and candidate.category == article.category
            )
            # 相关度 = 标签相似度 ×0.7 + 同分类 ×0.2 + 热度 ×0.1
            score = (
                tag_similarity * 0.7
                + (0.2 if same_category else 0.0)
                + popularity_score(candidate.views, candidate.likes) * 0.1
            )
            if score <= 0:
                continue
            scored.append((score, candidate, tag_similarity))

        scored.sort(key=lambda item: (-item[0], -int(item[1].views or 0), int(item[1].id)))
        return {
            "article_id": article_id,
            "base_tags": base_tags,
            "total": len(scored),
            "items": [
                {
                    **self._article_out(candidate),
                    "similarity": round(float(similarity), 6),
                    "score": round(float(score), 6),
                }
                for score, candidate, similarity in scored[: max(1, min(limit, 50))]
            ],
        }

    # ------------------------------------------------------------------ 热门
    async def popular(
        self, db: AsyncSession, *, days: Optional[int] = None, limit: int = 10
    ) -> Dict[str, Any]:
        """热门文章

        - ``days`` 为空：按 ``articles.views`` 累计排序（快照）
        - 指定 ``days``：按窗口内 ``page_views`` 的真实计数排序（page_url 归一后匹配 slug）
        """
        limit = max(1, min(limit, 50))
        if not days:
            rows = (
                await db.execute(
                    select(Article)
                    .where(Article.status == 1)
                    .order_by(Article.views.desc().nullslast(), Article.likes.desc().nullslast())
                    .limit(limit)
                )
            ).scalars().all()
            return {
                "window_days": None,
                "source": "articles.views（累计快照）",
                "items": [self._article_out(row) for row in rows],
            }

        window = max(1, min(int(days), 365))
        since = datetime.now() - timedelta(days=window)
        views = await self._view_counts(db, since)
        if not views:
            return {
                "window_days": window,
                "source": f"page_views（近 {window} 天，暂无数据）",
                "items": [],
            }

        top = sorted(views.items(), key=lambda item: (-item[1], item[0]))[: limit * 3]
        slugs = [slug for slug, _count in top]
        rows = (
            await db.execute(
                select(Article).where(Article.status == 1, Article.slug.in_(slugs))
            )
        ).scalars().all()
        by_slug = {row.slug: row for row in rows}

        items = []
        for slug, count in top:
            article = by_slug.get(slug)
            if article is None:
                continue
            items.append({**self._article_out(article), "window_views": int(count)})
            if len(items) >= limit:
                break
        return {
            "window_days": window,
            "source": f"page_views（近 {window} 天真实计数）",
            "items": items,
        }

    # ------------------------------------------------------------------ 个性化
    async def for_user(self, db: AsyncSession, user_id: int, *, limit: int = 10) -> Dict[str, Any]:
        """个性化推荐：兴趣画像（点赞 ×3 + 阅读 ×1，30 天衰减）→ 候选打分"""
        now = datetime.now()
        actions, read_ids = await self._user_behavior(db, user_id, now=now)
        interests = interest_weights(actions, now=now)
        affinity = category_affinity(actions, now=now)

        rows = await self._candidates(db, exclude_ids=list(read_ids))
        scored: List[Tuple[float, Article, Dict[str, Any]]] = []
        for candidate in rows:
            if candidate.user is not None and int(candidate.user) == int(user_id):
                continue  # 不推荐自己写的
            parts = score_candidate(
                interests=interests,
                candidate_tags=split_tags(candidate.tags_list),
                category_score=affinity.get(int(candidate.category or 0), 0.0),
                published_at=candidate.published_at,
                views=candidate.views,
                likes=candidate.likes,
                now=now,
            )
            if parts["score"] <= 0:
                continue
            scored.append((parts["score"], candidate, parts))

        scored.sort(key=lambda item: (-item[0], int(item[1].id)))
        return {
            "user_id": user_id,
            "behavior_samples": len(actions),
            "interest_tags": sorted(interests.items(), key=lambda item: -item[1])[:10],
            "cold_start": not interests,
            "items": [
                {**self._article_out(candidate), **parts}
                for _score, candidate, parts in scored[: max(1, min(limit, 50))]
            ],
        }

    # ------------------------------------------------------------------ 标签
    async def tag_suggestions(
        self, db: AsyncSession, article_id: int, *, limit: int = 10
    ) -> Dict[str, Any]:
        """标签建议：正文关键词（复用技能框架的算法）+ 与现有标签库的匹配情况"""
        from src.api.v3.modules.ai.skill.builtin import extract_keywords

        article = await db.get(Article, article_id)
        if article is None:
            raise NotFoundError("文章不存在")
        content_row = (
            await db.execute(
                select(ArticleContent)
                .where(ArticleContent.article == article_id)
                .order_by(ArticleContent.id.asc())
                .limit(1)
            )
        ).scalars().first()
        text = f"{article.title or ''}\n{(content_row.content if content_row is not None else '') or ''}"

        current = split_tags(article.tags_list)
        try:
            keywords = extract_keywords(text, limit=max(1, min(limit, 30)))
        except Exception:  # noqa: BLE001 - 文本过短时给空建议而不是 500
            keywords = []

        known = await self._known_tags(db)
        return {
            "article_id": article_id,
            "current_tags": current,
            "known_tags": sorted(known)[:50],
            "suggestions": [
                {
                    "tag": item["keyword"],
                    "count": item["count"],
                    "score": item["score"],
                    "in_use": item["keyword"] in known,
                    "already_on_article": item["keyword"] in current,
                }
                for item in keywords
            ],
        }

    async def trending_tags(self, db: AsyncSession, *, days: int = 30, limit: int = 20) -> Dict[str, Any]:
        """热门标签：窗口内已发布文章的 ``tags_list`` 计数（真表）"""
        window = max(1, min(int(days), 365))
        since = datetime.now() - timedelta(days=window)
        rows = (
            await db.execute(
                select(Article.tags_list)
                .where(Article.status == 1, Article.published_at >= since)
                .limit(CANDIDATE_LIMIT * 2)
            )
        ).scalars().all()

        counter: Counter = Counter()
        for raw in rows:
            for tag in split_tags(raw):
                counter[tag] += 1
        return {
            "window_days": window,
            "total_tags": len(counter),
            "items": [
                {"tag": tag, "count": int(count)}
                for tag, count in counter.most_common(max(1, min(limit, 100)))
            ],
        }

    # ------------------------------------------------------------------ 内部
    async def _candidates(
        self, db: AsyncSession, *, exclude_ids: Sequence[int] = ()
    ) -> List[Article]:
        stmt = select(Article).where(Article.status == 1)
        if exclude_ids:
            stmt = stmt.where(Article.id.notin_([int(item) for item in exclude_ids]))
        stmt = stmt.order_by(Article.published_at.desc().nullslast(), Article.id.desc()).limit(
            CANDIDATE_LIMIT
        )
        return list((await db.execute(stmt)).scalars().all())

    async def _view_counts(self, db: AsyncSession, since: datetime) -> Dict[str, int]:
        """窗口内每篇文章的浏览量：把 ``page_views.page_url`` 归一成 slug 后计数"""
        from shared.models.analytics.page_view import PageView

        rows = (
            await db.execute(
                select(PageView.page_url).where(PageView.created_at >= since).limit(20000)
            )
        ).scalars().all()
        counter: Counter = Counter()
        for url in rows:
            slug = slug_from_page_url(url)
            if slug:
                counter[slug] += 1
        return dict(counter)

    async def _user_behavior(
        self, db: AsyncSession, user_id: int, *, now: datetime
    ) -> Tuple[List[Dict[str, Any]], List[int]]:
        """用户行为：点赞（权重高）+ 最近阅读；返回 ``(行为列表, 已读文章 id)``"""
        from shared.models.analytics.page_view import PageView

        likes = (
            await db.execute(
                select(ArticleLike.article, ArticleLike.created_at)
                .where(ArticleLike.user == user_id)
                .order_by(ArticleLike.created_at.desc())
                .limit(BEHAVIOR_LIMIT)
            )
        ).all()
        like_ids = [int(article) for article, _at in likes if article is not None]

        views = (
            await db.execute(
                select(PageView.page_url, PageView.created_at)
                .where(PageView.user == user_id)
                .order_by(PageView.created_at.desc())
                .limit(BEHAVIOR_LIMIT)
            )
        ).all()
        view_slugs = {
            slug: at for url, at in views if (slug := slug_from_page_url(url)) is not None
        }

        wanted = set(like_ids)
        if view_slugs:
            wanted |= set(
                (
                    await db.execute(
                        select(Article.id).where(Article.slug.in_(list(view_slugs)[:BEHAVIOR_LIMIT]))
                    )
                ).scalars().all()
            )
        if not wanted:
            return [], []

        rows = (
            await db.execute(select(Article).where(Article.id.in_(wanted)))
        ).scalars().all()
        by_id = {int(row.id): row for row in rows}
        by_slug = {row.slug: row for row in rows}

        actions: List[Dict[str, Any]] = []
        for article_id, at in likes:
            row = by_id.get(int(article_id))
            if row is not None:
                actions.append(
                    {"tags": split_tags(row.tags_list), "category": row.category, "action": "like", "at": at}
                )
        for slug, at in view_slugs.items():
            row = by_slug.get(slug)
            if row is not None:
                actions.append(
                    {"tags": split_tags(row.tags_list), "category": row.category, "action": "view", "at": at}
                )

        read_ids = sorted(set(by_id) | {int(row.id) for row in by_slug.values()})
        return actions, read_ids

    async def _known_tags(self, db: AsyncSession, *, scan_limit: int = 500) -> set:
        rows = (
            await db.execute(
                select(Article.tags_list)
                .where(Article.status == 1, Article.tags_list.isnot(None))
                .limit(scan_limit)
            )
        ).scalars().all()
        known: set = set()
        for raw in rows:
            known.update(split_tags(raw))
        return known

    @staticmethod
    def _article_out(row: Article) -> Dict[str, Any]:
        return {
            "id": int(row.id),
            "title": row.title,
            "slug": row.slug,
            "excerpt": row.excerpt,
            "category": row.category,
            "tags": split_tags(row.tags_list),
            "views": int(row.views or 0),
            "likes": int(row.likes or 0),
            "is_featured": bool(row.is_featured),
            "published_at": row.published_at.isoformat() if row.published_at else None,
        }


recommend_service = RecommendService()
