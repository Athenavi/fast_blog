"""
SQLAlchemy 模型定义 - FormField
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""


from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey,
                        Index, Integer, String, Text)

from . import Base  # 使用统一的 Base


class FormField(Base):
    """表单字段模型模型"""
    __tablename__ = 'form_fields'


    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='id')


    form_id = Column(BigInteger, ForeignKey('forms.id'), nullable=False, doc='form_id')


    label = Column(String(255), nullable=True, doc='label')

    field_type = Column(String(50), nullable=True, doc='field_type')

    placeholder = Column(String(255), nullable=True, doc='placeholder')

    help_text = Column(String(255), nullable=True, doc='help_text')

    required = Column(Boolean, default=False, doc='required')

    options = Column(String(255), nullable=True, doc='options')

    validation_rules = Column(String(255), nullable=True, doc='validation_rules')

    default_value = Column(String(255), nullable=True, doc='default_value')

    order_index = Column(BigInteger, default=0, doc='order_index')

    is_active = Column(Boolean, default=True, doc='is_active')

    created_at = Column(DateTime, doc='created_at')

    updated_at = Column(DateTime, doc='updated_at')


    __table_args__ = (

    Index('idx_form_fields_form_id', 'form_id'),
        Index('idx_form_fields_order', 'order_index'),
    )


    def to_dict(self, exclude_sensitive=True):
        """转换为字典
        
        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'form_id': self.form_id,
            'label': self.label,
            'field_type': self.field_type,
            'placeholder': self.placeholder,
            'help_text': self.help_text,
            'required': self.required,
            'options': self.options,
            'validation_rules': self.validation_rules,
            'default_value': self.default_value,
            'order_index': self.order_index,
            'is_active': self.is_active,
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
        return f'<FormField id={self.id}>'
