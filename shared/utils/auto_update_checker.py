#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto update checker - checks GitHub Releases and local update packages.
"""

from datetime import datetime
from typing import Optional, Dict

import httpx
import asyncio

from shared.logging import default_logger as logger


class AutoUpdateChecker:
    """Auto update checker (simplified)."""

    def __init__(self):
        self.github_repo = "Athenavi/fast_blog"
        self.current_version = "0.0.0"
        self.last_check_time = None

    async def check_github_releases(self) -> Optional[Dict]:
        """Check GitHub Releases for the latest version."""
        try:
            url = f"https://api.github.com/repos/{self.github_repo}/releases/latest"
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'FastBlog-Update-Checker'
            }

            response = httpx.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            latest_version = data.get('tag_name', '').lstrip('vV')
            if not latest_version:
                return None

            return {
                'version': latest_version,
                'name': data.get('name', ''),
                'published_at': data.get('published_at', ''),
                'html_url': data.get('html_url', ''),
                'body': data.get('body', '')
            }

        except Exception as e:
            logger.error(f"Failed to check GitHub Releases: {e}")
            return None

    async def check_local_releases(self) -> Optional[str]:
        """Check local releases directory for the latest update package."""
        try:
            from pathlib import Path

            project_root = Path(__file__).resolve().parent.parent.parent
            releases_dir = project_root / "releases"

            if not releases_dir.exists():
                return None

            update_packages = list(releases_dir.glob("update_*.zip"))
            if not update_packages:
                return None

            # Sort by filename to get the latest version
            update_packages.sort(key=lambda x: x.name, reverse=True)
            version = update_packages[0].stem.replace('update_', '')
            logger.info(f"Latest local update package: {version}")
            return version

        except Exception as e:
            logger.error(f"Failed to check local releases: {e}")
            return None

    @staticmethod
    def compare_versions(current: str, latest: str) -> bool:
        """Compare version strings; returns True if latest > current."""
        try:
            def parse_version(v: str):
                v = v.lstrip('vV')
                parts = v.split('.')
                return [int(p) for p in parts if p.isdigit()]

            current_parts = parse_version(current)
            latest_parts = parse_version(latest)

            # Pad to equal length
            max_len = max(len(current_parts), len(latest_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            latest_parts.extend([0] * (max_len - len(latest_parts)))

            # Compare digit by digit
            for c, l in zip(current_parts, latest_parts):
                if l > c:
                    return True
                elif l < c:
                    return False

            return False

        except Exception as e:
            logger.error(f"Version comparison failed: {e}")
            return False

    async def check_for_updates(self) -> Dict:
        """Run update check."""
        logger.info("Checking for updates...")
        self.last_check_time = datetime.now()

        # Get current version
        try:
            from shared.utils.version_manager import version_manager
            backend_info = version_manager.get_backend_version()
            self.current_version = backend_info.get('version', '0.0.0')
        except Exception as e:
            logger.error(f"Failed to get current version: {e}")
            self.current_version = "0.0.0"

        # Check both GitHub and local releases concurrently
        github_result, local_version = await asyncio.gather(
            self.check_github_releases(),
            self.check_local_releases()
        )

        result = {
            'has_update': False,
            'current_version': self.current_version,
            'github_latest': None,
            'local_latest': local_version,
            'check_time': self.last_check_time.isoformat(),
            'message': 'Already up to date.',
        }

        # Process GitHub result
        if github_result:
            result['github_latest'] = github_result['version']
            if self.compare_versions(self.current_version, github_result['version']):
                result['has_update'] = True
                result['message'] = f"New version available: {github_result['version']}"
                result['release_info'] = github_result

        # Check local updates
        if not result['has_update'] and local_version:
            if self.compare_versions(self.current_version, local_version):
                result['has_update'] = True
                result['message'] = f"Local update package found: {local_version}"

        logger.info(f"Update check result: {result['message']}")
        return result


# Global singleton
auto_update_checker = AutoUpdateChecker()


async def check_updates_now() -> Dict:
    """Convenience function: check for updates immediately."""
    return await auto_update_checker.check_for_updates()
