"""WordPress WXR 导入器：**真实的**「解析 → 转换 → 入库」

源格式由用户拍板定为 **WordPress WXR**（eXtended RSS 1.2，WordPress「工具 → 导出」产出的 XML）。

覆盖范围（**如实报告，不做假成功**）：

  - ``post`` → 本地文章（``articles`` + ``article_content``）；``publish`` → 已发布，
    ``draft`` → 草稿，其它状态（``pending`` / ``private`` / ``trash``）→ 草稿**并写日志说明**；
  - ``page`` / ``attachment`` / ``nav_menu_item`` / ``revision`` 等**不导入**：每条写一条
    ``warning`` 日志（写明跳过原因）并计入 ``skipped``；
  - 分类：item 里 ``domain="category"`` → 取或建 ``categories``，写回 ``articles.category``；
  - 标签：``domain="post_tag"`` → 写入 ``articles.tags_list``（JSON 数组）；
  - 作者：``dc:creator`` 按用户名匹配本地用户；匹配不到 → 用任务创建者，并在日志里注明
    （**不静默丢作者**）；
  - 幂等：按 slug 判重，已存在则跳过（写日志），不会产生重复文章。

XML 解析用标准库 ``xml.etree.ElementTree``（不解析外部实体；调用方另有文件大小上限）。
"""

import xml.etree.ElementTree as ET
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.article.article_content import ArticleContent
from shared.models.category.category import Category
from shared.models.user import User
from src.api.v3.core.logger import get_logger

logger = get_logger("migration.wxr")

#: WXR 命名空间（1.2 为当前主流；1.1 的 wp 前缀不同，未做兼容）
NS = {
    "wp": "http://wordpress.org/export/1.2/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "excerpt": "http://wordpress.org/export/1.2/excerpt/",
    "dc": "http://purl.org/dc/elements/1.1/",
}

#: 可导入的 post_type（其余一律跳过并记日志）
IMPORTABLE_POST_TYPES = {"post"}

#: WordPress 状态 → 本地 Article.status（0 草稿 / 1 已发布）
STATUS_MAP = {"publish": 1, "draft": 0}

#: 本地「已删除」状态（软删除）；同 slug 的这类文章会被**恢复并覆盖**，而不是永久挡住再导入
STATUS_DELETED = -1

LOG_LEVEL_INFO = "info"
LOG_LEVEL_WARNING = "warning"
LOG_LEVEL_ERROR = "error"

OUTCOME_IMPORTED = "imported"
OUTCOME_SKIPPED = "skipped"


@dataclass
class WXRCategory:
    """WXR 顶部的分类 / 标签声明（``wp:category`` / ``wp:tag``）"""

    nicename: str
    name: str
    parent_nicename: Optional[str] = None


@dataclass
class WXRItem:
    """一条 ``<item>``（文章 / 页面 / 附件 / 菜单项…）"""

    post_id: str
    title: str
    slug: str
    post_type: str
    status: str
    content: str
    excerpt: str
    creator: str
    post_date: Optional[str]
    link: Optional[str]
    categories: list[tuple[str, str, str]] = field(default_factory=list)

    def names_for(self, domain: str) -> list[str]:
        """取某个 domain 下的名字列表（``category`` / ``post_tag``）"""
        return [name for dom, _slug, name in self.categories if dom == domain and name]

    def slugs_for(self, domain: str) -> list[str]:
        """取某个 domain 下的 nicename 列表（用作本地 slug）"""
        return [slug for dom, slug, _name in self.categories if dom == domain and slug]


@dataclass
class WXRFeed:
    """解析结果"""

    version: Optional[str]
    title: str
    categories: list[WXRCategory] = field(default_factory=list)
    tags: list[WXRCategory] = field(default_factory=list)
    items: list[WXRItem] = field(default_factory=list)

    @property
    def importable_items(self) -> list[WXRItem]:
        return [item for item in self.items if item.post_type in IMPORTABLE_POST_TYPES]


@dataclass
class ImportLog:
    """一条待落库的任务日志（由 service 写入 ``migration_logs``）"""

    level: str
    message: str
    item_type: Optional[str] = None
    item_id: Optional[int] = None


@dataclass
class ImportStats:
    """导入统计（写回任务表的 ``total_items`` / ``migrated_items`` / ``progress``）"""

    total: int = 0
    imported: int = 0
    skipped: int = 0
    failed: int = 0

    @property
    def handled(self) -> int:
        return self.imported + self.skipped + self.failed

    def progress(self) -> int:
        if self.total <= 0:
            return 100
        return min(100, int(self.handled * 100 / self.total))


# ---------------------------------------------------------------- 解析
def _find_text(node: ET.Element, path: str) -> Optional[str]:
    found = node.find(path, NS)
    if found is None or found.text is None:
        return None
    text = found.text.strip()
    return text or None


def _declared_terms(channel: ET.Element, tag: str) -> list[WXRCategory]:
    out: list[WXRCategory] = []
    for node in channel.findall(f"wp:{tag}", NS):
        name = _find_text(node, "wp:cat_name") or _find_text(node, "wp:tag_name")
        if not name:
            continue
        out.append(
            WXRCategory(
                nicename=(
                    _find_text(node, "wp:category_nicename")
                    or _find_text(node, "wp:tag_slug")
                    or ""
                ),
                name=name,
                parent_nicename=_find_text(node, "wp:category_parent"),
            )
        )
    return out


def parse_wxr(raw: bytes | str) -> WXRFeed:
    """解析 WXR；不是合法 WXR 时抛 ``ValueError``（调用方据此把任务标 failed）"""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError(f"WXR 解析失败：{exc}") from exc

    channel = root.find("channel")
    if channel is None:
        raise ValueError("不是合法的 WXR：缺少 <channel> 节点")

    items: list[WXRItem] = []
    for node in channel.findall("item"):
        categories = [
            (cat.get("domain") or "", cat.get("nicename") or "", (cat.text or "").strip())
            for cat in node.findall("category")
        ]
        items.append(
            WXRItem(
                post_id=_find_text(node, "wp:post_id") or "",
                title=(_find_text(node, "title") or "").strip(),
                slug=(_find_text(node, "wp:post_name") or "").strip(),
                post_type=(_find_text(node, "wp:post_type") or "post").strip(),
                status=(_find_text(node, "wp:status") or "draft").strip(),
                content=_find_text(node, "content:encoded") or "",
                excerpt=_find_text(node, "excerpt:encoded") or "",
                creator=_find_text(node, "dc:creator") or "",
                post_date=_find_text(node, "wp:post_date"),
                link=_find_text(node, "link"),
                categories=categories,
            )
        )

    return WXRFeed(
        version=_find_text(channel, "wp:wxr_version"),
        title=(_find_text(channel, "title") or "").strip(),
        categories=_declared_terms(channel, "category"),
        tags=_declared_terms(channel, "tag"),
        items=items,
    )


def parse_wxr_datetime(value: Optional[str]) -> Optional[datetime]:
    """解析 WXR 时间（``2024-01-02 03:04:05`` 为主，兼容 ISO 与 RFC822）"""
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=None)
        except ValueError:
            continue
    return None


def _safe_int(value: str) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- 导入
class WXRImporter:
    """把 WXR 灌进本地库；逐条产出日志，进度由 ``ImportStats`` 计算"""

    def __init__(self, default_author_id: Optional[int] = None) -> None:
        #: WXR 里的作者在本站匹配不到时使用的作者（一般是任务创建者）
        self.default_author_id = default_author_id

    async def run(
        self,
        db: AsyncSession,
        feed: WXRFeed,
        *,
        on_progress: Optional[Callable[[ImportStats, list[ImportLog]], Awaitable[None]]] = None,
        should_cancel: Optional[Callable[[], bool]] = None,
    ) -> tuple[ImportStats, list[ImportLog]]:
        """执行导入，返回 ``(统计, 日志)``

        - ``on_progress(stats, new_logs)``：每处理一条 item 调一次（调用方据此落库日志、
          更新任务进度）—— 交给调用方是为了**实时可查**，也避免长任务把日志全堆在内存里；
        - ``should_cancel()``：返回 True 时**立即停止**（已导入的部分保留），
          调用方随后把任务置 ``cancelled``；取消点在同一处（每条 item 处理完）。
        """
        stats = ImportStats(total=len(feed.items))
        logs: list[ImportLog] = []
        category_cache: dict[str, int] = {}
        category_rows: dict[str, Category] = {}
        author_cache: dict[str, Optional[int]] = {}

        if feed.version:
            await self._emit(logs, on_progress, stats,
                             ImportLog(LOG_LEVEL_INFO, f"WXR 版本 {feed.version}；feed 标题「{feed.title}」"))
        await self._emit(
            logs,
            on_progress,
            stats,
            ImportLog(
                LOG_LEVEL_INFO,
                f"共 {stats.total} 条 item，可导入类型 {len(feed.importable_items)} 条"
                f"（只支持 {sorted(IMPORTABLE_POST_TYPES)}）",
            ),
        )

        cancelled = False
        for item in feed.items:
            if should_cancel is not None and should_cancel():
                cancelled = True
                break

            if item.post_type not in IMPORTABLE_POST_TYPES:
                stats.skipped += 1
                await self._emit(
                    logs,
                    on_progress,
                    stats,
                    ImportLog(
                        LOG_LEVEL_WARNING,
                        f"跳过 {item.post_type}「{item.title or item.slug}」："
                        f"本导入器只处理 {sorted(IMPORTABLE_POST_TYPES)}",
                        item_type=item.post_type,
                        item_id=_safe_int(item.post_id),
                    ),
                )
                continue

            try:
                outcome, log = await self._import_post(
                    db, item, category_cache, category_rows, author_cache
                )
            except Exception as exc:  # noqa: BLE001 - 单条失败不影响整体，如实记账
                await db.rollback()
                stats.failed += 1
                await self._emit(
                    logs,
                    on_progress,
                    stats,
                    ImportLog(
                        LOG_LEVEL_ERROR,
                        f"导入失败「{item.title or item.slug}」：{exc}",
                        item_type=item.post_type,
                        item_id=_safe_int(item.post_id),
                    ),
                )
                continue

            if outcome == OUTCOME_IMPORTED:
                stats.imported += 1
            else:
                stats.skipped += 1
            await self._emit(logs, on_progress, stats, log)

        if cancelled:
            await self._emit(
                logs,
                on_progress,
                stats,
                ImportLog(
                    LOG_LEVEL_WARNING,
                    f"收到取消请求，已停止（已导入 {stats.imported} 条，剩余未处理）",
                ),
            )
        else:
            await self._emit(
                logs,
                on_progress,
                stats,
                ImportLog(
                    LOG_LEVEL_INFO,
                    f"完成：导入 {stats.imported} / 跳过 {stats.skipped} / 失败 {stats.failed}"
                    f"（共 {stats.total}）",
                ),
            )
        return stats, logs

    @staticmethod
    async def _emit(
        logs: list[ImportLog],
        on_progress: Optional[Callable[[ImportStats, list[ImportLog]], Awaitable[None]]],
        stats: ImportStats,
        log: ImportLog,
    ) -> None:
        """把一条日志交给回调（没有回调时只累积在内存里）"""
        if on_progress is None:
            logs.append(log)
            return
        await on_progress(stats, [log])

    async def _import_post(
        self,
        db: AsyncSession,
        item: WXRItem,
        category_cache: dict[str, int],
        category_rows: dict[str, Category],
        author_cache: dict[str, Optional[int]],
    ) -> tuple[str, ImportLog]:
        """导入一条 post，返回 ``(outcome, log)``"""
        item_ref = ImportLog("", "", item_type=item.post_type, item_id=_safe_int(item.post_id))
        slug = item.slug or (f"wp-{item.post_id}" if item.post_id else "")
        if not slug:
            item_ref.level = LOG_LEVEL_WARNING
            item_ref.message = "跳过：既无 slug 也无 post_id"
            return OUTCOME_SKIPPED, item_ref
        if not item.title:
            item_ref.level = LOG_LEVEL_WARNING
            item_ref.message = f"跳过 slug={slug}：标题为空"
            return OUTCOME_SKIPPED, item_ref

        existing = (
            await db.execute(select(Article).where(Article.slug == slug).limit(1))
        ).scalars().first()

        notes: list[str] = []
        revived = False
        if existing is not None:
            if int(existing.status or 0) != STATUS_DELETED:
                item_ref.level = LOG_LEVEL_WARNING
                item_ref.message = (
                    f"跳过「{item.title}」：slug「{slug}」已存在（article id={existing.id}）"
                )
                return OUTCOME_SKIPPED, item_ref
            # 同 slug 的文章此前被**软删除**：恢复并覆盖，否则它会永久挡住再次导入
            revived = True
            notes.append("同 slug 的文章此前已删除，已恢复并覆盖")

        status = STATUS_MAP.get(item.status)
        if status is None:
            status = 0
            notes.append(f"原状态「{item.status}」不支持，按草稿导入")

        author_id = await self._resolve_author(db, item.creator, author_cache, notes)
        category_id = await self._resolve_category(
            db,
            item.names_for("category"),
            item.slugs_for("category"),
            category_cache,
            category_rows,
        )
        published_at = parse_wxr_datetime(item.post_date)
        now = datetime.now()

        common_fields: dict[str, Any] = {
            "title": item.title[:255],
            "slug": slug[:255],
            "excerpt": (item.excerpt or "").strip()[:255] or None,
            "category": category_id,
            "tags_list": item.names_for("post_tag") or None,
            "user": author_id,
            "status": status,
            "hidden": False,
            "is_vip_only": False,
            "required_vip_level": 0,
            "post_type": "article",
            "published_at": published_at if status == 1 else None,
            "updated_at": now,
        }

        if revived and existing is not None:
            for key, value in common_fields.items():
                setattr(existing, key, value)
            existing.deleted_at = None
            article = existing
            await db.flush()
        else:
            article = Article(
                **common_fields,
                views=0,
                likes=0,
                is_featured=False,
                is_sticky=False,
                sort_order=0,
                created_at=published_at or now,
            )
            db.add(article)
            await db.flush()  # 需要 article.id 才能写正文

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

        if category_id is not None and not revived:
            row = category_rows.get(str(category_id))
            if row is not None:
                row.articles_count = int(row.articles_count or 0) + 1
        await db.commit()

        item_ref.level = LOG_LEVEL_INFO
        suffix = f"；{'；'.join(notes)}" if notes else ""
        item_ref.message = (
            f"已导入「{item.title}」（{item.status} → article id={article.id}）{suffix}"
        )
        return OUTCOME_IMPORTED, item_ref

    async def _resolve_author(
        self,
        db: AsyncSession,
        creator: str,
        cache: dict[str, Optional[int]],
        notes: list[str],
    ) -> Optional[int]:
        """把 WXR 作者映射到本地用户；映射不到就退回任务创建者并**在日志里说明**"""
        if not creator:
            if self.default_author_id is not None:
                notes.append("WXR 未提供作者，使用任务创建者")
            return self.default_author_id
        if creator in cache:
            found = cache[creator]
        else:
            found = (
                await db.execute(select(User.id).where(User.username == creator).limit(1))
            ).scalar()
            found = int(found) if found is not None else None
            cache[creator] = found
        if found is None:
            notes.append(f"作者「{creator}」在本站不存在，使用任务创建者")
            return self.default_author_id
        return found

    async def _resolve_category(
        self,
        db: AsyncSession,
        names: list[str],
        slugs: list[str],
        cache: dict[str, int],
        rows: dict[str, Category],
    ) -> Optional[int]:
        """取 item 的第一个分类（不存在则新建）"""
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
                slug=(slugs[0] if slugs else name)[:255] or None,
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
