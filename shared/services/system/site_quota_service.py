"""
站点配额管理服务

管理每个站点的资源配额（文章数、用户数、存储空间等）
"""
from typing import Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.site import Site


class SiteQuotaService:
    """站点配额服务"""

    # 默认配额限制
    DEFAULT_QUOTAS = {
        'max_articles': 10000,  # 最大文章数
        'max_users': 1000,  # 最大用户数
        'max_media_size_mb': 5000,  # 最大媒体存储空间 (MB)
        'max_categories': 500,  # 最大分类数
        'max_plugins': 50,  # 最大插件数
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_site_quota(self, site_id: int) -> Dict:
        """
        获取站点配额信息
        
        Args:
            site_id: 站点ID
            
        Returns:
            配额信息，包括限制和当前使用量
        """
        # 获取站点
        stmt = select(Site).where(Site.id == site_id)
        result = await self.db.execute(stmt)
        site = result.scalar_one_or_none()

        if not site:
            raise ValueError(f"Site {site_id} not found")

        # 从 settings 中获取自定义配额，或使用默认值
        quotas = site.settings.get('quotas', self.DEFAULT_QUOTAS) if site.settings else self.DEFAULT_QUOTAS

        # TODO: 统计当前使用量（需要 Article, User, Media 等模型支持 site_id）
        # 目前返回占位数据
        usage = {
            'articles': 0,
            'users': 0,
            'media_size_mb': 0,
            'categories': 0,
            'plugins': 0,
        }

        return {
            'site_id': site_id,
            'site_name': site.name,
            'quotas': quotas,
            'usage': usage,
            'utilization': {
                key: round((usage.get(key, 0) / quotas[key]) * 100, 2) if quotas[key] > 0 else 0
                for key in quotas.keys()
            }
        }

    async def check_quota_available(self, site_id: int, resource_type: str, requested_amount: int = 1) -> Dict:
        """
        检查是否有可用配额
        
        Args:
            site_id: 站点ID
            resource_type: 资源类型 (articles/users/media_size_mb/categories/plugins)
            requested_amount: 请求的数量
            
        Returns:
            检查结果
        """
        quota_info = await self.get_site_quota(site_id)

        if resource_type not in quota_info['quotas']:
            return {
                'available': True,
                'message': f'Unknown resource type: {resource_type}'
            }

        max_limit = quota_info['quotas'][resource_type]
        current_usage = quota_info['usage'].get(resource_type, 0)
        available = max_limit - current_usage

        is_available = available >= requested_amount

        return {
            'available': is_available,
            'resource_type': resource_type,
            'max_limit': max_limit,
            'current_usage': current_usage,
            'available_amount': available,
            'requested_amount': requested_amount,
            'message': 'Quota available' if is_available else f'Quota exceeded. Available: {available}, Requested: {requested_amount}'
        }

    async def update_site_quota(self, site_id: int, quotas: Dict) -> Dict:
        """
        更新站点配额
        
        Args:
            site_id: 站点ID
            quotas: 新的配额设置
            
        Returns:
            更新结果
        """
        stmt = select(Site).where(Site.id == site_id)
        result = await self.db.execute(stmt)
        site = result.scalar_one_or_none()

        if not site:
            raise ValueError(f"Site {site_id} not found")

        # 更新 settings 中的 quotas
        if not site.settings:
            site.settings = {}

        site.settings['quotas'] = {**self.DEFAULT_QUOTAS, **quotas}

        await self.db.commit()

        return {
            'success': True,
            'message': 'Quotas updated successfully',
            'quotas': site.settings['quotas']
        }


def create_site_quota_service(db: AsyncSession) -> SiteQuotaService:
    """创建站点配额服务实例"""
    return SiteQuotaService(db)
