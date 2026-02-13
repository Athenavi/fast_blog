"""扩展模块，初始化FastAPI兼容的扩展实例"""

import logging
from contextlib import contextmanager
from typing import Generator, AsyncGenerator

import redis
from slowapi import _rate_limit_exceeded_handler, Limiter
from slowapi.util import get_remote_address
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# 创建SQLAlchemy基类
Base = declarative_base()

# 缓存
try:
    cache = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    cache.ping()  # 测试连接
except (redis.ConnectionError, ImportError):
    # 如果Redis不可用，使用简单内存缓存
    class SimpleCache:
        def __init__(self):
            self._cache = {}

        def get(self, key):
            return self._cache.get(key)

        def set(self, key, value, ex=None):
            if ex:
                # 简单实现不支持过期时间
                self._cache[key] = value
            else:
                self._cache[key] = value

        def delete(self, key):
            self._cache.pop(key, None)

        def memoize(self, timeout=300):
            """
            简单的memoize装饰器实现
            :param timeout: 超时时间（秒），对于SimpleCache不起作用，因为不支持过期
            """

            def decorator(func):
                import asyncio
                import functools
                
                if asyncio.iscoroutinefunction(func):
                    # 异步函数的处理
                    @functools.wraps(func)
                    async def async_wrapper(*args, **kwargs):
                        # 创建缓存键，将参数转换为字符串
                        cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"

                        # 尝试从缓存中获取结果
                        result = self.get(cache_key)
                        if result is not None:
                            return result

                        # 如果缓存中没有，则执行函数并将结果存储在缓存中
                        result = await func(*args, **kwargs)
                        self.set(cache_key, result)
                        return result
                    return async_wrapper
                else:
                    # 同步函数的处理
                    @functools.wraps(func)
                    def sync_wrapper(*args, **kwargs):
                        # 创建缓存键，将参数转换为字符串
                        cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"

                        # 尝试从缓存中获取结果
                        result = self.get(cache_key)
                        if result is not None:
                            return result

                        # 如果缓存中没有，则执行函数并将结果存储在缓存中
                        result = func(*args, **kwargs)
                        self.set(cache_key, result)
                        return result
                    return sync_wrapper

            return decorator

        def cached(self, timeout=300, key_prefix=''):
            """
            简单的cached装饰器实现
            :param timeout: 超时时间（秒），对于SimpleCache不起作用，因为不支持过期
            :param key_prefix: 缓存键前缀
            """

            def decorator(func):
                import asyncio
                import functools
                
                if asyncio.iscoroutinefunction(func):
                    # 异步函数的处理
                    @functools.wraps(func)
                    async def async_wrapper(*args, **kwargs):
                        # 创建缓存键
                        cache_key = f"{key_prefix}{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"

                        # 尝试从缓存中获取结果
                        result = self.get(cache_key)
                        if result is not None:
                            return result

                        # 如果缓存中没有，则执行函数并将结果存储在缓存中
                        result = await func(*args, **kwargs)
                        self.set(cache_key, result)
                        return result
                    return async_wrapper
                else:
                    # 同步函数的处理
                    @functools.wraps(func)
                    def sync_wrapper(*args, **kwargs):
                        # 创建缓存键
                        cache_key = f"{key_prefix}{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"

                        # 尝试从缓存中获取结果
                        result = self.get(cache_key)
                        if result is not None:
                            return result

                        # 如果缓存中没有，则执行函数并将结果存储在缓存中
                        result = func(*args, **kwargs)
                        self.set(cache_key, result)
                        return result
                    return sync_wrapper

            return decorator

        def __call__(self, *args, **kwargs):
            """
            使SimpleCache对象本身可调用，模拟Flask-Cache的用法
            这是为了处理直接调用cache()的情况
            """
            # 如果没有参数，返回自身
            if len(args) == 0 and len(kwargs) == 0:
                return self

            # 如果第一个参数是函数，将其包装为缓存装饰器
            if args and callable(args[0]):
                func = args[0]
                # 默认使用cached装饰器行为
                return self.cached(**kwargs)(func)

            # 否则，根据参数决定行为
            timeout = kwargs.get('timeout', 300)
            key_prefix = kwargs.get('key_prefix', '')
            return self.cached(timeout=timeout, key_prefix=key_prefix)


    cache = SimpleCache()


# JWT密码哈希上下文
def _get_pwd_context():
    """获取密码上下文，处理passlib和bcrypt兼容性问题"""
    try:
        from passlib.context import CryptContext
        # 捕获并忽略关于版本属性的警告
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
            # 尝试使用一次以确保其正常工作
            ctx.hash("test")
        return ctx
    except (AttributeError, TypeError, ValueError):
        # 如果初始化失败，返回一个使用bcrypt直接实现的类
        import bcrypt
        class SafeCryptContext:
            def hash(self, secret):
                # 确保密码不超过72字节限制
                if len(secret.encode('utf-8')) > 72:
                    secret = secret.encode('utf-8')[:72].decode('utf-8', errors='ignore')
                return bcrypt.hashpw(secret.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            def verify(self, secret, hash):
                try:
                    return bcrypt.checkpw(secret.encode('utf-8'), hash.encode('utf-8'))
                except Exception:
                    # 处理各种可能的错误情况
                    try:
                        return bcrypt.checkpw(secret.encode('utf-8'), hash)
                    except Exception:
                        return False

        return SafeCryptContext()


pwd_context = _get_pwd_context()

# 数据库引擎和会话
engine = None
SessionLocal = None
_async_engine_instance = None
_AsyncSessionLocal_instance = None


def _get_async_engine():
    """延迟获取异步引擎实例"""
    global _async_engine_instance, _AsyncSessionLocal_instance

    if _async_engine_instance is None:
        # 从设置中获取数据库URL
        try:
            from src.setting import settings
            database_url = settings.database_url
        except ImportError:
            database_url = "sqlite:///./blog.db"

        # 根据数据库类型选择合适的异步驱动
        try:
            if "postgresql" in database_url:
                # 替换为 asyncpg 驱动
                async_database_url = database_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://").replace(
                    "postgresql://", "postgresql+asyncpg://")
            elif "mysql" in database_url:
                # 替换为 aiomysql 驱动
                async_database_url = database_url.replace("mysql+pymysql://", "mysql+aiomysql://").replace("mysql://",
                                                                                                           "mysql+aiomysql://")
            elif "sqlite" in database_url:
                # 替换为 aiosqlite 驱动
                async_database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
            else:
                # 对于未知类型，默认使用原始URL
                async_database_url = database_url

            # 创建异步引擎
            _async_engine_instance = create_async_engine(
                async_database_url,
                pool_pre_ping=True,
                pool_recycle=300,
                pool_size=20,
                max_overflow=30
            )

            _AsyncSessionLocal_instance = async_sessionmaker(
                _async_engine_instance,
                class_=AsyncSession,
                expire_on_commit=False
            )
        except Exception as e:
            logging.error(f"Failed to create async engine: {e}")
            # 不抛出异常，而是记录错误并保持为 None
            _async_engine_instance = None
            _AsyncSessionLocal_instance = None

    return _async_engine_instance, _AsyncSessionLocal_instance


def init_extensions(app):
    """初始化所有FastAPI扩展"""
    global engine, SessionLocal

    # 从设置中获取数据库URL
    try:
        from src.setting import settings
        database_url = settings.database_url
    except ImportError:
        # 如果settings不可用，使用默认配置
        database_url = "sqlite:///./blog.db"

    # 数据库初始化
    if database_url.startswith("sqlite"):
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},  # SQLite特定参数
            poolclass=QueuePool,
            pool_pre_ping=True,
            pool_recycle=300,
        )
    else:
        # 对于PostgreSQL, MySQL等
        engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=20,
            max_overflow=30
        )

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # 限流中间件
    try:
        app.state.limiter = Limiter(key_func=get_remote_address)
        app.add_exception_handler(429, _rate_limit_exceeded_handler)
    except Exception as e:
        logging.warning(f"Failed to initialize rate limiter: {e}")

    # 初始化数据库表
    Base.metadata.create_all(bind=engine)


# 便捷函数：获取数据库会话
@contextmanager
def get_db() -> Generator:
    """获取数据库会话的便捷函数"""
    if SessionLocal is None:
        raise RuntimeError("Extensions not initialized. Call init_extensions first.")

    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


# 异步便捷函数：获取异步数据库会话
async def get_async_db() -> AsyncGenerator:
    """获取异步数据库会话的便捷函数"""
    async_engine, AsyncSessionLocal = _get_async_engine()

    if AsyncSessionLocal is None:
        raise RuntimeError(
            "Async extensions not initialized. Call init_extensions first or async support is unavailable.")

    async with AsyncSessionLocal() as db_session:
        try:
            yield db_session
        finally:
            await db_session.close()


# FastAPI依赖注入函数 - 同步版本
def get_sync_db():
    """FastAPI依赖注入：获取同步数据库会话"""
    with get_db() as session:
        yield session


async def get_async_db_session():
    """FastAPI依赖注入：获取异步数据库会话"""
    async for session in get_async_db():
        yield session
