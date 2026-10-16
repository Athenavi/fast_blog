"""
外部资源下载后台任务处理器
定期检查并处理待处理的下载任务
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select, update

from shared.logging import default_logger as logger
from shared.models import DownloadTask
from shared.services.performance.resource_transfer_service import ResourceTransferService
from src.utils.database.unified_manager import db_manager


class DownloadQueueProcessor:
    """下载队列处理器"""

    #: processing 超过该秒数视为"上次执行时进程挂了"，重置回 pending 重试
    STALE_PROCESSING_SECONDS = 900

    def __init__(self, max_concurrent: int = 3, check_interval: int = 30):
        """
        初始化处理器

        Args:
            max_concurrent: 最大并发下载数
            check_interval: 检查间隔（秒）
        """
        self.max_concurrent = max_concurrent
        self.check_interval = check_interval
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def start(self):
        """启动队列处理器"""
        if self.is_running:
            logger.warning("Download queue processor is already running")
            return

        self.is_running = True
        self.task = asyncio.create_task(self._run_processor())
        logger.info(
            f"Download queue processor started (max_concurrent={self.max_concurrent}, interval={self.check_interval}s)")

    async def stop(self):
        """停止队列处理器"""
        if not self.is_running:
            logger.warning("Download queue processor is not running")
            return

        self.is_running = False

        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        logger.info("Download queue processor stopped")

    async def _run_processor(self):
        """运行处理器主循环"""
        while self.is_running:
            try:
                await self._process_queue()
            except Exception as e:
                logger.error(f"Error in download queue processor: {e}", exc_info=True)

            # 等待下一个检查周期
            await asyncio.sleep(self.check_interval)

    async def _process_queue(self):
        """处理下载队列"""
        try:
            # 是否已安装：以**数据库**为准（是否存在超级管理员），与 system/install 同口径。
            # 原先读本地文件 storage/.installation_completed —— 多副本部署时未持有该文件的
            # 副本会永远认为"未安装"，从而完全不处理下载队列。
            if not await self._has_superuser():
                logger.debug("System not installed, skipping download queue processing")
                return

            # 获取待处理的任务（原子性标记为 processing，防止多实例竞态）
            async with db_manager.get_session() as db:
                # 先回收僵尸任务，否则崩溃留下的 processing 会永远占位、队列静默卡死
                await self._reclaim_stale(db)
                result = await db.execute(
                    select(DownloadTask)
                    .where(DownloadTask.status == "pending")
                    .order_by(DownloadTask.priority, DownloadTask.created_at)
                    .limit(self.max_concurrent)
                    .with_for_update(skip_locked=True)
                )
                pending_tasks = result.scalars().all()

                if not pending_tasks:
                    await db.commit()
                    return

                # 原子性标记为 processing
                task_ids = [t.id for t in pending_tasks]
                from sqlalchemy import update as sa_update
                await db.execute(
                    sa_update(DownloadTask)
                    .where(DownloadTask.id.in_(task_ids), DownloadTask.status == "pending")
                    .values(status="processing")
                )
                await db.commit()

                logger.info(f"Found {len(pending_tasks)} pending download tasks")

                # 并发处理任务
                tasks = []
                for task in pending_tasks:
                    # 使用信号量限制并发
                    coro = self._process_single_task(task.id)
                    tasks.append(asyncio.create_task(coro))

                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # 检查结果
                    success_count = sum(1 for r in results if isinstance(r, bool) and r)
                    logger.info(f"Processed {len(tasks)} tasks, {success_count} succeeded")

        except Exception as e:
            logger.error(f"Failed to process queue: {e}", exc_info=True)

    @staticmethod
    async def _has_superuser() -> bool:
        """以数据库为准判断"是否已安装"（存在超级管理员即已安装）"""
        from shared.models.user import User

        try:
            async with db_manager.get_session() as db:
                result = await db.execute(
                    select(func.count()).select_from(User).where(User.is_superuser.is_(True))
                )
                return int(result.scalar() or 0) > 0
        except Exception as exc:  # noqa: BLE001 - 查不动就本轮不跑队列
            logger.warning("安装状态检查失败（%s），本次跳过下载队列", type(exc).__name__)
            return False

    async def _reclaim_stale(self, db) -> None:
        """把超时仍停在 ``processing`` 的任务重置为 ``pending``

        进程在处理中被重启 / 缩容时，这些任务没有任何人回收，队列会静默卡死。
        """
        cutoff = datetime.now() - timedelta(seconds=self.STALE_PROCESSING_SECONDS)
        result = await db.execute(
            update(DownloadTask)
            .where(DownloadTask.status == "processing", DownloadTask.updated_at < cutoff)
            .values(status="pending", error_message="重置：上次处理超时未完成")
        )
        await db.commit()
        if result.rowcount:
            logger.warning("回收 %s 个超时未完成的下载任务", result.rowcount)

    async def _process_single_task(self, task_id: int) -> bool:
        """处理单个任务"""
        async with self.semaphore:
            try:
                async with db_manager.get_session() as db:
                    service = ResourceTransferService(db)
                    media = await service.execute_download(task_id)

                    if media:
                        logger.info(f"Task {task_id} completed successfully, media_id={media.id}")
                        return True
                    else:
                        logger.warning(f"Task {task_id} failed")
                        return False

            except Exception as e:
                logger.error(f"Task {task_id} processing error: {e}", exc_info=True)
                return False


# 全局实例
download_queue_processor = DownloadQueueProcessor(
    max_concurrent=3,
    check_interval=30
)


async def init_download_processor():
    """初始化下载处理器（在应用启动时调用）"""
    await download_queue_processor.start()


async def shutdown_download_processor():
    """关闭下载处理器（在应用关闭时调用）"""
    await download_queue_processor.stop()
