from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey

from . import Base  # 使用统一的Base


class SystemSettings(Base):
    __tablename__ = 'system_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text)
    description = Column(Text)
    category = Column(String(100))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_by = Column(Integer, ForeignKey('users.id'))


class Menus(Base):
    __tablename__ = 'menus'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class MenuItems(Base):
    __tablename__ = 'menu_items'

    id = Column(Integer, primary_key=True, autoincrement=True)
    menu_id = Column(Integer, ForeignKey('menus.id'))
    parent_id = Column(Integer, ForeignKey('menu_items.id'))
    title = Column(String(255), nullable=False)
    url = Column(String(500))
    target = Column(String(20), default='_self')
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Pages(Base):
    __tablename__ = 'pages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    content = Column(Text)
    excerpt = Column(Text)
    template = Column(String(100))
    status = Column(Integer, default=0)
    author_id = Column(Integer, ForeignKey('users.id'))
    parent_id = Column(Integer, ForeignKey('pages.id'))
    order_index = Column(Integer, default=0)
    meta_title = Column(String(255))
    meta_description = Column(Text)
    meta_keywords = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    published_at = Column(DateTime)