"""
SQLAlchemy 模型定义 - SLAReport
SLA 报告模型，记录企业许可证的 SLA 达标情况与历史报告。
"""

from sqlalchemy import Column, BigInteger, String, Integer, Boolean, DateTime, Numeric, Index

from .. import Base  # 使用统一的 Base


class SLAReport(Base):
    """SLA 报告模型"""
    __tablename__ = 'sla_reports'

    __table_args__ = (
        Index('idx_sla_license_period', 'license_id', 'period_start', 'period_end'),
        Index('idx_sla_compliant', 'is_compliant'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, doc='报告 ID')

    license_id = Column(BigInteger, nullable=False, doc='企业许可证 ID')

    period_start = Column(DateTime, doc='报告周期开始时间')

    period_end = Column(DateTime, doc='报告周期结束时间')

    uptime_percentage = Column(Numeric(10, 2), nullable=False, doc='在线率百分比')

    target_percentage = Column(Numeric(10, 2), nullable=False, doc='目标 SLA 百分比')

    is_compliant = Column(Boolean, default=False, doc='是否达标')

    downtime_minutes = Column(Integer, default=0, doc='宕机分钟数')

    total_minutes = Column(Integer, nullable=False, doc='周期总分钟数')

    created_at = Column(DateTime, doc='创建时间')

    checked_at = Column(DateTime, doc='检查时间')

    def to_dict(self, exclude_sensitive=True):
        """转换为字典

        Args:
            exclude_sensitive: 是否排除敏感字段（密码、密钥、token 等）
        """
        data = {
            'id': self.id,
            'license_id': self.license_id,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'uptime_percentage': self.uptime_percentage,
            'target_percentage': self.target_percentage,
            'is_compliant': self.is_compliant,
            'downtime_minutes': self.downtime_minutes,
            'total_minutes': self.total_minutes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'checked_at': self.checked_at.isoformat() if self.checked_at else None,
        }

        if not exclude_sensitive:
            sensitive_data = {
            }
            data.update(sensitive_data)

        return data

    def __repr__(self):
        """字符串表示"""
        return f'<SLAReport id={self.id} license_id={self.license_id}>'
