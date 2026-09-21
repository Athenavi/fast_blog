"""
数据备份服务
提供数据库和文件的自动备份、恢复和管理功能

本模块是**备份能力的唯一权威实现**（`ops/backup` API 与 MCP 工具都用它）：
数据库 / 文件 / 全量备份、恢复、增量与差异备份（表级变更检测 + 恢复链）、
备份校验（verify）。原先 `shared/utils/backup_manager.py` +
`shared/services/system/incremental_backup_service.py` 那条无人调用的实现已删除，
其独有能力（增量/差异备份、云上传、校验）都在这里重新实现且有测试。
"""
import asyncio
import gzip
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from shared.logging import default_logger as logger


class BackupService:
    """
    数据备份服务

    功能:
    1. 数据库备份（PostgreSQL）
    2. 文件备份（媒体文件、上传文件）
    3. 增量备份
    4. 自动备份调度
    5. 备份恢复
    6. 异地备份支持
    """

    def __init__(self, backup_dir: str = None):
        """
        初始化备份服务

        Args:
            backup_dir: 备份目录路径
        """
        self.backup_dir = backup_dir or os.getenv('BACKUP_DIR', './backups')
        self.database_backup_dir = os.path.join(self.backup_dir, 'database')
        self.files_backup_dir = os.path.join(self.backup_dir, 'files')
        self.full_backup_dir = os.path.join(self.backup_dir, 'full')
        #: 增量 / 差异备份（表级数据快照，恢复时要挂在基准备份后面）
        self.incremental_backup_dir = os.path.join(self.backup_dir, 'incremental')

        # 确保目录存在
        os.makedirs(self.database_backup_dir, exist_ok=True)
        os.makedirs(self.files_backup_dir, exist_ok=True)
        os.makedirs(self.full_backup_dir, exist_ok=True)
        os.makedirs(self.incremental_backup_dir, exist_ok=True)

        # 默认配置
        self.config = {
            'retention_days': 30,
            'auto_backup_enabled': True,
            'auto_backup_schedule': 'daily',
            'compress_backups': True,
            'backup_database': True,
            'backup_files': True,
        }

        # 异步 subprocess 运行器
    async def _run_subprocess(self, cmd, env=None, timeout=300, check=False):
        """异步运行子进程，不阻塞事件循环"""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            stdout_data, stderr_data = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise Exception(f"Subprocess timed out after {timeout}s: {' '.join(cmd)}")
        stderr_text = stderr_data.decode('utf-8', errors='replace')
        if process.returncode != 0:
            if check:
                raise Exception(stderr_text)
            raise Exception(stderr_text)
        return type('Result', (), {'returncode': process.returncode, 'stdout': stdout_data, 'stderr': stderr_data})()
    def get_db_config(self) -> Dict[str, str]:
        """获取数据库配置"""
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'fast_blog'),
        }

    async def backup_database(self, backup_type: str = 'full') -> Dict[str, Any]:
        """
        备份数据库

        Args:
            backup_type: 备份类型 ('full' 或 'incremental')

        Returns:
            备份结果信息
        """
        try:
            db_config = self.get_db_config()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"db_backup_{timestamp}.sql"
            backup_path = os.path.join(self.database_backup_dir, backup_filename)

            logger.info(f"Starting database backup: {backup_filename}")

            # 使用pg_dump进行备份
            env = os.environ.copy()
            if db_config['password']:
                env['PGPASSWORD'] = db_config['password']

            cmd = [
                'pg_dump',
                '-h', db_config['host'],
                '-p', db_config['port'],
                '-U', db_config['user'],
                '-F', 'c',  # 自定义格式（支持增量备份）
                '-f', backup_path,
                db_config['database']
            ]

            result = await self._run_subprocess(cmd, env=env, timeout=300)

            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")

            # 压缩备份文件
            compressed_path = None
            if self.config['compress_backups']:
                compressed_path = self._compress_file(backup_path)
                # 删除未压缩的文件
                os.remove(backup_path)
                backup_path = compressed_path

            # 记录备份元数据
            backup_size = os.path.getsize(backup_path)
            # 表指纹：增量 / 差异备份据此判断"哪些表变了"；拿不到时如实记下原因（不影响本次全量）
            fingerprints: Dict[str, str] = {}
            fingerprint_error = None
            try:
                fingerprints = await self.table_fingerprints(db_config)
            except Exception as exc:  # noqa: BLE001 - 指纹只是增量的辅助信息
                fingerprint_error = str(exc)
                logger.warning(f"Table fingerprints unavailable: {exc}")
            metadata = {
                'type': 'database',
                'backup_type': backup_type,
                'filename': os.path.basename(backup_path),
                'path': backup_path,
                'size': backup_size,
                'size_human': self._format_size(backup_size),
                'created_at': datetime.now().isoformat(),
                'database': db_config['database'],
                'checksum': self._sha256_file(backup_path),
                'table_fingerprints': fingerprints,
                'table_fingerprint_error': fingerprint_error,
                'verify_status': 'unverified',
                'status': 'completed'
            }

            self._save_metadata(backup_path, metadata)

            logger.info(f"Database backup completed: {backup_path} ({self._format_size(backup_size)})")

            return {
                'success': True,
                'backup_path': backup_path,
                'metadata': metadata
            }

        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def backup_files(self) -> Dict[str, Any]:
        """
        备份文件（媒体文件、上传文件等）

        Returns:
            备份结果信息
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"files_backup_{timestamp}.tar.gz"
            backup_path = os.path.join(self.files_backup_dir, backup_filename)

            logger.info(f"Starting files backup: {backup_filename}")

            # 需要备份的目录
            directories_to_backup = [
                './media',
                './upload_chunks',
                './static',
                './themes',
                './plugins',
            ]

            # 使用tar命令打包
            files_to_backup = []
            for dir_path in directories_to_backup:
                if os.path.exists(dir_path):
                    files_to_backup.append(dir_path)

            if not files_to_backup:
                return {
                    'success': True,
                    'message': 'No files to backup',
                    'backup_path': None
                }

            cmd = ['tar', '-czf', backup_path] + files_to_backup

            result = await self._run_subprocess(cmd, timeout=600)

            if result.returncode != 0:
                raise Exception(f"tar failed: {result.stderr}")

            # 记录备份元数据
            backup_size = os.path.getsize(backup_path)
            metadata = {
                'type': 'files',
                'filename': os.path.basename(backup_path),
                'path': backup_path,
                'size': backup_size,
                'size_human': self._format_size(backup_size),
                'created_at': datetime.now().isoformat(),
                'directories': files_to_backup,
                'checksum': self._sha256_file(backup_path),
                'verify_status': 'unverified',
                'status': 'completed'
            }

            self._save_metadata(backup_path, metadata)

            logger.info(f"Files backup completed: {backup_path} ({self._format_size(backup_size)})")

            return {
                'success': True,
                'backup_path': backup_path,
                'metadata': metadata
            }

        except Exception as e:
            logger.error(f"Files backup failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def full_backup(self) -> Dict[str, Any]:
        """
        完整备份（数据库 + 文件）

        Returns:
            备份结果信息
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = os.path.join(self.full_backup_dir, f"full_backup_{timestamp}")
            os.makedirs(backup_dir, exist_ok=True)

            logger.info(f"Starting full backup: {backup_dir}")

            # 备份数据库
            db_result = await self.backup_database()
            if db_result['success']:
                # 复制数据库备份到完整备份目录
                db_backup_path = db_result['backup_path']
                db_backup_name = os.path.basename(db_backup_path)
                shutil.copy2(db_backup_path, os.path.join(backup_dir, db_backup_name))

            # 备份文件
            files_result = await self.backup_files()
            if files_result['success'] and files_result['backup_path']:
                # 复制文件备份到完整备份目录
                files_backup_path = files_result['backup_path']
                files_backup_name = os.path.basename(files_backup_path)
                shutil.copy2(files_backup_path, os.path.join(backup_dir, files_backup_name))

            # 创建完整备份元数据
            metadata = {
                'type': 'full',
                'backup_dir': backup_dir,
                'created_at': datetime.now().isoformat(),
                'database_backup': db_result.get('metadata'),
                'files_backup': files_result.get('metadata'),
                'status': 'completed'
            }

            metadata_path = os.path.join(backup_dir, 'metadata.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            logger.info(f"Full backup completed: {backup_dir}")

            return {
                'success': True,
                'backup_dir': backup_dir,
                'metadata': metadata
            }

        except Exception as e:
            logger.error(f"Full backup failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def backup_full(self) -> Dict[str, Any]:
        """
        完整备份（数据库 + 文件）的别名方法

        Returns:
            备份结果信息
        """
        return await self.full_backup()

    async def restore_database(self, backup_path: str) -> Dict[str, Any]:
        """
        恢复数据库

        Args:
            backup_path: 备份文件路径

        Returns:
            恢复结果
        """
        try:
            resolved = self.resolve_backup_path(backup_path)
            if not resolved or not os.path.exists(resolved):
                return {
                    'success': False,
                    'error': f'Backup file not found（或不在备份目录内）: {backup_path}'
                }

            db_config = self.get_db_config()

            logger.info(f"Starting database restore from: {resolved}")

            env = os.environ.copy()
            if db_config['password']:
                env['PGPASSWORD'] = db_config['password']

            # 先删除现有数据库（注意：此操作不可回滚）
            drop_cmd = [
                'dropdb',
                '-h', db_config['host'],
                '-p', db_config['port'],
                '-U', db_config['user'],
                '--if-exists',
                db_config['database']
            ]

            await self._run_subprocess(drop_cmd, env=env, check=True)

            # 创建新数据库
            create_cmd = [
                'createdb',
                '-h', db_config['host'],
                '-p', db_config['port'],
                '-U', db_config['user'],
                db_config['database']
            ]

            await self._run_subprocess(create_cmd, env=env, check=True)

            # 恢复数据库：备份是「pg_dump 自定义格式 + gzip」，pg_restore 读不了 .gz，先解压到临时文件
            restore_source, temp_path = self._decompress_to_temp(resolved)
            try:
                restore_cmd = [
                    'pg_restore',
                    '-h', db_config['host'],
                    '-p', db_config['port'],
                    '-U', db_config['user'],
                    '-d', db_config['database'],
                    '--no-owner',
                    '--no-privileges',
                    restore_source
                ]

                result = await self._run_subprocess(restore_cmd, env=env, timeout=300)

                if result.returncode != 0:
                    raise Exception(f"pg_restore failed: {result.stderr}")
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)

            logger.info("Database restore completed successfully")

            return {
                'success': True,
                'message': 'Database restored successfully'
            }

        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def restore_files(self, backup_path: str) -> Dict[str, Any]:
        """
        恢复文件

        Args:
            backup_path: 备份文件路径

        Returns:
            恢复结果
        """
        try:
            resolved = self.resolve_backup_path(backup_path)
            if not resolved or not os.path.exists(resolved):
                return {
                    'success': False,
                    'error': f'Backup file not found（或不在备份目录内）: {backup_path}'
                }

            logger.info(f"Starting files restore from: {resolved}")

            # 解压并恢复到**项目根**：打包时用的是 cwd 下的相对路径（./media、./static、./themes…），
            # 解到别的目录会"恢复成功但文件落在错误位置"（旧实现解到 shared/services/system/）。
            restore_base = os.getcwd()
            cmd = ['tar', '-xzf', resolved, '-C', restore_base]

            result = await self._run_subprocess(cmd, timeout=600)

            if result.returncode != 0:
                raise Exception(f"tar restore failed: {result.stderr}")

            logger.info("Files restore completed successfully")

            return {
                'success': True,
                'message': 'Files restored successfully'
            }

        except Exception as e:
            logger.error(f"Files restore failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def list_backups(self, backup_type: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """
        列出所有备份

        Args:
            backup_type: 备份类型过滤 ('database', 'files', 'full')
            limit: 返回数量限制

        Returns:
            备份列表
        """
        backups = []

        # 扫描数据库备份
        if not backup_type or backup_type == 'database':
            for filename in os.listdir(self.database_backup_dir):
                if filename.endswith('.sql') or filename.endswith('.gz'):
                    filepath = os.path.join(self.database_backup_dir, filename)
                    metadata = self._load_metadata(filepath)
                    if metadata:
                        backups.append(metadata)

        # 扫描文件备份
        if not backup_type or backup_type == 'files':
            for filename in os.listdir(self.files_backup_dir):
                if filename.endswith('.tar.gz'):
                    filepath = os.path.join(self.files_backup_dir, filename)
                    metadata = self._load_metadata(filepath)
                    if metadata:
                        backups.append(metadata)

        # 扫描完整备份
        if not backup_type or backup_type == 'full':
            for dirname in os.listdir(self.full_backup_dir):
                dirpath = os.path.join(self.full_backup_dir, dirname)
                if os.path.isdir(dirpath):
                    metadata_path = os.path.join(dirpath, 'metadata.json')
                    if os.path.exists(metadata_path):
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            backups.append(metadata)

        # 扫描增量 / 差异备份（同一个目录，靠 metadata.type 区分）
        if not backup_type or backup_type in ('incremental', 'differential'):
            for filename in os.listdir(self.incremental_backup_dir):
                if not filename.endswith('.dump'):
                    continue
                filepath = os.path.join(self.incremental_backup_dir, filename)
                metadata = self._load_metadata(filepath)
                if metadata and (not backup_type or metadata.get('type') == backup_type):
                    backups.append(metadata)

        # 按创建时间排序
        backups.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        # 应用限制
        if limit and limit > 0:
            backups = backups[:limit]

        return backups

    def delete_backup(self, backup_path: str) -> bool:
        """
        删除备份

        Args:
            backup_path: 备份文件或目录路径

        Returns:
            是否删除成功
        """
        try:
            if os.path.isfile(backup_path):
                os.remove(backup_path)
            elif os.path.isdir(backup_path):
                shutil.rmtree(backup_path)

            logger.info(f"Backup deleted: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete backup: {e}")
            return False

    async def cleanup_old_backups(self, days: int = None) -> Dict[str, Any]:
        """
        清理旧备份

        Args:
            days: 保留天数

        Returns:
            清理结果统计
        """
        retention_days = days or self.config['retention_days']
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        backups = self.list_backups()

        deleted_count = 0
        freed_space = 0
        deleted_backups = []

        for backup in backups:
            created_at_str = backup.get('created_at', '')
            if not created_at_str:
                continue

            try:
                created_at = datetime.fromisoformat(created_at_str)
                if created_at < cutoff_date:
                    backup_path = backup.get('path') or backup.get('backup_dir')
                    if backup_path and os.path.exists(backup_path):
                        # 获取文件大小
                        if os.path.isfile(backup_path):
                            file_size = os.path.getsize(backup_path)
                        else:
                            # 目录大小
                            file_size = sum(
                                os.path.getsize(os.path.join(dirpath, filename))
                                for dirpath, dirnames, filenames in os.walk(backup_path)
                                for filename in filenames
                            )

                        if self.delete_backup(backup_path):
                            deleted_count += 1
                            freed_space += file_size
                            deleted_backups.append({
                                'filename': backup.get('filename', ''),
                                'size': file_size,
                                'size_human': self._format_size(file_size),
                                'created_at': created_at_str
                            })
            except Exception as e:
                logger.error(f"Failed to process backup for cleanup: {e}")

        logger.info(
            f"Cleaned up {deleted_count} old backups (older than {retention_days} days), freed {self._format_size(freed_space)}")

        return {
            'deleted_count': deleted_count,
            'freed_space': freed_space,
            'freed_space_human': self._format_size(freed_space),
            'deleted_backups': deleted_backups
        }

    def get_backup_schedule(self) -> Dict[str, Any]:
        """获取备份计划配置"""
        return {
            'auto_backup_enabled': self.config['auto_backup_enabled'],
            'auto_backup_schedule': self.config['auto_backup_schedule'],
            'retention_days': self.config['retention_days'],
            'compress_backups': self.config['compress_backups'],
            'backup_database': self.config['backup_database'],
            'backup_files': self.config['backup_files'],
        }

    def update_backup_schedule(self, config: Dict[str, Any]):
        """更新备份计划配置"""
        if 'auto_backup_enabled' in config:
            self.config['auto_backup_enabled'] = config['auto_backup_enabled']
        if 'auto_backup_schedule' in config:
            self.config['auto_backup_schedule'] = config['auto_backup_schedule']
        if 'retention_days' in config:
            self.config['retention_days'] = config['retention_days']
        if 'compress_backups' in config:
            self.config['compress_backups'] = config['compress_backups']
        if 'backup_database' in config:
            self.config['backup_database'] = config['backup_database']
        if 'backup_files' in config:
            self.config['backup_files'] = config['backup_files']

        logger.info(f"Backup schedule updated: {self.config}")

    def get_backup_stats(self) -> Dict[str, Any]:
        """获取备份统计信息"""
        backups = self.list_backups()

        total_size = 0
        latest_backup = None
        type_stats = {
            'database': {'count': 0, 'size': 0},
            'files': {'count': 0, 'size': 0},
            'full': {'count': 0, 'size': 0},
            'incremental': {'count': 0, 'size': 0},
            'differential': {'count': 0, 'size': 0},
        }

        for backup in backups:
            size = backup.get('size', 0)
            total_size += size
            backup_type = backup.get('type', 'unknown')

            if backup_type in type_stats:
                type_stats[backup_type]['count'] += 1
                type_stats[backup_type]['size'] += size

            if not latest_backup or backup.get('created_at', '') > latest_backup.get('created_at', ''):
                latest_backup = backup

        return {
            'total_backups': len(backups),
            'total_size': total_size,
            'total_size_human': self._format_size(total_size),
            'latest_backup': latest_backup,
            'by_type': type_stats,
        }

    def _compress_file(self, file_path: str) -> str:
        """压缩文件"""
        compressed_path = file_path + '.gz'

        with open(file_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        return compressed_path

    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def _save_metadata(self, backup_path: str, metadata: Dict[str, Any]):
        """保存备份元数据"""
        metadata_path = backup_path + '.meta.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def _load_metadata(self, backup_path: str) -> Optional[Dict[str, Any]]:
        """加载备份元数据"""
        metadata_path = backup_path + '.meta.json'
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    # ==================== 路径 / 校验和（公共基础设施） ====================
    def resolve_backup_path(self, backup_path: str) -> Optional[str]:
        """把入参解析成**备份目录内**的真实路径；越界返回 ``None``

        API 收的 ``backup_path`` 来自列表回显，有三种形态：绝对路径、``./backups/...``
        相对路径、以及**纯文件名**（前端 restore 传的是 ``row.filename``）。
        不做限制就等于"可对任意路径做恢复 / 删除 / 读取"，所以这里统一收口到 ``BACKUP_DIR``。
        """
        if not backup_path:
            return None
        root = os.path.realpath(self.backup_dir)

        candidates = [
            backup_path if os.path.isabs(backup_path) else os.path.join(os.getcwd(), backup_path),
            os.path.join(root, backup_path),
        ]
        for item in candidates:
            resolved = os.path.realpath(item)
            if os.path.exists(resolved) and (
                resolved == root or resolved.startswith(root + os.sep)
            ):
                return resolved

        # 纯文件名：在备份根下按名字找（database/files/incremental 及 full_backup_* 子目录）
        if os.sep not in backup_path and '/' not in backup_path:
            name = os.path.basename(backup_path)
            for dirpath, dirnames, filenames in os.walk(root):
                if name in filenames or name in dirnames:
                    return os.path.join(dirpath, name)
        return None

    @staticmethod
    def _sha256_file(file_path: str, chunk_size: int = 1024 * 1024) -> str:
        """文件 sha256（分块读，支持大备份文件）"""
        digest = hashlib.sha256()
        with open(file_path, 'rb') as handle:
            for chunk in iter(lambda: handle.read(chunk_size), b''):
                digest.update(chunk)
        return digest.hexdigest()

    def _decompress_to_temp(self, backup_path: str) -> tuple:
        """把 ``.gz`` 备份解压到临时文件；返回 ``(可读路径, 临时文件或 None)``

        备份文件是「``pg_dump`` 自定义格式 + gzip」（``*.sql.gz``）：``pg_restore`` /
        ``pg_restore --list`` **不能直接读 gz**（旧实现直接把 .gz 交给 pg_restore，
        恢复必然失败）。调用方用完要删掉临时文件。
        """
        if not backup_path.endswith('.gz'):
            return backup_path, None
        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.dump')
        temp.close()
        with gzip.open(backup_path, 'rb') as src, open(temp.name, 'wb') as dst:
            shutil.copyfileobj(src, dst)
        return temp.name, temp.name

    # ==================== 表指纹 / 变更检测（增量备份的基础） ====================
    async def _connect(self, db_config: Dict[str, str]):
        """连库（asyncpg 可选依赖；调用方负责 close）"""
        import asyncpg

        return await asyncpg.connect(
            host=db_config['host'],
            port=int(db_config['port']),
            database=db_config['database'],
            user=db_config['user'],
            password=db_config['password'] or None,
        )

    async def table_fingerprints(
        self, db_config: Dict[str, str] = None, tables: List[str] = None
    ) -> Dict[str, str]:
        """算出每张表"最近被写过"的事务号上界（``MAX(xmin)``）

        增量 / 差异备份靠它判断"哪些表变了"：

        - 比 ``COUNT(*)`` 可靠：改一行内容（行数不变）也能测出来；
        - 比 ``pg_stat_user_tables`` 的计数器可靠：不依赖统计收集器、不受重启影响；
        - 代价是每表一次顺序扫描（自建站点规模完全可接受；超大表请用显式 ``tables`` 缩小范围）。
        """
        db_config = db_config or self.get_db_config()
        fingerprints: Dict[str, str] = {}
        conn = await self._connect(db_config)
        try:
            if not tables:
                rows = await conn.fetch(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                    """
                )
                tables = [row['table_name'] for row in rows]
            for table in tables:
                value = await conn.fetchval(
                    f'SELECT COALESCE(MAX(xmin::text::bigint), 0) FROM "{table}"'
                )
                fingerprints[table] = str(value)
        finally:
            await conn.close()
        return fingerprints

    def _pick_base_backup(self, base_path: str = None) -> Optional[Dict[str, Any]]:
        """挑基准备份：优先入参，否则取最近一次带表指纹的数据库全量备份"""
        if base_path:
            resolved = self.resolve_backup_path(base_path)
            if not resolved:
                return None
            return self._load_metadata(resolved)
        for backup in self.list_backups(backup_type='database'):
            if backup.get('table_fingerprints'):
                return backup
        return None

    # ==================== 增量 / 差异备份 ====================
    async def create_incremental_backup(
        self,
        base_path: str = None,
        tables: List[str] = None,
        differential: bool = False,
    ) -> Dict[str, Any]:
        """创建增量 / 差异备份（**自基准以来发生变化的表的完整数据快照**）

        - **增量**（``differential=False``）：以给定的（默认最近）基准为准，只导出变化表的数据；
        - **差异**（``differential=True``）：同样相对基准，但基准固定为最近一次数据库全量备份，
          便于把多个差异备份并行挂在同一个全量上。

        数据用 ``pg_dump -F c --data-only --table=...`` 导出（结构与基准一致，不需要重复导 DDL）。
        恢复要用 :meth:`restore_backup_chain`：先恢复基准全量，再按顺序覆盖这些表。
        """
        db_config = self.get_db_config()
        base = self._pick_base_backup(base_path)
        if not base:
            return {
                'success': False,
                'error': '没有可用的基准备份：请先做一次数据库全量备份（增量/差异备份相对它计算变化）',
            }
        base_fingerprints = base.get('table_fingerprints') or {}
        if not base_fingerprints:
            return {
                'success': False,
                'error': (
                    f"基准备份 {base.get('filename')} 没有记录表指纹，无法做变化检测；"
                    "请重新做一次数据库全量备份后再建增量"
                ),
            }

        current = await self.table_fingerprints(db_config, tables)
        changed = sorted(
            table
            for table, value in current.items()
            if base_fingerprints.get(table) != value
        )
        if not changed:
            return {
                'success': True,
                'skipped': True,
                'message': '没有检测到数据变化，跳过增量备份',
                'changed_tables': [],
            }

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        kind = 'differential' if differential else 'incremental'
        filename = f"{kind}_{timestamp}.dump"
        backup_path = os.path.join(self.incremental_backup_dir, filename)

        env = os.environ.copy()
        if db_config['password']:
            env['PGPASSWORD'] = db_config['password']
        cmd = [
            'pg_dump',
            '-h', db_config['host'],
            '-p', db_config['port'],
            '-U', db_config['user'],
            '-F', 'c',
            '--data-only',
            '-f', backup_path,
            *[f'--table={table}' for table in changed],
            db_config['database'],
        ]
        try:
            await self._run_subprocess(cmd, env=env, timeout=600)
        except Exception as exc:
            logger.error(f"{kind} backup failed: {exc}")
            return {'success': False, 'error': str(exc)}

        size = os.path.getsize(backup_path)
        metadata = {
            'type': kind,
            'backup_type': kind,
            'filename': filename,
            'path': backup_path,
            'size': size,
            'size_human': self._format_size(size),
            'created_at': datetime.now().isoformat(),
            'database': db_config['database'],
            'base_backup': base.get('filename'),
            'base_path': base.get('path'),
            'tables': changed,
            'table_fingerprints': {table: current[table] for table in changed},
            'base_fingerprints': {
                table: base_fingerprints.get(table) for table in changed
            },
            'checksum': self._sha256_file(backup_path),
            'verify_status': 'unverified',
            'status': 'completed',
        }
        self._save_metadata(backup_path, metadata)
        logger.info(f"{kind} backup completed: {backup_path} ({len(changed)} tables)")

        return {
            'success': True,
            'backup_path': backup_path,
            'changed_tables': changed,
            'metadata': metadata,
        }

    def build_restore_chain(self, backup_path: str) -> List[Dict[str, Any]]:
        """由某个增量 / 差异备份回溯出完整恢复链（基准 → ... → 目标），按时间升序"""
        resolved = self.resolve_backup_path(backup_path)
        if not resolved:
            return []
        target = self._load_metadata(resolved)
        if not target:
            return []

        chain: List[Dict[str, Any]] = []
        cursor = target
        seen = set()
        while cursor:
            filename = cursor.get('filename') or cursor.get('path')
            if not filename or filename in seen:
                break
            seen.add(filename)
            chain.append(cursor)
            base_path = cursor.get('base_path') or cursor.get('base_backup')
            cursor = self._load_metadata(base_path) if base_path else None
        chain.reverse()
        return chain

    async def restore_backup_chain(
        self, backup_path: str, *, truncate: bool = True
    ) -> Dict[str, Any]:
        """按恢复链还原：基准全量 → 依次覆盖每个增量 / 差异备份里的表

        ``truncate=True``（默认）会先清空增量覆盖的表（``TRUNCATE ... CASCADE``）再灌数据 ——
        不清空直接 ``pg_restore --data-only`` 会变成"追加"，产生重复行。
        """
        chain = self.build_restore_chain(backup_path)
        if not chain:
            return {'success': False, 'error': f'无法解析恢复链：{backup_path}'}

        applied: List[str] = []
        for index, entry in enumerate(chain):
            if index == 0:
                result = await self.restore_database(entry.get('path') or entry.get('backup_dir'))
            else:
                result = await self._apply_incremental(entry, truncate=truncate)
            if not result.get('success'):
                return {
                    'success': False,
                    'error': f"恢复链在第 {index + 1} 步失败（{entry.get('filename')}）：{result.get('error')}",
                    'applied': applied,
                }
            applied.append(entry.get('filename') or '')

        return {
            'success': True,
            'message': f'已按链恢复 {len(applied)} 个备份',
            'chain': applied,
        }

    async def _apply_incremental(self, entry: Dict[str, Any], *, truncate: bool) -> Dict[str, Any]:
        """把单个增量 / 差异备份应用到已恢复的基准库上"""
        path = entry.get('path')
        tables = list(entry.get('tables') or [])
        if not path or not os.path.exists(path):
            return {'success': False, 'error': f"增量备份文件不存在：{path}"}
        if not tables:
            return {'success': False, 'error': f"增量备份 {entry.get('filename')} 未记录表清单"}

        db_config = self.get_db_config()
        env = os.environ.copy()
        if db_config['password']:
            env['PGPASSWORD'] = db_config['password']

        try:
            if truncate:
                conn = await self._connect(db_config)
                try:
                    quoted = ', '.join(f'"{table}"' for table in tables)
                    await conn.execute(f'TRUNCATE TABLE {quoted} CASCADE')
                finally:
                    await conn.close()

            cmd = [
                'pg_restore',
                '-h', db_config['host'],
                '-p', db_config['port'],
                '-U', db_config['user'],
                '-d', db_config['database'],
                '--no-owner',
                '--no-privileges',
                '--data-only',
                *[f'--table={table}' for table in tables],
                path,
            ]
            await self._run_subprocess(cmd, env=env, timeout=600)
        except Exception as exc:
            logger.error(f"Apply {entry.get('type')} backup failed: {exc}")
            return {'success': False, 'error': str(exc)}
        return {'success': True, 'tables': tables}

    # ==================== 备份校验 ====================
    async def verify_backup(self, backup_path: str) -> Dict[str, Any]:
        """校验备份的完整性（**真读文件**，不是只看元数据）

        检查项随类型不同：

        - 通用：文件存在、元数据可解析、sha256 与创建时记录一致；
        - 数据库（``*.sql.gz`` / ``*.dump``）：gzip 可解 + ``pg_restore --list`` 能列出内容；
        - 文件（``*.tar.gz``）：``tar -tzf`` 能列出内容；
        - 全量（目录）：``metadata.json`` 可读 + 目录内文件非空。
        """
        checks: List[Dict[str, Any]] = []

        def record(name: str, passed: bool, detail: str) -> None:
            checks.append({'name': name, 'passed': bool(passed), 'detail': detail})

        resolved = self.resolve_backup_path(backup_path)
        if not resolved:
            # 区分"越界"与"目录内但文件不存在"：前者是安全问题，后者是常规缺失
            raw = os.path.realpath(
                backup_path if os.path.isabs(backup_path) else os.path.join(os.getcwd(), backup_path)
            )
            root = os.path.realpath(self.backup_dir)
            inside = raw == root or raw.startswith(root + os.sep)
            return {
                'valid': False,
                'path': backup_path,
                'checks': [
                    {
                        'name': 'exists' if inside else 'path_within_backup_dir',
                        'passed': False,
                        'detail': f'备份不存在：{backup_path}' if inside else '路径不在备份目录内，已拒绝',
                    }
                ],
            }

        if not os.path.exists(resolved):
            record('exists', False, f'备份不存在：{resolved}')
            return {'valid': False, 'path': resolved, 'checks': checks}
        record('exists', True, resolved)

        metadata = (
            self._load_metadata(resolved)
            or (self._load_full_metadata(resolved) if os.path.isdir(resolved) else None)
        )
        record('metadata', metadata is not None, '元数据可解析' if metadata else '缺少 / 无法解析元数据')

        result: Dict[str, Any] = {
            'path': resolved,
            'kind': metadata.get('type') if metadata else None,
            'size': None,
            'size_human': None,
            'checksum': None,
            'checks': checks,
            'metadata': metadata,
        }

        if os.path.isdir(resolved):
            files = [name for name in os.listdir(resolved) if not name.startswith('.')]
            record('content', bool(files), f'目录内 {len(files)} 个文件')
            total = sum(
                os.path.getsize(os.path.join(resolved, name))
                for name in files
                if os.path.isfile(os.path.join(resolved, name))
            )
            result['size'] = total
            result['size_human'] = self._format_size(total)
            result['valid'] = all(item['passed'] for item in checks)
            return result

        size = os.path.getsize(resolved)
        result['size'] = size
        result['size_human'] = self._format_size(size)

        expected = (metadata or {}).get('checksum')
        if expected:
            actual = self._sha256_file(resolved)
            matched = actual == expected
            result['checksum'] = {'expected': expected, 'actual': actual, 'matched': matched}
            record('checksum', matched, 'sha256 与创建时一致' if matched else 'sha256 与创建时不符（文件被改动或损坏）')
        else:
            record('checksum', True, '该备份创建时未记录 sha256（跳过比对）')

        if resolved.endswith('.tar.gz'):
            ok, detail = await self._run_tar_list(resolved)
            record('archive', ok, detail)
        elif resolved.endswith('.gz') or resolved.endswith('.dump'):
            ok, detail = await self._run_pg_restore_list(resolved)
            record('pg_restore_list', ok, detail)

        result['valid'] = all(item['passed'] for item in checks)
        return result

    def _load_full_metadata(self, directory: str) -> Optional[Dict[str, Any]]:
        metadata_path = os.path.join(directory, 'metadata.json')
        if not os.path.exists(metadata_path):
            return None
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    async def _run_tar_list(self, path: str) -> tuple:
        """``tar -tzf`` 能否列出内容（归档可读）"""
        try:
            result = await self._run_subprocess(['tar', '-tzf', path], timeout=120)
        except Exception as exc:
            return False, f'tar 无法读取该归档：{exc}'
        entries = result.stdout.decode('utf-8', errors='replace').strip().splitlines()
        return True, f'归档可读，{len(entries)} 个条目'

    async def _run_pg_restore_list(self, path: str) -> tuple:
        """``pg_restore --list`` 能否列出内容（数据库备份可用）"""
        temp_path = None
        try:
            source, temp_path = self._decompress_to_temp(path)
        except Exception as exc:
            return False, f'gzip 解压失败（文件损坏？）：{exc}'
        try:
            result = await self._run_subprocess(['pg_restore', '--list', source], timeout=120)
        except Exception as exc:
            return False, f'pg_restore 无法读取该备份：{exc}'
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        entries = [line for line in result.stdout.decode('utf-8', errors='replace').splitlines() if line.strip()]
        return True, f'数据库备份可读，{len(entries)} 个条目'

    # ==================== 云上传留痕 ====================
    def record_cloud_upload(self, backup_path: str, info: Dict[str, Any]) -> bool:
        """把云上传结果写回备份元数据（列表里能看到"上传到哪"）；返回是否写入成功"""
        resolved = self.resolve_backup_path(backup_path)
        if not resolved:
            return False
        payload = {**info, 'uploaded_at': datetime.now().isoformat()}
        if os.path.isdir(resolved):
            metadata_path = os.path.join(resolved, 'metadata.json')
            if not os.path.exists(metadata_path):
                return False
            with open(metadata_path, 'r', encoding='utf-8') as handle:
                metadata = json.load(handle)
            metadata['cloud'] = payload
            with open(metadata_path, 'w', encoding='utf-8') as handle:
                json.dump(metadata, handle, ensure_ascii=False, indent=2)
            return True
        metadata = self._load_metadata(resolved)
        if not metadata:
            return False
        metadata['cloud'] = payload
        self._save_metadata(resolved, metadata)
        return True


# 全局实例
backup_service = BackupService()
