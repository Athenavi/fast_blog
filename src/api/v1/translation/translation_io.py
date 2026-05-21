"""
翻译导出/导入 API

提供翻译文件的导出和导入功能
支持JSON、YAML、PO格式
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Body, UploadFile, File

from shared.services.translation.translation_io import translation_io
from src.api.v1.core.responses import ApiResponse
from src.auth.auth_deps import jwt_required_dependency as jwt_required

router = APIRouter()


@router.get("/export/{language_code}", summary="导出翻译", description="导出指定语言的翻译文件")
async def export_translation(
        language_code: str,
        format: str = Query('json', pattern='^(json|yaml|po)$', description="导出格式"),
        current_user=Depends(jwt_required),
):
    """导出翻译"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    # TODO: 从实际的翻译服务获取数据
    # 这里使用示例数据
    sample_translations = {
        'hello': {'translation': '你好', 'translated': True},
        'welcome': {'translation': '欢迎', 'translated': True},
        'goodbye': {'translation': '', 'translated': False},
    }

    if format == 'json':
        content = translation_io.export_to_json(sample_translations, language_code)
        media_type = 'application/json'
        filename = f'{language_code}.json'
    elif format == 'yaml':
        content = translation_io.export_to_yaml(sample_translations, language_code)
        media_type = 'application/x-yaml'
        filename = f'{language_code}.yaml'
    elif format == 'po':
        content = translation_io.export_to_po(sample_translations, language_code)
        media_type = 'text/plain'
        filename = f'{language_code}.po'
    else:
        return ApiResponse(success=False, error=f"Unsupported format: {format}")

    from fastapi.responses import Response

    return Response(
        content=content,
        media_type=media_type,
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
        }
    )


@router.post("/export/all", summary="批量导出", description="批量导出所有语言的翻译文件")
async def export_all_translations(
        format: str = Body('json', pattern='^(json|yaml|po)$', description="导出格式"),
        current_user=Depends(jwt_required),
):
    """批量导出"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    # TODO: 从实际的翻译服务获取所有语言数据
    sample_all_translations = {
        'zh-CN': {
            'hello': {'translation': '你好', 'translated': True},
            'welcome': {'translation': '欢迎', 'translated': True},
        },
        'en-US': {
            'hello': {'translation': 'Hello', 'translated': True},
            'welcome': {'translation': 'Welcome', 'translated': True},
        },
    }

    results = translation_io.batch_export(sample_all_translations, format=format)

    return ApiResponse(
        success=True,
        message=f"Exported {len(results)} languages",
        data={
            'languages': list(results.keys()),
            'format': format,
            'total_files': len(results),
        }
    )


@router.post("/import/{language_code}", summary="导入翻译", description="导入翻译文件")
async def import_translation(
        language_code: str,
        file: UploadFile = File(..., description="翻译文件"),
        current_user=Depends(jwt_required),
):
    """导入翻译"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 读取文件内容
    content = await file.read()
    content_str = content.decode('utf-8')

    # 根据文件格式导入
    filename = file.filename.lower()
    if filename.endswith('.json'):
        result = translation_io.import_from_json(content_str)
    elif filename.endswith('.yaml') or filename.endswith('.yml'):
        result = translation_io.import_from_yaml(content_str)
    elif filename.endswith('.po'):
        result = translation_io.import_from_po(content_str)
    else:
        return ApiResponse(
            success=False,
            error="Unsupported file format. Use .json, .yaml, or .po"
        )

    if result['success']:
        # Save imported translations to database
        # Example implementation:
        # from shared.models.translation import Translation
        # language_code = result.get('language')
        # translations = result.get('translations', {})
        # 
        # for key, trans_data in translations.items():
        #     stmt = select(Translation).where(
        #         (Translation.key == key) & (Translation.language == language_code)
        #     )
        #     db_result = await db.execute(stmt)
        #     existing = db_result.scalar_one_or_none()
        #     
        #     if existing:
        #         existing.translation = trans_data.get('translation', '')
        #         existing.is_translated = trans_data.get('translated', False)
        #         existing.updated_at = datetime.now()
        #     else:
        #         new_translation = Translation(
        #             key=key,
        #             language=language_code,
        #             translation=trans_data.get('translation', ''),
        #             is_translated=trans_data.get('translated', False),
        #         )
        #         db.add(new_translation)
        # 
        # await db.commit()
        
        return ApiResponse(
            success=True,
            message=result['message'],
            data={
                'language': result.get('language'),
                'total_strings': result.get('total_strings'),
            }
        )
    else:
        return ApiResponse(
            success=False,
            error=result.get('error', 'Import failed')
        )


@router.post("/import/batch", summary="批量导入", description="批量导入多个翻译文件")
async def batch_import_translations(
        files: List[UploadFile] = File(..., description="翻译文件列表"),
        format: str = Query('json', pattern='^(json|yaml|po)$', description="文件格式"),
        current_user=Depends(jwt_required),
):
    """批量导入"""
    # 检查权限
    is_admin = getattr(current_user, 'is_superuser', False) or getattr(current_user, 'is_staff', False)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 读取所有文件
    file_contents = {}
    for file in files:
        content = await file.read()
        file_contents[file.filename] = content.decode('utf-8')

    # Batch import results
    results = translation_io.batch_import(file_contents, format=format)

    # Save successfully imported translations to database
    # Example implementation:
    # for detail in results.get('details', []):
    #     if detail.get('success'):
    #         language_code = detail.get('language')
    #         translations = detail.get('translations', {})
    #         # Similar save logic as single import above
    #         pass
    # 
    # await db.commit()

    return ApiResponse(
        success=results['successful'] > 0,
        message=f"Imported {results['successful']} files, {results['failed']} failed",
        data=results
    )


@router.get("/formats", summary="支持的格式", description="获取支持的导入导出格式")
async def get_supported_formats():
    """获取支持的格式"""
    formats = {
        'export': ['json', 'yaml', 'po'],
        'import': ['json', 'yaml', 'po'],
        'descriptions': {
            'json': {
                'name': 'JSON',
                'extension': '.json',
                'mime_type': 'application/json',
                'description': 'JavaScript对象 notation，易于阅读和编辑',
            },
            'yaml': {
                'name': 'YAML',
                'extension': '.yaml/.yml',
                'mime_type': 'application/x-yaml',
                'description': '人类友好的数据序列化格式',
            },
            'po': {
                'name': 'PO (Gettext)',
                'extension': '.po',
                'mime_type': 'text/plain',
                'description': 'GNU Gettext翻译文件格式，广泛用于国际化',
            },
        }
    }

    return ApiResponse(
        success=True,
        data=formats
    )


@router.get("/examples", summary="使用示例", description="获取翻译导出导入使用示例")
async def get_usage_examples():
    """获取使用示例"""
    examples = {
        "export_single": {
            'description': '导出单个语言',
            'example': '''
# 导出为JSON
GET /api/v1/translation/export/zh-CN?format=json

# 导出为YAML
GET /api/v1/translation/export/zh-CN?format=yaml

# 导出为PO
GET /api/v1/translation/export/zh-CN?format=po
            '''.strip()
        },
        "export_batch": {
            'description': '批量导出',
            'example': '''
POST /api/v1/translation/export/all
Content-Type: application/json

{
  "format": "json"
}

# 返回所有语言的导出文件
            '''.strip()
        },
        "import_single": {
            'description': '导入单个文件',
            'example': '''
POST /api/v1/translation/import/zh-CN
Content-Type: multipart/form-data

file: zh-CN.json
            '''.strip()
        },
        "import_batch": {
            'description': '批量导入',
            'example': '''
POST /api/v1/translation/import/batch?format=json
Content-Type: multipart/form-data

files: [zh-CN.json, en-US.json, ja-JP.json]
            '''.strip()
        },
        "file_formats": {
            'description': '文件格式说明',
            'formats': {
                'JSON': {
                    'structure': {
                        'language': '语言代码',
                        'exported_at': '导出时间',
                        'total_strings': '字符串总数',
                        'translations': {
                            'key': {
                                'translation': '翻译内容',
                                'translated': '是否已翻译'
                            }
                        }
                    }
                },
                'YAML': '与JSON结构相同，但使用YAML语法',
                'PO': '标准Gettext PO格式，包含msgid和msgstr',
            }
        },
        "best_practices": {
            'description': '最佳实践',
            'practices': [
                '定期导出备份翻译文件',
                '使用版本控制系统管理翻译文件',
                '导入前先在测试环境验证',
                '保持翻译键的一致性',
                '为翻译人员提供清晰的上下文说明',
                '使用自动化脚本定期检查未翻译的字符串',
            ]
        }
    }

    return ApiResponse(
        success=True,
        data=examples
    )
