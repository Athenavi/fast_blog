"""admin_menu 模块的请求 / 响应模型"""

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase

#: 菜单类型（对齐官方 sys_menu：1 目录 / 2 菜单 / 3 按钮）
MENU_TYPE_DIR = 1
MENU_TYPE_MENU = 2
MENU_TYPE_BUTTON = 3


class AdminMenuOut(SchemaBase):
    id: int
    code: Optional[str] = None
    title: Optional[str] = None
    parent_id: Optional[int] = None
    menu_type: int = MENU_TYPE_MENU
    permission_code: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    children: List["AdminMenuOut"] = Field(default_factory=list)


AdminMenuOut.model_rebuild()


class AdminMenuCreate(SchemaBase):
    code: str = Field(
        min_length=1, max_length=100, description="菜单稳定标识（与前端路由 name/meta.menuCode 一致）"
    )
    title: str = Field(min_length=1, max_length=100, description="菜单名称")
    parent_id: Optional[int] = None
    menu_type: int = Field(default=MENU_TYPE_MENU, description="1 目录 / 2 菜单 / 3 按钮")
    permission_code: Optional[str] = Field(
        default=None, max_length=100, description="关联权限码（与 capabilities.code 同构）"
    )
    sort_order: int = 0
    is_active: bool = True


class AdminMenuUpdate(SchemaBase):
    code: Optional[str] = Field(default=None, min_length=1, max_length=100)
    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    parent_id: Optional[int] = None
    menu_type: Optional[int] = None
    permission_code: Optional[str] = Field(default=None, max_length=100)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class RoleMenuAssign(SchemaBase):
    menu_ids: List[int] = Field(default_factory=list, description="全量覆盖该角色已授权的菜单")


class MyMenusOut(SchemaBase):
    menu_codes: List[str] = Field(default_factory=list)
    is_superuser: bool = False
