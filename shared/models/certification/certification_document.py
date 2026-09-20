"""
SQLAlchemy 模型定义 - CertificationDocument
手写模型（T5-11 批次 13），写法对齐代码生成器产物。

认证**证明材料**：只存**已上传文件的引用**（走批次 6 的媒体库），
不在这里接收二进制，也不保存外链内容的副本。
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, String

from shared.models import Base  # 使用统一的 Base（跨子包引用）


class CertificationDocument(Base):
    """认证证明材料模型"""
    __tablename__ = 'certification_documents'

    __table_args__ = (Index('idx_certification_documents_cert', 'certification_id'),)

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='材料 ID')

    certification_id = Column(
        BigInteger, ForeignKey('expert_certifications.id', ondelete='CASCADE'),
        nullable=False, doc='认证 ID',
    )

    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False, doc='上传者 ID')

    file_name = Column(String(255), doc='文件名')

    file_url = Column(String(500), nullable=False, doc='文件地址（媒体库 URL）')

    file_type = Column(String(50), doc='MIME 类型')

    file_size = Column(BigInteger, default=0, doc='文件大小（字节）')

    created_at = Column(DateTime, doc='创建时间')

    updated_at = Column(DateTime, doc='更新时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'certification_id': self.certification_id,
            'user_id': self.user_id,
            'file_name': self.file_name,
            'file_url': self.file_url,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<CertificationDocument id={self.id} cert={self.certification_id}>'
