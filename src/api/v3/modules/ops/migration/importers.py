"""多格式导入器：Markdown（Jekyll/Hexo）/ Ghost / 通用 JSON / CSV

契约与 ``wxr_importer`` 完全一致 —— ``run(db, feed, *, on_progress, should_cancel)``，
并复用它的 ``ImportStats`` / ``ImportLog`` / 日志级别常量。各格式只负责把源文件**解析**成
统一的 ``ImportArticle``；**写库路径只有一条**（``ArticleImporter``），避免四份重复的落库逻辑。

Markdown 转 HTML 复用项目已有的 markdown-it-py（``src/utils/filters.py`` 用的是同一个库），
不引入新依赖。渲染配置与 ``filters.md2html`` 同样取向：``html=False`` 会转义正文里的原始
HTML 片段，防止导入带来的存储型 XSS；这里只取 HTML 片段，不拼 ``filters`` 那层页面级 CSS。
"""

import csv
import io
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

import yaml
from markdown_it import MarkdownIt
from mdit_py_plugins import tasklists
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.article.article_content import ArticleContent
from shared.models.category.category import Category
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.ops.migration.wxr_importer import (
    LOG_LEVEL_ERROR,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARNING,
    ImportLog,
    ImportStats,
)

logger = get_logger("ops.migration.importers")

#: platform → 解析器种类（jekyll/hexo 都是「Markdown + YAML front matter」）
IMPORTER_KINDS: dict[str, str] = {
    "markdown": "markdown",
    "jekyll": "markdown",
    "hexo": "markdown",
    "hugo": "markdown",
    "ghost": "ghost",
    "json": "json",
    "csv": "csv",
}

STATUS_PUBLISHED = 1
STATUS_DRAFT = 0
STATUS_DELETED = -1

#: 源状态词 → 本站状态（与 wxr_importer 的取向一致：不认识就按草稿并记日志）
STATUS_MAP: dict[str, int] = {
    "published": STATUS_PUBLISHED,
    "publish": STATUS_PUBLISHED,
    "public": STATUS_PUBLISHED,
    "live": STATUS_PUBLISHED,
    "draft": STATUS_DRAFT,
    "unpublished": STATUS_DRAFT,
    "private": STATUS_DRAFT,
    "hidden": STATUS_DRAFT,
    "deleted": STATUS_DELETED,
}

OUTCOME_IMPORTED = "imported"
OUTCOME_SKIPPED = "skipped"
OUTCOME_FAILED = "failed"

#: 源字段候选名（JSON / CSV 用；可由 ``config.field_map`` 覆盖）
DEFAULT_FIELD_MAP: dict[str, tuple[str, ...]] = {
    "title": ("title", "name", "subject", "headline"),
    "content": ("content", "html", "body", "markdown", "text", "description", "post"),
    "slug": ("slug", "url_slug", "permalink", "path"),
    "status": ("status", "state", "published", "draft"),
    "created_at": ("created_at", "date", "published_at", "pubDate", "created", "updated_at"),
    "categories": ("categories", "category", "section", "sections"),
    "tags": ("tags", "tag", "keywords"),
    "source_url": ("url", "link", "source_url", "original_url", "guid"),
}

_MARKDOWN_SUFFIXES = (".md", ".markdown")
_HEADING = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_SLUG_KEEP = re.compile(r"[^\w-]+", re.UNICODE)
_TIME_FORMATS = (
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y%m%d",
)


def _markdown_renderer() -> MarkdownIt:
    """与 ``filters.md2html`` 同取向的渲染器（表格 + 任务列表，原始 HTML 转义）"""
    md = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False})
    md.enable("table")
    md.use(tasklists.tasklists_plugin, enabled=True, label=True)
    return md


_MD = _markdown_renderer()


# ---------------------------------------------------------------- 统一载体
@dataclass
class ImportArticle:
    """各格式解析后的统一文章（只有它会被 ``ArticleImporter`` 写库）"""

    title: str
    content: str = ""
    slug: Optional[str] = None
    status: str = "published"
    created_at: Optional[datetime] = None
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    #: 原站地址（有则导入后可据此生成 301 跳转）
    source_url: Optional[str] = None


@dataclass
class ArticleFeed:
    items: list[ImportArticle]
    source: str = ""
    note: str = ""


# ---------------------------------------------------------------- 值归一化
def slugify(text: str) -> str:
    """生成 slug（保留中文等 ``\\w`` 字符，其余折叠为 ``-``）"""
    value = (text or "").strip().lower().replace(" ", "-")
    value = _SLUG_KEEP.sub("-", value)
    return re.sub(r"-{2,}", "-", value).strip("-")[:200]


def as_list(value: Any) -> list[str]:
    """把「分类/标签」的多种来源形式统一成字符串列表"""
    if value is None or value == "":
        return []
    items: list[Any]
    if isinstance(value, (list, tuple, set)):
        items = list(value)
    elif isinstance(value, str):
        items = re.split(r"[,;\n]+", value)
    else:
        items = [value]

    result: list[str] = []
    for item in items:
        if isinstance(item, dict):
            item = item.get("name") or item.get("title") or item.get("slug") or ""
        text = str(item).strip()
        if text and text not in result:
            result.append(text[:100])
    return result


def as_datetime(value: Any) -> Optional[datetime]:
    """时间字段归一化：datetime / date / 时间戳 / 常见字符串格式 / RFC822"""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, (int, float)):
        # 毫秒时间戳（Ghost/Jekyll 前端工具常见）与秒时间戳都兼容
        seconds = float(value) / 1000 if float(value) > 1e11 else float(value)
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(tzinfo=None)
        except (OverflowError, OSError, ValueError):
            return None

    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00") if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        pass
    for fmt in _TIME_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    return None


def as_status(value: Any, default: str = "draft") -> Optional[str]:
    """状态归一化；返回 ``None`` 表示无法识别（调用方按草稿处理并记日志）"""
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return "published" if value else "draft"
    if isinstance(value, (int, float)):
        return {1: "published", 0: "draft", -1: "deleted"}.get(int(value))
    text = str(value).strip().lower()
    if not text:
        return default
    if text in STATUS_MAP:
        return "published" if STATUS_MAP[text] == STATUS_PUBLISHED else text
    return {"true": "published", "yes": "published", "false": "draft", "no": "draft"}.get(text)


def pick(record: dict[str, Any], field_name: str, field_map: Optional[dict[str, Any]] = None) -> Any:
    """按「配置覆盖 → 默认候选名」顺序取字段值"""
    candidates: list[str] = []
    if field_map and field_map.get(field_name):
        configured = field_map[field_name]
        candidates.extend(configured if isinstance(configured, (list, tuple)) else [configured])
    candidates.extend(DEFAULT_FIELD_MAP.get(field_name, ()))
    for key in candidates:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return None


def to_html(content: str) -> str:
    """正文按需转 HTML：已经是 HTML 的（含块级标签）原样返回，Markdown 才渲染"""
    text = content or ""
    if re.search(r"<(p|div|h[1-6]|ul|ol|table|img|pre|blockquote)[\s>/]", text, re.IGNORECASE):
        return text
    return _MD.render(text).strip()


# ---------------------------------------------------------------- Markdown
def split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    """拆 YAML front matter；没有或格式错误时返回空 meta + 原文"""
    if not text.lstrip("\ufeff").startswith("---"):
        return {}, text
    body_text = text.lstrip("\ufeff")
    parts = body_text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta: dict[str, Any] = {}
    try:
        loaded = yaml.safe_load(parts[1])
        if isinstance(loaded, dict):
            meta = loaded
    except yaml.YAMLError as exc:
        logger.warning("front matter 解析失败，按无元数据导入：%s", exc)
    return meta, parts[2].lstrip("\r\n")


def parse_markdown_file(path: Path, *, base: Optional[Path] = None) -> ImportArticle:
    text = path.read_text(encoding="utf-8", errors="replace")
    meta, body = split_front_matter(text)

    title = str(meta.get("title") or "").strip()
    if not title:
        heading = _HEADING.search(body)
        title = (heading.group(1).strip() if heading else "") or path.stem
    # 无显式 slug 时按静态站点生成器的语义用文件名派生（URL 由文件名决定）；
    # 写库层（ArticleImporter）在 slug 仍为空时会用标题兜底
    slug = (
        str(meta.get("slug") or meta.get("permalink") or "").strip()
        or slugify(path.stem)
        or None
    )

    status_raw = meta.get("status")
    if status_raw in (None, ""):
        status_raw = "published" if meta.get("published", True) else "draft"
    status = as_status(status_raw) or "draft"

    created = as_datetime(meta.get("date") or meta.get("created_at") or meta.get("updated_at"))
    if created is None:
        created = datetime.fromtimestamp(path.stat().st_mtime)

    return ImportArticle(
        title=title[:255],
        content=to_html(body),
        slug=slug,
        status=status,
        created_at=created,
        categories=as_list(meta.get("categories") or meta.get("category")),
        tags=as_list(meta.get("tags")),
        source_url=str(meta.get("url") or meta.get("permalink") or "").strip() or None,
    )


def parse_markdown_path(path: Path) -> ArticleFeed:
    """``file_path`` 可以是单个 ``.md`` 文件，也可以是目录（递归收集）"""
    if path.is_dir():
        files = sorted(
            item
            for item in path.rglob("*")
            if item.is_file() and item.suffix.lower() in _MARKDOWN_SUFFIXES
        )
    else:
        files = [path]
    items = [parse_markdown_file(item, base=path) for item in files]
    return ArticleFeed(items=items, source=str(path), note=f"{len(items)} 个 markdown 文件")


# ---------------------------------------------------------------- Ghost
def parse_ghost(raw: bytes | str) -> ArticleFeed:
    """Ghost 导出 JSON：``{"db":[{"data":{"posts":[],"tags":[],"posts_tags":[]}}]}`` 或扁平的 ``{"posts":[]}``"""
    data = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
    payload: dict[str, Any] = {}
    if isinstance(data, dict) and isinstance(data.get("db"), list) and data["db"]:
        first = data["db"][0]
        if isinstance(first, dict):
            payload = first.get("data") or {}
    if not payload and isinstance(data, dict):
        payload = data
    if not isinstance(payload, dict):
        raise ValueError("Ghost 导出结构无法识别：期望 {db:[{data:{...}}]} 或 {posts:[...]}")

    posts = payload.get("posts") or []
    tag_names = {
        str(tag.get("id")): (tag.get("name") or tag.get("slug") or "")
        for tag in (payload.get("tags") or [])
        if isinstance(tag, dict)
    }
    tags_by_post: dict[str, list[str]] = {}
    for link in payload.get("posts_tags") or []:
        if not isinstance(link, dict):
            continue
        post_id = str(link.get("post_id") or "")
        name = tag_names.get(str(link.get("tag_id") or ""), "")
        if post_id and name:
            tags_by_post.setdefault(post_id, []).append(name)

    items: list[ImportArticle] = []
    for post in posts:
        if not isinstance(post, dict):
            continue
        title = str(post.get("title") or "").strip()
        if not title:
            continue
        tags = [str(tag.get("name") or "") for tag in (post.get("tags") or []) if isinstance(tag, dict)]
        tags = [tag for tag in tags if tag] or tags_by_post.get(str(post.get("id") or ""), [])
        items.append(
            ImportArticle(
                title=title[:255],
                content=to_html(str(post.get("html") or post.get("plaintext") or "")),
                slug=str(post.get("slug") or "").strip() or None,
                status=as_status(post.get("status") or post.get("type")) or "draft",
                created_at=as_datetime(post.get("published_at") or post.get("created_at")),
                categories=as_list(post.get("primary_tag") or []),
                tags=as_list(tags) or as_list(post.get("keywords")),
                source_url=str(post.get("url") or "").strip() or None,
            )
        )
    return ArticleFeed(items=items, source="ghost-export", note=f"{len(items)} 篇 post")


# ---------------------------------------------------------------- JSON / CSV
def _records_from_json(raw: bytes | str) -> list[dict[str, Any]]:
    data = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        records = []
        for key in ("posts", "articles", "items", "data", "records", "entries"):
            value = data.get(key)
            if isinstance(value, list):
                records = value
                break
        if not records and not any(key in data for key in ("posts", "articles", "items")):
            records = [data]
    else:
        raise ValueError("JSON 导出结构无法识别：期望数组或含 posts/articles/items 的对象")
    return [item for item in records if isinstance(item, dict)]


def records_to_feed(records: list[dict[str, Any]], *, source: str, config: dict[str, Any]) -> ArticleFeed:
    field_map = config.get("field_map") or {}
    default_status = str(config.get("default_status") or "draft")
    html_content = bool(config.get("content_is_html", False))

    items: list[ImportArticle] = []
    for record in records:
        title = str(pick(record, "title", field_map) or "").strip()
        if not title:
            continue
        raw_content = str(pick(record, "content", field_map) or "")
        items.append(
            ImportArticle(
                title=title[:255],
                content=raw_content if html_content else to_html(raw_content),
                slug=str(pick(record, "slug", field_map) or "").strip() or None,
                status=as_status(pick(record, "status", field_map), default_status) or default_status,
                created_at=as_datetime(pick(record, "created_at", field_map)),
                categories=as_list(pick(record, "categories", field_map)),
                tags=as_list(pick(record, "tags", field_map)),
                source_url=str(pick(record, "source_url", field_map) or "").strip() or None,
            )
        )
    return ArticleFeed(items=items, source=source, note=f"{len(items)} 条记录")


def parse_json(raw: bytes | str, config: dict[str, Any]) -> ArticleFeed:
    return records_to_feed(_records_from_json(raw), source="json", config=config)


def parse_csv(raw: bytes | str, config: dict[str, Any]) -> ArticleFeed:
    text = raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw
    reader = csv.DictReader(io.StringIO(text))
    records = [dict(row) for row in reader]
    return records_to_feed(records, source="csv", config=config)


# ---------------------------------------------------------------- 写库
class ArticleImporter:
    """把 ``ArticleFeed`` 灌进本地库；逐条产出日志，进度由 ``ImportStats`` 计算"""

    def __init__(
        self,
        default_author_id: Optional[int] = None,
        *,
        on_article_imported: Optional[
            Callable[[AsyncSession, ImportArticle, Article], Awaitable[None]]
        ] = None,
    ) -> None:
        #: 源文件没有作者信息时使用的作者（一般是任务创建者）
        self.default_author_id = default_author_id
        #: 导入成功后的钩子（可用它生成 301 跳转等派生数据）
        self.on_article_imported = on_article_imported

    async def run(
        self,
        db: AsyncSession,
        feed: ArticleFeed,
        *,
        on_progress: Optional[Callable[[ImportStats, list[ImportLog]], Awaitable[None]]] = None,
        should_cancel: Optional[Callable[[], bool]] = None,
    ) -> tuple[ImportStats, list[ImportLog]]:
        stats = ImportStats(total=len(feed.items))
        logs: list[ImportLog] = []
        category_cache: dict[str, int] = {}
        category_rows: dict[str, Category] = {}

        await self._emit(
            logs,
            on_progress,
            stats,
            ImportLog(
                LOG_LEVEL_INFO,
                f"来源 {feed.source}：{feed.note or f'{stats.total} 条'}；缺少作者信息的条目归属任务创建者",
            ),
        )

        cancelled = False
        for item in feed.items:
            if should_cancel is not None and should_cancel():
                cancelled = True
                break
            try:
                outcome, entry = await self._import_article(
                    db, item, category_cache, category_rows
                )
            except Exception as exc:  # noqa: BLE001 - 单条失败不能中断整个任务
                await db.rollback()
                stats.failed += 1
                entry = ImportLog(
                    LOG_LEVEL_ERROR,
                    f"导入「{item.title}」失败：{exc}",
                    item_type="article",
                )
            else:
                if outcome == OUTCOME_IMPORTED:
                    stats.imported += 1
                elif outcome == OUTCOME_SKIPPED:
                    stats.skipped += 1
                else:
                    stats.failed += 1
            await self._emit(logs, on_progress, stats, entry)

        if cancelled:
            await self._emit(
                logs,
                on_progress,
                stats,
                ImportLog(LOG_LEVEL_WARNING, "任务被取消，已导入的内容保留"),
            )
        return stats, logs

    async def _emit(
        self,
        logs: list[ImportLog],
        on_progress: Optional[Callable[[ImportStats, list[ImportLog]], Awaitable[None]]],
        stats: ImportStats,
        entry: ImportLog,
    ) -> None:
        logs.append(entry)
        if on_progress is not None:
            await on_progress(stats, [entry])

    async def _import_article(
        self,
        db: AsyncSession,
        item: ImportArticle,
        category_cache: dict[str, int],
        category_rows: dict[str, Category],
    ) -> tuple[str, ImportLog]:
        title = (item.title or "").strip()
        if not title:
            return OUTCOME_SKIPPED, ImportLog(LOG_LEVEL_WARNING, "跳过：标题为空")
        slug = (item.slug or slugify(title))[:255]
        if not slug:
            return OUTCOME_SKIPPED, ImportLog(LOG_LEVEL_WARNING, f"跳过「{title}」：slug 为空")

        existing = (
            await db.execute(select(Article).where(Article.slug == slug).limit(1))
        ).scalars().first()

        notes: list[str] = []
        revived = False
        if existing is not None:
            if int(existing.status or 0) != STATUS_DELETED:
                return OUTCOME_SKIPPED, ImportLog(
                    LOG_LEVEL_WARNING,
                    f"跳过「{title}」：slug「{slug}」已存在（article id={existing.id}）",
                    item_type="article",
                    item_id=int(existing.id),
                )
            # 同 slug 的文章此前被软删除：恢复并覆盖，否则它会永久挡住再次导入
            revived = True
            notes.append("同 slug 的文章此前已删除，已恢复并覆盖")

        status = STATUS_MAP.get((item.status or "").strip().lower())
        if status is None:
            status = STATUS_DRAFT
            notes.append(f"原状态「{item.status}」不支持，按草稿导入")
        if item.slug and item.slug != slug:
            notes.append("原 slug 已规范化为 URL 安全形式")

        category_id = await self._resolve_category(db, item.categories, category_cache, category_rows)
        published_at = item.created_at
        now = datetime.now()

        common_fields: dict[str, Any] = {
            "title": title[:255],
            "slug": slug,
            "excerpt": None,
            "category": category_id,
            "tags_list": item.tags or None,
            "user": self.default_author_id,
            "status": status,
            "hidden": False,
            "is_vip_only": False,
            "required_vip_level": 0,
            "post_type": "article",
            "published_at": published_at if status == STATUS_PUBLISHED else None,
            "updated_at": now,
        }

        if revived and existing is not None:
            for key, value in common_fields.items():
                setattr(existing, key, value)
            existing.deleted_at = None
            article = existing
            await db.flush()
        else:
            article = Article(**common_fields, created_at=published_at or now)
            db.add(article)
            await db.flush()

        content_row = (
            await db.execute(
                select(ArticleContent).where(ArticleContent.article == article.id).limit(1)
            )
        ).scalars().first()
        if content_row is None:
            db.add(
                ArticleContent(
                    article=article.id,
                    content=item.content or "",
                    language_code="zh-CN",
                    created_at=published_at or now,
                    updated_at=now,
                )
            )
        else:
            content_row.content = item.content or ""
            content_row.updated_at = now

        if not revived and category_id is not None:
            row = category_rows.get(str(category_id))
            if row is not None:
                row.articles_count = int(row.articles_count or 0) + 1

        if self.on_article_imported is not None:
            await self.on_article_imported(db, item, article)

        await db.commit()

        suffix = f"（{'；'.join(notes)}）" if notes else ""
        return OUTCOME_IMPORTED, ImportLog(
            LOG_LEVEL_INFO,
            f"已导入「{title}」（{item.status} → article id={article.id}）{suffix}",
            item_type="article",
            item_id=int(article.id),
        )

    async def _resolve_category(
        self,
        db: AsyncSession,
        names: list[str],
        cache: dict[str, int],
        rows: dict[str, Category],
    ) -> Optional[int]:
        """取第一个分类（不存在则新建），与 WXR 导入器同一策略"""
        if not names:
            return None
        name = names[0][:100]
        if name in cache:
            return cache[name]
        row = (
            await db.execute(select(Category).where(Category.name == name).limit(1))
        ).scalars().first()
        if row is None:
            now = datetime.now()
            row = Category(
                name=name,
                slug=slugify(name)[:255] or None,
                description=None,
                parent_id=None,
                sort_order=0,
                is_visible=True,
                articles_count=0,
                created_at=now,
                updated_at=now,
            )
            db.add(row)
            await db.flush()
        cache[name] = int(row.id)
        rows[str(int(row.id))] = row
        return int(row.id)


# ---------------------------------------------------------------- 分派
def load_feed(kind: str, path: Path, config: dict[str, Any]) -> ArticleFeed:
    """按解析器种类读文件；markdown 支持目录"""
    if kind == "markdown":
        return parse_markdown_path(path)
    raw = path.read_bytes()
    if kind == "ghost":
        return parse_ghost(raw)
    if kind == "json":
        return parse_json(raw, config)
    if kind == "csv":
        return parse_csv(raw, config)
    raise ValueError(f"未知的导入器种类：{kind}")


def build_import_job(
    platform: str,
    path: Path,
    config: dict[str, Any],
    default_author_id: Optional[int] = None,
    *,
    on_article_imported: Optional[
        Callable[[AsyncSession, ImportArticle, Article], Awaitable[None]]
    ] = None,
):
    """返回 ``(feed, importer)``；wordpress 走既有的 WXR 通道，其余走 ``ArticleImporter``"""
    kind = IMPORTER_KINDS.get(platform)
    if kind is None:
        from src.api.v3.modules.ops.migration.wxr_importer import WXRImporter, parse_wxr

        return (
            parse_wxr(path.read_bytes()),
            WXRImporter(
                default_author_id=default_author_id,
                on_article_imported=on_article_imported,
            ),
        )
    return (
        load_feed(kind, path, config),
        ArticleImporter(default_author_id=default_author_id, on_article_imported=on_article_imported),
    )
