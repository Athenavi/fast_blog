"""
多站点管理服务
提供站点配置隔离、独立域名绑定、共享用户体系和跨站点内容同步功能
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

logger = logging.getLogger(__name__)

Base = declarative_base()


class Site(Base):
    """站点模型"""
    __tablename__ = 'sites'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    domain = Column(String(255), unique=True, nullable=False, index=True)  # 主域名
    additional_domains = Column(Text)  # JSON格式的附加域名列表
    description = Column(Text)
    logo_url = Column(String(500))
    favicon_url = Column(String(500))
    theme = Column(String(100), default='default')
    language = Column(String(10), default='en')
    timezone = Column(String(50), default='UTC')

    # 站点设置（JSON格式）
    settings = Column(Text)

    # 状态
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    site_users = relationship("SiteUser", back_populates="site")
    content_mappings = relationship("ContentMapping", back_populates="source_site")

    __table_args__ = (
        Index('idx_sites_slug', 'slug'),
        Index('idx_sites_domain', 'domain'),
    )


class SiteUser(Base):
    """站点-用户关联模型（共享用户体系）"""
    __tablename__ = 'site_users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    role = Column(String(50), default='subscriber')  # 在该站点的角色
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    site = relationship("Site", back_populates="site_users")
    user = relationship("User")

    __table_args__ = (
        Index('idx_site_users_site', 'site_id'),
        Index('idx_site_users_user', 'user_id'),
        Index('idx_site_users_unique', 'site_id', 'user_id', unique=True),
    )


class ContentMapping(Base):
    """内容映射模型（跨站点内容同步）"""
    __tablename__ = 'content_mappings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    target_site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    content_type = Column(String(50), nullable=False)  # article, page等
    source_content_id = Column(Integer, nullable=False)
    target_content_id = Column(Integer)
    sync_mode = Column(String(20), default='manual')  # manual, auto
    last_synced_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    source_site = relationship("Site", back_populates="content_mappings", foreign_keys=[source_site_id])
    target_site = relationship("Site", foreign_keys=[target_site_id])

    __table_args__ = (
        Index('idx_content_mapping_source', 'source_site_id', 'content_type', 'source_content_id'),
        Index('idx_content_mapping_target', 'target_site_id', 'content_type', 'target_content_id'),
    )


class MultiSiteService:
    """
    多站点管理服务
    
    功能:
    1. 站点配置隔离
    2. 独立域名绑定
    3. 共享用户体系
    4. 跨站点内容同步
    """

    def __init__(self):
        pass

    async def create_site(self, db, name: str, slug: str, domain: str,
                          description: str = None, is_default: bool = False,
                          settings: Dict = None) -> Site:
        """
        创建新站点
        
        Args:
            db: 数据库会话
            name: 站点名称
            slug: 站点标识
            domain: 主域名
            description: 描述
            is_default: 是否为默认站点
            settings: 站点设置
            
        Returns:
            创建的站点
        """
        from sqlalchemy import select

        # 检查slug是否已存在
        stmt = select(Site).where(Site.slug == slug)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise ValueError(f"Site with slug '{slug}' already exists")

        # 检查域名是否已存在
        stmt = select(Site).where(Site.domain == domain)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise ValueError(f"Site with domain '{domain}' already exists")

        # 如果设置为默认站点，取消其他站点的默认状态
        if is_default:
            stmt = select(Site).where(Site.is_default == True)
            result = await db.execute(stmt)
            default_sites = result.scalars().all()
            for site in default_sites:
                site.is_default = False

        # 创建站点
        site = Site(
            name=name,
            slug=slug,
            domain=domain,
            description=description,
            is_default=is_default,
            settings=str(settings) if settings else None
        )

        db.add(site)
        await db.commit()
        await db.refresh(site)

        logger.info(f"Site created: {slug} ({domain})")
        return site

    async def update_site(self, db, site_id: int, updates: Dict[str, Any]) -> Site:
        """
        更新站点配置
        
        Args:
            db: 数据库会话
            site_id: 站点ID
            updates: 更新字段
            
        Returns:
            更新后的站点
        """
        site = await db.get(Site, site_id)
        if not site:
            raise ValueError("Site not found")

        for key, value in updates.items():
            if hasattr(site, key):
                setattr(site, key, value)

        await db.commit()
        await db.refresh(site)

        logger.info(f"Site updated: {site.slug}")
        return site

    async def delete_site(self, db, site_id: int):
        """
        删除站点
        
        Args:
            db: 数据库会话
            site_id: 站点ID
        """
        site = await db.get(Site, site_id)
        if not site:
            raise ValueError("Site not found")

        # 不能删除默认站点
        if site.is_default:
            raise ValueError("Cannot delete default site")

        # 删除站点-用户关联
        from sqlalchemy import delete
        stmt = delete(SiteUser).where(SiteUser.site_id == site_id)
        await db.execute(stmt)

        # 删除内容映射
        stmt = delete(ContentMapping).where(
            (ContentMapping.source_site_id == site_id) |
            (ContentMapping.target_site_id == site_id)
        )
        await db.execute(stmt)

        # 删除站点
        await db.delete(site)
        await db.commit()

        logger.info(f"Site deleted: {site.slug}")

    async def add_domain(self, db, site_id: int, domain: str):
        """
        添加附加域名
        
        Args:
            db: 数据库会话
            site_id: 站点ID
            domain: 域名
        """
        import json

        site = await db.get(Site, site_id)
        if not site:
            raise ValueError("Site not found")

        # 解析现有附加域名
        additional_domains = []
        if site.additional_domains:
            try:
                additional_domains = json.loads(site.additional_domains)
            except:
                additional_domains = []

        # 检查域名是否已存在
        if domain in additional_domains:
            raise ValueError("Domain already added")

        # 检查域名是否被其他站点使用
        from sqlalchemy import select
        stmt = select(Site).where(Site.domain == domain)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise ValueError("Domain is used as primary domain by another site")

        # 添加域名
        additional_domains.append(domain)
        site.additional_domains = json.dumps(additional_domains)

        await db.commit()

        logger.info(f"Domain added to site {site.slug}: {domain}")

    async def remove_domain(self, db, site_id: int, domain: str):
        """
        移除附加域名
        
        Args:
            db: 数据库会话
            site_id: 站点ID
            domain: 域名
        """
        import json

        site = await db.get(Site, site_id)
        if not site:
            raise ValueError("Site not found")

        if site.additional_domains:
            try:
                additional_domains = json.loads(site.additional_domains)
                if domain in additional_domains:
                    additional_domains.remove(domain)
                    site.additional_domains = json.dumps(additional_domains)
                    await db.commit()
                    logger.info(f"Domain removed from site {site.slug}: {domain}")
            except:
                pass

    async def get_site_by_domain(self, db, domain: str) -> Optional[Site]:
        """
        根据域名获取站点
        
        Args:
            db: 数据库会话
            domain: 域名
            
        Returns:
            站点对象
        """
        import json
        from sqlalchemy import select

        # 检查主域名
        stmt = select(Site).where(Site.domain == domain, Site.is_active == True)
        result = await db.execute(stmt)
        site = result.scalar_one_or_none()

        if site:
            return site

        # 检查附加域名
        stmt = select(Site).where(Site.is_active == True)
        result = await db.execute(stmt)
        sites = result.scalars().all()

        for site in sites:
            if site.additional_domains:
                try:
                    additional_domains = json.loads(site.additional_domains)
                    if domain in additional_domains:
                        return site
                except:
                    pass

        # 返回默认站点
        stmt = select(Site).where(Site.is_default == True, Site.is_active == True)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def add_user_to_site(self, db, site_id: int, user_id: int, role: str = 'subscriber'):
        """
        添加用户到站点（共享用户体系）
        
        Args:
            db: 数据库会话
            site_id: 站点ID
            user_id: 用户ID
            role: 在该站点的角色
        """
        from sqlalchemy import select

        # 检查是否已存在
        stmt = select(SiteUser).where(
            SiteUser.site_id == site_id,
            SiteUser.user_id == user_id
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.role = role
            existing.is_active = True
        else:
            site_user = SiteUser(
                site_id=site_id,
                user_id=user_id,
                role=role
            )
            db.add(site_user)

        await db.commit()

        logger.info(f"User {user_id} added to site {site_id} as {role}")

    async def remove_user_from_site(self, db, site_id: int, user_id: int):
        """
        从站点移除用户
        
        Args:
            db: 数据库会话
            site_id: 站点ID
            user_id: 用户ID
        """
        from sqlalchemy import select

        stmt = select(SiteUser).where(
            SiteUser.site_id == site_id,
            SiteUser.user_id == user_id
        )
        result = await db.execute(stmt)
        site_user = result.scalar_one_or_none()

        if site_user:
            site_user.is_active = False
            await db.commit()

            logger.info(f"User {user_id} removed from site {site_id}")

    async def get_user_sites(self, db, user_id: int) -> List[Dict[str, Any]]:
        """
        获取用户所属的所有站点
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            站点列表
        """
        from sqlalchemy import select

        stmt = (
            select(Site, SiteUser)
            .join(SiteUser, Site.id == SiteUser.site_id)
            .where(
                SiteUser.user_id == user_id,
                SiteUser.is_active == True,
                Site.is_active == True
            )
        )

        result = await db.execute(stmt)
        rows = result.all()

        sites = []
        for site, site_user in rows:
            sites.append({
                'id': site.id,
                'name': site.name,
                'slug': site.slug,
                'domain': site.domain,
                'role': site_user.role,
                'joined_at': site_user.joined_at.isoformat() if site_user.joined_at else None,
            })

        return sites

    async def sync_content(self, db, source_site_id: int, target_site_id: int,
                           content_type: str, source_content_id: int,
                           sync_mode: str = 'manual') -> ContentMapping:
        """
        同步内容到其他站点
        
        Args:
            db: 数据库会话
            source_site_id: 源站点ID
            target_site_id: 目标站点ID
            content_type: 内容类型
            source_content_id: 源内容ID
            sync_mode: 同步模式 (manual/auto)
            
        Returns:
            内容映射记录
        """
        from sqlalchemy import select

        # 检查是否已有映射
        stmt = select(ContentMapping).where(
            ContentMapping.source_site_id == source_site_id,
            ContentMapping.target_site_id == target_site_id,
            ContentMapping.content_type == content_type,
            ContentMapping.source_content_id == source_content_id
        )
        result = await db.execute(stmt)
        mapping = result.scalar_one_or_none()

        if mapping:
            mapping.sync_mode = sync_mode
            mapping.last_synced_at = datetime.utcnow()
        else:
            mapping = ContentMapping(
                source_site_id=source_site_id,
                target_site_id=target_site_id,
                content_type=content_type,
                source_content_id=source_content_id,
                sync_mode=sync_mode
            )
            db.add(mapping)

        await db.commit()
        await db.refresh(mapping)

        logger.info(
            f"Content synced: {content_type}#{source_content_id} from site {source_site_id} to {target_site_id}")
        return mapping

    async def get_all_sites(self, db, include_inactive: bool = False) -> List[Site]:
        """
        获取所有站点
        
        Args:
            db: 数据库会话
            include_inactive: 是否包含非活动站点
            
        Returns:
            站点列表
        """
        from sqlalchemy import select

        query = select(Site)
        if not include_inactive:
            query = query.where(Site.is_active == True)

        result = await db.execute(query)
        return result.scalars().all()


# 全局实例
multisite_service = MultiSiteService()
