"""
静态页面生成（SSG）- V2 原生实现

提供静态站点生成的 REST API 接口
"""
from functools import wraps
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.static_generation.static_site_generator import ssg_service
from src.api.v2._helpers import ok, fail
from src.auth import admin_required
from src.utils.database.main import get_async_session

router = APIRouter(tags=["Static Site Generation"], dependencies=[Depends(admin_required)])


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return fail(f"操作失败: {e}")
    return wrapper


@router.post("/articles/{article_id}", summary="生成文章静态页面")
@_catch
async def generate_article_page(article_id: int, force: bool = Query(False),
                                db: AsyncSession = Depends(get_async_session)):
    result = await ssg_service.generate_article_page(db, article_id, force)
    if not result.get('success'):
        return fail(result.get('error', '文章页面生成失败'))
    return ok(data=result, msg='文章页面生成成功')


@router.post("/categories/{category_id}", summary="生成分类列表页")
@_catch
async def generate_category_page(category_id: int, page: int = Query(1, ge=1),
                                 per_page: int = Query(20, ge=1, le=100),
                                 force: bool = Query(False),
                                 db: AsyncSession = Depends(get_async_session)):
    result = await ssg_service.generate_category_page(db, category_id, page, per_page, force)
    if not result.get('success'):
        return fail(result.get('error', '分类页面生成失败'))
    return ok(data=result, msg='分类页面生成成功')


@router.post("/homepage", summary="生成首页")
@_catch
async def generate_homepage(per_page: int = Query(20, ge=1, le=100), force: bool = Query(False),
                            db: AsyncSession = Depends(get_async_session)):
    result = await ssg_service.generate_homepage(db, per_page, force)
    if not result.get('success'):
        return fail(result.get('error', '首页生成失败'))
    return ok(data=result, msg='首页生成成功')


@router.post("/articles/batch", summary="批量生成所有文章")
@_catch
async def generate_all_articles(batch_size: int = Query(50, ge=1, le=200), force: bool = Query(False),
                                db: AsyncSession = Depends(get_async_session)):
    result = await ssg_service.generate_all_articles(db, batch_size, force)
    if not result.get('success'):
        return fail(result.get('error', '批量生成失败'))
    return ok(data=result, msg='批量生成成功')


@router.delete("/clean", summary="清理旧的静态文件")
@_catch
async def clean_old_files(max_age_days: int = Query(30, ge=1, le=365)):
    result = await ssg_service.clean_old_files(max_age_days)
    if not result.get('success'):
        return fail(result.get('error', '清理失败'))
    return ok(data=result, msg='清理成功')


@router.get("/stats", summary="获取生成统计")
@_catch
async def get_generation_stats():
    return ok(data=ssg_service.get_generation_stats())


@router.get("/config", summary="获取配置信息")
@_catch
async def get_config():
    return ok(data={
        'output_dir': str(ssg_service.output_dir),
        'template_dir': str(ssg_service.template_dir),
        'cache_enabled': True,
        'cache_ttl_hours': 24,
        'batch_size_default': 50,
        'supported_pages': ['article', 'category', 'homepage'],
    })
