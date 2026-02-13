import logging
from datetime import datetime

from fastapi import FastAPI
from fastscheduler import FastScheduler
from fastscheduler.fastapi_integration import create_scheduler_routes

from src.extensions import cache, SessionLocal
from src.models import Article

# 配置日志
logging.basicConfig()
logging.getLogger('fastscheduler').setLevel(logging.INFO)


class SessionScheduler:
    def __init__(self, app=None):
        # 使用FastScheduler替代BackgroundScheduler
        self.scheduler = FastScheduler(quiet=True, max_workers=10)
        self.app = app

    def init_app(self, app):
        self.app = app
        self._init_scheduler()
        # 添加FastScheduler的FastAPI路由到应用
        if isinstance(app, FastAPI):
            app.include_router(create_scheduler_routes(self.scheduler))

    def _init_scheduler(self):
        """初始化计划任务"""

        # 同步文章浏览量，每5分钟执行一次
        @self.scheduler.every(5).minutes
        def sync_article_views():
            """同步文章浏览量"""
            try:
                # 获取所有带缓存的文章浏览量
                # 使用缓存的keys()方法而不是直接访问内部缓存
                try:
                    # 尝试使用缓存的keys方法，如果不可用则跳过
                    if hasattr(cache.cache, 'keys'):
                        keys = cache.cache.keys()
                    else:
                        # 如果缓存后端不支持keys()方法，可以使用其他方式获取
                        # 这里使用一个安全的默认值，避免直接访问内部缓存
                        keys = []

                    article_keys = [key for key in keys if str(key).startswith('article_views_')]
                except Exception:
                    # 如果无法获取缓存键，则跳过同步
                    article_keys = []

                db_session = SessionLocal()
                updated_count = 0
                for key in article_keys:
                    # 从键名中提取文章ID
                    article_id = int(key.split('_')[-1])

                    # 获取缓存中的浏览量
                    cached_views = cache.get(key)

                    if cached_views is not None:
                        # 更新文章的浏览量
                        article = db_session.query(Article).filter_by(article_id=article_id).first()
                        if article:
                            article.views = cached_views
                            updated_count += 1

                # 提交事务
                db_session.commit()

                # 清除已同步的缓存
                for key in article_keys:
                    cache.delete(key)

                if updated_count > 0:
                    print(f"{datetime.now()}: 成功同步 {updated_count} 篇文章的浏览量")

                db_session.close()

            except Exception as e:
                if 'db_session' in locals():
                    db_session.rollback()
                    db_session.close()
                print(f"{datetime.now()}: 同步文章浏览量时出错: {e}")

        # 启动调度器
        self.scheduler.start()

        print("###计划任务已启动###")


# 创建全局调度器实例
session_scheduler = SessionScheduler()


def init_scheduler(app):
    """初始化调度器"""
    session_scheduler.init_app(app)
