"""
全站编辑 API - Full Site Editing
提供模板管理、全局样式、导航菜单的RESTful接口
"""

from fastapi import APIRouter, Depends

from src.auth import admin_required
from shared.services.full_site_editor import (
    template_manager,
    global_styles_manager,
    navigation_menu_manager,
)
from src.api.v1.responses import ApiResponse

router = APIRouter(tags=["full-site-editing"])


# ==================== 模板管理 ====================

@router.get("/templates")
async def list_templates(current_user=Depends(admin_required)):
    """获取所有可用模板"""
    try:
        templates = template_manager.get_available_templates()

        return ApiResponse(
            success=True,
            data={
                'templates': templates,
                'total': len(templates),
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/templates/{template_type}")
async def get_template(
        template_type: str,
        current_user=Depends(admin_required)
):
    """获取指定类型的模板"""
    try:
        template = template_manager.get_template(template_type)

        if not template:
            return ApiResponse(
                success=False,
                error=f"模板不存在: {template_type}"
            )

        return ApiResponse(
            success=True,
            data={
                'template': template,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/templates/{template_type}")
async def save_template(
        template_type: str,
        content: str,
        current_user=Depends(admin_required)
):
    """保存模板"""
    try:
        success = template_manager.save_template(template_type, content)

        if success:
            return ApiResponse(
                success=True,
                message="模板保存成功"
            )
        else:
            return ApiResponse(
                success=False,
                error="保存模板失败"
            )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.delete("/templates/{template_type}")
async def reset_template(
        template_type: str,
        current_user=Depends(admin_required)
):
    """重置模板为默认值"""
    try:
        success = template_manager.reset_template(template_type)

        if success:
            return ApiResponse(
                success=True,
                message="模板已重置为默认值"
            )
        else:
            return ApiResponse(
                success=False,
                error="重置模板失败"
            )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


# ==================== 全局样式管理 ====================

@router.get("/global-styles")
async def get_global_styles(current_user=Depends(admin_required)):
    """获取全局样式配置"""
    try:
        styles = global_styles_manager.get_styles()

        return ApiResponse(
            success=True,
            data={
                'styles': styles,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/global-styles")
async def save_global_styles(
        styles: dict,
        current_user=Depends(admin_required)
):
    """保存全局样式配置"""
    try:
        success = global_styles_manager.save_styles(styles)

        if success:
            return ApiResponse(
                success=True,
                message="样式配置保存成功"
            )
        else:
            return ApiResponse(
                success=False,
                error="保存样式失败"
            )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/global-styles/css")
async def generate_css(current_user=Depends(admin_required)):
    """生成CSS变量"""
    try:
        styles = global_styles_manager.get_styles()
        css = global_styles_manager.generate_css(styles)

        return ApiResponse(
            success=True,
            data={
                'css': css,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


# ==================== 导航菜单管理 ====================

@router.get("/menus")
async def list_menus(current_user=Depends(admin_required)):
    """获取所有导航菜单"""
    try:
        menus = navigation_menu_manager.get_menus()

        return ApiResponse(
            success=True,
            data={
                'menus': menus,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/menus/{menu_location}")
async def get_menu(
        menu_location: str,
        current_user=Depends(admin_required)
):
    """获取指定位置的菜单"""
    try:
        menu = navigation_menu_manager.get_menu(menu_location)

        if not menu:
            return ApiResponse(
                success=False,
                error=f"菜单不存在: {menu_location}"
            )

        return ApiResponse(
            success=True,
            data={
                'menu': menu,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/menus/{menu_location}")
async def save_menu(
        menu_location: str,
        menu_data: dict,
        current_user=Depends(admin_required)
):
    """保存菜单"""
    try:
        success = navigation_menu_manager.save_menu(menu_location, menu_data)

        if success:
            return ApiResponse(
                success=True,
                message="菜单保存成功"
            )
        else:
            return ApiResponse(
                success=False,
                error="保存菜单失败"
            )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/menus/{menu_location}/items")
async def add_menu_item(
        menu_location: str,
        item: dict,
        current_user=Depends(admin_required)
):
    """添加菜单项"""
    try:
        success = navigation_menu_manager.add_menu_item(menu_location, item)

        if success:
            return ApiResponse(
                success=True,
                message="菜单项添加成功"
            )
        else:
            return ApiResponse(
                success=False,
                error="添加菜单项失败"
            )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.delete("/menus/{menu_location}/items/{item_index}")
async def remove_menu_item(
        menu_location: str,
        item_index: int,
        current_user=Depends(admin_required)
):
    """删除菜单项"""
    try:
        success = navigation_menu_manager.remove_menu_item(menu_location, item_index)

        if success:
            return ApiResponse(
                success=True,
                message="菜单项删除成功"
            )
        else:
            return ApiResponse(
                success=False,
                error="删除菜单项失败"
            )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


# ==================== 全站编辑仪表板 ====================

@router.get("/dashboard")
async def get_fse_dashboard(current_user=Depends(admin_required)):
    """获取全站编辑仪表板数据"""
    try:
        dashboard = {
            'templates': template_manager.get_available_templates(),
            'global_styles': global_styles_manager.get_styles(),
            'menus': navigation_menu_manager.get_menus(),
        }

        return ApiResponse(
            success=True,
            data={
                'dashboard': dashboard,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))
