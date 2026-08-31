"""
BaseModelMixin — 为 SQLAlchemy 模型提供默认 to_dict() 序列化

利用 __table__.columns 反射自动生成字段字典，
消除 ~130 个模型中重复的 to_dict() 定义。

用法:
    class Article(BaseModelMixin, Base):
        __tablename__ = 'articles'
        ...

    article.to_dict()  # 自动包含所有列

若要排除敏感字段或添加额外逻辑，子类可覆盖:
    _sensitive_fields = {'password', 'totp_secret'}

    def to_dict(self, exclude_sensitive=True):
        data = super().to_dict(exclude_sensitive)
        # 自定义逻辑
        return data
"""

from datetime import date, datetime
from typing import Any, Dict, Set


class BaseModelMixin:
    """提供默认 to_dict() 序列化的混入类"""

    # 子类可覆盖此集合声明敏感字段
    _sensitive_fields: Set[str] = set()

    def to_dict(self, exclude_sensitive: bool = True) -> Dict[str, Any]:
        """将模型转换为字典（通过列反射自动生成）"""
        data = {}
        for col in self.__table__.columns:
            value = getattr(self, col.name, None)
            # datetime/date → ISO 字符串
            if isinstance(value, (datetime, date)):
                value = value.isoformat()
            data[col.name] = value

        if exclude_sensitive and self._sensitive_fields:
            # 过滤敏感字段，防止列反射自动暴露
            for field in self._sensitive_fields:
                data.pop(field, None)

        return data

    def __repr__(self) -> str:
        """默认字符串表示"""
        pk = self.__table__.primary_key.columns.keys()[0]
        pk_val = getattr(self, pk, None)
        return f'<{self.__class__.__name__} {pk}={pk_val}>'
