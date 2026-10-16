"""帮助系统：默认帮助主题 + 自定义帮助持久化 + 相关性搜索 + 字段提示 + 视频教程

移植自 v2 的 ``shared/services/system/help_system.py``（硬编码字典），v3 做三点实质改进：

1. **内容落真表而非源码硬编码**：默认主题仍是内置常量（``DEFAULT_TOPICS``，内容照搬 v2），
   但**自定义 / 覆盖**条目落 ``system_settings`` 的键 ``help.topics``（JSON 数组）；
   ``get_all_topics`` 把默认与自定义合并（同 ``page_key`` 时自定义覆盖默认）。
2. **真实相关性打分**：v2 的 ``_calculate_relevance`` 只有"标题 +0.5 / 内容 +0.3 /
   链接标题 +0.2"三档子串判断；v3 引入**标题命中权重高于正文**、**命中次数加成**、
   **短语完整匹配加成**、**多词部分命中**，并返回命中字段（``matched_fields``）与
   命中位置附近的摘要（``excerpt``）。
3. **字段提示带上下文**：v2 的 ``get_field_tooltip`` 只按字段名查一张扁平表；v3 支持
   字段名 + 上下文（如 ``article_editor``），未命中返回 ``None``。

纯函数（``_strip_html`` / ``_extract_excerpt`` / ``_score_topic`` / ``_search_topics`` /
``_merge_topics`` / ``_lookup_tooltip``）与 DB 读写分离，便于在有 / 无数据库两种场景下使用与测试。
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger

logger = get_logger("system.help")

#: 自定义帮助条目在 ``system_settings`` 里的键（JSON 数组）
STORAGE_KEY = "help.topics"

#: 自定义帮助条目允许的字段（写入时拒绝未知字段）
TOPIC_FIELDS = ("page_key", "title", "content", "tags", "language", "related_links")

#: 允许的语言
SUPPORTED_LANGUAGES = ("zh_CN", "en_US")

#: 默认帮助主题（内容照搬 v2 ``DEFAULT_HELP_CONTENT``，转成结构化条目）
DEFAULT_TOPICS: List[Dict[str, Any]] = [
    {
        "page_key": "admin_dashboard",
        "title": "管理仪表板",
        "content": (
            "<h3>仪表板概览</h3>"
            "<p>仪表板显示网站的关键统计信息和快速操作。</p>"
            "<ul>"
            "<li><strong>文章统计</strong> - 查看已发布、草稿和待审文章数量</li>"
            "<li><strong>访问统计</strong> - 今日/本周/本月访问量</li>"
            "<li><strong>快速操作</strong> - 快速创建新文章或页面</li>"
            "</ul>"
            "<h4>常见问题</h4>"
            "<p><strong>Q: 如何查看详细的访问统计？</strong><br>"
            "A: 点击“访问统计”卡片可进入详细分析页面。</p>"
        ),
        "tags": ["仪表板", "统计", "概览", "dashboard", "访问统计"],
        "language": "zh_CN",
        "related_links": [
            {"title": "文章管理指南", "url": "/docs/articles"},
            {"title": "SEO 优化技巧", "url": "/docs/seo"},
        ],
    },
    {
        "page_key": "article_editor",
        "title": "文章编辑器",
        "content": (
            "<h3>使用文章编辑器</h3>"
            "<p>文章编辑器支持 Markdown 和富文本两种模式。</p>"
            "<h4>主要功能</h4>"
            "<ul>"
            "<li><strong>标题设置</strong> - 设置文章标题和副标题</li>"
            "<li><strong>分类和标签</strong> - 为文章添加分类和标签</li>"
            "<li><strong>特色图片</strong> - 上传封面图片</li>"
            "<li><strong>SEO 设置</strong> - 自定义 meta 标题和描述</li>"
            "<li><strong>定时发布</strong> - 设置未来发布时间</li>"
            "</ul>"
            "<h4>快捷键</h4>"
            "<ul>"
            "<li><code>Ctrl/Cmd + S</code> - 保存草稿</li>"
            "<li><code>Ctrl/Cmd + P</code> - 预览</li>"
            "<li><code>Ctrl/Cmd + Enter</code> - 发布文章</li>"
            "</ul>"
        ),
        "tags": ["文章", "编辑器", "markdown", "富文本", "快捷键", "seo"],
        "language": "zh_CN",
        "related_links": [
            {"title": "Markdown 语法指南", "url": "/docs/markdown"},
            {"title": "SEO 最佳实践", "url": "/docs/seo-tips"},
        ],
    },
    {
        "page_key": "media_library",
        "title": "媒体库",
        "content": (
            "<h3>管理媒体文件</h3>"
            "<p>媒体库支持图片、视频、音频和文档等多种文件类型。</p>"
            "<h4>支持的文件类型</h4>"
            "<ul>"
            "<li><strong>图片</strong> - JPG, PNG, GIF, WebP, SVG</li>"
            "<li><strong>视频</strong> - MP4, WebM, AVI</li>"
            "<li><strong>音频</strong> - MP3, WAV, OGG</li>"
            "<li><strong>文档</strong> - PDF, DOC, DOCX</li>"
            "</ul>"
            "<h4>拖拽上传</h4>"
            "<p>直接将文件拖拽到媒体库区域即可上传。支持批量上传。</p>"
            "<h4>文件夹管理</h4>"
            "<p>可以创建文件夹来组织媒体文件，支持嵌套文件夹结构。</p>"
        ),
        "tags": ["媒体", "图片", "视频", "上传", "文件", "media"],
        "language": "zh_CN",
        "related_links": [
            {"title": "图片优化指南", "url": "/docs/image-optimization"},
            {"title": "SVG 安全上传", "url": "/docs/svg-security"},
        ],
    },
    {
        "page_key": "theme_settings",
        "title": "主题设置",
        "content": (
            "<h3>自定义主题</h3>"
            "<p>主题设置允许您自定义网站的外观和行为。</p>"
            "<h4>主要设置项</h4>"
            "<ul>"
            "<li><strong>颜色和字体</strong> - 设置主色调和字体</li>"
            "<li><strong>布局</strong> - 选择页面布局和侧边栏位置</li>"
            "<li><strong>首页设置</strong> - 配置首页显示内容</li>"
            "<li><strong>页脚</strong> - 自定义页脚内容和版权信息</li>"
            "</ul>"
            "<h4>预览更改</h4>"
            "<p>所有更改都会实时预览，满意后点击“保存”应用。</p>"
        ),
        "tags": ["主题", "外观", "样式", "布局", "theme", "css"],
        "language": "zh_CN",
        "related_links": [
            {"title": "主题开发指南", "url": "/docs/theme-development"},
            {"title": "自定义 CSS", "url": "/docs/custom-css"},
        ],
    },
    {
        "page_key": "plugin_manager",
        "title": "插件管理",
        "content": (
            "<h3>管理插件</h3>"
            "<p>插件可以扩展网站的功能。</p>"
            "<h4>插件操作</h4>"
            "<ul>"
            "<li><strong>安装</strong> - 从市场搜索并安装插件</li>"
            "<li><strong>激活/停用</strong> - 控制插件是否生效</li>"
            "<li><strong>配置</strong> - 调整插件设置</li>"
            "<li><strong>更新</strong> - 检查并安装最新版本</li>"
            "<li><strong>卸载</strong> - 完全移除插件</li>"
            "</ul>"
            "<h4>注意事项</h4>"
            "<ul>"
            "<li>定期更新插件以获得最新功能和安全补丁</li>"
            "<li>避免安装过多插件影响性能</li>"
            "<li>卸载前备份相关数据</li>"
            "</ul>"
        ),
        "tags": ["插件", "扩展", "安装", "plugin"],
        "language": "zh_CN",
        "related_links": [
            {"title": "插件开发指南", "url": "/docs/plugin-development"},
            {"title": "推荐插件列表", "url": "/docs/recommended-plugins"},
        ],
    },
    {
        "page_key": "user_management",
        "title": "用户管理",
        "content": (
            "<h3>管理用户账户</h3>"
            "<p>创建和管理网站用户及其权限。</p>"
            "<h4>用户角色</h4>"
            "<ul>"
            "<li><strong>管理员</strong> - 完全访问权限</li>"
            "<li><strong>编辑</strong> - 可以管理和发布所有文章</li>"
            "<li><strong>作者</strong> - 只能管理自己的文章</li>"
            "<li><strong>贡献者</strong> - 可以撰写但不能发布文章</li>"
            "<li><strong>订阅者</strong> - 只能阅读内容</li>"
            "</ul>"
            "<h4>批量操作</h4>"
            "<p>可以选择多个用户进行批量操作，如更改角色或删除。</p>"
        ),
        "tags": ["用户", "角色", "权限", "账户", "user", "role"],
        "language": "zh_CN",
        "related_links": [
            {"title": "用户角色详解", "url": "/docs/user-roles"},
            {"title": "权限管理", "url": "/docs/permissions"},
        ],
    },
]

#: 字段提示（v2 的扁平表 + v3 的上下文变体；``general`` 为兜底上下文）
DEFAULT_TOOLTIPS: Dict[str, Dict[str, str]] = {
    "slug": {
        "general": "URL 友好的标识符，只允许小写字母、数字和连字符",
        "article_editor": "文章别名（slug），留空则根据标题自动生成；发布后可保持稳定",
        "category": "分类别名（slug），用于生成 /category/<slug> 这样的访问地址",
    },
    "excerpt": {
        "general": "文章摘要，用于列表页显示和 SEO 描述",
        "article_editor": "文章摘要，建议 100-160 字；留空会截取正文前若干字",
    },
    "featured_image": {
        "general": "文章封面图，建议在列表页和社交媒体分享时显示",
        "article_editor": "特色图片的媒体库 URL，建议尺寸 1200×630，用于分享卡片",
    },
    "tags": {
        "general": "用逗号分隔的标签，帮助读者发现相关内容",
    },
    "status": {
        "general": "草稿不会公开显示，已发布文章对所有访客可见",
        "article_editor": "草稿 / 待审 / 已发布；贡献者只能保存草稿，由编辑发布",
    },
    "publish_date": {
        "general": "留空则立即发布，设置未来时间可定时发布",
    },
    "meta_title": {
        "general": "搜索引擎显示的标题，建议 50-60 个字符",
        "seo": "meta 标题，通常包含核心关键词与站点名，避免超长被截断",
    },
    "meta_description": {
        "general": "搜索引擎显示的描述，建议 150-160 个字符",
        "seo": "meta 描述，概括页面内容以提升点击率，建议 150-160 个字符",
    },
}

#: 视频教程（照搬 v2，并补 ``topic`` 供过滤）
DEFAULT_VIDEOS: List[Dict[str, str]] = [
    {
        "id": "getting-started",
        "title": "快速入门指南",
        "description": "学习如何使用 FastBlog 的基本功能",
        "duration": "5:30",
        "url": "/tutorials/getting-started",
        "thumbnail": "/api/v3/static/tutorials/getting-started.jpg",
        "topic": "getting-started",
    },
    {
        "id": "writing-articles",
        "title": "撰写优秀文章",
        "description": "掌握文章编辑器的所有功能",
        "duration": "8:15",
        "url": "/tutorials/writing-articles",
        "thumbnail": "/api/v3/static/tutorials/writing.jpg",
        "topic": "article_editor",
    },
    {
        "id": "seo-optimization",
        "title": "SEO 优化技巧",
        "description": "提高文章在搜索引擎中的排名",
        "duration": "12:00",
        "url": "/tutorials/seo",
        "thumbnail": "/api/v3/static/tutorials/seo.jpg",
        "topic": "seo",
    },
]

#: 打分的字段权重（标题命中权重高于正文）
_FIELD_WEIGHTS: Dict[str, float] = {"title": 0.55, "tags": 0.35, "content": 0.30}

#: 标题 / 标签中"完整短语"命中的额外加成
_PHRASE_BONUS = 0.10

#: 正文中每多命中一次的加成与封顶次数
_REPEAT_BONUS = 0.05
_REPEAT_CAP = 4

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html(content: str) -> str:
    """去标签 + 压缩空白，得到用于搜索 / 摘要的纯文本"""
    text = _TAG_RE.sub(" ", content or "")
    return _WS_RE.sub(" ", text).strip()


def _extract_excerpt(content: str, query: str, max_length: int = 160, window: int = 60) -> str:
    """提取命中位置附近的摘要（不是简单截头）

    - 命中关键词时，从命中点向前后各取一段（前后以 ``...`` 标出被截断）；
    - 未命中时退回正文开头 ``max_length`` 个字符（同样以 ``...`` 结尾）。
    """
    text = _strip_html(content)
    if not text:
        return ""
    if len(text) <= max_length:
        return text

    query_lower = (query or "").strip().lower()
    pos = text.lower().find(query_lower) if query_lower else -1
    if pos == -1:
        return text[:max_length] + "..."

    start = max(0, pos - window)
    end = min(len(text), pos + len(query_lower) + max_length - window)
    excerpt = text[start:end]
    if start > 0:
        excerpt = "..." + excerpt
    if end < len(text):
        excerpt += "..."
    return excerpt


def _score_topic(topic: Dict[str, Any], query: str) -> Dict[str, Any]:
    """对单个主题按查询打分，返回 ``{"score", "matched_fields"}``

    打分规则（真实相关度，而非 v2 的固定三档）：

    - 字段权重：标题 0.55 > 标签 0.35 > 正文 0.30（标题命中权重高于正文）；
    - 命中次数：同一字段内除首次外，每多命中一次 +0.05（正文封顶 4 次）；
    - 短语加成：查询作为**完整短语**出现在标题 / 标签中额外 +0.10；
    - 多词部分命中：正规化分词后，所有词都出现在某字段时给该字段权重的一部分；
    - 最终分值裁剪到 ``[0, 1]``。
    """
    q = (query or "").strip().lower()
    if not q:
        return {"score": 0.0, "matched_fields": []}

    title = str(topic.get("title") or "")
    content_text = _strip_html(str(topic.get("content") or ""))
    tags_text = " ".join(topic.get("tags") or [])
    fields = {"title": title, "tags": tags_text, "content": content_text}

    terms = [term for term in re.split(r"\s+", q) if term]
    score = 0.0
    matched: List[str] = []

    for name, text in fields.items():
        low = text.lower()
        if not low:
            continue
        occurrences = low.count(q)
        term_hits = sum(1 for term in terms if term in low)
        weight = _FIELD_WEIGHTS[name]

        if occurrences:
            matched.append(name)
            score += weight
            score += min(occurrences - 1, _REPEAT_CAP) * _REPEAT_BONUS
            if name in ("title", "tags"):
                score += _PHRASE_BONUS
        elif terms and term_hits == len(terms):
            # 词组未整体命中，但每个词都能找到 → 部分命中
            matched.append(name)
            score += weight * 0.6

    return {"score": round(min(score, 1.0), 4), "matched_fields": matched}


def _search_topics(
    topics: List[Dict[str, Any]], query: str, *, limit: int = 20
) -> List[Dict[str, Any]]:
    """对一组主题执行相关性搜索，按分值降序返回（纯函数，便于测试）"""
    results: List[Dict[str, Any]] = []
    for topic in topics:
        scored = _score_topic(topic, query)
        if scored["score"] <= 0:
            continue
        results.append(
            {
                "page_key": topic.get("page_key"),
                "title": topic.get("title"),
                "excerpt": _extract_excerpt(str(topic.get("content") or ""), query),
                "score": scored["score"],
                "matched_fields": scored["matched_fields"],
            }
        )
    results.sort(key=lambda item: (-item["score"], str(item["title"])))
    return results[:limit] if limit and limit > 0 else results


def _normalize_topic(raw: Dict[str, Any]) -> Dict[str, Any]:
    """把任意来源的条目规范成统一结构（缺省字段补空）"""
    return {
        "page_key": str(raw.get("page_key") or "").strip(),
        "title": str(raw.get("title") or "").strip(),
        "content": str(raw.get("content") or ""),
        "tags": [str(tag) for tag in (raw.get("tags") or [])],
        "language": str(raw.get("language") or "zh_CN"),
        "related_links": list(raw.get("related_links") or []),
    }


def _merge_topics(
    defaults: List[Dict[str, Any]], custom: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """合并默认与自定义主题：同 ``page_key`` 时自定义覆盖默认（纯函数）"""
    merged: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for topic in defaults:
        item = _normalize_topic(topic)
        key = item["page_key"]
        merged[key] = item
        order.append(key)
    for topic in custom:
        item = _normalize_topic(topic)
        key = item["page_key"]
        if not key:
            continue
        if key not in merged:
            order.append(key)
        merged[key] = item
    return [merged[key] for key in order]


def _lookup_tooltip(field_name: str, context: str = "general") -> Optional[str]:
    """按字段名 + 上下文查提示（未命中返回 ``None``；纯函数）"""
    entry = DEFAULT_TOOLTIPS.get(field_name)
    if not entry:
        return None
    if context in entry:
        return entry[context]
    if "general" in entry:
        return entry["general"]
    return next(iter(entry.values()), None)


class HelpService:
    """帮助内容：默认主题 + 自定义持久化 + 搜索 + 字段提示 + 视频"""

    # ------------------------------------------------------------------ 存储
    async def _load_custom(self, db: AsyncSession) -> List[Dict[str, Any]]:
        from shared.models.system.system_settings import SystemSettings

        row = (
            await db.execute(
                select(SystemSettings).where(SystemSettings.setting_key == STORAGE_KEY).limit(1)
            )
        ).scalars().first()
        if row is None or not row.setting_value:
            return []
        try:
            parsed = json.loads(row.setting_value)
        except ValueError:
            logger.warning("自定义帮助内容不是合法 JSON，忽略：%s", (row.setting_value or "")[:80])
            return []
        if not isinstance(parsed, list):
            logger.warning("自定义帮助内容不是数组，忽略")
            return []
        return [_normalize_topic(item) for item in parsed if isinstance(item, dict)]

    async def _save_custom(
        self, db: AsyncSession, items: List[Dict[str, Any]], *, user_id: Optional[int] = None
    ) -> None:
        from shared.models.system.system_settings import SystemSettings

        row = (
            await db.execute(
                select(SystemSettings).where(SystemSettings.setting_key == STORAGE_KEY).limit(1)
            )
        ).scalars().first()
        now = datetime.now()
        value = json.dumps(items, ensure_ascii=False)
        if row is None:
            db.add(
                SystemSettings(
                    setting_key=STORAGE_KEY,
                    setting_value=value,
                    setting_type="json",
                    description="帮助系统自定义 / 覆盖条目",
                    is_public=True,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            row.setting_value = value
            row.setting_type = "json"
            row.is_public = True
            row.updated_at = now
        await db.commit()
        logger.info("自定义帮助内容已更新（用户 %s，条目数 %d）", user_id, len(items))

    # ------------------------------------------------------------------ 查询
    async def get_all_topics(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """默认 + 自定义合并后的全部主题"""
        custom = await self._load_custom(db)
        return _merge_topics(DEFAULT_TOPICS, custom)

    async def get_topic(self, db: AsyncSession, page_key: str) -> Dict[str, Any]:
        """按 ``page_key`` 取单条主题（不存在抛 404）"""
        for topic in await self.get_all_topics(db):
            if topic["page_key"] == page_key:
                return topic
        raise NotFoundError(f"帮助主题不存在：{page_key}")

    async def search(
        self, db: AsyncSession, query: str, *, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """在全部主题上做相关性搜索（标题命中优先，含 excerpt 与命中字段）"""
        if not (query or "").strip():
            raise BadRequestError("搜索关键词不能为空")
        return _search_topics(await self.get_all_topics(db), query, limit=limit)

    # ------------------------------------------------------------------ 写入
    async def upsert_topic(
        self, db: AsyncSession, payload: Dict[str, Any], *, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """新增 / 覆盖一条自定义帮助（未知字段直接 400，不是静默丢弃）"""
        if not isinstance(payload, dict) or not payload:
            raise BadRequestError("请求体不能为空")

        unknown = [key for key in payload if key not in TOPIC_FIELDS]
        if unknown:
            raise BadRequestError(
                f"未知字段：{unknown}（可选：{list(TOPIC_FIELDS)}）"
            )

        page_key = str(payload.get("page_key") or "").strip()
        title = str(payload.get("title") or "").strip()
        content = str(payload.get("content") or "").strip()
        if not page_key:
            raise BadRequestError("page_key 不能为空")
        if not title:
            raise BadRequestError("title 不能为空")
        if not content:
            raise BadRequestError("content 不能为空")

        language = str(payload.get("language") or "zh_CN")
        if language not in SUPPORTED_LANGUAGES:
            raise BadRequestError(
                f"language 只支持 {list(SUPPORTED_LANGUAGES)}，收到「{language}」"
            )

        tags = payload.get("tags") or []
        if not isinstance(tags, list):
            raise BadRequestError("tags 必须是字符串数组")
        related_links = payload.get("related_links") or []
        if not isinstance(related_links, list):
            raise BadRequestError("related_links 必须是数组")

        item = _normalize_topic(
            {
                "page_key": page_key,
                "title": title,
                "content": content,
                "tags": tags,
                "language": language,
                "related_links": related_links,
            }
        )

        custom = await self._load_custom(db)
        replaced = False
        for index, existing in enumerate(custom):
            if existing["page_key"] == page_key:
                custom[index] = item
                replaced = True
                break
        if not replaced:
            custom.append(item)

        await self._save_custom(db, custom, user_id=user_id)

        is_default = any(topic["page_key"] == page_key for topic in DEFAULT_TOPICS)
        return {
            "page_key": page_key,
            "action": "updated" if replaced else "created",
            "overrides_default": is_default,
        }

    async def delete_topic(
        self, db: AsyncSession, page_key: str, *, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """删除一条自定义帮助（不存在抛 404；默认主题无法删除，只能被覆盖）"""
        custom = await self._load_custom(db)
        remaining = [item for item in custom if item["page_key"] != page_key]
        if len(remaining) == len(custom):
            raise NotFoundError(f"自定义帮助不存在：{page_key}")
        await self._save_custom(db, remaining, user_id=user_id)
        is_default = any(topic["page_key"] == page_key for topic in DEFAULT_TOPICS)
        return {"page_key": page_key, "deleted": True, "reverted_to_default": is_default}

    # ------------------------------------------------------------------ 提示 / 视频
    async def field_tooltip(
        self, db: AsyncSession, field_name: str, context: str = "general"
    ) -> Optional[str]:
        """按字段名 + 上下文查字段提示（未命中返回 ``None``）"""
        return _lookup_tooltip(field_name, context)

    @staticmethod
    def videos(topic: Optional[str] = None) -> List[Dict[str, str]]:
        """视频教程列表（``topic`` 命中标题或 topic 时过滤）"""
        if not topic:
            return list(DEFAULT_VIDEOS)
        key = topic.lower()
        return [
            item
            for item in DEFAULT_VIDEOS
            if key in item["title"].lower() or key in item.get("topic", "").lower()
        ]


help_service = HelpService()
