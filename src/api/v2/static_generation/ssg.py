"""
静态页面生成（SSG）- V2 原生实现

提供静态站点生成的 REST API 接口
优化: 通过 _call_service 消除 8 处重复 try/except 模板
"""
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.static_generation.static_site_generator import ssg_service
from src.api.v2._base import ApiResponse
from src.auth import admin_required
from src.utils.database.unified_manager import db_manager


def _ok(data: Any = None, msg: str = "") -> ApiResponse:
    return ApiResponse(success=True, data=data, message=msg or None)


def _fail(msg: str) -> ApiResponse:
    return ApiResponse(success=False, error=msg)


async def _call(coro, error_prefix: str = "操作") -> ApiResponse:
    """执行 ssg_service 调用，统一处理异常"""
    try:
        result = await coro if hasattr(coro, '__await__') else coro()
        if not result.get('success'):
            return _fail(result.get('error', f'{error_prefix}失败'))
        return _ok(data=result, msg=f'{error_prefix}成功')
    except Exception as e:
        return _fail(f'{error_prefix}失败: {e}')


router = APIRouter(tags=["Static Site Generation"], dependencies=[Depends(admin_required)])


@router.post("/articles/{article_id}", summary="生成文章静态页面")
async def generate_article_page(article_id: int, force: bool = Query(False),
                                db: AsyncSession = Depends(db_manager.get_session)):
    return await _call(
        ssg_service.generate_article_page(db, article_id, force), "文章页面生成")


@router.post("/categories/{category_id}", summary="生成分类列表页")
async def generate_category_page(category_id: int, page: int = Query(1, ge=1),
                                 per_page: int = Query(20, ge=1, le=100),
                                 force: bool = Query(False),
                                 db: AsyncSession = Depends(db_manager.get_session)):
    return await _call(
        ssg_service.generate_category_page(db, category_id, page, per_page, force), "分类页面生成")


@router.post("/homepage", summary="生成首页")
async def generate_homepage(per_page: int = Query(20, ge=1, le=100), force: bool = Query(False),
                            db: AsyncSession = Depends(db_manager.get_session)):
    return await _call(
        ssg_service.generate_homepage(db, per_page, force), "首页生成")


@router.post("/articles/batch", summary="批量生成所有文章")
async def generate_all_articles(batch_size: int = Query(50, ge=1, le=200), force: bool = Query(False),
                                db: AsyncSession = Depends(db_manager.get_session)):
    return await _call(
        ssg_service.generate_all_articles(db, batch_size, force), "批量生成")


@router.delete("/clean", summary="清理旧的静态文件")
async def clean_old_files(max_age_days: int = Query(30, ge=1, le=365)):
    return await _call(
        ssg_service.clean_old_files(max_age_days), "清理")


@router.get("/stats", summary="获取生成统计")
async def get_generation_stats():
    try:
        return _ok(data=ssg_service.get_generation_stats())
    except Exception as e:
        return _fail(f"获取统计失败: {e}")


@router.get("/config", summary="获取配置信息")
async def get_config():
    try:
        return _ok(data={
            'output_dir': str(ssg_service.output_dir),
            'template_dir': str(ssg_service.template_dir),
            'cache_enabled': True,
            'cache_ttl_hours': 24,
            'batch_size_default': 50,
            'supported_pages': ['article', 'category', 'homepage'],
        })
    except Exception as e:
        return _fail(f"获取配置失败: {e}")
