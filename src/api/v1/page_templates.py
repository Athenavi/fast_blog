"""
页面模板API
"""
from typing import Optional

from fastapi import APIRouter, Depends, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.page_template_service import page_template_service
from src.api.v1.responses import ApiResponse
from src.auth.auth_deps import jwt_required_dependency as jwt_required
from src.utils.database.main import get_async_session

router = APIRouter()


@router.get("/available",
            summary="获取可用模板列表",
            description="获取当前主题下所有可用的页面模板",
            response_description="返回模板列表")
async def get_available_templates_api(
        theme_slug: Optional[str] = None,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_session)
):
    """获取可用模板列表"""
    try:
        templates = await page_template_service.get_available_templates(db, theme_slug)
        
        return ApiResponse(
            success=True,
            data={
                "templates": templates
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in get_available_templates_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/{page_id}/template",
            summary="获取页面模板",
            description="获取指定页面当前使用的模板",
            response_description="返回模板信息")
async def get_page_template_api(
        page_id: int = Path(..., description="页面ID"),
        db: AsyncSession = Depends(get_async_session)
):
    """获取页面模板"""
    try:
        template = await page_template_service.get_page_template(db, page_id)
        
        return ApiResponse(
            success=True,
            data={
                "page_id": page_id,
                "template": template or "default"
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in get_page_template_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/{page_id}/template",
             summary="设置页面模板",
             description="为页面设置模板，需要管理员或作者权限",
             response_description="返回操作结果")
async def set_page_template_api(
        page_id: int = Path(..., description="页面ID"),
        template: Optional[str] = Body(None, embed=True, description="模板slug，null表示使用默认模板"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_session)
):
    """设置页面模板"""
    try:
        from sqlalchemy import select
        from shared.models.pages import Pages
        
        # 检查权限
        page_query = select(Pages).where(Pages.id == page_id)
        page_result = await db.execute(page_query)
        page = page_result.scalar_one_or_none()
        
        if not page:
            return ApiResponse(success=False, error="Page not found")
        
        # 仅管理员或作者可设置模板
        if (not getattr(current_user, 'is_staff', False) and 
            not getattr(current_user, 'is_superuser', False) and
            page.author_id != current_user.id):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Permission denied")
        
        result = await page_template_service.set_page_template(db, page_id, template)
        
        return ApiResponse(
            success=result['success'],
            data=result
        )
    except Exception as e:
        import traceback
        print(f"Error in set_page_template_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/preview/{theme_slug}/{template_slug}",
            summary="获取模板预览图",
            description="获取指定主题和模板的预览图路径",
            response_description="返回预览图路径")
async def get_template_preview_api(
        theme_slug: str = Path(..., description="主题slug"),
        template_slug: str = Path(..., description="模板slug"),
        current_user=Depends(jwt_required)
):
    """获取模板预览图"""
    try:
        preview_path = await page_template_service.get_template_preview(theme_slug, template_slug)
        
        if preview_path:
            return ApiResponse(
                success=True,
                data={
                    "preview_url": f"/static/{preview_path}"
                }
            )
        else:
            return ApiResponse(
                success=True,
                data={
                    "preview_url": None,
                    "message": "No preview image available"
                }
            )
    except Exception as e:
        import traceback
        print(f"Error in get_template_preview_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))
