import functools
import os
import secrets

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from shared.services.articles.article_view_stats import article_view_stats
from shared.services.system.backup_service import backup_service
from src.unified_logger import default_logger as logger

#: Redis 不可用时使用的哨兵令牌：表示"本次放行、无需（也无法）释放"
_NO_REDIS_TOKEN = "__no_redis__"

#: 仅在令牌匹配时删除锁 —— 避免"任务超时后锁已易主，却被旧持有者删掉"
_RELEASE_LOCK_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


async def _acquire_job_lock(name: str, ttl: int = 600) -> "str | None":
    """获取定时任务的分布式锁，成功时返回持有令牌，未获得返回 ``None``。

    设计要点：

    - **TTL 必须小于该任务的调度间隔**。否则会出现"上一轮的锁还没过期、
      这一轮拿不到"的倒挂：例如每 5 分钟跑一次的任务若给 ttl=600，实际会变成
      每 10 分钟才执行一次。
    - 任务结束后由 ``_release_job_lock`` 主动释放，正常路径下下一轮立即可获取。
    - **Redis 不可用时放行**（返回哨兵令牌）：此时限流、缓存、会话都已降级，
      让幂等的定时任务继续跑比整体停摆更安全；代价是多副本下可能重复执行，
      因此这里显式告警，不做静默降级。
    """
    token = secrets.token_urlsafe(16)
    try:
        from src.services.redis_service import redis_service

        if redis_service._redis is None:
            await redis_service.connect()
        acquired = await redis_service.redis.set(
            f"fb:sched_lock:{name}", token, nx=True, ex=ttl
        )
        return token if acquired else None
    except Exception as exc:  # noqa: BLE001 - Redis 故障不应让定时任务整体停摆
        logger.warning(
            "分布式锁不可用（%s），本次放行执行 %s；多副本部署下可能重复执行",
            type(exc).__name__,
            name,
        )
        return _NO_REDIS_TOKEN


async def _release_job_lock(name: str, token: "str | None") -> None:
    """释放分布式锁（仅当令牌仍匹配时删除）"""
    if not token or token == _NO_REDIS_TOKEN:
        return
    try:
        from src.services.redis_service import redis_service

        await redis_service.redis.eval(_RELEASE_LOCK_SCRIPT, 1, f"fb:sched_lock:{name}", token)
    except Exception as exc:  # noqa: BLE001 - 释放失败交给 TTL 兜底
        logger.warning("释放分布式锁失败（%s）：%s，将由 TTL 自然过期", type(exc).__name__, name)


def _with_job_lock(name: str, ttl: int):
    """装饰器：给定时任务套上分布式锁（未获得则跳过，结束后释放）"""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper():
            token = await _acquire_job_lock(name, ttl)
            if token is None:
                return
            try:
                return await func()
            finally:
                await _release_job_lock(name, token)

        return wrapper

    return decorator


async def _upload_backup_if_configured(*backup_paths: "str | None") -> None:
    """备份成功后按配置自动上传云存储。

    - **未配置**云存储：静默跳过（不是错误，本地备份仍然有效）。
    - 已配置但**上传失败**：显式告警 —— 否则会出现"本地有备份、云端没有"，
      在宿主机损毁的场景下等于没有备份。
    """
    paths = [path for path in backup_paths if path]
    if not paths:
        return
    try:
        from src.api.v3.modules.ops.backup.service import backup_ops_service
        from src.utils.database.unified_manager import db_manager

        async with db_manager.get_session() as db:
            if not await backup_ops_service.is_cloud_configured(db):
                logger.info("未配置云存储，跳过自动上传（本地备份仍已完成）")
                return
            for path in paths:
                try:
                    result = await backup_ops_service.upload_to_cloud(db, path)
                    logger.info(f"备份已上传云端：{os.path.basename(path)} → {result.get('location')}")
                except Exception as exc:  # noqa: BLE001 - 单个失败不应中断其余上传
                    logger.error(
                        f"备份上传云端失败：{path}（{exc}）—— 云端缺少该备份，请检查云存储配置"
                    )
    except Exception as exc:  # noqa: BLE001 - 自动上传是增强能力，异常不得影响备份任务本身
        logger.error(f"自动上传备份到云端失败（{exc}）")


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
        # ttl(240) 必须小于调度间隔(300)：原 ttl=300 贴着间隔，偶发跳过一轮
        @_with_job_lock("sync_article_views", ttl=240)
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
                logger.exception("同步文章浏览量详细错误")

        # 添加定时任务（AsyncIOScheduler 直接支持异步函数）

        self.scheduler.add_job(
            sync_article_views_to_db,
            trigger=IntervalTrigger(minutes=5),
            id='sync_article_views',
            replace_existing=True
        )

        # 每日备份任务（凌晨 2 点）
        @_with_job_lock("daily_backup", ttl=3600)
        async def daily_backup():
            logger.info("Starting daily database backup...")
            try:
                result = await backup_service.backup_database(backup_type='full')
                if result.get('success'):
                    logger.info(f"Daily backup completed: {result.get('backup_path')}")
                    # 备份只落本地卷不构成灾备：已配置云存储时自动上传
                    await _upload_backup_if_configured(result.get('backup_path'))
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
        @_with_job_lock("weekly_backup", ttl=3600)
        async def weekly_backup():
            logger.info("Starting weekly full backup...")
            try:
                db_result = await backup_service.backup_database(backup_type='full')
                files_result = await backup_service.backup_files()
                if db_result.get('success') and files_result.get('success'):
                    logger.info(f"Weekly backup completed")
                else:
                    logger.error(f"Weekly backup had issues: db={db_result.get('success')}, files={files_result.get('success')}")
                # 成功的那部分也要上云（失败的部分自然没有路径）
                await _upload_backup_if_configured(
                    db_result.get('backup_path'),
                    files_result.get('backup_path'),
                )
            except Exception as e:
                logger.error(f"Weekly backup failed: {e}")

        self.scheduler.add_job(
            weekly_backup,
            trigger=CronTrigger(day_of_week='sun', hour=3, minute=0),
            id='weekly_backup',
            replace_existing=True
        )

        # 定时发布到期文章检查（每 5 分钟）
        # ttl(240) < 间隔(300)：原 ttl=600 让实际检查频率降为每 10 分钟一次
        @_with_job_lock("publish_due_articles", ttl=240)
        async def check_due_scheduled_articles():
            """检查并发布到期的定时文章"""
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
                logger.exception("检查定时发布详细错误")

        self.scheduler.add_job(
            check_due_scheduled_articles,
            trigger=IntervalTrigger(minutes=5),
            id='publish_due_articles',
            replace_existing=True
        )

        # VIP 订阅过期检查（每 30 分钟）
        @_with_job_lock("check_vip_expiry", ttl=900)
        async def check_expired_vip_subscriptions():
            """检查并标记过期的 VIP 订阅"""
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
                logger.exception("检查 VIP 过期详细错误")

        self.scheduler.add_job(
            check_expired_vip_subscriptions,
            trigger=IntervalTrigger(minutes=30),
            id='check_vip_expiry',
            replace_existing=True
        )

        # 审计日志保留策略（每日 04:00）。此前 cleanup_old_logs 已实现但无人调用，
        # audit_logs 会无限增长；保留天数由 AuditLogService.retention_days 决定。
        @_with_job_lock("cleanup_audit_logs", ttl=3600)
        async def cleanup_audit_logs():
            try:
                from shared.services.security.audit_log_service import audit_log_service
                from src.utils.database.unified_manager import db_manager

                async with db_manager.get_session() as db:
                    await audit_log_service.cleanup_old_logs(db)
            except Exception as e:
                logger.error(f"审计日志清理失败：{e}")

        self.scheduler.add_job(
            cleanup_audit_logs,
            trigger=CronTrigger(hour=4, minute=0),
            id='cleanup_audit_logs',
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
