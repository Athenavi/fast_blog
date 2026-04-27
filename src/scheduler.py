import logging
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from shared.models.article import Article
from shared.services.backup_manager import BackupService
from src.extensions import cache, SessionLocal

# 配置日志
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SessionScheduler:
    def __init__(self, app=None):
        # 使用 BackgroundScheduler 替代 FastScheduler
        self.scheduler = BackgroundScheduler()
        self.app = app

    def init_app(self, app):
        self.app = app
        self._init_scheduler()
        # 不再添加 FastScheduler 的 FastAPI 路由

    def _cleanup_old_backups(self, backup_dir: Path, days: int = 7):
        """
        清理旧备份文件
        
        Args:
            backup_dir: 备份目录
            days: 保留天数
        """
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (days * 24 * 60 * 60)

            deleted_count = 0
            for backup_path in backup_dir.iterdir():
                if backup_path.is_dir():
                    # 检查备份目录的修改时间
                    if backup_path.stat().st_mtime < cutoff_time:
                        import shutil
                        shutil.rmtree(backup_path)
                        deleted_count += 1
                        logger.info(f"删除旧备份: {backup_path.name}")

            if deleted_count > 0:
                logger.info(f"已清理 {deleted_count} 个旧备份文件")
        except Exception as e:
            logger.error(f"清理旧备份失败: {e}")

    def _init_scheduler(self):
        """初始化计划任务"""

        # 同步文章浏览量，每 5 分钟执行一次
        def sync_article_views():
            """同步文章浏览量"""
            try:
                # 获取所有带缓存的文章浏览量
                try:
                    if hasattr(cache.cache, 'keys'):
                        keys = cache.cache.keys()
                    else:
                        keys = []

                    article_keys = [key for key in keys if str(key).startswith('article_views_')]
                except Exception:
                    article_keys = []

                db_session = SessionLocal()
                updated_count = 0
                for key in article_keys:
                    article_id = int(key.split('_')[-1])
                    cached_views = cache.get(key)

                    if cached_views is not None:
                        article = db_session.query(Article).filter_by(article_id=article_id).first()
                        if article:
                            article.views = cached_views
                            updated_count += 1

                db_session.commit()

                for key in article_keys:
                    cache.delete(key)

                if updated_count > 0:
                    logger.info(f"成功同步 {updated_count} 篇文章的浏览量")

                db_session.close()

            except Exception as e:
                if 'db_session' in locals():
                    db_session.rollback()
                    db_session.close()
                logger.error(f"同步文章浏览量时出错：{e}")

        # 添加定时任务
        self.scheduler.add_job(
            sync_article_views,
            trigger=IntervalTrigger(minutes=5),
            id='sync_article_views',
            replace_existing=True
        )

        # 定时备份任务（每天凌晨2点执行）
        def scheduled_backup():
            """定时备份数据库和文件"""
            try:
                logger.info("开始执行定时备份...")
                backup_service = BackupService(backup_dir="backups")

                # 执行完整备份（包含文件）
                result = backup_service.create_backup(include_files=True, incremental=False)

                if result['success']:
                    logger.info(f"定时备份成功: {result['backup_name']}")

                    # 清理旧备份（保留最近7天）
                    self._cleanup_old_backups(backup_service.backup_dir, days=7)
                else:
                    logger.error(f"定时备份失败: {result.get('error')}")
            except Exception as e:
                logger.error(f"定时备份异常: {e}")
                import traceback
                traceback.print_exc()

        # 添加定时备份任务（每天凌晨2点）
        self.scheduler.add_job(
            scheduled_backup,
            trigger=CronTrigger(hour=2, minute=0),
            id='scheduled_backup',
            replace_existing=True
        )

        logger.info("定时备份任务已注册：每天凌晨2点执行")

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
