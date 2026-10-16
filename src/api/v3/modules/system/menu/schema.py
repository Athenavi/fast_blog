"""menu 模块的请求 / 响应模型"""

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class MenuItemOut(SchemaBase):
    id: int
    menu_id: int
    parent_id: Optional[int] = None
    title: str
    url: Optional[str] = None
    target: Optional[str] = None
    order_index: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    children: List["MenuItemOut"] = Field(default_factory=list)


MenuItemOut.model_rebuild()


class MenuOut(SchemaBase):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    items: List[MenuItemOut] = Field(default_factory=list)


class MenuCreate(SchemaBase):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None


class MenuUpdate(SchemaBase):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class MenuItemCreate(SchemaBase):
    title: str = Field(min_length=1, max_length=200)
    url: Optional[str] = Field(default=None, max_length=500)
    parent_id: Optional[int] = None
    target: str = Field(default="_self")
    order_index: int = 0
    is_active: bool = True


class MenuItemUpdate(SchemaBase):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    url: Optional[str] = Field(default=None, max_length=500)
    parent_id: Optional[int] = None
    target: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None


class MenuItemOrder(SchemaBase):
    id: int
    order_index: int


class MenuItemOrderRequest(SchemaBase):
    items: List[MenuItemOrder] = Field(default_factory=list, description="菜单项新顺序")
