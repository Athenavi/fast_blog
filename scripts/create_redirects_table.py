"""
创建重定向表的脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


async def create_redirects_table():
    """创建 redirects 表"""
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
    from shared.models.redirect import Redirect
    from shared.models import Base
    from src.setting import AppConfig

    # 获取数据库 URL - 需要实例化 AppConfig
    config = AppConfig()
    db_url = config.database_url
    
    # 将 psycopg2 转换为 asyncpg 以支持异步操作
    if db_url.startswith('postgresql+psycopg2://'):
        db_url = db_url.replace('postgresql+psycopg2://', 'postgresql+asyncpg://')

    print(f"正在连接到数据库: {db_url}")

    # 创建引擎
    engine = create_async_engine(db_url, echo=False)

    try:
        async with engine.begin() as conn:
            # 只创建 redirects 表
            await conn.run_sync(Base.metadata.create_all, tables=[Redirect.__table__])
            print("✅ redirects 表创建成功")

            # 验证表是否存在
            result = await conn.execute(
                text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'redirects')")
            )
            exists = result.scalar()

            if exists:
                print("✅ 验证通过：redirects 表已存在")
            else:
                print("❌ 验证失败：redirects 表不存在")

    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_redirects_table())
