#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backup Management Module - Enhanced Version
Manages system backups, database backups, automatic scheduling, and cloud storage integration.
"""

import hashlib
import json

import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from shared.logging import default_logger as logger


class BackupManager:
    """Backup Manager (Enhanced Edition)

    Features:
    1. Automatic scheduled backups
    2. Incremental backup support
    3. Cloud storage integration (S3/OSS)
    4. Backup verification
    5. Retention policy management
    """

    def __init__(self, backup_dir: str = "backups/update_backups", db_backup_dir: str = "backups/database"):
        self.backup_dir = Path(backup_dir)
        self.db_backup_dir = Path(db_backup_dir)
        self.backup_info_file = self.backup_dir / "backups_index.json"
        self.backups = []
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.db_backup_dir.mkdir(parents=True, exist_ok=True)
        self._load_backups()

        # Initialize scheduler
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

        # Cloud storage configuration
        self.cloud_config = {
            'enabled': False,
            'provider': 's3',  # s3, oss, cos
            'bucket': '',
            'access_key': '',
            'secret_key': '',
            'region': '',
        }

        # Backup retention policy
        self.retention_policy = {
            'daily': 7,  # Keep 7 daily backups
            'weekly': 4,  # Keep 4 weekly backups
            'monthly': 12,  # Keep 12 monthly backups
        }
    
    def _load_backups(self):
        """Load backup index"""
        if self.backup_info_file.exists():
            try:
                with open(self.backup_info_file, 'r', encoding='utf-8') as f:
                    self.backups = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load backup index: {e}")
                self.backups = []
        else:
            self._scan_existing_backups()
    
    def _scan_existing_backups(self):
        """Scan existing backup directories"""
        try:
            if not self.backup_dir.exists():
                return
            
            for backup_path in self.backup_dir.iterdir():
                if backup_path.is_dir() and backup_path.name.startswith('backup_'):
                    info_file = backup_path / "backup_info.json"
                    if info_file.exists():
                        try:
                            with open(info_file, 'r', encoding='utf-8') as f:
                                info = json.load(f)
                                info['path'] = str(backup_path)
                                self.backups.append(info)
                        except Exception:
                            pass
            
            self.backups.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            self._save_backups()
        except Exception as e:
            logger.error(f"Failed to scan backups: {e}")
    
    def _save_backups(self):
        """Save backup index"""
        try:
            with open(self.backup_info_file, 'w', encoding='utf-8') as f:
                json.dump(self.backups, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save backup index: {e}")
    
    def create(self, source_path: str, version: str = None) -> Optional[Dict]:
        """Create backup"""
        try:
            timestamp = int(datetime.now().timestamp())
            backup_name = f"backup_{timestamp}"
            backup_path = self.backup_dir / backup_name
            
            logger.info(f"Starting backup creation: {backup_path}")
            shutil.copytree(source_path, backup_path, dirs_exist_ok=True)
            
            backup_info = {
                'timestamp': timestamp,
                'datetime': datetime.fromtimestamp(timestamp).isoformat(),
                'version': version or 'unknown',
                'path': str(backup_path),
                'status': 'success'
            }
            
            # Save backup info
            info_file = backup_path / "backup_info.json"
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, indent=2, ensure_ascii=False)
            
            self.backups.append(backup_info)
            self._save_backups()
            
            logger.info(f"Backup created successfully: {backup_path}")
            return backup_info
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def get(self, backup_id: str) -> Optional[Dict]:
        """Get backup info by ID"""
        for backup in self.backups:
            if str(backup.get('timestamp')) == backup_id or backup.get('path') == backup_id:
                return backup
        return None
    
    def list(self, limit: int = 10) -> List[Dict]:
        """List backups"""
        return self.backups[:limit]
    
    def restore(self, backup_id: str, target_path: str) -> bool:
        """Restore backup"""
        try:
            backup = self.get(backup_id)
            if not backup:
                logger.error(f"Backup not found: {backup_id}")
                return False
            
            backup_path = Path(backup['path'])
            if not backup_path.exists():
                logger.error(f"Backup file does not exist: {backup_path}")
                return False
            
            logger.info(f"Starting restore: {backup_path} -> {target_path}")
            
            target = Path(target_path)
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(backup_path, target)
            
            logger.info(f"Backup restored successfully: {target}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False
    
    def delete(self, backup_id: str) -> bool:
        """Delete backup"""
        try:
            backup = self.get(backup_id)
            if not backup:
                logger.error(f"Backup not found: {backup_id}")
                return False
            
            backup_path = Path(backup['path'])
            if backup_path.exists():
                shutil.rmtree(backup_path)
                logger.info(f"Deleted backup files: {backup_path}")
            
            self.backups = [b for b in self.backups if b.get('timestamp') != backup.get('timestamp')]
            self._save_backups()
            
            logger.info(f"Backup removed from index: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete backup: {e}")
            return False

    # ==================== Automated Backup Features ====================

    def schedule_auto_backup(self, cron_expression: str = "0 2 * * *", backup_type: str = "full"):
        """
        Set up automatic backup scheduling
        
        Args:
            cron_expression: Cron expression, default is daily at 2 AM
            backup_type: Backup type (full/incremental)
        """
        try:
            # Parse cron expression
            trigger = CronTrigger.from_crontab(cron_expression)

            # Add scheduled job
            self.scheduler.add_job(
                func=self._auto_backup_job,
                trigger=trigger,
                id='auto_backup',
                name='Auto Database Backup',
                kwargs={'backup_type': backup_type},
                replace_existing=True
            )

            logger.info(f"Auto backup scheduled: {cron_expression}, type: {backup_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to set auto backup schedule: {e}")
            return False

    def _auto_backup_job(self, backup_type: str = "full"):
        """Auto backup job"""
        try:
            logger.info(f"Starting auto backup job: {backup_type}")

            # Execute backup
            if backup_type == "incremental":
                result = self.create_incremental_backup()
            else:
                result = self.create_full_backup()

            if result:
                logger.info(f"Auto backup succeeded: {result.get('name')}")

                # Upload to cloud storage
                if self.cloud_config.get('enabled'):
                    self.upload_to_cloud(result['path'])

                # Clean up expired backups
                self.cleanup_old_backups()
            else:
                logger.error("Auto backup failed")

        except Exception as e:
            logger.error(f"Auto backup job execution failed: {e}", exc_info=True)

    def create_full_backup(self, source_paths: List[str] = None) -> Optional[Dict]:
        """
        Create a full backup
        
        Args:
            source_paths: List of source paths to back up
            
        Returns:
            Backup info dictionary
        """
        try:
            timestamp = datetime.now()
            backup_name = f"full_backup_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            backup_path = self.backup_dir / backup_name
            backup_path.mkdir(parents=True, exist_ok=True)

            # If no source paths specified, back up the entire project
            if not source_paths:
                source_paths = [
                    'apps',
                    'config',
                    'plugins',
                    'themes',
                    '.env',
                ]

            # Copy files
            for source in source_paths:
                src_path = Path(source)
                if src_path.exists():
                    dest_path = backup_path / src_path.name
                    if src_path.is_dir():
                        shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src_path, dest_path)

            # Create backup metadata
            backup_info = {
                'id': backup_name,
                'name': backup_name,
                'type': 'full',
                'timestamp': int(timestamp.timestamp()),
                'datetime': timestamp.isoformat(),
                'path': str(backup_path),
                'size': self._get_directory_size(backup_path),
                'status': 'success',
                'source_paths': source_paths,
            }

            # Save metadata
            info_file = backup_path / "backup_info.json"
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, indent=2, ensure_ascii=False)

            # Add to index
            self.backups.insert(0, backup_info)
            self._save_backups()

            logger.info(f"Full backup created successfully: {backup_name}")
            return backup_info

        except Exception as e:
            logger.error(f"Failed to create full backup: {e}", exc_info=True)
            return None

    def create_incremental_backup(self, last_backup_id: str = None) -> Optional[Dict]:
        """
        Create an incremental backup
        
        Args:
            last_backup_id: Previous backup ID, if None uses the most recent backup
            
        Returns:
            Backup info dictionary
        """
        try:
            # Get last backup
            if not last_backup_id and self.backups:
                last_backup = self.backups[0]
                last_backup_id = last_backup.get('id')

            if not last_backup_id:
                logger.warning("No historical backup found, executing full backup instead")
                return self.create_full_backup()

            last_backup = self.get(last_backup_id)
            if not last_backup:
                logger.error(f"Backup not found: {last_backup_id}")
                return None

            timestamp = datetime.now()
            backup_name = f"incremental_backup_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            backup_path = self.backup_dir / backup_name
            backup_path.mkdir(parents=True, exist_ok=True)

            # Compare file changes
            changed_files = self._detect_changes(
                Path(last_backup['path']),
                Path('.'),
                backup_path
            )

            if not changed_files:
                logger.info("No file changes detected, skipping incremental backup")
                shutil.rmtree(backup_path)
                return None

            # Create backup metadata
            backup_info = {
                'id': backup_name,
                'name': backup_name,
                'type': 'incremental',
                'base_backup': last_backup_id,
                'timestamp': int(timestamp.timestamp()),
                'datetime': timestamp.isoformat(),
                'path': str(backup_path),
                'size': self._get_directory_size(backup_path),
                'status': 'success',
                'changed_files_count': len(changed_files),
            }

            # Save metadata
            info_file = backup_path / "backup_info.json"
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, indent=2, ensure_ascii=False)

            # Add to index
            self.backups.insert(0, backup_info)
            self._save_backups()

            logger.info(f"Incremental backup created successfully: {backup_name}, changed files: {len(changed_files)}")
            return backup_info

        except Exception as e:
            logger.error(f"Failed to create incremental backup: {e}", exc_info=True)
            return None

    def _detect_changes(self, base_path: Path, current_path: Path, diff_path: Path) -> List[str]:
        """
        Detect file changes
        
        Returns:
            List of changed files
        """
        changed_files = []

        try:
            # Scan current directory
            for file_path in current_path.rglob('*'):
                if not file_path.is_file():
                    continue

                # Skip hidden files and specific directories
                if any(part.startswith('.') or part in ['node_modules', '__pycache__', '.git']
                       for part in file_path.parts):
                    continue

                # Compute relative path
                rel_path = file_path.relative_to(current_path)
                base_file = base_path / rel_path

                # Check if file exists or has changed
                if not base_file.exists():
                    # New file
                    dest = diff_path / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, dest)
                    changed_files.append(str(rel_path))
                else:
                    # Check if file content changed
                    if self._file_hash(file_path) != self._file_hash(base_file):
                        dest = diff_path / rel_path
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file_path, dest)
                        changed_files.append(str(rel_path))

        except Exception as e:
            logger.error(f"Failed to detect file changes: {e}")

        return changed_files

    def _file_hash(self, file_path: Path) -> str:
        """Calculate file hash value"""
        hasher = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except:
            return ""

    def _get_directory_size(self, path: Path) -> int:
        """Calculate directory size"""
        total_size = 0
        try:
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except:
            pass
        return total_size

    # ==================== Cloud Storage Integration ====================

    def configure_cloud_storage(self, config: Dict):
        """
        Configure cloud storage
        
        Args:
            config: Cloud storage configuration
        """
        self.cloud_config.update(config)
        logger.info(f"Cloud storage configuration updated: {config.get('provider')}")

    def upload_to_cloud(self, backup_path: str) -> bool:
        """
        Upload backup to cloud storage
        
        Args:
            backup_path: Backup file path
            
        Returns:
            Whether successful
        """
        if not self.cloud_config.get('enabled'):
            logger.warning("Cloud storage is not enabled")
            return False

        try:
            provider = self.cloud_config.get('provider')

            if provider == 's3':
                return self._upload_to_s3(backup_path)
            elif provider == 'oss':
                return self._upload_to_oss(backup_path)
            else:
                logger.error(f"Unsupported cloud storage provider: {provider}")
                return False

        except Exception as e:
            logger.error(f"Failed to upload to cloud storage: {e}")
            return False

    def _upload_to_s3(self, backup_path: str) -> bool:
        """Upload to AWS S3"""
        try:
            import boto3
            from botocore.exceptions import ClientError

            s3_client = boto3.client(
                's3',
                aws_access_key_id=self.cloud_config['access_key'],
                aws_secret_access_key=self.cloud_config['secret_key'],
                region_name=self.cloud_config.get('region', 'us-east-1')
            )

            backup_file = Path(backup_path)
            object_key = f"backups/{backup_file.name}.tar.gz"

            # Compress backup
            tar_path = backup_file.with_suffix('.tar.gz')
            shutil.make_archive(str(backup_file), 'gztar', backup_file.parent, backup_file.name)

            # Upload
            s3_client.upload_file(
                str(tar_path),
                self.cloud_config['bucket'],
                object_key
            )

            logger.info(f"Backup uploaded to S3: {object_key}")
            return True

        except ImportError:
            logger.error("boto3 library not installed, please run: pip install boto3")
            return False
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return False

    def _upload_to_oss(self, backup_path: str) -> bool:
        """Upload to Alibaba Cloud OSS"""
        try:
            import oss2

            auth = oss2.Auth(
                self.cloud_config['access_key'],
                self.cloud_config['secret_key']
            )
            bucket = oss2.Bucket(
                auth,
                f"https://oss-{self.cloud_config.get('region', 'oss-cn-hangzhou')}.aliyuncs.com",
                self.cloud_config['bucket']
            )

            backup_file = Path(backup_path)
            object_key = f"backups/{backup_file.name}.tar.gz"

            # Compress and upload
            tar_path = backup_file.with_suffix('.tar.gz')
            shutil.make_archive(str(backup_file), 'gztar', backup_file.parent, backup_file.name)

            bucket.put_object_from_file(object_key, str(tar_path))

            logger.info(f"Backup uploaded to OSS: {object_key}")
            return True

        except ImportError:
            logger.error("oss2 library not installed, please run: pip install oss2")
            return False
        except Exception as e:
            logger.error(f"OSS upload failed: {e}")
            return False

    # ==================== Backup Cleanup Policy ====================

    def cleanup_old_backups(self):
        """Clean up old backups based on retention policy"""
        try:
            now = datetime.now()
            deleted_count = 0

            for backup in self.backups[:]:
                backup_time = datetime.fromisoformat(backup.get('datetime', ''))
                age_days = (now - backup_time).days

                should_delete = False

                # Daily backups exceed retention period
                if age_days > self.retention_policy['daily']:
                    should_delete = True

                # Weekly backups exceed retention period
                elif age_days > self.retention_policy['weekly'] * 7:
                    should_delete = True

                # Monthly backups exceed retention period
                elif age_days > self.retention_policy['monthly'] * 30:
                    should_delete = True

                if should_delete:
                    self.delete(backup.get('id'))
                    deleted_count += 1

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired backups")

        except Exception as e:
            logger.error(f"Failed to clean up old backups: {e}")

    # ==================== Backup Verification ====================

    def verify_backup(self, backup_id: str) -> Dict:
        """
        Verify backup integrity
        
        Args:
            backup_id: Backup ID
            
        Returns:
            Verification result
        """
        try:
            backup = self.get(backup_id)
            if not backup:
                return {'valid': False, 'error': 'Backup not found'}

            backup_path = Path(backup['path'])
            if not backup_path.exists():
                return {'valid': False, 'error': 'Backup file does not exist'}

            # Check metadata file
            info_file = backup_path / "backup_info.json"
            if not info_file.exists():
                return {'valid': False, 'error': 'Backup metadata missing'}

            # Verify metadata
            with open(info_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # Check file size
            actual_size = self._get_directory_size(backup_path)
            expected_size = backup.get('size', 0)

            size_match = abs(actual_size - expected_size) < 1024  # Allow 1KB error

            return {
                'valid': True,
                'backup_id': backup_id,
                'size_check': size_match,
                'actual_size': actual_size,
                'expected_size': expected_size,
                'metadata_valid': True,
            }

        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return {'valid': False, 'error': str(e)}


# Global singleton
backup_manager = BackupManager()
