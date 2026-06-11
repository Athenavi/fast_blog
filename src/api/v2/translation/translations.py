"""
翻译管理 API
"""
from typing import Optional
from functools import wraps

from fastapi import APIRouter, HTTPException, Query

from shared.services.translation.translation import translation_service
from src.api.v2._helpers import ok, fail

router = APIRouter(tags=["translations"])


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


@router.get("/items/{locale}/{key}")
@_catch
async def get_translation(
        locale: str,
        key: str,
        default: Optional[str] = None
):
    """
    获取单个翻译
    
    Args:
        locale: 语言代码
        key: 翻译键
        default: 默认值
        
    Returns:
        翻译文本
    """
    value = translation_service.get_translation(locale, key, default)

    return ok(data={
        'locale': locale,
        'key': key,
        'value': value,
    })


@router.post("/items/{locale}/{key}")
@_catch
async def set_translation(
        locale: str,
        key: str,
        value: str
):
    """
    设置翻译
    
    Args:
        locale: 语言代码
        key: 翻译键
        value: 翻译值
        
    Returns:
        操作结果
    """
    translation_service.set_translation(locale, key, value)

    return ok(msg='Translation updated')


@router.get("/items/{locale}")
@_catch
async def get_all_translations(locale: str):
    """
    获取所有翻译
    
    Args:
        locale: 语言代码
        
    Returns:
        翻译字典
    """
    translations = translation_service.get_all_translations(locale)

    return ok(data=translations)


@router.get("/progress")
@_catch
async def get_translation_progress(
        source_locale: str = Query('zh-CN', description="源语言")
):
    """
    获取翻译进度
    
    Args:
        source_locale: 源语言
        
    Returns:
        各语言的翻译进度
    """
    progress = translation_service.get_translation_progress(source_locale)

    return ok(data=progress)


@router.get("/missing/{locale}")
@_catch
async def get_missing_translations(
        locale: str,
        source_locale: str = Query('zh-CN', description="源语言")
):
    """
    获取缺失的翻译
    
    Args:
        locale: 目标语言
        source_locale: 源语言
        
    Returns:
        缺失的翻译键列表
    """
    missing = translation_service.get_missing_translations(locale, source_locale)

    return ok(data={
        'locale': locale,
        'missing_keys': missing,
        'count': len(missing),
    })


@router.get("/export")
@_catch
async def export_translations(
        format: str = Query('json', enum=['json'], description="导出格式")
):
    """
    导出所有翻译
    
    Args:
        format: 导出格式
        
    Returns:
        导出的文件
    """
    content = translation_service.export_translations(format)

    return ok(data=content.decode('utf-8'))
