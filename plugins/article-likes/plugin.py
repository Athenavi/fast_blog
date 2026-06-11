"""
文章点赞插件
为文章添加点赞/取消点赞功能。
使用本地 SQLite 持久化，完全独立于主数据库。
通过 EventBus article.content 管道在文章内容后注入点赞按钮 HTML。
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from sqlalchemy import Column, Integer, BigInteger, String, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from shared.services.plugins.plugin_manager.core import BasePlugin
from shared.services.plugins.event_bus import event_bus

# ── 插件本地 ORM ──
LikesBase = declarative_base()


class LikeModel(LikesBase):
    __tablename__ = "article_likes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    article_id = Column(BigInteger, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ArticleLikesPlugin(BasePlugin):
    """
    文章点赞插件

    功能:
    1. 点赞/取消点赞
    2. 获取文章点赞数
    3. 检查用户是否已点赞
    4. 热门文章排行
    """

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="Article Likes",
            slug="article-likes",
            version="1.0.0",
        )

        self.settings = {
            'enabled': True,
        }

        self._session_factory = None

    def _get_session(self):
        if self._session_factory is None:
            engine = self.get_db_engine()
            self._session_factory = sessionmaker(bind=engine)
        return self._session_factory()

    def activate(self):
        super().activate()
        self.init_db(LikesBase)
        print("[ArticleLikes] Plugin activated")

    def deactivate(self):
        super().deactivate()
        if self._session_factory:
            self._session_factory.close_all_sessions()
            self._session_factory = None
        print("[ArticleLikes] Plugin deactivated")

    # ── 公开动作 API ──

    def like(self, article_id: int, user_id: int) -> Dict[str, Any]:
        """点赞文章"""
        if not self.settings.get('enabled'):
            return {'success': False, 'error': 'Likes disabled'}

        session = self._get_session()
        try:
            existing = session.query(LikeModel).filter_by(
                user_id=user_id, article_id=article_id
            ).first()

            if existing:
                return {
                    'success': True,
                    'liked': True,
                    'message': 'Already liked',
                    'count': self._count(session, article_id),
                }

            like = LikeModel(user_id=user_id, article_id=article_id)
            session.add(like)
            session.commit()

            count = self._count(session, article_id)
            print(f"[ArticleLikes] User {user_id} liked article {article_id} (total: {count})")
            return {'success': True, 'liked': True, 'count': count}
        except Exception as e:
            session.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            session.close()

    def unlike(self, article_id: int, user_id: int) -> Dict[str, Any]:
        """取消点赞"""
        session = self._get_session()
        try:
            existing = session.query(LikeModel).filter_by(
                user_id=user_id, article_id=article_id
            ).first()

            if not existing:
                return {
                    'success': True,
                    'liked': False,
                    'message': 'Not liked yet',
                    'count': self._count(session, article_id),
                }

            session.delete(existing)
            session.commit()

            count = self._count(session, article_id)
            print(f"[ArticleLikes] User {user_id} unliked article {article_id} (total: {count})")
            return {'success': True, 'liked': False, 'count': count}
        except Exception as e:
            session.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            session.close()

    def status(self, article_id: int, user_id: Optional[int] = 0) -> Dict[str, Any]:
        """获取文章点赞状态"""
        session = self._get_session()
        try:
            liked = False
            if user_id:
                liked = session.query(LikeModel).filter_by(
                    user_id=user_id, article_id=article_id
                ).first() is not None

            return {
                'success': True,
                'article_id': article_id,
                'liked': liked,
                'count': self._count(session, article_id),
            }
        finally:
            session.close()

    def popular(self, limit: int = 10) -> Dict[str, Any]:
        """获取热门文章排行"""
        session = self._get_session()
        try:
            from sqlalchemy import func

            rows = (
                session.query(LikeModel.article_id, func.count(LikeModel.id).label('cnt'))
                .group_by(LikeModel.article_id)
                .order_by(func.count(LikeModel.id).desc())
                .limit(limit)
                .all()
            )

            return {
                'success': True,
                'data': [
                    {'article_id': row.article_id, 'likes': row.cnt}
                    for row in rows
                ],
            }
        finally:
            session.close()

    @staticmethod
    def _count(session, article_id: int) -> int:
        """查询文章点赞数"""
        from sqlalchemy import func
        result = session.query(func.count(LikeModel.id)).filter_by(
            article_id=article_id
        ).scalar()
        return result or 0

    def get_settings_ui(self) -> Dict[str, Any]:
        return {
            'fields': [
                {'key': 'enabled', 'type': 'boolean', 'label': '启用点赞功能'},
            ],
            'actions': [
                {'type': 'button', 'label': '热门排行', 'action': 'popular', 'variant': 'outline'},
            ],
        }


plugin_instance = ArticleLikesPlugin()
