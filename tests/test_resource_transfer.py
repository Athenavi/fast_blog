"""
外部资源转存功能测试脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.database.unified_manager import db_manager
from shared.services.resource_transfer_service import ResourceTransferService


async def test_create_task():
    """测试创建下载任务"""
    print("\n" + "=" * 60)
    print("测试1: 创建下载任务")
    print("=" * 60)

    async with db_manager.get_session() as db:
        service = ResourceTransferService(db)

        # 创建测试任务
        task = await service.create_download_task(
            user_id=1,
            source_url="https://picsum.photos/800/600",
            resource_type="image",
            priority=0
        )

        print(f"✅ 任务创建成功:")
        print(f"   任务ID: {task.id}")
        print(f"   状态: {task.status}")
        print(f"   URL: {task.source_url}")

        return task.id


async def test_execute_download(task_id: int):
    """测试执行下载"""
    print("\n" + "=" * 60)
    print("测试2: 执行下载任务")
    print("=" * 60)

    async with db_manager.get_session() as db:
        service = ResourceTransferService(db)

        print(f"开始下载任务 {task_id}...")
        media = await service.execute_download(task_id)

        if media:
            print(f"✅ 下载成功!")
            print(f"   媒体ID: {media.id}")
            print(f"   文件名: {media.original_filename}")
            print(f"   文件大小: {media.file_size} bytes")
            print(f"   MIME类型: {media.mime_type}")
            return True
        else:
            print(f"❌ 下载失败")
            return False


async def test_get_task_status(task_id: int):
    """测试获取任务状态"""
    print("\n" + "=" * 60)
    print("测试3: 获取任务状态")
    print("=" * 60)

    async with db_manager.get_session() as db:
        service = ResourceTransferService(db)

        status = await service.get_task_status(task_id)

        if status:
            print(f"✅ 任务状态:")
            for key, value in status.items():
                print(f"   {key}: {value}")
            return True
        else:
            print(f"❌ 未找到任务")
            return False


async def test_batch_create():
    """测试批量创建任务"""
    print("\n" + "=" * 60)
    print("测试4: 批量创建下载任务")
    print("=" * 60)

    urls = [
        "https://picsum.photos/400/300",
        "https://picsum.photos/600/400",
        "https://picsum.photos/800/600",
    ]

    async with db_manager.get_session() as db:
        service = ResourceTransferService(db)

        tasks = []
        for url in urls:
            task = await service.create_download_task(
                user_id=1,
                source_url=url,
                resource_type="image",
                priority=0
            )
            tasks.append(task)
            print(f"   创建任务 {task.id}: {url}")

        print(f"✅ 批量创建成功，共 {len(tasks)} 个任务")
        return [t.id for t in tasks]


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("外部资源转存功能测试")
    print("=" * 60)

    try:
        # 初始化数据库
        db_manager.initialize()
        print("✅ 数据库连接成功")

        # 测试1: 创建单个任务
        task_id = await test_create_task()

        # 等待一下让任务进入队列
        await asyncio.sleep(1)

        # 测试2: 执行下载
        success = await test_execute_download(task_id)

        if success:
            # 测试3: 获取任务状态
            await test_get_task_status(task_id)

        # 测试4: 批量创建
        batch_ids = await test_batch_create()

        print("\n" + "=" * 60)
        print("✅ 所有测试完成!")
        print("=" * 60)

        print("\n提示:")
        print("- 可以通过 API 查看任务状态: GET /api/v1/resource-transfer/tasks/{task_id}")
        print("- 可以手动处理队列: POST /api/v1/resource-transfer/process-queue")
        print("- 后台处理器会自动处理待处理的任务（每30秒检查一次）")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
