"""
全文搜索引擎插件
基于 Meilisearch 实现高性能全文搜索

功能：
1. 自动同步文章到 Meilisearch
2. 提供增强的搜索API
3. 支持拼音搜索、模糊匹配
4. 搜索结果高亮
5. 搜索统计和分析
"""
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from shared.services.plugin_manager import BasePlugin, plugin_hooks
from shared.services.meilisearch_service import meilisearch_service
from shared.utils.plugin_database import plugin_db


class FullTextSearchPlugin(BasePlugin):
    """全文搜索引擎插件"""

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="全文搜索引擎",
            slug="fulltext-search",
            version="1.0.0"
        )

        self.settings = {
            'enabled': True,
            'host': 'http://localhost:7700',
            'api_key': '',
            'auto_sync': True,
            'index_on_publish': True
        }

    def register_hooks(self):
        """注册钩子"""
        # 文章发布/更新时同步索引
        plugin_hooks.add_action(
            "article_published",
            self.on_article_published,
            priority=10
        )

        plugin_hooks.add_action(
            "article_updated",
            self.on_article_updated,
            priority=10
        )

        plugin_hooks.add_action(
            "article_deleted",
            self.on_article_deleted,
            priority=10
        )

        # 应用启动时初始化
        plugin_hooks.add_action(
            "app_startup",
            self.on_app_startup,
            priority=5
        )

    async def on_app_startup(self, context: Dict[str, Any] = None):
        """应用启动时初始化搜索引擎"""
        if not self.settings.get('enabled'):
            return

        try:
            # 从设置中获取配置
            host = self.settings.get('host', 'http://localhost:7700')
            api_key = self.settings.get('api_key', '')

            # 重新初始化服务
            meilisearch_service.host = host
            meilisearch_service.api_key = api_key

            # 初始化
            success = await meilisearch_service.initialize()

            if success:
                print("[FullTextSearch] Meilisearch initialized successfully")

                # 检查是否需要重建索引
                await self._check_and_rebuild_index()
            else:
                print("[FullTextSearch] Failed to initialize Meilisearch")

        except Exception as e:
            print(f"[FullTextSearch] Error during initialization: {e}")

    async def on_article_published(self, context: Dict[str, Any] = None):
        """文章发布时创建索引"""
        if not self.settings.get('enabled') or not self.settings.get('index_on_publish'):
            return

        try:
            article_data = context.get('article_data')
            if not article_data:
                return

            # 准备索引数据
            index_data = await self._prepare_article_data(article_data)

            # 索引文章
            await meilisearch_service.index_article(index_data)

            # 更新索引状态
            await self._update_index_status(article_data.get('id'), indexed=True)

            print(f"[FullTextSearch] Article indexed: {article_data.get('id')}")

        except Exception as e:
            print(f"[FullTextSearch] Failed to index article: {e}")

    async def on_article_updated(self, context: Dict[str, Any] = None):
        """文章更新时更新索引"""
        if not self.settings.get('enabled') or not self.settings.get('auto_sync'):
            return

        try:
            article_data = context.get('article_data')
            if not article_data:
                return

            # 检查内容是否变化
            article_id = article_data.get('id')
            content_hash = meilisearch_service.calculate_content_hash(article_data)

            # 获取之前的哈希
            old_hash = await self._get_index_hash(article_id)

            # 如果内容没有变化，跳过
            if old_hash and old_hash == content_hash:
                return

            # 准备索引数据
            index_data = await self._prepare_article_data(article_data)

            # 更新索引
            await meilisearch_service.update_article(index_data)

            # 更新索引状态
            await self._update_index_status(article_id, indexed=True, hash=content_hash)

            print(f"[FullTextSearch] Article index updated: {article_id}")

        except Exception as e:
            print(f"[FullTextSearch] Failed to update article index: {e}")

    async def on_article_deleted(self, context: Dict[str, Any] = None):
        """文章删除时删除索引"""
        if not self.settings.get('enabled'):
            return

        try:
            article_id = context.get('id')
            if not article_id:
                return

            # 删除索引
            await meilisearch_service.delete_article(article_id)

            # 更新索引状态
            await self._update_index_status(article_id, indexed=False)

            print(f"[FullTextSearch] Article index deleted: {article_id}")

        except Exception as e:
            print(f"[FullTextSearch] Failed to delete article index: {e}")

    async def _prepare_article_data(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备文章索引数据
        
        Args:
            article_data: 原始文章数据
            
        Returns:
            索引数据
        """
        # 提取需要的字段
        index_data = {
            'id': article_data.get('id'),
            'title': article_data.get('title', ''),
            'slug': article_data.get('slug', ''),
            'excerpt': article_data.get('excerpt', ''),
            'content': article_data.get('content', ''),
            'cover_image': article_data.get('cover_image', ''),
            'category_id': article_data.get('category_id'),
            'category_name': article_data.get('category_name', ''),
            'author_id': article_data.get('user') or article_data.get('author_id'),
            'author_name': article_data.get('author_name', ''),
            'tags': article_data.get('tags_list', []) or article_data.get('tags', []),
            'views': article_data.get('views', 0),
            'likes': article_data.get('likes', 0),
            'status': 'published' if article_data.get('status') == 1 else 'draft',
            'is_featured': article_data.get('is_featured', False),
            'created_at': int(article_data.get('created_at').timestamp()) if article_data.get('created_at') else 0,
            'updated_at': int(article_data.get('updated_at').timestamp()) if article_data.get('updated_at') else 0,
        }

        return index_data

    async def _update_index_status(self, article_id: int, indexed: bool, hash: str = None):
        """
        更新文章索引状态
        
        Args:
            article_id: 文章ID
            indexed: 是否已索引
            hash: 内容哈希
        """
        try:
            from shared.models.search_index import SearchIndex
            from sqlalchemy import select
            from src.utils.database.unified_manager import db_manager

            async with db_manager.get_session() as session:
                # 查询是否存在记录
                stmt = select(SearchIndex).where(SearchIndex.article_id == article_id)
                result = await session.execute(stmt)
                index_record = result.scalar_one_or_none()

                now = datetime.utcnow()

                if index_record:
                    # 更新现有记录
                    index_record.indexed = indexed
                    index_record.last_indexed_at = now
                    if hash:
                        index_record.index_hash = hash
                    index_record.updated_at = now
                else:
                    # 创建新记录
                    index_record = SearchIndex(
                        article_id=article_id,
                        indexed=indexed,
                        last_indexed_at=now,
                        index_hash=hash,
                        created_at=now,
                        updated_at=now
                    )
                    session.add(index_record)

                await session.commit()

        except Exception as e:
            print(f"[FullTextSearch] Failed to update index status: {e}")

    async def _get_index_hash(self, article_id: int) -> Optional[str]:
        """
        获取文章的索引哈希
        
        Args:
            article_id: 文章ID
            
        Returns:
            哈希字符串
        """
        try:
            from shared.models.search_index import SearchIndex
            from sqlalchemy import select
            from src.utils.database.unified_manager import db_manager

            async with db_manager.get_session() as session:
                stmt = select(SearchIndex).where(SearchIndex.article_id == article_id)
                result = await session.execute(stmt)
                index_record = result.scalar_one_or_none()

                return index_record.index_hash if index_record else None

        except Exception as e:
            print(f"[FullTextSearch] Failed to get index hash: {e}")
            return None

    async def _check_and_rebuild_index(self):
        """检查并重建索引（首次安装时）"""
        try:
            from shared.models.search_index import SearchIndex
            from sqlalchemy import select, func
            from src.utils.database.unified_manager import db_manager

            async with db_manager.get_session() as session:
                # 检查已索引的文章数量
                stmt = select(func.count()).select_from(SearchIndex).where(SearchIndex.indexed == True)
                result = await session.execute(stmt)
                indexed_count = result.scalar() or 0

                # 如果没有任何索引，可能需要重建
                if indexed_count == 0:
                    print("[FullTextSearch] No indexed articles found, you may need to rebuild the index")

        except Exception as e:
            print(f"[FullTextSearch] Failed to check index status: {e}")

    def activate(self):
        """激活插件"""
        super().activate()
        print("[FullTextSearch] Plugin activated")

    def deactivate(self):
        """停用插件"""
        super().deactivate()
        print("[FullTextSearch] Plugin deactivated")


# 插件实例
plugin = FullTextSearchPlugin()
