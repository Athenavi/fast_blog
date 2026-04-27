"""
SQLAlchemy 模型定义 - SearchHistory
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey,
                        Integer, String, Text)

from . import Base  # 使用统一的 Base


class SearchHistory(Base):
    """搜索历史模型模型"""
    __tablename__ = 'search_history'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    user = Column(BigInteger, ForeignKey('users.id'), nullable=False, doc='user')


    keyword = Column(String(255), nullable=True, doc='keyword')

    results_count = Column(BigInteger, doc='results_count')

    created_at = Column(DateTime, doc='created_at')




    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'user': self.user,
            'keyword': self.keyword,
            'results_count': self.results_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        # 只有当明确要求包含敏感字段时才添加
        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<SearchHistory id={self.id}>'
