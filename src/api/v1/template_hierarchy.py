"""
主题模板层级API
提供模板查找和解析功能
"""
from typing import Dict, Any

from fastapi import APIRouter, Depends, Request, Body

from shared.models.user import User
from shared.services.theme_manager import template_loader
from src.api.v1.responses import ApiResponse
from src.auth.auth_deps import admin_required_api

router = APIRouter()


@router.post("/resolve/article",
             summary="解析文章模板",
             description="根据文章数据解析应使用的模板(仅管理员)",
             response_description="返回模板路径")
async def resolve_article_template_api(
        request: Request,
        data: Dict[str, Any] = Body(...),
        current_user: User = Depends(admin_required_api)
):
    """
    解析文章模板API
    
    Request Body:
    {
        "article": {
            "id": 123,
            "slug": "my-article",
            "post_type": "post"
        },
        "theme": "default"
    }
    """
    try:
        article = data.get('article', {})
        theme = data.get('theme', 'default')
        
        if not article:
            return ApiResponse(success=False, error='缺少文章数据')
        
        template_path = template_loader.resolve_article_template(article, theme)
        
        return ApiResponse(
            success=True,
            data={
                'template': str(template_path) if template_path else None,
                'template_name': template_path.stem if template_path else None,
                'theme': theme,
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in resolve_article_template_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/resolve/page",
             summary="解析页面模板",
             description="根据页面数据解析应使用的模板(仅管理员)",
             response_description="返回模板路径")
async def resolve_page_template_api(
        request: Request,
        data: Dict[str, Any] = Body(...),
        current_user: User = Depends(admin_required_api)
):
    """解析页面模板API"""
    try:
        page = data.get('page', {})
        theme = data.get('theme', 'default')
        
        if not page:
            return ApiResponse(success=False, error='缺少页面数据')
        
        template_path = template_loader.resolve_page_template(page, theme)
        
        return ApiResponse(
            success=True,
            data={
                'template': str(template_path) if template_path else None,
                'template_name': template_path.stem if template_path else None,
                'theme': theme,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/resolve/archive",
             summary="解析归档模板",
             description="根据归档类型解析应使用的模板(仅管理员)",
             response_description="返回模板路径")
async def resolve_archive_template_api(
        request: Request,
        data: Dict[str, Any] = Body(...),
        current_user: User = Depends(admin_required_api)
):
    """解析归档模板API"""
    try:
        archive_type = data.get('archive_type', '')
        term_slug = data.get('term_slug', '')
        theme = data.get('theme', 'default')
        
        if not archive_type:
            return ApiResponse(success=False, error='缺少归档类型')
        
        template_path = template_loader.resolve_archive_template(archive_type, term_slug, theme)
        
        return ApiResponse(
            success=True,
            data={
                'template': str(template_path) if template_path else None,
                'template_name': template_path.stem if template_path else None,
                'archive_type': archive_type,
                'theme': theme,
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/templates/{theme}",
            summary="获取可用模板",
            description="获取指定主题的所有可用模板(仅管理员)",
            response_description="返回模板列表")
async def get_available_templates_api(
        request: Request,
        theme: str,
        current_user: User = Depends(admin_required_api)
):
    """获取可用模板API"""
    try:
        templates = template_loader.get_available_templates(theme)
        
        return ApiResponse(
            success=True,
            data={
                'theme': theme,
                'templates': templates,
                'count': len(templates),
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/hierarchy",
            summary="获取模板层级说明",
            description="获取完整的模板层级查找规则",
            response_description="返回层级说明")
async def template_hierarchy_info_api(request: Request):
    """模板层级信息API"""
    try:
        hierarchy = template_loader.get_template_hierarchy_info()
        
        return ApiResponse(
            success=True,
            data={
                'hierarchy': hierarchy,
                'description': 'WordPress-style template hierarchy for FastBlog',
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))
