"""
静态页面管理API端点
提供页面的完整CRUD操作
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.page_service import (
    get_pages_list,
    get_page_by_slug,
    create_page,
    update_page,
    delete_page,
    get_page_hierarchy
)
from src.api.v1.responses import ApiResponse
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(prefix="/pages", tags=["pages"])


@router.get("")
async def list_pages(
        page: int = Query(1, ge=1, description="页码"),
        per_page: int = Query(20, ge=1, le=100, description="每页数量"),
        status: Optional[int] = Query(None, description="状态筛选（0:草稿，1:已发布）"),
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取页面列表
    
    Args:
        page: 页码
        per_page: 每页数量
        status: 状态筛选
    """
    try:
        result = await get_pages_list(
            db=db,
            page=page,
            per_page=per_page,
            status=status
        )

        if not result["success"]:
            return ApiResponse(
                success=False,
                error=result.get("error", "获取页面列表失败")
            )

        return ApiResponse(
            success=True,
            data=result
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/hierarchy")
async def get_pages_tree(
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取页面层级结构（树形）
    
    Returns:
        层级化的页面列表
    """
    try:
        hierarchy = await get_page_hierarchy(db=db)

        return ApiResponse(
            success=True,
            data={"pages": hierarchy}
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/{slug}")
async def get_page_detail(
        slug: str,
        request: Request = None,
        db: AsyncSession = Depends(get_async_db)
):
    """
    根据slug获取页面详情
    
    Args:
        slug: 页面slug
    """
    try:
        page = await get_page_by_slug(db=db, slug=slug)

        if not page:
            return ApiResponse(
                success=False,
                error="页面不存在"
            )

        # 只返回已发布的页面（除非是管理员）
        from shared.services.permission_system import permission_manager
        is_admin = await permission_manager.has_permission(db, current_user.id, 'manage_pages')
        
        if page.status != 1 and not is_admin:  # status 1 = published
            return ApiResponse(
                success=False,
                error="页面未发布"
            )

        return ApiResponse(
            success=True,
            data=page
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("")
async def create_new_page(
        request: Request,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    创建新页面
    
    Body参数:
        title: 页面标题（必填）
        slug: 页面slug（必填）
        content: 页面内容（必填）
        excerpt: 摘要（可选）
        template: 模板（可选）
        status: 状态（0:草稿，1:已发布，默认0）
        parent_id: 父页面ID（可选）
        order_index: 排序索引（默认0）
        meta_title: SEO标题（可选）
        meta_description: SEO描述（可选）
        meta_keywords: SEO关键词（可选）
    """
    try:
        form_data = await request.form()

        # 验证必填字段
        title = form_data.get('title', '').strip()
        slug = form_data.get('slug', '').strip()
        content = form_data.get('content', '').strip()

        if not title or not slug or not content:
            return ApiResponse(
                success=False,
                error="标题、slug和内容不能为空"
            )

        # 处理可选字段
        excerpt = form_data.get('excerpt', None)
        template = form_data.get('template', None)

        try:
            status = int(form_data.get('status', 0))
        except ValueError:
            status = 0

        try:
            parent_id = int(form_data.get('parent_id')) if form_data.get('parent_id') else None
        except ValueError:
            parent_id = None

        try:
            order_index = int(form_data.get('order_index', 0))
        except ValueError:
            order_index = 0

        meta_title = form_data.get('meta_title', None)
        meta_description = form_data.get('meta_description', None)
        meta_keywords = form_data.get('meta_keywords', None)

        # 创建页面
        page = await create_page(
            db=db,
            title=title,
            slug=slug,
            content=content,
            author_id=current_user.id,
            excerpt=excerpt,
            template=template,
            status=status,
            parent_id=parent_id,
            order_index=order_index,
            meta_title=meta_title,
            meta_description=meta_description,
            meta_keywords=meta_keywords
        )

        if not page:
            return ApiResponse(
                success=False,
                error="创建页面失败"
            )

        return ApiResponse(
            success=True,
            data={
                "message": "页面创建成功",
                "page_id": page.id
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.put("/{page_id}")
async def update_existing_page(
        page_id: int,
        request: Request,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    更新页面
    
    Args:
        page_id: 页面ID
    
    Body参数:
        title: 页面标题（可选）
        slug: 页面slug（可选）
        content: 页面内容（可选）
        excerpt: 摘要（可选）
        template: 模板（可选）
        status: 状态（可选）
        parent_id: 父页面ID（可选）
        order_index: 排序索引（可选）
        meta_title: SEO标题（可选）
        meta_description: SEO描述（可选）
        meta_keywords: SEO关键词（可选）
    """
    try:
        form_data = await request.form()

        # 构建更新数据
        update_data = {}

        if 'title' in form_data:
            update_data['title'] = form_data.get('title')
        if 'slug' in form_data:
            update_data['slug'] = form_data.get('slug')
        if 'content' in form_data:
            update_data['content'] = form_data.get('content')
        if 'excerpt' in form_data:
            update_data['excerpt'] = form_data.get('excerpt')
        if 'template' in form_data:
            update_data['template'] = form_data.get('template')
        if 'status' in form_data:
            try:
                update_data['status'] = int(form_data.get('status'))
            except ValueError:
                pass
        if 'parent_id' in form_data:
            try:
                update_data['parent_id'] = int(form_data.get('parent_id')) if form_data.get('parent_id') else None
            except ValueError:
                update_data['parent_id'] = None
        if 'order_index' in form_data:
            try:
                update_data['order_index'] = int(form_data.get('order_index', 0))
            except ValueError:
                pass
        if 'meta_title' in form_data:
            update_data['meta_title'] = form_data.get('meta_title')
        if 'meta_description' in form_data:
            update_data['meta_description'] = form_data.get('meta_description')
        if 'meta_keywords' in form_data:
            update_data['meta_keywords'] = form_data.get('meta_keywords')

        if not update_data:
            return ApiResponse(
                success=False,
                error="没有提供要更新的字段"
            )

        success = await update_page(db=db, page_id=page_id, **update_data)

        if not success:
            return ApiResponse(
                success=False,
                error="更新页面失败，页面可能不存在"
            )

        return ApiResponse(
            success=True,
            data={"message": "页面更新成功"}
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.delete("/{page_id}")
async def delete_existing_page(
        page_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    删除页面
    
    Args:
        page_id: 页面ID
    """
    try:
        # 添加权限检查（只有作者或管理员可以删除）
        from shared.models.page import Page
        from sqlalchemy import select
        
        stmt = select(Page).where(Page.id == page_id)
        result = await db.execute(stmt)
        page = result.scalar_one_or_none()
        
        if not page:
            return ApiResponse(
                success=False,
                error="页面不存在"
            )
        
        # 检查权限：作者或管理员
        from shared.services.permission_system import permission_manager
        is_admin = await permission_manager.has_permission(db, current_user.id, 'manage_pages')
        is_author = page.author_id == current_user.id
        
        if not is_admin and not is_author:
            return ApiResponse(
                success=False,
                error="没有权限删除此页面"
            )

        success = await delete_page(db=db, page_id=page_id)

        if not success:
            return ApiResponse(
                success=False,
                error="删除页面失败，页面可能不存在"
            )

        return ApiResponse(
            success=True,
            data={"message": "页面删除成功"}
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))
