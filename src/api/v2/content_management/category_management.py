"""
分类管理API - 处理分类的创建、更新和删除
"""
from functools import wraps

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article import Article
from shared.models.category import Category, CategorySubscription
from src.api.v2._helpers import ok, fail
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["category-management"])


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            return fail(str(e))
    return wrapper


@router.post("/")
@_catch
async def create_category_api(
        request: Request,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    创建分类API
    """
    # 检查用户权限 - 只有超级用户才能创建分类
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )

    form_data = await request.json()
    name = form_data.get('name')
    description = form_data.get('description', '')
    parent_id = form_data.get('parent_id')

    if not name:
        return fail('分类名称不能为空')

    if parent_id is not None:
        # 验证父分类存在且不构成循环引用
        parent = await db.scalar(select(Category.id).where(Category.id == parent_id))
        if not parent:
            return fail(f'父分类不存在: parent_id={parent_id}')

    # 检查分类名称是否已存在
    existing_category_result = await db.execute(select(Category).filter_by(name=name))
    existing_category = existing_category_result.scalar_one_or_none()
    if existing_category:
        return fail('分类名称已存在')

    # 创建新分类
    category = Category(
        name=name,
        description=description,
        parent_id=parent_id
    )

    db.add(category)
    await db.commit()
    await db.refresh(category)

    return ok(data={
        'id': category.id,
        'name': category.name,
        'description': category.description,
        'created_at': category.created_at.isoformat() if category.created_at else None,
        'updated_at': category.updated_at.isoformat() if category.updated_at else None
    })


@router.put("/{category_id}")
@_catch
async def update_category_api(
        category_id: int,
        request: Request,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    更新分类API
    """
    # 检查用户权限 - 只有超级用户才能更新分类
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )

    category_result = await db.execute(select(Category).filter_by(id=category_id))
    category = category_result.scalar_one_or_none()
    if not category:
        return fail("分类不存在")

    form_data = await request.json()
    name = form_data.get('name')
    description = form_data.get('description', '')
    parent_id = form_data.get('parent_id')

    if not name:
        return fail('分类名称不能为空')

    if parent_id is not None:
        # 验证父分类存在且不构成循环引用
        if parent_id == category_id:
            return fail('分类不能将自身设为父分类')
        parent = await db.scalar(select(Category.id).where(Category.id == parent_id))
        if not parent:
            return fail(f'父分类不存在: parent_id={parent_id}')

    # 检查新名称是否与其他分类冲突
    existing_category_result = await db.execute(
        select(Category).filter_by(name=name).filter(Category.id != category_id))
    existing_category = existing_category_result.scalar_one_or_none()
    if existing_category:
        return fail('分类名称已存在')

    # 更新分类
    category.name = name
    category.description = description
    category.parent_id = parent_id

    await db.commit()
    await db.refresh(category)

    return ok(data={
        'id': category.id,
        'name': category.name,
        'description': category.description,
        'created_at': category.created_at.isoformat() if category.created_at else None,
        'updated_at': category.updated_at.isoformat() if category.updated_at else None
    })


@router.get("")
@_catch
async def get_categories_with_stats_api(
        current_user=Depends(jwt_required),
        page: int = 1,
        per_page: int = 10,
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取分类列表及统计信息API
    """
    # 检查用户权限 - 只有超级用户才能访问
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )

    # 计算偏移量
    offset = (page - 1) * per_page

    # 查询分类及其关联的统计信息
    category_stats_query = (
        select(
            Category,
            func.coalesce(func.count(func.distinct(Article.id)), 0).label('article_count'),
            func.coalesce(func.count(func.distinct(CategorySubscription.id)), 0).label('subscriber_count')
        )
        .select_from(
            Category.__table__.outerjoin(Article.__table__, Category.id == Article.category)
            .outerjoin(CategorySubscription.__table__, Category.id == CategorySubscription.category)
        )
        .group_by(Category.id)
        .order_by(Category.sort_order.asc(), Category.name.asc())
    )
    category_stats = await db.execute(category_stats_query)

    # 获取总数
    total_categories_query = await db.execute(select(func.count()).select_from(Category))
    total_categories = total_categories_query.scalar()

    # 应用分页
    categories_with_stats_query = category_stats_query.offset(offset).limit(per_page)
    categories_with_stats_result = await db.execute(categories_with_stats_query)
    categories_with_stats = categories_with_stats_result.all()

    # 构建返回数据
    categories_data = []
    for item in categories_with_stats:
        category = item[0]
        article_count = item[1]
        subscriber_count = item[2]

        categories_data.append({
            "category": {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'created_at': category.created_at.isoformat() if category.created_at else None,
                'updated_at': category.updated_at.isoformat() if category.updated_at else None
            },
            "article_count": article_count,
            "subscriber_count": subscriber_count
        })

    return ok(data={
        "categories": categories_data,
        "pagination": {
            "current_page": page,
            "pages": (total_categories + per_page - 1) // per_page,
            "total": total_categories,
            "has_next": page < (total_categories + per_page - 1) // per_page,
            "has_prev": page > 1,
            "per_page": per_page
        }
    })


@router.delete("/{category_id}")
@_catch
async def delete_category_api(
        category_id: int,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    删除分类API
    """
    # 检查用户权限 - 只有超级用户才能删除分类
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )

    category_result = await db.execute(select(Category).filter_by(id=category_id))
    category = category_result.scalar_one_or_none()
    if not category:
        return fail("分类不存在")

    # 检查是否有文章属于这个分类
    articles_count_query = await db.execute(
        select(func.count()).select_from(Article).filter_by(category=category_id))
    articles_count = articles_count_query.scalar()
    if articles_count > 0:
        return fail("无法删除：该分类下还有文章")

    # 删除分类
    await db.delete(category)
    await db.commit()

    return ok(data={'message': '分类删除成功'})


# ---------- 分类拖拽排序 ----------
@router.post("/reorder")
@_catch
async def reorder_categories_api(
        request: Request,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    分类拖拽排序

    请求体格式：
    {
        "categories": [
            {"id": 1, "sort_order": 0},
            {"id": 2, "sort_order": 1},
            ...
        ]
    }
    """
    # 检查用户权限 - 只有超级用户才能排序分类
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )

    body = await request.json()
    categories_data = body.get('categories', [])

    if not categories_data:
        return fail("缺少分类数据")

    # 提取分类ID列表
    category_ids = [item['id'] for item in categories_data]

    # 查询所有分类
    query = select(Category).where(Category.id.in_(category_ids))
    result = await db.execute(query)
    categories = {category.id: category for category in result.scalars().all()}

    # 更新排序
    updated_count = 0
    for item in categories_data:
        category_id = item['id']
        new_sort_order = item.get('sort_order', 0)

        if category_id in categories:
            categories[category_id].sort_order = new_sort_order
            updated_count += 1

    await db.commit()

    return ok(data={
        "message": "分类排序更新成功",
        "updated_count": updated_count
    })
