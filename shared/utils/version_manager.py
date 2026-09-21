"""
版本管理器
统一版本管理 — 文件格式为 **INI**（``[RELEASE]`` / ``[DATABASE]`` / ``[AUTHOR]``），
读取时兼容历史 JSON（2026-09-21 批次 18 修正，见 ``_save`` 的说明）。
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class VersionManager:
    """版本管理器（JSON 格式优先，向后兼容 configparser）"""

    def __init__(self, version_file_path: Optional[str] = None):
        if version_file_path is None:
            current = Path(os.path.dirname(os.path.abspath(__file__)))
            project_root = current.parent.parent
            self.version_file = project_root / 'version.txt'
        else:
            self.version_file = Path(version_file_path)
        
        self._data = self._load()

    def _load(self) -> dict:
        """加载版本信息（JSON 优先，回退到 configparser）"""
        if not self.version_file.exists():
            return self._create_default()

        raw = self.version_file.read_text(encoding='utf-8')

        # 尝试 JSON 解析
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # 回退：configparser 格式
        import configparser
        cp = configparser.ConfigParser()
        try:
            cp.read_string(raw)
            data = {}
            for section in cp.sections():
                data[section.lower()] = dict(cp[section])
            return data
        except Exception:
            return self._create_default()

    def _create_default(self) -> dict:
        data = {
            'release': {'version': '0.1.0', 'build_time': datetime.now().isoformat()},
            'database': {'migration': 'base', 'status': 'up_to_date'},
            'author': {'maintainer': 'Athenavi', 'repository': 'https://github.com/Athenavi/fast_blog'},
        }
        self._save(data)
        return data

    def _save(self, data: dict = None):
        """写回 **INI** 格式（与仓库现状、scripts/ 里的读取方保持一致）

        历史缺陷：本模块曾"读 INI、写 JSON"，于是 `bump_version()` 调用一次就把
        ``version.txt`` 变成 JSON，而 ``scripts/build_release.py``、``scripts/cli.py``
        以及部署脚本仍按 INI 解析 —— 版本号随即读不到（升级演练时实测复现）。
        现在统一写 INI；读取侧继续兼容 JSON，历史上已被改写成 JSON 的文件也能读。
        """
        if data is None:
            data = self._data
        lines: list[str] = []
        for section in ('release', 'database', 'author'):
            values = data.get(section) or {}
            lines.append(f'[{section.upper()}]')
            for key, value in values.items():
                lines.append(f'{key} = {value}')
            lines.append('')
        self.version_file.write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')

    # ── 读取 ──

    def get_version(self) -> str:
        return self._data.get('release', {}).get('version', '0.0.0')

    def get_release_info(self) -> Dict[str, str]:
        return self._data.get('release', {})

    def get_database_info(self) -> Dict[str, str]:
        return self._data.get('database', {})

    def get_author_info(self) -> Dict[str, str]:
        return self._data.get('author', {})

    def get_all(self) -> Dict[str, Dict[str, str]]:
        return {
            'release': self.get_release_info(),
            'database': self.get_database_info(),
            'author': self.get_author_info(),
        }

    def get_backend_version(self) -> dict:
        return self._data.get('release', {})

    def get_frontend_version(self) -> dict:
        return self._data.get('release', {})

    def get_all_versions(self) -> dict:
        return {'BACKEND': self.get_backend_version(), 'FRONTEND': self.get_frontend_version()}

    # ── 写入 ──

    def bump_version(self, version: str):
        self._data.setdefault('release', {})['version'] = version
        self._data['release']['build_time'] = datetime.now().isoformat()
        self._save()

    def update_database(self, migration: str, status: str = 'up_to_date'):
        self._data.setdefault('database', {})['migration'] = migration
        self._data['database']['status'] = status
        self._save()


version_manager = VersionManager()
