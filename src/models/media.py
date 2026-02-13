from datetime import datetime

from sqlalchemy import Column, Integer, String, BigInteger, DateTime
from sqlalchemy.orm import relationship

from . import Base  # 使用统一的Base


class FileHash(Base):
    __tablename__ = 'file_hashes'
    id = Column(BigInteger, primary_key=True)
    hash = Column(String(64), nullable=False, unique=True)
    filename = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now())
    reference_count = Column(Integer, default=1)
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)
    storage_path = Column(String(512), nullable=False)

    media = relationship('Media', back_populates='file_hash', primaryjoin="Media.hash == foreign(FileHash.hash)", uselist=False)


class Media(Base):
    __tablename__ = 'media'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now())
    hash = Column(String(64), nullable=False)
    original_filename = Column(String(255), nullable=False)
    user = relationship('User', back_populates='media', primaryjoin="Media.user_id == foreign(User.id)",
                        overlaps="articles,author,notifications,recipient,subscriber,user,vip_subscriptions")
    file_hash = relationship('FileHash', back_populates='media', primaryjoin="Media.hash == foreign(FileHash.hash)", uselist=False)