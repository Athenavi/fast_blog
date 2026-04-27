"""
PostgreSQL备份管理器插件
提供数据库的可视化导出导入操作,支持完整备份和恢复
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from shared.services.plugin_manager import BasePlugin, plugin_hooks


class PostgreSQLBackupPlugin(BasePlugin):
    """
    PostgreSQL备份管理器插件
    
    功能:
    1. PostgreSQL数据库导出(pg_dump)
    2. PostgreSQL数据库导入(pg_restore/psql)
    3. 备份文件管理
    4. 备份历史追踪(独立SQLite)
    5. 自动化备份调度
    """
    
    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="PostgreSQL备份管理器",
            slug="backup-manager",
            version="1.0.0"
        )

        # 默认设置
        self.settings = {
            'auto_backup_enabled': False,
            'backup_interval_hours': 24,
            'max_backups': 10,
            'backup_format': 'custom',
            'compress_backups': True,
            'enable_encryption': False,
            'encryption_password': '',
            'cloud_storage_enabled': False,
            'cloud_provider': 's3',
            's3_bucket': '',
            's3_access_key': '',
            's3_secret_key': '',
            's3_region': 'us-east-1',
            'auto_sync_to_cloud': True,
        }
        self.plugin_info = {
            "name": "PostgreSQL备份管理器",
            "slug": "backup-manager",
            "version": "1.0.0",
            "description": "PostgreSQL数据库可视化导出导入工具",
            "author": "FastBlog Team",
            "category": "system"
        }
        
        # 插件数据目录
        self.data_dir = Path("plugins_data") / "backup-manager"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 备份文件存储目录
        self.backup_dir = Path("backups") / "database"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # SQLite数据库路径(仅用于记录备份历史)
        self.history_db_path = self.data_dir / "backup_history.db"
        
        # 初始化历史数据库
        self._init_history_database()

    def register_hooks(self):
        """注册钩子"""
        # 定时备份任务
        if self.settings.get('auto_backup_enabled'):
            plugin_hooks.add_action(
                "daily_cleanup",
                self.perform_scheduled_backup,
                priority=10
            )

    def activate(self):
        """激活插件"""
        super().activate()
        print("[BackupManager] Plugin activated")

    def deactivate(self):
        """停用插件"""
        super().deactivate()
        print("[BackupManager] Plugin deactivated")
    
    def _get_history_connection(self):
        """获取历史记录数据库连接"""
        import sqlite3
        conn = sqlite3.connect(str(self.history_db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_history_database(self):
        """初始化备份历史数据库"""
        conn = self._get_history_connection()
        cursor = conn.cursor()
        
        # 创建备份历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backup_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE,
                backup_type TEXT NOT NULL DEFAULT 'full',
                format TEXT NOT NULL DEFAULT 'custom',
                database_name TEXT,
                file_size INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                duration_seconds REAL,
                notes TEXT,
                metadata TEXT
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_backup_created 
            ON backup_history(created_at DESC)
        ''')
        
        conn.commit()
        conn.close()
    
    def _get_pg_config(self) -> Dict[str, str]:
        """
        获取PostgreSQL连接配置
        
        Returns:
            配置字典
        """
        import os
        
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'fast_blog'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', ''),
        }
    
    async def export_database(
        self,
        filename: str = None,
        format: str = 'custom',
        compress: bool = True,
        include_schema: bool = True,
        include_data: bool = True,
        tables: List[str] = None,
        notes: str = ''
    ) -> Dict[str, Any]:
        """
        导出PostgreSQL数据库
        
        Args:
            filename: 备份文件名(不含扩展名)
            format: 备份格式 (custom, plain, tar, directory)
            compress: 是否压缩
            include_schema: 是否包含schema
            include_data: 是否包含数据
            tables: 指定表列表(None表示全部)
            notes: 备注
            
        Returns:
            导出结果
        """
        start_time = datetime.utcnow()
        
        try:
            # 生成文件名
            if not filename:
                timestamp = start_time.strftime('%Y%m%d_%H%M%S')
                filename = f"backup_{timestamp}"
            
            # 根据格式确定扩展名
            ext_map = {
                'custom': '.dump',
                'plain': '.sql',
                'tar': '.tar',
                'directory': ''
            }
            ext = ext_map.get(format, '.dump')
            backup_path = self.backup_dir / f"{filename}{ext}"
            
            # 如果是directory格式,创建目录
            if format == 'directory':
                backup_path.mkdir(parents=True, exist_ok=True)
            
            # 构建pg_dump命令
            config = self._get_pg_config()
            cmd = ['pg_dump']
            
            # 添加连接参数
            cmd.extend(['-h', config['host']])
            cmd.extend(['-p', config['port']])
            cmd.extend(['-U', config['user']])
            cmd.extend(['-d', config['database']])
            
            # 设置密码环境变量
            env = os.environ.copy()
            env['PGPASSWORD'] = config['password']
            
            # 添加格式选项
            if format == 'custom':
                cmd.append('-Fc')  # custom format
            elif format == 'tar':
                cmd.append('-Ft')  # tar format
            elif format == 'directory':
                cmd.append('-Fd')  # directory format
            else:
                cmd.append('-Fp')  # plain SQL format
            
            # 压缩选项
            if compress and format in ['custom', 'directory']:
                cmd.extend(['-Z', '9'])  # 最高压缩级别
            
            # Schema和数据选项
            if include_schema and not include_data:
                cmd.append('-s')  # schema only
            elif include_data and not include_schema:
                cmd.append('-a')  # data only
            
            # 指定表
            if tables:
                for table in tables:
                    cmd.extend(['-t', table])
            
            # 输出文件
            if format != 'directory':
                cmd.extend(['-f', str(backup_path)])
            else:
                cmd.extend(['-f', str(backup_path)])
            
            # 执行导出
            print(f"开始导出数据库: {filename}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await process.communicate()
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                print(f"导出失败: {error_msg}")
                
                # 记录失败历史
                self._save_history(
                    filename=f"{filename}{ext}",
                    backup_type='manual',
                    format=format,
                    status='failed',
                    duration=duration,
                    notes=f"导出失败: {error_msg[:200]}"
                )
                
                return {
                    'success': False,
                    'error': f'导出失败: {error_msg}',
                    'filename': None
                }
            
            # 获取文件大小
            if format == 'directory':
                file_size = sum(
                    f.stat().st_size for f in backup_path.rglob('*') if f.is_file()
                )
            else:
                file_size = backup_path.stat().st_size
            
            print(f"导出成功: {filename}, 大小: {file_size / (1024*1024):.2f} MB")
            
            # 保存历史记录
            self._save_history(
                filename=f"{filename}{ext}",
                backup_type='manual',
                format=format,
                file_size=file_size,
                status='completed',
                duration=duration,
                notes=notes or f"手动导出 - {start_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            return {
                'success': True,
                'filename': f"{filename}{ext}",
                'path': str(backup_path),
                'size': file_size,
                'size_mb': round(file_size / (1024*1024), 2),
                'duration': duration,
                'format': format
            }
            
        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            print(f"导出异常: {e}")
            import traceback
            traceback.print_exc()
            
            # 记录失败历史
            self._save_history(
                filename=filename or f"backup_{start_time.strftime('%Y%m%d_%H%M%S')}",
                backup_type='manual',
                format=format,
                status='failed',
                duration=duration,
                notes=f"导出异常: {str(e)}"
            )
            
            return {
                'success': False,
                'error': str(e),
                'filename': None
            }
    
    async def import_database(
        self,
        filename: str,
        drop_existing: bool = False,
        create_database: bool = False,
        notes: str = ''
    ) -> Dict[str, Any]:
        """
        导入PostgreSQL数据库
        
        Args:
            filename: 备份文件名
            drop_existing: 是否删除现有数据
            create_database: 是否创建数据库
            notes: 备注
            
        Returns:
            导入结果
        """
        start_time = datetime.utcnow()
        
        try:
            backup_path = self.backup_dir / filename
            
            if not backup_path.exists():
                return {
                    'success': False,
                    'error': f'备份文件不存在: {filename}'
                }
            
            # 检测备份格式
            format = self._detect_backup_format(filename)
            
            # 构建导入命令
            config = self._get_pg_config()
            
            if format == 'plain':
                # 使用psql导入SQL文件
                cmd = ['psql']
                cmd.extend(['-h', config['host']])
                cmd.extend(['-p', config['port']])
                cmd.extend(['-U', config['user']])
                cmd.extend(['-d', config['database']])
                cmd.extend(['-f', str(backup_path)])
                
                # 如果需要删除现有数据
                if drop_existing:
                    # 先清空数据库
                    await self._drop_all_tables(config)
            else:
                # 使用pg_restore导入
                cmd = ['pg_restore']
                cmd.extend(['-h', config['host']])
                cmd.extend(['-p', config['port']])
                cmd.extend(['-U', config['user']])
                cmd.extend(['-d', config['database']])
                
                if drop_existing:
                    cmd.append('--clean')
                    cmd.append('--if-exists')
                
                cmd.append(str(backup_path))
            
            # 设置密码环境变量
            env = os.environ.copy()
            env['PGPASSWORD'] = config['password']
            
            # 执行导入
            print(f"开始导入数据库: {filename}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await process.communicate()
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                print(f"导入失败: {error_msg}")
                
                return {
                    'success': False,
                    'error': f'导入失败: {error_msg}'
                }
            
            print(f"导入成功: {filename}, 耗时: {duration:.2f}秒")
            
            return {
                'success': True,
                'filename': filename,
                'duration': duration,
                'message': f'数据库导入成功,耗时{duration:.2f}秒'
            }
            
        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            print(f"导入异常: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def _detect_backup_format(self, filename: str) -> str:
        """检测备份文件格式"""
        if filename.endswith('.sql'):
            return 'plain'
        elif filename.endswith('.tar'):
            return 'tar'
        elif filename.endswith('.dump'):
            return 'custom'
        else:
            # 检查是否是目录
            backup_path = self.backup_dir / filename
            if backup_path.is_dir():
                return 'directory'
            return 'custom'
    
    async def _drop_all_tables(self, config: Dict[str, str]):
        """删除所有表(谨慎使用)"""
        import asyncpg
        
        try:
            conn = await asyncpg.connect(
                host=config['host'],
                port=int(config['port']),
                user=config['user'],
                password=config['password'],
                database=config['database']
            )
            
            # 获取所有表
            tables = await conn.fetch('''
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
            ''')
            
            # 删除所有表
            for table in tables:
                table_name = table['tablename']
                await conn.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')
            
            await conn.close()
            print("已清空数据库所有表")
            
        except Exception as e:
            print(f"清空表失败: {e}")
            raise
    
    def list_backups(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        列出备份文件
        
        Args:
            limit: 返回数量
            
        Returns:
            备份文件列表
        """
        try:
            backups = []
            
            # 扫描备份目录
            for file_path in sorted(self.backup_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if file_path.is_file() or file_path.is_dir():
                    stat = file_path.stat()
                    backups.append({
                        'filename': file_path.name,
                        'path': str(file_path),
                        'size': stat.st_size if file_path.is_file() else 0,
                        'size_mb': round(stat.st_size / (1024*1024), 2) if file_path.is_file() else 0,
                        'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'is_directory': file_path.is_dir()
                    })
                    
                    if len(backups) >= limit:
                        break
            
            return backups
            
        except Exception as e:
            print(f"列出备份失败: {e}")
            return []
    
    def delete_backup(self, filename: str) -> bool:
        """
        删除备份文件
        
        Args:
            filename: 备份文件名
            
        Returns:
            是否成功
        """
        try:
            backup_path = self.backup_dir / filename
            
            if not backup_path.exists():
                return False
            
            # 删除文件或目录
            if backup_path.is_dir():
                import shutil
                shutil.rmtree(backup_path)
            else:
                backup_path.unlink()
            
            # 删除历史记录
            self._delete_history(filename)
            
            return True
            
        except Exception as e:
            print(f"删除备份失败: {e}")
            return False
    
    def get_backup_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        获取备份文件信息
        
        Args:
            filename: 备份文件名
            
        Returns:
            备份信息
        """
        try:
            backup_path = self.backup_dir / filename
            
            if not backup_path.exists():
                return None
            
            stat = backup_path.stat()
            
            # 从历史记录中获取额外信息
            history = self._get_history(filename)
            
            info = {
                'filename': filename,
                'path': str(backup_path),
                'size': stat.st_size if backup_path.is_file() else 0,
                'size_mb': round(stat.st_size / (1024*1024), 2) if backup_path.is_file() else 0,
                'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'is_directory': backup_path.is_dir(),
                'format': self._detect_backup_format(filename)
            }
            
            # 合并历史信息
            if history:
                info.update({
                    'backup_type': history.get('backup_type'),
                    'status': history.get('status'),
                    'duration': history.get('duration_seconds'),
                    'notes': history.get('notes')
                })
            
            return info
            
        except Exception as e:
            print(f"获取备份信息失败: {e}")
            return None
    
    def _save_history(
        self,
        filename: str,
        backup_type: str,
        format: str,
        file_size: int = 0,
        status: str = 'completed',
        duration: float = 0,
        notes: str = ''
    ):
        """保存备份历史"""
        try:
            import json
            from datetime import datetime
            
            conn = self._get_history_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO backup_history 
                (filename, backup_type, format, file_size, status, 
                 completed_at, duration_seconds, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                filename,
                backup_type,
                format,
                file_size,
                status,
                datetime.utcnow().isoformat(),
                duration,
                notes
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"保存历史失败: {e}")
    
    def _get_history(self, filename: str) -> Optional[Dict[str, Any]]:
        """获取备份历史"""
        try:
            conn = self._get_history_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM backup_history WHERE filename = ?",
                (filename,)
            )
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            print(f"获取历史失败: {e}")
            return None
    
    def _delete_history(self, filename: str):
        """删除备份历史"""
        try:
            conn = self._get_history_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "DELETE FROM backup_history WHERE filename = ?",
                (filename,)
            )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"删除历史失败: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取备份统计信息"""
        try:
            # 统计文件
            total_files = 0
            total_size = 0
            
            for file_path in self.backup_dir.iterdir():
                if file_path.is_file():
                    total_files += 1
                    total_size += file_path.stat().st_size
            
            # 从历史数据库获取统计
            conn = self._get_history_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM backup_history WHERE status = 'completed'")
            completed_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM backup_history WHERE status = 'failed'")
            failed_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT MAX(completed_at) FROM backup_history WHERE status = 'completed'")
            last_backup = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_files': total_files,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024*1024), 2),
                'completed_backups': completed_count,
                'failed_backups': failed_count,
                'last_backup_at': last_backup
            }
            
        except Exception as e:
            print(f"获取统计失败: {e}")
            return {
                'total_files': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0,
                'completed_backups': 0,
                'failed_backups': 0,
                'last_backup_at': None
            }

    def encrypt_backup(self, filename: str) -> Dict[str, Any]:
        """
        加密备份文件
        
        Args:
            filename: 备份文件名
            
        Returns:
            加密结果
        """
        if not self.settings.get('enable_encryption'):
            return {'success': False, 'error': 'Encryption not enabled'}

        password = self.settings.get('encryption_password', '')
        if not password:
            return {'success': False, 'error': 'No encryption password set'}

        try:
            import subprocess
            backup_path = self.backup_dir / filename
            encrypted_path = self.backup_dir / f"{filename}.enc"

            # 使用openssl加密
            cmd = [
                'openssl', 'enc', '-aes-256-cbc',
                '-salt', '-pbkdf2',
                '-in', str(backup_path),
                '-out', str(encrypted_path),
                '-pass', f'pass:{password}'
            ]

            process = subprocess.run(cmd, capture_output=True, text=True)

            if process.returncode != 0:
                return {'success': False, 'error': process.stderr}

            print(f"[BackupManager] Backup encrypted: {filename}")
            return {
                'success': True,
                'encrypted_file': f"{filename}.enc",
                'original_size': backup_path.stat().st_size,
                'encrypted_size': encrypted_path.stat().st_size,
            }

        except Exception as e:
            print(f"[BackupManager] Encryption failed: {e}")
            return {'success': False, 'error': str(e)}

    def decrypt_backup(self, filename: str) -> Dict[str, Any]:
        """
        解密备份文件
        
        Args:
            filename: 加密的备份文件名
            
        Returns:
            解密结果
        """
        password = self.settings.get('encryption_password', '')
        if not password:
            return {'success': False, 'error': 'No encryption password set'}

        try:
            import subprocess
            encrypted_path = self.backup_dir / filename
            decrypted_path = self.backup_dir / filename.replace('.enc', '')

            # 使用openssl解密
            cmd = [
                'openssl', 'enc', '-aes-256-cbc',
                '-d', '-pbkdf2',
                '-in', str(encrypted_path),
                '-out', str(decrypted_path),
                '-pass', f'pass:{password}'
            ]

            process = subprocess.run(cmd, capture_output=True, text=True)

            if process.returncode != 0:
                return {'success': False, 'error': process.stderr}

            print(f"[BackupManager] Backup decrypted: {filename}")
            return {
                'success': True,
                'decrypted_file': decrypted_path.name,
            }

        except Exception as e:
            print(f"[BackupManager] Decryption failed: {e}")
            return {'success': False, 'error': str(e)}

    async def upload_to_cloud(self, filename: str) -> Dict[str, Any]:
        """
        上传备份到云存储
        
        Args:
            filename: 备份文件名
            
        Returns:
            上传结果
        """
        if not self.settings.get('cloud_storage_enabled'):
            return {'success': False, 'error': 'Cloud storage not enabled'}

        provider = self.settings.get('cloud_provider', 's3')

        try:
            if provider == 's3':
                return await self._upload_to_s3(filename)
            elif provider == 'oss':
                return await self._upload_to_oss(filename)
            elif provider == 'cos':
                return await self._upload_to_cos(filename)
            else:
                return {'success': False, 'error': f'Unsupported provider: {provider}'}

        except Exception as e:
            print(f"[BackupManager] Cloud upload failed: {e}")
            return {'success': False, 'error': str(e)}

    async def _upload_to_s3(self, filename: str) -> Dict[str, Any]:
        """上传到Amazon S3"""
        try:
            import boto3
            from botocore.exceptions import ClientError

            s3_client = boto3.client(
                's3',
                aws_access_key_id=self.settings.get('s3_access_key', ''),
                aws_secret_access_key=self.settings.get('s3_secret_key', ''),
                region_name=self.settings.get('s3_region', 'us-east-1')
            )

            bucket = self.settings.get('s3_bucket', '')
            if not bucket:
                return {'success': False, 'error': 'S3 bucket not configured'}

            backup_path = self.backup_dir / filename

            # 上传文件
            s3_key = f"backups/{filename}"
            s3_client.upload_file(str(backup_path), bucket, s3_key)

            print(f"[BackupManager] Uploaded to S3: {s3_key}")
            return {
                'success': True,
                'provider': 's3',
                'bucket': bucket,
                'key': s3_key,
                'url': f"https://{bucket}.s3.amazonaws.com/{s3_key}"
            }

        except ImportError:
            return {'success': False, 'error': 'boto3 not installed. Run: pip install boto3'}
        except Exception as e:
            print(f"[BackupManager] S3 upload error: {e}")
            return {'success': False, 'error': str(e)}

    async def _upload_to_oss(self, filename: str) -> Dict[str, Any]:
        """上传到阿里云OSS"""
        try:
            import oss2

            auth = oss2.Auth(
                self.settings.get('s3_access_key', ''),
                self.settings.get('s3_secret_key', '')
            )

            bucket = oss2.Bucket(
                auth,
                f"https://oss-{self.settings.get('s3_region', 'oss-cn-hangzhou')}.aliyuncs.com",
                self.settings.get('s3_bucket', '')
            )

            backup_path = self.backup_dir / filename

            # 上传文件
            oss_key = f"backups/{filename}"
            bucket.put_object_from_file(oss_key, str(backup_path))

            print(f"[BackupManager] Uploaded to OSS: {oss_key}")
            return {
                'success': True,
                'provider': 'oss',
                'bucket': self.settings.get('s3_bucket', ''),
                'key': oss_key,
            }

        except ImportError:
            return {'success': False, 'error': 'oss2 not installed. Run: pip install oss2'}
        except Exception as e:
            print(f"[BackupManager] OSS upload error: {e}")
            return {'success': False, 'error': str(e)}

    async def _upload_to_cos(self, filename: str) -> Dict[str, Any]:
        """上传到腾讯云COS"""
        try:
            from qcloud_cos import CosConfig, CosS3Client

            config = CosConfig(
                Region=self.settings.get('s3_region', 'ap-guangzhou'),
                SecretId=self.settings.get('s3_access_key', ''),
                SecretKey=self.settings.get('s3_secret_key', ''),
            )

            client = CosS3Client(config)
            bucket = self.settings.get('s3_bucket', '')

            backup_path = self.backup_dir / filename

            # 上传文件
            cos_key = f"backups/{filename}"
            with open(backup_path, 'rb') as fp:
                client.put_object(Bucket=bucket, Body=fp, Key=cos_key)

            print(f"[BackupManager] Uploaded to COS: {cos_key}")
            return {
                'success': True,
                'provider': 'cos',
                'bucket': bucket,
                'key': cos_key,
            }

        except ImportError:
            return {'success': False, 'error': 'cos-python-sdk-v5 not installed. Run: pip install cos-python-sdk-v5'}
        except Exception as e:
            print(f"[BackupManager] COS upload error: {e}")
            return {'success': False, 'error': str(e)}

    async def download_from_cloud(self, filename: str) -> Dict[str, Any]:
        """
        从云存储下载备份
        
        Args:
            filename: 备份文件名
            
        Returns:
            下载结果
        """
        if not self.settings.get('cloud_storage_enabled'):
            return {'success': False, 'error': 'Cloud storage not enabled'}

        provider = self.settings.get('cloud_provider', 's3')

        try:
            if provider == 's3':
                return await self._download_from_s3(filename)
            else:
                return {'success': False, 'error': f'Download not supported for: {provider}'}

        except Exception as e:
            print(f"[BackupManager] Cloud download failed: {e}")
            return {'success': False, 'error': str(e)}

    async def _download_from_s3(self, filename: str) -> Dict[str, Any]:
        """从S3下载备份"""
        try:
            import boto3

            s3_client = boto3.client(
                's3',
                aws_access_key_id=self.settings.get('s3_access_key', ''),
                aws_secret_access_key=self.settings.get('s3_secret_key', ''),
                region_name=self.settings.get('s3_region', 'us-east-1')
            )

            bucket = self.settings.get('s3_bucket', '')
            s3_key = f"backups/{filename}"
            local_path = self.backup_dir / filename

            # 下载文件
            s3_client.download_file(bucket, s3_key, str(local_path))

            print(f"[BackupManager] Downloaded from S3: {s3_key}")
            return {
                'success': True,
                'local_path': str(local_path),
            }

        except Exception as e:
            print(f"[BackupManager] S3 download error: {e}")
            return {'success': False, 'error': str(e)}

    async def one_click_restore(self, filename: str) -> Dict[str, Any]:
        """
        一键恢复备份(包括下载、解密、导入)
        
        Args:
            filename: 备份文件名
            
        Returns:
            恢复结果
        """
        result_steps = []

        try:
            # Step 1: 如果本地不存在，从云存储下载
            backup_path = self.backup_dir / filename
            if not backup_path.exists():
                print("[BackupManager] Step 1: Downloading from cloud...")
                download_result = await self.download_from_cloud(filename)
                if not download_result['success']:
                    return download_result
                result_steps.append({'step': 'download', 'status': 'success'})
            else:
                result_steps.append({'step': 'download', 'status': 'skipped', 'reason': 'File exists locally'})

            # Step 2: 如果是加密文件，先解密
            if filename.endswith('.enc'):
                print("[BackupManager] Step 2: Decrypting backup...")
                decrypt_result = self.decrypt_backup(filename)
                if not decrypt_result['success']:
                    return decrypt_result
                filename = decrypt_result['decrypted_file']
                result_steps.append({'step': 'decrypt', 'status': 'success'})
            else:
                result_steps.append({'step': 'decrypt', 'status': 'skipped', 'reason': 'Not encrypted'})

            # Step 3: 导入数据库
            print("[BackupManager] Step 3: Importing database...")
            import_result = await self.import_database(
                filename=filename,
                drop_existing=True,
                notes='One-click restore'
            )

            if not import_result['success']:
                return import_result

            result_steps.append({'step': 'import', 'status': 'success'})

            print("[BackupManager] One-click restore completed successfully")
            return {
                'success': True,
                'steps': result_steps,
                'message': 'Database restored successfully',
                'duration': import_result.get('duration', 0)
            }

        except Exception as e:
            print(f"[BackupManager] One-click restore failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'steps': result_steps
            }

    def get_settings_ui(self) -> Dict[str, Any]:
        """返回设置界面配置"""
        return {
            'fields': [
                {
                    'key': 'auto_backup_enabled',
                    'type': 'boolean',
                    'label': '启用自动备份',
                },
                {
                    'key': 'auto_backup_interval',
                    'type': 'number',
                    'label': '自动备份间隔(小时)',
                    'min': 1,
                    'max': 168,
                },
                {
                    'key': 'max_backups',
                    'type': 'number',
                    'label': '最大备份数量',
                    'min': 3,
                    'max': 50,
                },
                {
                    'key': 'include_files',
                    'type': 'boolean',
                    'label': '包含媒体文件',
                },
                {
                    'key': 'enable_encryption',
                    'type': 'boolean',
                    'label': '启用备份加密',
                },
                {
                    'key': 'encryption_password',
                    'type': 'password',
                    'label': '加密密码',
                },
                {
                    'key': 'cloud_storage_enabled',
                    'type': 'boolean',
                    'label': '启用云存储同步',
                },
                {
                    'key': 'cloud_provider',
                    'type': 'select',
                    'label': '云存储提供商',
                    'options': [
                        {'value': 's3', 'label': 'Amazon S3'},
                        {'value': 'oss', 'label': '阿里云OSS'},
                        {'value': 'cos', 'label': '腾讯云COS'},
                    ],
                },
                {
                    'key': 's3_bucket',
                    'type': 'text',
                    'label': 'Bucket名称',
                },
                {
                    'key': 's3_access_key',
                    'type': 'text',
                    'label': 'Access Key',
                },
                {
                    'key': 's3_secret_key',
                    'type': 'password',
                    'label': 'Secret Key',
                },
                {
                    'key': 's3_region',
                    'type': 'text',
                    'label': '区域',
                },
                {
                    'key': 'auto_sync_to_cloud',
                    'type': 'boolean',
                    'label': '自动同步到云存储',
                },
            ],
            'actions': [
                {
                    'type': 'button',
                    'label': '立即备份',
                    'action': 'create_backup',
                    'variant': 'default',
                },
                {
                    'type': 'button',
                    'label': '测试云存储连接',
                    'action': 'test_cloud_connection',
                    'variant': 'outline',
                },
            ]
        }


# 全局实例
postgresql_backup_plugin = PostgreSQLBackupPlugin()
