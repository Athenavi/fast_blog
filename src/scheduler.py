from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from shared.services.articles.article_view_stats import article_view_stats
from shared.services.system.backup_service import backup_service
from src.unified_logger import default_logger as logger


async def _acquire_job_lock(name: str, ttl: int = 600) -> bool:
    """
    多 worker 场景下用 Redis 分布式锁保证定时任务全局只执行一次。

    - Redis 可用：只有持有锁的 worker 执行，其余跳过（锁自然过期，不手动释放）。
    - Redis 不可用：放行执行（单 worker / 降级场景）。
    """
    try:
        from src.services.redis_service import redis_service
        if redis_service._redis is None:
            await redis_service.connect()
        return bool(await redis_service.redis.set(f"fb:sched_lock:{name}", "1", nx=True, ex=ttl))
    except Exception:
        return True


class SessionScheduler:
    def __init__(self, app=None):
        # 使用 AsyncIOScheduler 在同一事件循环中运行异步任务
        self.scheduler = AsyncIOScheduler()
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
            if not await _acquire_job_lock("sync_article_views", ttl=300):
                return
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

        # 添加定时任务（AsyncIOScheduler 直接支持异步函数）

        self.scheduler.add_job(
            sync_article_views_to_db,
            trigger=IntervalTrigger(minutes=5),
            id='sync_article_views',
            replace_existing=True
        )

        # 每日备份任务（凌晨 2 点）
        async def daily_backup():
            if not await _acquire_job_lock("daily_backup", ttl=3600):
                return
            logger.info("Starting daily database backup...")
            try:
                result = await backup_service.backup_database(backup_type='full')
                if result.get('success'):
                    logger.info(f"Daily backup completed: {result.get('backup_path')}")
                else:
                    logger.error(f"Daily backup failed: {result.get('error')}")
            except Exception as e:
                logger.error(f"Daily backup failed: {e}")

        self.scheduler.add_job(
            daily_backup,
            trigger=CronTrigger(hour=2, minute=0),
            id='daily_backup',
            replace_existing=True
        )

        # 每周完整备份（周日凌晨 3 点）
        async def weekly_backup():
            if not await _acquire_job_lock("weekly_backup", ttl=3600):
                return
            logger.info("Starting weekly full backup...")
            try:
                db_result = await backup_service.backup_database(backup_type='full')
                files_result = await backup_service.backup_files()
                if db_result.get('success') and files_result.get('success'):
                    logger.info(f"Weekly backup completed")
                else:
                    logger.error(f"Weekly backup had issues: db={db_result.get('success')}, files={files_result.get('success')}")
            except Exception as e:
                logger.error(f"Weekly backup failed: {e}")

        self.scheduler.add_job(
            weekly_backup,
            trigger=CronTrigger(day_of_week='sun', hour=3, minute=0),
            id='weekly_backup',
            replace_existing=True
        )

        # 定时发布到期文章检查（每 5 分钟）
        async def check_due_scheduled_articles():
            """检查并发布到期的定时文章"""
            if not await _acquire_job_lock("publish_due_articles", ttl=600):
                return
            try:
                from src.utils.database.unified_manager import db_manager
                from shared.services.articles.scheduled_publish import create_scheduled_publish_service

                async with db_manager.get_session() as db:
                    service = create_scheduled_publish_service(db)
                    result = await service.publish_due_articles()
                    if result.get('success') and result.get('published_count', 0) > 0:
                        logger.info(f"自动发布了 {result['published_count']} 篇到期定时文章")
                    if result.get('failed_count', 0) > 0:
                        logger.warning(f"定时发布 {result.get('published_count', 0)} 成功，{result.get('failed_count', 0)} 失败")
                    elif result.get('published_count', 0) == 0:
                        pass  # 无到期文章，不记录日志
            except Exception as e:
                logger.error(f"检查定时发布时出错：{e}")
                import traceback
                traceback.print_exc()

        self.scheduler.add_job(
            check_due_scheduled_articles,
            trigger=IntervalTrigger(minutes=5),
            id='publish_due_articles',
            replace_existing=True
        )

        # VIP 订阅过期检查（每 30 分钟）
        async def check_expired_vip_subscriptions():
            """检查并标记过期的 VIP 订阅"""
            if not await _acquire_job_lock("check_vip_expiry", ttl=600):
                return
            try:
                from src.utils.database.unified_manager import db_manager
                from shared.services.core.membership import create_membership_service

                async with db_manager.get_session() as db:
                    service = create_membership_service(db)
                    count = await service.check_expired_subscriptions()
                    if count > 0:
                        logger.info(f"已处理 {count} 个过期 VIP 订阅")
            except Exception as e:
                logger.error(f"检查 VIP 过期时出错：{e}")
                import traceback
                traceback.print_exc()

        self.scheduler.add_job(
            check_expired_vip_subscriptions,
            trigger=IntervalTrigger(minutes=30),
            id='check_vip_expiry',
            replace_existing=True
        )

        # 启动调度器
        self.scheduler.start()

        # 每个 worker 都输出自己的计划任务信息（带 worker 标识，使用环境变量避免重复）
        from shared.config.settings import _get_worker_info
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
