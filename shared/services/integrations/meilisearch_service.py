"""
Meilisearch 全文搜索引擎集成服务

功能：
1. 文章索引同步（增删改查）
2. 高性能全文搜索
3. 搜索结果高亮
4. 拼音搜索支持
5. 模糊匹配和纠错
6. 搜索统计和分析
7. 增量索引更新
"""
import hashlib
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from meilisearch_python_sdk import AsyncClient
from meilisearch_python_sdk.models.settings import MeilisearchSettings

from shared.logging import default_logger as logger

#: 默认索引名（`system/search` 模块的配置默认值与此保持一致）
DEFAULT_INDEX_NAME = "articles"
#: 环境变量缺失时的兜底地址（与既有行为一致，不改变默认部署）
DEFAULT_HOST = "http://localhost:7700"


class MeilisearchService:
    """
    Meilisearch 搜索引擎服务

    提供完整的全文搜索功能，包括索引管理、搜索、高亮等
    注意：客户端采用懒加载模式，首次使用时才创建连接，避免启动时阻塞

    ## 配置来源（三级，后者被前者覆盖）

      1. 环境变量 ``MEILISEARCH_HOST`` / ``MEILISEARCH_API_KEY`` / ``MEILISEARCH_INDEX_NAME``
         —— 兜底，保证已有部署升级后不失效；
      2. ``configure()`` 运行时重配置 —— 由后台"搜索设置"保存时调用，**立即生效**；
      3. 应用启动时 ``load_from_settings()`` 从 ``system_settings`` 载入一次。

    ## 为什么 `configure()` 必须清 `_unavailable`

    该标记用于"初始化失败后短路，避免每次请求都重复等待网络超时"。但管理员在后台
    改完地址后，**如果不清掉它，新的配置就永远不会被尝试** —— 表现是"改了没反应"。
    所以重配置必然重置客户端、索引句柄与这个标记。
    """

    def __init__(self, host: Optional[str] = None, api_key: Optional[str] = None):
        """
        初始化 Meilisearch 客户端（懒加载）

        Args:
            host: Meilisearch 服务器地址（默认取 MEILISEARCH_HOST 环境变量）
            api_key: API密钥（默认取 MEILISEARCH_API_KEY 环境变量）
        """
        self.host = (host or os.getenv("MEILISEARCH_HOST") or DEFAULT_HOST).strip()
        self.api_key = api_key if api_key is not None else os.getenv("MEILISEARCH_API_KEY", "")
        self.api_key = (self.api_key or "").strip()
        self._client: Optional[AsyncClient] = None  # 懒加载：首次访问时才创建
        self.index_name = (os.getenv("MEILISEARCH_INDEX_NAME") or DEFAULT_INDEX_NAME).strip() or DEFAULT_INDEX_NAME
        self.index = None
        #: 初始化失败后短路：避免每次请求都重复等待网络超时
        self._unavailable = False
        #: 是否启用（后台可关；关闭后搜索直接回退数据库，不再尝试连接）
        self.enabled = True

    def is_configured(self) -> bool:
        """是否具备可用的连接配置（有地址且已启用）"""
        return bool(self.enabled and self.host)

    def configure(
        self,
        *,
        host: str,
        api_key: Optional[str] = None,
        index_name: Optional[str] = None,
        enabled: bool = True,
    ) -> None:
        """运行时重配置（后台保存连接配置后立即调用）

        重建客户端并**清掉 `_unavailable`** —— 见类文档里"为什么必须清"的说明。
        """
        self.host = (host or "").strip()
        self.api_key = (api_key or "").strip()
        self.index_name = (index_name or "").strip() or DEFAULT_INDEX_NAME
        # 没有地址就谈不上启用：`enabled=True` 但 host 为空时仍视为未配置
        self.enabled = bool(enabled) and bool(self.host)
        self._client = None
        self.index = None
        self._unavailable = False
        logger.info(
            "Meilisearch 已重配置（host=%s, index=%s, enabled=%s）",
            self.host or "(空)", self.index_name, self.enabled,
        )

    async def probe(self) -> str:
        """真实连通性探测：返回引擎版本号

        连不上时**抛异常**（由调用方如实转述原因），不返回伪造的"成功"。
        """
        await self.client.health()
        version = await self.client.get_version()
        return str(getattr(version, "pkg_version", "") or "")

    @property
    def client(self) -> AsyncClient:
        """懒加载 Meilisearch 客户端，首次访问时才创建"""
        if self._client is None:
            self._client = AsyncClient(self.host, self.api_key or None, timeout=5)
        return self._client

    async def initialize(self):
        """初始化搜索引擎和索引配置（失败后标记不可用，不再重复尝试）"""
        if self._unavailable:
            return False
        try:
            # 获取或创建索引（AsyncClient.index 是同步方法，返回 AsyncIndex）
            self.index = self.client.index(self.index_name)

            # 配置索引设置
            await self._configure_index()

            logger.info(f"Meilisearch initialized successfully at {self.host}")
            return True

        except Exception as e:
            self._unavailable = True
            logger.warning(f"Meilisearch unavailable at {self.host}, falling back to database search: {e}")
            return False

    async def _ensure_index(self) -> bool:
        """确保索引可用；不可用时立即返回 False（不阻塞调用方）

        未配置或已被后台关闭时**直接返回 False**：让调用方立刻走数据库回退，
        而不是去连一个明知连不上的地址（那会白等一个 timeout）。
        """
        if not self.is_configured():
            return False
        if self.index is not None:
            return True
        return await self.initialize()

    async def _configure_index(self):
        """配置索引设置（ searchable attributes, filterable attributes等）"""
        settings = MeilisearchSettings(
            # 可搜索字段（按重要性排序）
            searchable_attributes=[
                "title",
                "excerpt",
                "content",
                "tags",
                "category_name"
            ],
            # 可过滤字段
            #
            # ⚠️ `hidden` / `site_id` / `scheduled_publish_at` / `is_vip_only` /
            # `required_vip_level` **必须**在这里。Meilisearch 只允许按
            # filterable 字段过滤，缺一个就意味着查询侧**根本无法**排除它 ——
            # 前台公开读的口径（`article/service.py::_published_stmt`）要求
            # 「已发布 + 未隐藏 + 定时已到 + 站点匹配」，这里必须能表达同样条件。
            filterable_attributes=[
                "category_id",
                "author_id",
                "status",
                "created_at",
                "views",
                "is_featured",
                "tags",
                # 可见性字段（缺一不可，见上方说明）
                "hidden",
                "site_id",
                "scheduled_publish_at",
                "is_vip_only",
                "required_vip_level",
            ],
            # 可排序字段
            sortable_attributes=[
                "created_at",
                "updated_at",
                "views",
                "likes"
            ],
            # 显示字段
            #
            # 可见性字段一并下发：即使查询侧已经过滤，调用方仍能**二次确认**
            # 拿到的文档确实可见 —— 过滤是防线，可见性字段是让防线可被验证。
            displayed_attributes=[
                "id",
                "title",
                "slug",
                "excerpt",
                "cover_image",
                "category_id",
                "category_name",
                "author_id",
                "author_name",
                "tags",
                "views",
                "likes",
                "status",
                "is_featured",
                "created_at",
                "updated_at",
                "hidden",
                "site_id",
                "is_vip_only",
                "required_vip_level",
            ],
            # 分词设置
            typo_tolerance={
                "enabled": True,
                "min_word_size_for_typos": {
                    "one_typo": 4,
                    "two_typos": 8
                }
            },
            # 高亮标记
            pagination={
                "max_total_hits": 1000
            }
        )

        # 应用设置
        task = await self.index.update_settings(settings)
        logger.info(f"Index settings updated, task uid: {task.task_uid}")

    async def index_article(self, article_data: Dict[str, Any]) -> bool:
        """
        索引单篇文章

        Args:
            article_data: 文章数据字典

        Returns:
            是否成功
        """
        if not await self._ensure_index():
            return False
        try:
            # 添加文档到索引
            task = await self.index.add_documents([article_data])

            logger.info(f"Article indexed: {article_data.get('id')}, task uid: {task.task_uid}")
            return True

        except Exception as e:
            logger.error(f"Failed to index article {article_data.get('id')}: {e}")
            return False

    async def update_article(self, article_data: Dict[str, Any]) -> bool:
        """
        更新文章索引

        Args:
            article_data: 文章数据字典

        Returns:
            是否成功
        """
        if not await self._ensure_index():
            return False
        try:
            # 更新文档
            task = await self.index.update_documents([article_data])

            logger.info(f"Article index updated: {article_data.get('id')}, task uid: {task.task_uid}")
            return True

        except Exception as e:
            logger.error(f"Failed to update article index {article_data.get('id')}: {e}")
            return False

    async def delete_article(self, article_id: int) -> bool:
        """
        删除文章索引

        Args:
            article_id: 文章ID

        Returns:
            是否成功
        """
        if not await self._ensure_index():
            return False
        try:
            # 删除文档
            task = await self.index.delete_document(article_id)

            logger.info(f"Article index deleted: {article_id}, task uid: {task.task_uid}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete article index {article_id}: {e}")
            return False

    async def bulk_index_articles(self, articles: List[Dict[str, Any]]) -> bool:
        """
        批量索引文章

        Args:
            articles: 文章数据列表

        Returns:
            是否成功
        """
        if not articles:
            return True
        if not await self._ensure_index():
            return False
        try:
            # 批量添加文档
            task = await self.index.add_documents(articles)

            logger.info(f"Bulk indexed {len(articles)} articles, task uid: {task.task_uid}")
            return True

        except Exception as e:
            logger.error(f"Failed to bulk index articles: {e}")
            return False

    async def search(
            self,
            query: str,
        *,
            category_id: Optional[int] = None,
            author_id: Optional[int] = None,
            date_from: Optional[datetime] = None,
            date_to: Optional[datetime] = None,
            status: str = "published",
            page: int = 1,
            per_page: int = 20,
        sort_by: str = "relevance",
        site_id: Optional[int] = None,
        vip_level: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        搜索文章

        ## 可见性过滤是**强制**的，不提供关闭开关

        前台公开读的口径见 ``article/service.py::_published_stmt``：已发布 + 未隐藏 +
        定时已到 + 站点匹配。这里必须表达同样条件 —— 少一条就是一次泄露，而
        调用方**不可能**记得每次都传对，所以由本方法内建。

        默认值一律取**最严**（fail-safe）：漏传参数的后果是"搜不到"，
        而不是"搜到不该看的"。

        Args:
            query: 搜索关键词
            category_id: 分类ID过滤
            author_id: 作者ID过滤
            date_from: 起始日期
            date_to: 结束日期
            status: 文章状态
            page: 页码
            per_page: 每页数量
            sort_by: 排序方式 (relevance, date, views)
            site_id: 站点 ID（多租户隔离键）。**未指定时只匹配无站点归属的文档**，
                而不是"全部站点" —— 见上方 fail-safe 说明。
            vip_level: 调用者当前的 VIP 等级。**未指定时只返回非 VIP 文档**。

        Returns:
            搜索结果和分页信息；引擎不可用时返回 None（调用方据此回退）
        """
        if not await self._ensure_index():
            return None
        try:
            # 强制过滤：顺序与 `_published_stmt()` 一致，便于对照审查
            filters = ["hidden = false"]

            if status:
                filters.append(f"status = '{status}'")

            # 站点隔离：未指定 → 只匹配 site_id 为空的文档（fail-safe）
            if site_id is None:
                filters.append("site_id IS NULL")
            else:
                filters.append(f"site_id = {int(site_id)}")

            # 定时发布：未到时间的不露出；`scheduled_publish_at` 为 None 表示无定时
            now_ts = int(datetime.now().timestamp())
            filters.append(
                f"(scheduled_publish_at IS NULL OR scheduled_publish_at <= {now_ts})"
            )

            # VIP：未给等级 → 只放非 VIP 文档
            if vip_level is None:
                filters.append("is_vip_only = false")
            else:
                filters.append(
                    f"(is_vip_only = false OR required_vip_level <= {int(vip_level)})"
                )

            # 调用方可选的收窄条件
            if category_id:
                filters.append(f"category_id = {category_id}")

            if author_id:
                filters.append(f"author_id = {author_id}")

            if date_from:
                filters.append(f"created_at >= {int(date_from.timestamp())}")

            if date_to:
                filters.append(f"created_at <= {int(date_to.timestamp())}")

            filter_str = " AND ".join(filters) if filters else None

            # 确定排序
            if sort_by == "date":
                sort = ["created_at:desc"]
            elif sort_by == "views":
                sort = ["views:desc"]
            else:  # relevance
                sort = None

            # 执行搜索
            result = await self.index.search(
                query,
                offset=(page - 1) * per_page,
                limit=per_page,
                filter=filter_str,
                sort=sort,
                attributes_to_highlight=["title", "excerpt"],
                highlight_pre_tag="<mark>",
                highlight_post_tag="</mark>"
            )

            # 格式化结果
            articles = []
            for hit in result.hits:
                article = {
                    'id': hit.get('id'),
                    'title': hit.get('title'),
                    'slug': hit.get('slug'),
                    'excerpt': hit.get('excerpt'),
                    'cover_image': hit.get('cover_image'),
                    'category_id': hit.get('category_id'),
                    'category_name': hit.get('category_name'),
                    'author_id': hit.get('author_id'),
                    'author_name': hit.get('author_name'),
                    'tags': hit.get('tags', []),
                    'views': hit.get('views', 0),
                    'likes': hit.get('likes', 0),
                    'status': hit.get('status'),
                    'is_featured': hit.get('is_featured', False),
                    'created_at': hit.get('created_at'),
                    'updated_at': hit.get('updated_at'),
                }

                # 添加高亮字段
                if '_formatted' in hit:
                    formatted = hit['_formatted']
                    article['highlighted_title'] = formatted.get('title', article['title'])
                    article['highlighted_excerpt'] = formatted.get('excerpt', article['excerpt'])
                else:
                    article['highlighted_title'] = article['title']
                    article['highlighted_excerpt'] = article['excerpt']

                articles.append(article)

            return {
                'articles': articles,
                'total': result.estimated_total_hits or len(result.hits),
                'page': page,
                'per_page': per_page,
                'total_pages': (
                                           result.estimated_total_hits + per_page - 1) // per_page if result.estimated_total_hits else 1,
                'query': query,
                'processing_time_ms': result.processing_time_ms,
            }

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return None

    async def get_search_suggestions(
            self,
            query: str,
            limit: int = 5
    ) -> List[str]:
        """
        获取搜索建议（自动完成）

        Args:
            query: 搜索前缀
            limit: 返回数量

        Returns:
            搜索建议列表
        """
        if not await self._ensure_index():
            return []
        try:
            # 使用 Meilisearch 的 facet search 功能
            result = await self.index.search(
                query,
                limit=limit,
                attributes_to_retrieve=["title"],
            )

            suggestions = [hit.get('title', '') for hit in result.hits if hit.get('title')]
            return suggestions[:limit]

        except Exception as e:
            logger.error(f"Failed to get search suggestions: {e}")
            return []

    async def rebuild_index(self, articles: List[Dict[str, Any]]) -> bool:
        """
        重建整个索引

        Args:
            articles: 所有文章数据列表

        Returns:
            是否成功
        """
        if not await self._ensure_index():
            return False
        try:
            # 清空索引
            await self.index.delete_all_documents()

            # 重新索引所有文章
            if articles:
                await self.bulk_index_articles(articles)

            logger.info(f"Index rebuilt with {len(articles)} articles")
            return True

        except Exception as e:
            logger.error(f"Failed to rebuild index: {e}")
            return False

    async def get_index_stats(self) -> Dict[str, Any]:
        """
        获取索引统计信息

        Returns:
            统计信息
        """
        if not await self._ensure_index():
            return {}
        try:
            stats = await self.index.get_stats()

            return {
                'number_of_documents': stats.number_of_documents,
                'index_size_in_bytes': stats.index_size_in_bytes,
                'field_distribution': stats.field_distribution,
                # 后台"搜索设置"要显示"是否正在建索引"，SDK 已提供该字段
                'is_indexing': bool(getattr(stats, 'is_indexing', False)),
            }

        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {}

    def calculate_content_hash(self, article_data: Dict[str, Any]) -> str:
        """
        计算文章内容哈希（用于检测变更）

        Args:
            article_data: 文章数据

        Returns:
            SHA256哈希字符串
        """
        # 提取关键字段
        content_str = f"{article_data.get('title', '')}|{article_data.get('content', '')}|{article_data.get('excerpt', '')}"
        return hashlib.sha256(content_str.encode('utf-8')).hexdigest()


# 全局实例
meilisearch_service = MeilisearchService()
