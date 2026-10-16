"""
站点健康检查服务
类似 WordPress 的 Site Health：系统 / 数据库 / 存储 / 安全 / 性能五组检查 + 总体评分。

改造说明：数据库检查原先定义了探测协程却**从未调用**，永远返回「正常」（相当于占位实现）。
现在真实执行 ``SELECT 1``，并把 ``run_full_check`` 改成 async。
"""
import os
import platform
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SiteHealthService:
    """站点健康检查服务"""

    def __init__(self):
        # 项目根目录 = site_health.py 向上 4 层: shared/services/system/site_health.py → project root
        self.base_dir = Path(__file__).resolve().parent.parent.parent.parent

    async def run_full_check(self, db: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """
        运行完整的健康检查

        Args:
            db: 可选的数据库会话（复用调用方的连接，避免健康检查自己再开一条）

        Returns:
            包含所有检查项的结果
        """
        checks = {
            'system': self.check_system_info(),
            'database': await self.check_database(db),
            'storage': self.check_storage(),
            'security': self.check_security(),
            'performance': self.check_performance(),
        }
        
        # 计算总体评分
        total_score = 0
        total_items = 0
        
        for category, items in checks.items():
            for item in items:
                if 'score' in item:
                    total_score += item['score']
                    total_items += 1
        
        overall_score = round((total_score / max(total_items, 1)) * 100)
        
        return {
            'overall_score': overall_score,
            'status': 'good' if overall_score >= 80 else 'warning' if overall_score >= 60 else 'critical',
            'checks': checks,
            'timestamp': datetime.now().isoformat(),
        }
    
    def check_system_info(self) -> List[Dict[str, Any]]:
        """检查系统信息"""
        results = []
        
        # Python 版本（项目要求 3.11+，见 pyproject requires-python）
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        results.append({
            'name': 'Python版本',
            'value': python_version,
            'status': 'pass' if sys.version_info >= (3, 11) else 'warning',
            'score': 1.0 if sys.version_info >= (3, 11) else 0.5,
            'recommendation': '建议使用 Python 3.11 或更高版本' if sys.version_info < (3, 11) else None,
        })
        
        # 操作系统
        results.append({
            'name': '操作系统',
            'value': f"{platform.system()} {platform.release()}",
            'status': 'info',
            'score': 1.0,
        })
        
        # 磁盘空间
        try:
            disk_usage = shutil.disk_usage(self.base_dir)
            free_gb = disk_usage.free / (1024 ** 3)
            results.append({
                'name': '可用磁盘空间',
                'value': f"{free_gb:.2f} GB",
                'status': 'pass' if free_gb > 1 else 'warning' if free_gb > 0.5 else 'fail',
                'score': 1.0 if free_gb > 1 else 0.5 if free_gb > 0.5 else 0.0,
                'recommendation': '磁盘空间不足,建议清理或扩容' if free_gb < 1 else None,
            })
        except Exception as e:
            results.append({
                'name': '磁盘空间',
                'value': '无法检测',
                'status': 'warning',
                'score': 0.5,
                'error': str(e),
            })
        
        return results
    
    async def check_database(self, db: Optional[AsyncSession] = None) -> List[Dict[str, Any]]:
        """检查数据库状态（真实执行一次 ``SELECT 1``）"""
        results = []

        # 数据库引擎（仅支持 PostgreSQL）
        results.append({
            'name': '数据库引擎',
            'value': 'PostgreSQL',
            'status': 'pass',
            'score': 1.0,
        })

        try:
            if db is not None:
                await db.execute(text('SELECT 1'))
            else:
                from src.utils.database.unified_manager import db_manager

                async with db_manager.get_session() as session:
                    await session.execute(text('SELECT 1'))
        except Exception as e:
            results.append({
                'name': '数据库连接',
                'value': '失败',
                'status': 'fail',
                'score': 0.0,
                'error': str(e),
                'recommendation': '检查数据库配置和连接',
            })
        else:
            results.append({
                'name': '数据库连接',
                'value': '正常',
                'status': 'pass',
                'score': 1.0,
            })

        return results
    
    def check_storage(self) -> List[Dict[str, Any]]:
        """检查存储目录"""
        results = []
        
        # 检查关键目录
        critical_dirs = [
            ('media', '媒体文件目录'),
            ('static', '静态文件目录'),
            ('storage/objects', '对象存储目录'),
            ('logs', '日志目录'),
        ]
        
        for dir_name, description in critical_dirs:
            dir_path = self.base_dir / dir_name
            exists = dir_path.exists()
            writable = os.access(dir_path, os.W_OK) if exists else False
            
            status = 'pass' if exists and writable else 'fail' if not exists else 'warning'
            score = 1.0 if exists and writable else 0.0 if not exists else 0.5
            
            results.append({
                'name': description,
                'value': f"{'存在且可写' if exists and writable else '存在但不可写' if exists else '不存在'}",
                'status': status,
                'score': score,
                'path': str(dir_path),
                'recommendation': f'请创建目录并设置权限: {dir_path}' if not exists else None,
            })
        
        return results
    
    def check_security(self) -> List[Dict[str, Any]]:
        """检查安全配置"""
        results = []
        
        # DEBUG模式
        debug_mode = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')
        results.append({
            'name': 'DEBUG模式',
            'value': '开启' if debug_mode else '关闭',
            'status': 'fail' if debug_mode else 'pass',
            'score': 0.0 if debug_mode else 1.0,
            'recommendation': '生产环境必须关闭DEBUG模式' if debug_mode else None,
        })
        
        # SECRET_KEY：未设置 / 仍是占位值 / 过短 都算不安全
        secret_key = os.getenv('SECRET_KEY', '')
        if not secret_key:
            try:
                from shared.config.settings import app_config

                secret_key = getattr(app_config, 'secret_key', '') or ''
            except Exception:  # noqa: BLE001 - 配置读取失败时按未设置处理
                secret_key = ''
        weak = (
            not secret_key
            or secret_key.startswith('test-secret-key')
            or 'insecure' in secret_key.lower()
            or len(secret_key) < 32
        )
        results.append({
            'name': 'SECRET_KEY',
            'value': '未设置或过弱' if weak else '已配置',
            'status': 'fail' if weak else 'pass',
            'score': 0.0 if weak else 1.0,
            'recommendation': '请设置至少 32 位随机 SECRET_KEY（见 .env.example）' if weak else None,
        })
        
        # CORS配置
        cors_all = os.getenv('CORS_ALLOW_ALL_ORIGINS', 'False').lower() in ('true', '1', 'yes')
        results.append({
            'name': 'CORS配置',
            'value': '允许所有来源' if cors_all else '限制来源',
            'status': 'warning' if cors_all else 'pass',
            'score': 0.5 if cors_all else 1.0,
            'recommendation': '生产环境应限制CORS来源' if cors_all else None,
        })
        
        return results
    
    def check_performance(self) -> List[Dict[str, Any]]:
        """检查性能配置"""
        results = []
        
        # 缓存配置：本项目用 Redis 作为共享缓存（未配置时只有进程内缓存）
        redis_url = os.getenv('REDIS_URL', '') or os.getenv('REDIS_HOST', '')
        cache_type = os.getenv('CACHE_TYPE', '')
        cache_enabled = bool(redis_url) or cache_type.lower() not in ('', 'none', 'simple', 'null')
        results.append({
            'name': '缓存系统',
            'value': 'Redis 已配置' if cache_enabled else '仅进程内缓存',
            'status': 'warning' if not cache_enabled else 'pass',
            'score': 0.5 if not cache_enabled else 1.0,
            'recommendation': '多 worker 部署建议配置 REDIS_URL 以共享缓存' if not cache_enabled else None,
        })
        
        # 上传限制
        upload_limit = int(os.getenv('UPLOAD_LIMIT', 62914560))
        upload_limit_mb = upload_limit / (1024 * 1024)
        results.append({
            'name': '上传限制',
            'value': f"{upload_limit_mb:.0f} MB",
            'status': 'info',
            'score': 1.0,
        })
        
        return results
    
    async def generate_report(self, format: str = 'json', db: Optional[AsyncSession] = None) -> str:
        """
        生成健康检查报告

        Args:
            format: 报告格式 (json/text)
            db: 可选的数据库会话

        Returns:
            报告内容
        """
        health_data = await self.run_full_check(db)
        
        if format == 'json':
            import json
            return json.dumps(health_data, indent=2, ensure_ascii=False)
        
        elif format == 'text':
            lines = []
            lines.append("=" * 60)
            lines.append("站点健康检查报告")
            lines.append("=" * 60)
            lines.append(f"总体评分: {health_data['overall_score']}/100")
            lines.append(f"状态: {health_data['status'].upper()}")
            lines.append(f"时间: {health_data['timestamp']}")
            lines.append("")
            
            for category, items in health_data['checks'].items():
                lines.append(f"\n[{category.upper()}]")
                for item in items:
                    status_icon = "✓" if item['status'] == 'pass' else "✗" if item['status'] == 'fail' else "⚠"
                    lines.append(f"  {status_icon} {item['name']}: {item['value']}")
                    if item.get('recommendation'):
                        lines.append(f"     建议: {item['recommendation']}")
            
            return "\n".join(lines)
        
        return str(health_data)


# 单例实例
site_health_service = SiteHealthService()
