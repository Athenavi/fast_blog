"""
SQLAlchemy 模型定义 - BlockPattern
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""


from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey,
                        Index, Integer, String, Text)

from . import Base  # 使用统一的 Base

# ============================================================================
# 自定义方法导入提示
# 以下导入是自定义方法可能需要的，如果不需要可以删除：
# - from datetime import datetime
# ============================================================================




class BlockPattern(Base):
    """自定义块模式模型模型"""
    __tablename__ = 'block_patterns'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    name = Column(String(100), unique=True, nullable=True, doc='name')


    title = Column(String(255), nullable=True, doc='title')

    description = Column(Text, nullable=True, doc='description')

    category = Column(String(50), default='custom', doc='category')

    blocks = Column(Text, nullable=False, doc='blocks')

    keywords = Column(Text, nullable=True, doc='keywords')

    thumbnail = Column(String(500), nullable=True, doc='thumbnail')

    is_public = Column(Boolean, default=False, doc='is_public')

    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=True, doc='user_id')

    viewport_width = Column(BigInteger, default=800, doc='viewport_width')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')


    __table_args__ = (

    Index('idx_block_patterns_name', 'name', unique=True),
        Index('idx_block_patterns_category', 'category'),
        Index('idx_block_patterns_user_id', 'user_id'),
    )


    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'name': self.name,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'blocks': self.blocks,
            'keywords': self.keywords,
            'thumbnail': self.thumbnail,
            'is_public': self.is_public,
            'user_id': self.user_id,
            'viewport_width': self.viewport_width,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        # 只有当明确要求包含敏感字段时才添加
        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<BlockPattern id={self.id}>'

    def get_blocks_data(self):
        """
        获取解析后的块数据

        Returns:
            List[Dict]: 解析后的块数据列表
        """
        import json

        if not self.blocks:
            return []

        try:
            # 如果 blocks 是字符串，尝试解析 JSON
            if isinstance(self.blocks, str):
                return json.loads(self.blocks)
            # 如果已经是列表或字典，直接返回
            elif isinstance(self.blocks, (list, dict)):
                return self.blocks if isinstance(self.blocks, list) else [self.blocks]
            else:
                return []
        except (json.JSONDecodeError, TypeError):
            return []


    def set_blocks_data(self, blocks_data) -> None:
        """
        设置块数据（自动序列化为 JSON）

        Args:
            blocks_data: 块数据列表
        """
        import json

        try:
            self.blocks = json.dumps(blocks_data, ensure_ascii=False)
        except (TypeError, ValueError):
            self.blocks = str(blocks_data)


    def get_keywords_list(self):
        """
        获取关键词列表

        Returns:
            List[str]: 关键词列表
        """

        if not self.keywords:
            return []

        try:
            # 如果 keywords 是逗号分隔的字符串
            if isinstance(self.keywords, str):
                return [kw.strip() for kw in self.keywords.split(',') if kw.strip()]
            # 如果已经是列表
            elif isinstance(self.keywords, list):
                return self.keywords
            else:
                return []
        except Exception:
            return []


    def set_keywords_list(self, keywords) -> None:
        """
        设置关键词列表（自动转换为逗号分隔的字符串）

        Args:
            keywords: 关键词列表
        """

        if isinstance(keywords, list):
            self.keywords = ','.join(keywords)
        elif isinstance(keywords, str):
            self.keywords = keywords

    def is_custom_pattern(self) -> bool:
        """
        判断是否为自定义模式（非系统预定义）

        Returns:
            bool: 是否为自定义模式
        """
        return self.category == 'custom'


    def to_pattern_dict(self):
        """
        转换为前端可用的模式字典格式

        Returns:
            Dict: 模式字典
        """

        return {
            'name': self.name,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'blocks': self.get_blocks_data(),
            'keywords': self.get_keywords_list(),
            'thumbnail': self.thumbnail,
            'viewport_width': self.viewport_width,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
