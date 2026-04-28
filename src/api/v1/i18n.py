"""
国际化(i18n)API
提供多语言翻译管理功能
"""

from typing import Dict, Optional

from fastapi import APIRouter, Depends, Query, Body, Request

from shared.services.translation_manager import i18n_service
from src.api.v1.responses import ApiResponse
from src.auth.auth_deps import admin_required as admin_required_api

router = APIRouter(tags=["i18n"])


@router.get("/i18n/languages")
async def get_supported_languages():
    """获取所有支持的语言"""
    try:
        languages = i18n_service.get_supported_languages()

        return ApiResponse(
            success=True,
            data={'languages': languages}
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"获取语言列表失败: {str(e)}")


@router.get("/i18n/detect-language")
async def detect_user_language(request: Request):
    """
    检测用户语言
    
    基于HTTP Accept-Language头自动检测
    """
    try:
        accept_language = request.headers.get('accept-language', '')
        detected = i18n_service.detect_language(accept_language)

        return ApiResponse(
            success=True,
            data={
                'detected_language': detected,
                'is_rtl': i18n_service.is_rtl(detected)
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"检测语言失败: {str(e)}")


@router.get("/i18n/translate")
async def translate_text(
        key: str = Query(..., description="翻译键"),
        lang: Optional[str] = Query(None, description="目标语言"),
        variables: Optional[str] = Query(None, description="变量(JSON格式)"),
        default: Optional[str] = Query(None, description="默认文本")
):
    """
    翻译文本
    
    Args:
        key: 翻译键
        lang: 目标语言代码
        variables: JSON格式的变量
        default: 默认文本
    """
    try:
        # 解析变量
        vars_dict = None
        if variables:
            import json
            try:
                vars_dict = json.loads(variables)
            except:
                pass

        translation = i18n_service.translate(
            key=key,
            language=lang,
            variables=vars_dict,
            default=default
        )

        return ApiResponse(
            success=True,
            data={
                'key': key,
                'translation': translation,
                'language': lang or i18n_service.default_language
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"翻译失败: {str(e)}")


@router.post("/i18n/translations/add")
async def add_translation(
        language: str = Body(...),
        key: str = Body(...),
        value: str = Body(...),
        current_user=Depends(admin_required_api)
):
    """
    添加翻译
    
    Args:
        language: 语言代码
        key: 翻译键
        value: 翻译值
    """
    try:
        result = i18n_service.add_translation(language, key, value)

        if result['success']:
            return ApiResponse(
                success=True,
                message=result['message']
            )
        else:
            return ApiResponse(success=False, error=result['error'])

    except Exception as e:
        return ApiResponse(success=False, error=f"添加翻译失败: {str(e)}")


@router.post("/i18n/translations/batch-add")
async def batch_add_translations(
        language: str = Body(...),
        translations: Dict[str, str] = Body(...),
        current_user=Depends(admin_required_api)
):
    """
    批量添加翻译
    
    Args:
        language: 语言代码
        translations: 翻译字典
    """
    try:
        result = i18n_service.batch_add_translations(language, translations)

        if result['success']:
            return ApiResponse(
                success=True,
                data={'count': result['count']},
                message=result['message']
            )
        else:
            return ApiResponse(success=False, error=result['error'])

    except Exception as e:
        return ApiResponse(success=False, error=f"批量添加失败: {str(e)}")


@router.get("/i18n/translations/missing")
async def get_missing_translations(
        language: str = Query(..., description="要检查的语言"),
        reference: Optional[str] = Query(None, description="参考语言")
):
    """
    获取缺失的翻译
    
    Args:
        language: 要检查的语言
        reference: 参考语言
    """
    try:
        missing = i18n_service.get_missing_translations(language, reference)

        return ApiResponse(
            success=True,
            data={
                'language': language,
                'reference': reference or i18n_service.default_language,
                'missing_keys': missing,
                'count': len(missing)
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"获取缺失翻译失败: {str(e)}")


@router.get("/i18n/translations/export")
async def export_translations(
        language: Optional[str] = Query(None, description="语言代码,None则导出所有"),
        format: str = Query('json', description="导出格式")
):
    """导出翻译"""
    try:
        result = i18n_service.export_translations(language, format)

        if result['success']:
            return ApiResponse(
                success=True,
                data=result['data']
            )
        else:
            return ApiResponse(success=False, error=result['error'])

    except Exception as e:
        return ApiResponse(success=False, error=f"导出失败: {str(e)}")


@router.post("/i18n/translations/import")
async def import_translations(
        data: Dict[str, Dict[str, str]] = Body(...),
        overwrite: bool = Body(False, description="是否覆盖现有翻译"),
        current_user=Depends(admin_required_api)
):
    """
    导入翻译
    
    Args:
        data: 翻译数据
        overwrite: 是否覆盖
    """
    try:
        result = i18n_service.import_translations(data, overwrite)

        if result['success']:
            return ApiResponse(
                success=True,
                data={'imported': result['imported']},
                message=result['message']
            )
        else:
            return ApiResponse(success=False, error=result['error'])

    except Exception as e:
        return ApiResponse(success=False, error=f"导入失败: {str(e)}")


@router.get("/i18n/stats")
async def get_language_stats():
    """获取语言统计信息"""
    try:
        stats = i18n_service.get_language_stats()

        return ApiResponse(
            success=True,
            data={'stats': stats}
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"获取统计失败: {str(e)}")


@router.get("/i18n/template")
async def get_translation_template():
    """获取翻译模板"""
    try:
        template = i18n_service.generate_translation_template()

        return ApiResponse(
            success=True,
            data={'template': template}
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"获取模板失败: {str(e)}")


@router.get("/i18n/rtl-languages")
async def get_rtl_languages():
    """获取RTL(从右到左)语言列表"""
    try:
        rtl_langs = i18n_service.get_rtl_languages()

        return ApiResponse(
            success=True,
            data={'rtl_languages': rtl_langs}
        )

    except Exception as e:
        return ApiResponse(success=False, error=f"获取RTL语言失败: {str(e)}")
