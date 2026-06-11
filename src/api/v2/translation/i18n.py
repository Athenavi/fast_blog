"""
多语言 API
提供翻译管理、语言检测、自动翻译等功能
"""
from typing import Optional, Dict, Any, List
from functools import wraps
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Header

from shared.services.translation.translation import translation_service
from src.api.v2._helpers import ok, fail
from src.auth.auth_deps import jwt_required_dependency as jwt_required, get_current_user

router = APIRouter(tags=["i18n"])


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


# ==================== 语言管理 ====================

@router.get("/languages", summary="获取支持的语言列表")
@_catch
async def get_supported_languages():
    """
    获取所有支持的语言
    
    Returns:
        语言列表
    """
    languages = translation_service.get_supported_languages()
    
    return ok(data={
        'languages': languages,
        'default_language': translation_service.default_language,
        'total': len(languages)
    })


@router.get("/detect", summary="检测用户语言")
@_catch
async def detect_language(
        accept_language: Optional[str] = Header(None, description="Accept-Language头"),
):
    """
    根据HTTP头检测用户首选语言
    
    Args:
        accept_language: Accept-Language头
        
    Returns:
        检测到的语言
    """
    detected_lang = translation_service.detect_language(accept_language)
    
    return ok(data={
        'detected_language': detected_lang,
        'accept_language': accept_language,
    })


# ==================== 翻译管理 ====================

@router.get("/translate/{key}", summary="获取翻译")
@_catch
async def get_translation(
        key: str,
        language: Optional[str] = Query(None, description="语言代码"),
        default: Optional[str] = Query(None, description="默认值"),
):
    """
    获取指定键的翻译
    
    Args:
        key: 翻译键
        language: 语言代码
        default: 默认值
        
    Returns:
        翻译文本
    """
    translation = translation_service.get_translation(key, language, default)
    
    return ok(data={
        'key': key,
        'translation': translation,
        'language': language or translation_service.default_language,
    })


@router.post("/translate", summary="批量获取翻译")
@_catch
async def batch_get_translations(
        keys: List[str] = Body(..., description="翻译键列表"),
        language: Optional[str] = Body(None, description="语言代码"),
):
    """
    批量获取多个翻译键的翻译
    
    Args:
        keys: 翻译键列表
        language: 语言代码
        
    Returns:
        翻译字典
    """
    translations = {}
    for key in keys:
        translations[key] = translation_service.get_translation(key, language)

    return ok(data={
        'translations': translations,
        'language': language or translation_service.default_language,
    })


@router.put("/translate/{key}", summary="设置翻译")
@_catch
async def set_translation(
        key: str,
        value: str = Body(..., description="翻译值"),
        language: str = Body(..., description="语言代码"),
        current_user=Depends(jwt_required)
):
    """
    设置或更新翻译
    
    Args:
        key: 翻译键
        value: 翻译值
        language: 语言代码
        
    Returns:
        设置结果
    """
    # 检查权限（需要admin权限）
    # 这里简化处理，实际应该检查用户权限

    translation_service.set_translation(key, value, language)

    return ok(msg=f"Translation set for key '{key}' in {language}")


@router.post("/translate/bulk", summary="批量设置翻译")
@_catch
async def bulk_set_translations(
        translations: Dict[str, str] = Body(..., description="翻译字典"),
        language: str = Body(..., description="语言代码"),
        current_user=Depends(jwt_required)
):
    """
    批量设置翻译
    
    Args:
        translations: 翻译字典 {key: value}
        language: 语言代码
        
    Returns:
        设置结果
    """
    for key, value in translations.items():
        translation_service.set_translation(key, value, language)
    
    return ok(
        msg=f"Bulk translations set for {language}",
        data={
            'count': len(translations),
            'language': language,
        }
    )


# ==================== 自动翻译 ====================

@router.post("/auto-translate", summary="自动翻译")
@_catch
async def auto_translate(
        text: str = Body(..., description="要翻译的文本"),
        from_lang: str = Body(..., description="源语言"),
        to_lang: str = Body(..., description="目标语言"),
        api_key: Optional[str] = Body(None, description="API密钥"),
        current_user=Depends(jwt_required)
):
    """
    使用第三方API自动翻译文本
    
    Args:
        text: 要翻译的文本
        from_lang: 源语言
        to_lang: 目标语言
        api_key: API密钥
        
    Returns:
        翻译结果
    """
    translated_text = await translation_service.auto_translate(
        text=text,
        from_lang=from_lang,
        to_lang=to_lang,
        api_key=api_key
    )

    return ok(data={
        'original_text': text,
        'translated_text': translated_text,
        'from_language': from_lang,
        'to_language': to_lang,
    })


# ==================== 翻译统计和管理 ====================

@router.get("/missing/{language}", summary="获取缺失翻译")
@_catch
async def get_missing_translations(
        language: str,
        current_user=Depends(jwt_required)
):
    """
    获取指定语言缺失的翻译键
    
    Args:
        language: 语言代码
        
    Returns:
        缺失的翻译键列表
    """
    missing_keys = translation_service.get_missing_translations(language)

    return ok(data={
        'language': language,
        'missing_keys': missing_keys,
        'count': len(missing_keys),
    })


@router.get("/stats", summary="获取翻译统计")
@_catch
async def get_translation_stats(current_user=Depends(jwt_required)):
    """
    获取所有语言的翻译统计信息
    
    Returns:
        统计数据
    """
    stats = translation_service.get_translation_stats()

    return ok(data={
        'statistics': stats,
        'default_language': translation_service.default_language,
    })


@router.get("/export", summary="导出翻译")
@_catch
async def export_translations(
        language: Optional[str] = Query(None, description="语言代码（None表示所有）"),
        current_user=Depends(jwt_required)
):
    """
    导出翻译数据
    
    Args:
        language: 语言代码
        
    Returns:
        翻译数据
    """
    exported_data = translation_service.export_translations(language)
    
    return ok(data=exported_data)


@router.post("/import", summary="导入翻译")
@_catch
async def import_translations(
        language: str = Body(..., description="语言代码"),
        translations: Dict[str, str] = Body(..., description="翻译数据"),
        merge: bool = Body(True, description="是否合并"),
        current_user=Depends(jwt_required)
):
    """
    导入翻译数据
    
    Args:
        language: 语言代码
        translations: 翻译数据
        merge: 是否合并
        
    Returns:
        导入结果
    """
    translation_service.import_translations(language, translations, merge)
    
    return ok(
        msg=f"Translations imported for {language}",
        data={
            'language': language,
            'count': len(translations),
            'merged': merge,
        }
    )


@router.get("/keys", summary="获取所有翻译键")
@_catch
async def get_all_keys(
        language: Optional[str] = Query(None, description="语言代码"),
        current_user=Depends(jwt_required)
):
    """
    获取所有翻译键
    
    Args:
        language: 语言代码（None表示默认语言）
        
    Returns:
        翻译键列表
    """
    lang = language or translation_service.default_language
    keys = list(translation_service.translation_cache.get(lang, {}).keys())
    
    return ok(data={
        'language': lang,
        'keys': keys,
        'total': len(keys),
    })
