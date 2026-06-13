"""
版本管理器
统一版本管理，不再区分前后端
"""
import configparser
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class VersionManager:
    """版本管理器"""

    def __init__(self, version_file_path: Optional[str] = None):
        if version_file_path is None:
            # 定位到项目根目录的 version.txt
            current = Path(os.path.dirname(os.path.abspath(__file__)))  # shared/utils/
            project_root = current.parent.parent  # 项目根目录
            self.version_file = project_root / 'version.txt'
        else:
            self.version_file = Path(version_file_path)

        self.config = configparser.ConfigParser()
        self._load()

    def _load(self):
        if self.version_file.exists():
            self.config.read(self.version_file, encoding='utf-8')
        else:
            self._create_default()

    def _create_default(self):
        self.config['RELEASE'] = {
            'version': '0.1.0',
            'build_time': datetime.now().isoformat(),
        }
        self.config['DATABASE'] = {
            'migration': 'base',
            'status': 'up_to_date',
        }
        self.config['AUTHOR'] = {
            'maintainer': 'Athenavi',
            'repository': 'https://github.com/Athenavi/fast_blog',
        }
        self.save()

    def save(self):
        with open(self.version_file, 'w', encoding='utf-8') as f:
            self.config.write(f)

    # ── 读取 ──

    def get_version(self) -> str:
        return self.config.get('RELEASE', 'version', fallback='0.0.0')

    def get_release_info(self) -> Dict[str, str]:
        return dict(self.config['RELEASE']) if 'RELEASE' in self.config else {}

    def get_database_info(self) -> Dict[str, str]:
        return dict(self.config['DATABASE']) if 'DATABASE' in self.config else {}

    def get_author_info(self) -> Dict[str, str]:
        return dict(self.config['AUTHOR']) if 'AUTHOR' in self.config else {}

    def get_all(self) -> Dict[str, Dict[str, str]]:
        return {
            'release': self.get_release_info(),
            'database': self.get_database_info(),
            'author': self.get_author_info(),
        }

    # ── 写入 ──

    def bump_version(self, version: str):
        if 'RELEASE' not in self.config:
            self.config['RELEASE'] = {}
        self.config['RELEASE']['version'] = version
        self.config['RELEASE']['build_time'] = datetime.now().isoformat()
        self.save()

    def update_database(self, migration: str, status: str = 'up_to_date'):
        if 'DATABASE' not in self.config:
            self.config['DATABASE'] = {}
        self.config['DATABASE']['migration'] = migration
        self.config['DATABASE']['status'] = status
        self.save()


version_manager = VersionManager()
