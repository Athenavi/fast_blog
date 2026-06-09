from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from shared.services.articles.article_view_stats import article_view_stats
from shared.services.ops.backup_manager import backup_manager
from src.unified_logger import default_logger as logger


class SessionScheduler:
    def __init__(self, app=None):
        # 使用 BackgroundScheduler 替代 FastScheduler
        self.scheduler = BackgroundScheduler()
        self.app = app

    def init_app(self, app):
        self.app = app
        self._init_scheduler()
        # 不再添加 FastScheduler 的 FastAPI 路由

    def _init_scheduler(self):
        """初始化计划任务"""

        # 同步文章浏览量到数据库，每 5 分钟执行一次
        async def sync_article_views_to_db():
            """使用新的 ArticleViewStatsService 同步文章浏览量"""
            try:
                from src.utils.database.unified_manager import db_manager

                # 使用 async with 正确管理数据库会话
                async with db_manager.get_session() as db:
                    # 批量同步所有文章
                    result = await article_view_stats.batch_sync_all(db)

                    # 检查结果是否为 None 或缺少预期字段
                    if result is None:
                        logger.warning("batch_sync_all 返回 None，可能没有需要同步的数据")
                        return

                    if result.get('synced', 0) > 0:
                        logger.info(f"成功同步 {result['synced']} 篇文章的浏览量")

                    if result.get('errors'):
                        logger.warning(f"同步错误: {result['errors'][:5]}")  # 只显示前5个错误

            except Exception as e:
                logger.error(f"同步文章浏览量时出错：{e}")
                import traceback
                traceback.print_exc()

        # 添加定时任务（使用 APScheduler 的异步支持）
        import asyncio

        def sync_article_views_job():
            """包装异步函数为同步函数"""
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(sync_article_views_to_db())
            finally:
                loop.close()

        self.scheduler.add_job(
            sync_article_views_job,
            trigger=IntervalTrigger(minutes=5),
            id='sync_article_views',
            replace_existing=True
        )

        # 每日备份任务（凌晨 2 点）
        async def daily_backup():
            logger.info("Starting daily database backup...")
            result = await backup_manager.create_database_backup('daily')
            if result['success']:
                logger.info(f"Daily backup completed: {result['filename']}")
            else:
                logger.error(f"Daily backup failed: {result.get('error')}")

        def daily_backup_job():
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(daily_backup())
            finally:
                loop.close()

        self.scheduler.add_job(
            daily_backup_job,
            trigger=CronTrigger(hour=2, minute=0),
            id='daily_backup',
            replace_existing=True
        )

        # 每周完整备份（周日凌晨 3 点）
        async def weekly_backup():
            logger.info("Starting weekly full backup...")
            db_result = await backup_manager.create_database_backup('weekly')
            files_result = await backup_manager.create_files_backup()
            if db_result['success'] and files_result['success']:
                logger.info(f"Weekly backup completed")
            else:
                logger.error(f"Weekly backup had issues")

        def weekly_backup_job():
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(weekly_backup())
            finally:
                loop.close()

        self.scheduler.add_job(
            weekly_backup_job,
            trigger=CronTrigger(day_of_week='sun', hour=3, minute=0),
            id='weekly_backup',
            replace_existing=True
        )

        # 启动调度器
        self.scheduler.start()

        # 每个 worker 都输出自己的计划任务信息（带 worker 标识，使用环境变量避免重复）
        from src.setting import _get_worker_info
        import os
        worker_info = _get_worker_info()
        env_key = f"SCHEDULER_PRINTED_{os.getpid()}"

        if not os.environ.get(env_key):
            logger.info(f"{worker_info} ###计划任务已启动###")
            os.environ[env_key] = "1"


# 创建全局调度器实例
session_scheduler = SessionScheduler()


def init_scheduler(app):
    """初始化调度器"""
    session_scheduler.init_app(app)
