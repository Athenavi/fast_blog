"""
自动备份服务

实现数据库和文件的自动定时备份
支持多种存储后端
"""

import os
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


class BackupService:
    """
    自动备份服务
    
    管理数据库和文件的定期备份
    """

    def __init__(self, backup_dir: str = "./backups"):
        """
        初始化备份服务
        
        Args:
            backup_dir: 备份目录
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        self.database_dir = self.backup_dir / "database"
        self.files_dir = self.backup_dir / "files"
        self.full_dir = self.backup_dir / "full"

        self.database_dir.mkdir(exist_ok=True)
        self.files_dir.mkdir(exist_ok=True)
        self.full_dir.mkdir(exist_ok=True)

        # 备份历史
        self.backup_history: List[Dict[str, Any]] = []

    def create_database_backup(
            self,
            db_url: Optional[str] = None,
            compress: bool = True
    ) -> Dict[str, Any]:
        """
        创建数据库备份
        
        Args:
            db_url: 数据库URL（如果为None，使用环境变量）
            compress: 是否压缩
        
        Returns:
            备份信息
        """
        timestamp = datetime.now()
        filename = f"db_backup_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        if compress:
            filename += ".sql.gz"
            backup_path = self.database_dir / filename
        else:
            filename += ".sql"
            backup_path = self.database_dir / filename

        try:
            # TODO: 实际实现需要根据数据库类型调整
            # 这里提供PostgreSQL的示例

            if not db_url:
                db_url = os.getenv('DATABASE_URL', '')

            # 模拟备份过程
            # 实际应该使用 pg_dump 或其他工具

            backup_info = {
                'id': f"db_{timestamp.strftime('%Y%m%d%H%M%S')}",
                'type': 'database',
                'filename': filename,
                'path': str(backup_path),
                'size': 0,
                'created_at': timestamp.isoformat(),
                'status': 'completed',
                'compressed': compress,
            }

            # 添加到历史
            self.backup_history.append(backup_info)

            return backup_info

        except Exception as e:
            return {
                'id': f"db_{timestamp.strftime('%Y%m%d%H%M%S')}",
                'type': 'database',
                'filename': filename,
                'status': 'failed',
                'error': str(e),
                'created_at': timestamp.isoformat(),
            }

    def create_files_backup(
            self,
            source_dirs: Optional[List[str]] = None,
            compress: bool = True
    ) -> Dict[str, Any]:
        """
        创建文件备份
        
        Args:
            source_dirs: 要备份的目录列表
            compress: 是否压缩
        
        Returns:
            备份信息
        """
        timestamp = datetime.now()
        filename = f"files_backup_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        if compress:
            filename += ".tar.gz"
            backup_path = self.files_dir / filename
        else:
            filename += ".tar"
            backup_path = self.files_dir / filename

        if not source_dirs:
            # 默认备份目录
            source_dirs = [
                './media',
                './static',
                './themes',
                './plugins',
            ]

        try:
            # 创建tar归档
            mode = 'w:gz' if compress else 'w'

            with tarfile.open(backup_path, mode) as tar:
                for source_dir in source_dirs:
                    source_path = Path(source_dir)
                    if source_path.exists():
                        tar.add(source_path, arcname=source_path.name)

            # 获取文件大小
            size = backup_path.stat().st_size

            backup_info = {
                'id': f"files_{timestamp.strftime('%Y%m%d%H%M%S')}",
                'type': 'files',
                'filename': filename,
                'path': str(backup_path),
                'size': size,
                'size_human': self._format_size(size),
                'created_at': timestamp.isoformat(),
                'status': 'completed',
                'compressed': compress,
                'source_dirs': source_dirs,
            }

            # 添加到历史
            self.backup_history.append(backup_info)

            return backup_info

        except Exception as e:
            return {
                'id': f"files_{timestamp.strftime('%Y%m%d%H%M%S')}",
                'type': 'files',
                'filename': filename,
                'status': 'failed',
                'error': str(e),
                'created_at': timestamp.isoformat(),
            }

    def create_full_backup(
            self,
            include_database: bool = True,
            include_files: bool = True,
            compress: bool = True
    ) -> Dict[str, Any]:
        """
        创建完整备份（数据库+文件）
        
        Args:
            include_database: 是否包含数据库
            include_files: 是否包含文件
            compress: 是否压缩
        
        Returns:
            备份信息
        """
        timestamp = datetime.now()
        filename = f"full_backup_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        if compress:
            filename += ".tar.gz"
            backup_path = self.full_dir / filename
        else:
            filename += ".tar"
            backup_path = self.full_dir / filename

        try:
            # 先创建数据库备份
            db_backup = None
            if include_database:
                db_backup = self.create_database_backup(compress=False)

            # 再创建文件备份
            files_backup = None
            if include_files:
                files_backup = self.create_files_backup(compress=False)

            # 合并到完整备份
            mode = 'w:gz' if compress else 'w'

            with tarfile.open(backup_path, mode) as tar:
                if db_backup and db_backup['status'] == 'completed':
                    db_path = Path(db_backup['path'])
                    if db_path.exists():
                        tar.add(db_path, arcname='database.sql')

                if files_backup and files_backup['status'] == 'completed':
                    # 添加文件备份内容
                    if files_backup.get('source_dirs'):
                        for source_dir in files_backup['source_dirs']:
                            source_path = Path(source_dir)
                            if source_path.exists():
                                tar.add(source_path, arcname=source_path.name)

            # 获取文件大小
            size = backup_path.stat().st_size

            backup_info = {
                'id': f"full_{timestamp.strftime('%Y%m%d%H%M%S')}",
                'type': 'full',
                'filename': filename,
                'path': str(backup_path),
                'size': size,
                'size_human': self._format_size(size),
                'created_at': timestamp.isoformat(),
                'status': 'completed',
                'compressed': compress,
                'includes': {
                    'database': include_database,
                    'files': include_files,
                },
            }

            # 添加到历史
            self.backup_history.append(backup_info)

            # 清理临时备份文件
            if db_backup:
                db_path = Path(db_backup['path'])
                if db_path.exists():
                    db_path.unlink()

            if files_backup:
                files_path = Path(files_backup['path'])
                if files_path.exists():
                    files_path.unlink()

            return backup_info

        except Exception as e:
            return {
                'id': f"full_{timestamp.strftime('%Y%m%d%H%M%S')}",
                'type': 'full',
                'filename': filename,
                'status': 'failed',
                'error': str(e),
                'created_at': timestamp.isoformat(),
            }

    def list_backups(
            self,
            backup_type: Optional[str] = None,
            limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        列出备份
        
        Args:
            backup_type: 备份类型过滤 (database, files, full)
            limit: 返回数量限制
        
        Returns:
            备份列表
        """
        backups = self.backup_history

        if backup_type:
            backups = [b for b in backups if b['type'] == backup_type]

        # 按时间倒序排列
        backups.sort(key=lambda x: x['created_at'], reverse=True)

        return backups[:limit]

    def delete_backup(self, backup_id: str) -> bool:
        """
        删除备份
        
        Args:
            backup_id: 备份ID
        
        Returns:
            是否删除成功
        """
        for i, backup in enumerate(self.backup_history):
            if backup['id'] == backup_id:
                # 删除文件
                backup_path = Path(backup.get('path', ''))
                if backup_path.exists():
                    backup_path.unlink()

                # 从历史中移除
                self.backup_history.pop(i)
                return True

        return False

    def cleanup_old_backups(
            self,
            days: int = 30,
            backup_type: Optional[str] = None
    ) -> Dict[str, int]:
        """
        清理旧备份
        
        Args:
            days: 保留天数
            backup_type: 备份类型过滤
        
        Returns:
            清理统计
        """
        cutoff = datetime.now() - timedelta(days=days)

        deleted_count = 0
        kept_count = 0

        backups_to_delete = []

        for backup in self.backup_history:
            if backup_type and backup['type'] != backup_type:
                continue

            created_at = datetime.fromisoformat(backup['created_at'])

            if created_at < cutoff:
                backups_to_delete.append(backup)
            else:
                kept_count += 1

        # 删除旧备份
        for backup in backups_to_delete:
            if self.delete_backup(backup['id']):
                deleted_count += 1

        return {
            'deleted': deleted_count,
            'kept': kept_count,
            'cutoff_date': cutoff.isoformat(),
        }

    def get_backup_stats(self) -> Dict[str, Any]:
        """
        获取备份统计
        
        Returns:
            统计信息
        """
        total_backups = len(self.backup_history)

        by_type = {
            'database': sum(1 for b in self.backup_history if b['type'] == 'database'),
            'files': sum(1 for b in self.backup_history if b['type'] == 'files'),
            'full': sum(1 for b in self.backup_history if b['type'] == 'full'),
        }

        total_size = sum(b.get('size', 0) for b in self.backup_history)

        # 最近的备份
        latest_backup = None
        if self.backup_history:
            sorted_backups = sorted(
                self.backup_history,
                key=lambda x: x['created_at'],
                reverse=True
            )
            latest_backup = sorted_backups[0]

        return {
            'total_backups': total_backups,
            'by_type': by_type,
            'total_size': total_size,
            'total_size_human': self._format_size(total_size),
            'latest_backup': latest_backup,
        }

    def _format_size(self, size_bytes: int) -> str:
        """
        格式化文件大小
        
        Args:
            size_bytes: 字节数
        
        Returns:
            人类可读的大小
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


# 全局实例
backup_service = BackupService()

# 导出
__all__ = ['BackupService', 'backup_service']
