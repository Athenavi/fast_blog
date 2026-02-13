import importlib
import logging
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import AsyncGenerator, List, Dict, Tuple

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, configure_mappers
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)
Base = declarative_base()
_models_imported = False  # 防止重复导入模型


def _import_models_once():
    """一次性导入所有模型模块（避免重复执行）"""
    global _models_imported
    if _models_imported:
        return

    try:
        # 动态导入settings模块，避免循环依赖
        from src.setting import settings

        # 尝试从配置中获取模型路径
        if hasattr(settings, 'MODELS_PATH'):
            models_path = Path(settings.MODELS_PATH)
        else:
            # 默认路径
            current_dir = Path(__file__).parent.parent
            models_path = current_dir.parent / "models"

        if not models_path.exists():
            logger.warning(f"模型目录不存在: {models_path}")
            _models_imported = True
            return

        # 添加父目录到Python路径
        parent_path = str(models_path.parent)
        if parent_path not in sys.path:
            sys.path.insert(0, parent_path)

        # 导入所有模型文件
        for file_path in models_path.glob("*.py"):
            if file_path.name == "__init__.py":
                continue

            module_name = f"models.{file_path.stem}"
            try:
                importlib.import_module(module_name)
                logger.debug(f"导入模型模块: {module_name}")
            except ImportError as e:
                logger.debug(f"导入失败 {module_name}: {e}")

        # 配置映射
        configure_mappers()
        _models_imported = True
        logger.info("模型导入完成")

    except ImportError as e:
        logger.error(f"无法导入settings模块: {e}")
    except Exception as e:
        logger.error(f"导入模型时出错: {e}")


class DatabaseManager:
    """简化的数据库管理器"""

    def __init__(self):
        self._sync_engine = None
        self._async_engine = None
        self._sync_session_factory = None
        self._async_session_factory = None

        # 驱动映射
        self._driver_map = {
            'postgresql': {'sync': 'psycopg2', 'async': 'asyncpg'},
            'mysql': {'sync': 'pymysql', 'async': 'aiomysql'},
            'sqlite': {'sync': 'sqlite3', 'async': 'aiosqlite'},
        }

    @property
    def database_url(self) -> str:
        """获取数据库URL"""
        from src.setting import settings
        return settings.database_url

    @property
    def echo_sql(self) -> bool:
        """是否输出SQL日志"""
        from src.setting import settings
        return getattr(settings, 'database_echo', False)

    def _parse_database_url(self, url: str) -> tuple:
        """解析数据库URL"""
        if "://" not in url:
            return "sqlite", url, None

        protocol, rest = url.split("://", 1)
        if "+" in protocol:
            db_type, driver = protocol.split("+", 1)
        else:
            db_type, driver = protocol, None

        return db_type, driver, rest

    def _build_url(self, db_type: str, driver: str, rest: str) -> str:
        """构建数据库URL"""
        if driver:
            return f"{db_type}+{driver}://{rest}"
        return f"{db_type}://{rest}"

    @property
    def sync_engine(self):
        """获取同步引擎（懒加载）"""
        if self._sync_engine is None:
            self._init_sync_engine()
        return self._sync_engine

    @property
    def async_engine(self):
        """获取异步引擎（懒加载）"""
        if self._async_engine is None:
            self._init_async_engine()
        return self._async_engine

    @property
    def sync_session(self):
        """获取同步会话工厂"""
        if self._sync_session_factory is None:
            self._init_sync_engine()
        return self._sync_session_factory

    @property
    def async_session(self):
        """获取异步会话工厂"""
        if self._async_session_factory is None:
            self._init_async_engine()
        return self._async_session_factory

    def _init_sync_engine(self):
        """初始化同步引擎"""
        db_type, driver, rest = self._parse_database_url(self.database_url)

        # 如果没有指定驱动，使用默认同步驱动
        if driver is None:
            driver = self._driver_map.get(db_type, {}).get('sync')

        sync_url = self._build_url(db_type, driver, rest)

        # SQLite特殊配置
        connect_args = {}
        if db_type == "sqlite":
            connect_args = {"check_same_thread": False}

        self._sync_engine = create_engine(
            sync_url,
            connect_args=connect_args,
            poolclass=QueuePool,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=10,  # 减少连接池大小
            max_overflow=20,  # 减少最大溢出连接数
            echo=self.echo_sql
        )

        self._sync_session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self._sync_engine
        )

    def _init_async_engine(self):
        """初始化异步引擎"""
        db_type, driver, rest = self._parse_database_url(self.database_url)

        # 确保使用异步驱动
        async_driver = self._driver_map.get(db_type, {}).get('async')
        if async_driver:
            # 构建带有异步驱动的URL
            async_url = f"{db_type}+{async_driver}://{rest}"
        else:
            # 如果没有可用的异步驱动，则使用原始URL（可能失败）
            async_url = self.database_url

        self._async_engine = create_async_engine(
            async_url,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=10,
            max_overflow=20,
            echo=self.echo_sql
        )

        self._async_session_factory = async_sessionmaker(
            self._async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )


# 全局数据库管理器实例
db = DatabaseManager()


# 会话管理
@contextmanager
def get_session():
    """同步会话上下文管理器"""
    session = db.sync_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """异步会话生成器"""
    async with db.async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# FastAPI依赖注入
def get_db():
    """同步数据库依赖"""
    with get_session() as session:
        yield session


async def get_async_db():
    """异步数据库依赖"""
    async for session in get_async_session():
        yield session


# 模型相关函数
def get_model_classes() -> List:
    """获取所有模型类"""
    _import_models_once()

    model_classes = []
    for mapper in Base.registry.mappers:
        model_class = mapper.class_
        if hasattr(model_class, '__tablename__'):
            model_classes.append(model_class)

    return model_classes


def check_consistency() -> Tuple[List[Dict], List[str]]:
    """快速一致性检查"""
    _import_models_once()

    try:
        engine = db.sync_engine
        inspector = inspect(engine)
        model_classes = get_model_classes()

        inconsistent = []
        existing_tables = set(inspector.get_table_names())
        model_tables = set()

        for model in model_classes:
            table_name = getattr(model, '__tablename__', None)
            if not table_name:
                continue

            model_tables.add(table_name)

            if table_name not in existing_tables:
                inconsistent.append({
                    'table': table_name,
                    'issue': 'missing',
                    'model': model.__name__
                })
                continue

            # 快速列检查（可选，可注释掉以提高性能）
            try:
                model_cols = {c.name for c in model.__table__.columns}
                db_cols = {c['name'] for c in inspector.get_columns(table_name)}

                if model_cols != db_cols:
                    inconsistent.append({
                        'table': table_name,
                        'issue': 'columns_mismatch',
                        'model': model.__name__
                    })
            except Exception as e:
                logger.debug(f"检查列时出错 {table_name}: {e}")

        # 找出数据库中多余的表
        extra_tables = [
            t for t in existing_tables
            if t not in model_tables and t != 'alembic_version'
        ]

        return inconsistent, extra_tables

    except Exception as e:
        logger.error(f"一致性检查失败: {e}")
        return [{'error': str(e)}], []


def create_tables():
    """创建所有表"""
    _import_models_once()

    try:
        Base.metadata.create_all(db.sync_engine)
        logger.info("表创建完成")
        return True
    except Exception as e:
        logger.error(f"创建表失败: {e}")
        return False


def drop_tables():
    """删除所有表（仅用于测试）"""
    _import_models_once()

    try:
        Base.metadata.drop_all(db.sync_engine)
        logger.info("表删除完成")
        return True
    except Exception as e:
        logger.error(f"删除表失败: {e}")
        return False


# 连接测试
def test_connection() -> bool:
    """快速连接测试"""
    try:
        with db.sync_engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            return result == 1
    except Exception as e:
        logger.error(f"连接测试失败: {e}")
        return False


def get_table_count() -> int:
    """获取表数量"""
    try:
        inspector = inspect(db.sync_engine)
        return len(inspector.get_table_names())
    except Exception:
        return 0


# 初始化函数
def init_database(create_if_missing=True, check_consistency=True):
    """初始化数据库"""

    # 预加载引擎
    _ = db.sync_engine

    if not test_connection():
        logger.error("数据库连接失败")
        return False

    logger.info("数据库连接成功")

    table_count = get_table_count()
    logger.info(f"发现 {table_count} 个表")

    if table_count == 0 and create_if_missing:
        logger.info("创建缺失表...")
        create_tables()

    if check_consistency and table_count > 0:
        inconsistent, extra = check_consistency()
        if inconsistent or extra:
            logger.warning(f"发现不一致: {len(inconsistent)} 处, 多余表: {len(extra)}")

    return True


# 简化版本，按需初始化
def ensure_database():
    """确保数据库已初始化"""
    return init_database()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ensure_database()
