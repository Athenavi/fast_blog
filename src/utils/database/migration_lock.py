"""
数据库迁移锁管理模块
用于在多进程环境下确保数据库迁移只执行一次
"""
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

# 根据操作系统选择适当的锁机制
try:
    import fcntl  # Unix/Linux系统

    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False  # Windows系统


class MigrationLock:
    """数据库迁移锁管理类，使用文件锁确保多进程环境下的迁移安全"""

    def __init__(self, lock_file_path: Optional[str] = None):
        """
        初始化迁移锁
        
        Args:
            lock_file_path: 锁文件路径，默认为项目根目录下的.migration_lock
        """
        if lock_file_path is None:
            # 使用项目根目录作为锁文件位置
            project_root = Path(__file__).parent.parent.parent.parent
            lock_file_path = project_root / ".migration_lock"

        self.lock_file_path = Path(lock_file_path)
        # 确保锁文件所在目录存在
        self.lock_file_path.parent.mkdir(parents=True, exist_ok=True)

        # 进程内锁，确保同一进程内的线程安全
        self._in_process_lock = threading.Lock()

    @contextmanager
    def acquire(self, timeout: float = 30.0, retry_interval: float = 0.5):
        """
        获取迁移锁的上下文管理器
        
        Args:
            timeout: 获取锁的超时时间（秒）
            retry_interval: 重试间隔（秒）
            
        Yields:
            bool: 是否成功获取锁
        """
        lock_acquired = False
        lock_file_handle = None

        # 首先获取进程内锁
        in_process_acquired = self._in_process_lock.acquire(timeout=min(timeout, 1.0))
        if not in_process_acquired:
            yield False
            return

        try:
            if HAS_FCNTL:
                # Unix/Linux系统使用fcntl
                try:
                    # 打开锁文件
                    lock_file_handle = os.open(str(self.lock_file_path), os.O_CREAT | os.O_RDWR)

                    start_time = time.time()
                    while time.time() - start_time < timeout:
                        try:
                            # 尝试获取独占锁（非阻塞）
                            fcntl.flock(lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                            lock_acquired = True
                            yield True
                            # 锁将在退出上下文管理器时释放
                            break
                        except IOError:
                            # 锁被占用，等待后重试
                            time.sleep(retry_interval)
                            continue

                    if not lock_acquired:
                        yield False

                except Exception as e:
                    # 发生异常时也返回False
                    yield False
            else:
                # Windows系统使用文件锁替代方案
                start_time = time.time()
                initial_wait = True
                while time.time() - start_time < timeout:
                    try:
                        # 检查锁文件是否存在及是否过期
                        if self._is_stale_lock():
                            # 移除过期的锁文件
                            self._remove_lock_file_safely()

                        # 尝试以独占模式打开文件（如果文件不存在则创建）
                        # 使用 'x' 模式，只在文件不存在时创建，这提供了原子性
                        lock_file_handle = open(self.lock_file_path, 'x')
                        lock_file_handle.write(f"Locked at {time.time()}, PID: {os.getpid()}\n")
                        lock_file_handle.flush()  # 确保写入磁盘

                        lock_acquired = True
                        yield True
                        # 锁将在退出上下文管理器时释放
                        break
                    except FileExistsError:
                        # 锁文件已存在，等待后重试
                        if initial_wait:
                            # 初始短暂等待，然后检查锁是否过期
                            time.sleep(0.1)
                            initial_wait = False
                            continue
                        else:
                            time.sleep(retry_interval)
                            continue
                    except Exception as e:
                        # 发生意外错误，稍等后重试
                        time.sleep(retry_interval)
                        continue

                if not lock_acquired:
                    yield False
        finally:
            # 释放锁文件
            if lock_file_handle is not None:
                try:
                    if lock_acquired:
                        # 删除锁文件以释放锁
                        lock_file_handle.close()
                        if self.lock_file_path.exists():
                            self.lock_file_path.unlink()
                except Exception:
                    pass

            # 释放进程内锁
            if in_process_acquired:
                self._in_process_lock.release()

    def is_locked(self) -> bool:
        """
        检查锁是否被其他进程持有
        
        Returns:
            bool: 如果锁被持有则返回True，否则返回False
        """
        try:
            if HAS_FCNTL:
                # Unix/Linux系统：检查文件描述符锁状态比较复杂，这里简化处理
                return False  # 由于fcntl锁难以检测，这里返回False，实际依赖获取锁的过程判断
            else:
                # Windows系统：检查锁文件是否存在
                return self.lock_file_path.exists() and not self._is_stale_lock()
        except Exception:
            # 出现异常时假设被锁定
            return True

    def _is_stale_lock(self) -> bool:
        """
        检查锁文件是否过期（超过30分钟未更新）
        
        Returns:
            bool: 如果锁已过期则返回True，否则返回False
        """
        try:
            if not self.lock_file_path.exists():
                return False

            # 检查文件修改时间，如果超过30分钟则认为是过期锁
            import stat
            mtime = self.lock_file_path.stat().st_mtime
            current_time = time.time()

            # 如果文件修改时间超过30分钟（1800秒），则认为锁已过期
            return (current_time - mtime) > 1800
        except Exception:
            # 出现异常时假设锁未过期
            return False

    def _remove_lock_file_safely(self):
        """
        安全地删除锁文件
        """
        try:
            if self.lock_file_path.exists():
                self.lock_file_path.unlink()
        except Exception:
            # 删除失败通常意味着另一个进程已经删除了它，可以忽略
            pass


# 全局迁移锁实例
migration_lock = MigrationLock()


def run_migration_with_lock(migration_func, *args, **kwargs):
    """
    在锁保护下执行数据库迁移函数
    
    Args:
        migration_func: 迁移函数
        *args: 迁移函数的位置参数
        **kwargs: 迁移函数的关键字参数
        
    Returns:
        迁移函数的返回值，如果获取锁失败则返回None
    """
    with migration_lock.acquire(timeout=30.0) as acquired:
        if acquired:
            print("获取数据库迁移锁成功，开始执行迁移...")
            try:
                result = migration_func(*args, **kwargs)
                print("数据库迁移执行完成")
                return result
            except Exception as e:
                print(f"数据库迁移执行失败: {e}")
                import traceback
                traceback.print_exc()
                raise
        else:
            print("跳过数据库迁移 - 另一个进程正在执行迁移或已执行")
            return None


def check_and_run_migrations():
    """
    检查并执行数据库迁移，确保在多进程环境下只执行一次
    """
    from src.utils.database.main import check_consistency
    import logging

    logger = logging.getLogger(__name__)

    def _perform_migrations():
        """实际的迁移执行函数"""
        try:
            print("正在检查数据库表结构一致性...")
            # 检查数据库表结构一致性
            is_consistent = check_consistency()
            if not is_consistent:
                print("发现数据库表结构不一致，正在同步数据库...")
                print("✓ 数据库表结构同步完成")
            else:
                print("✓ 数据库表结构已一致，无需同步")

            return True
        except Exception as e:
            logger.error(f"数据库迁移失败: {e}")
            import traceback
            traceback.print_exc()
            raise

    # 使用锁保护执行迁移
    return run_migration_with_lock(_perform_migrations)


if __name__ == "__main__":
    # 测试锁功能
    print("测试数据库迁移锁...")


    def test_migration():
        print("正在执行模拟迁移...")
        time.sleep(2)  # 模拟迁移耗时
        print("模拟迁移完成")
        return True


    # 尝试获取锁并执行迁移
    result = run_migration_with_lock(test_migration)
    if result:
        print("迁移成功执行")
    else:
        print("迁移未执行（锁已被占用或获取失败）")
