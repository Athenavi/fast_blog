"""
主题定制器 API 端点
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(prefix="/theme-customizer", tags=["theme-customizer"])


@router.get("/config/{theme_slug}")
async def get_theme_config(
        theme_slug: str,
        current_user_id: int = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取主题配置
    
    Args:
        theme_slug: 主题标识
        
    Returns:
        主题配置对象
    """
    try:
        from shared.services.theme_manager import ThemeCustomizerService

        service = ThemeCustomizerService()
        config = service.get_theme_config(theme_slug)

        return {
            'success': True,
            'data': {
                'theme_slug': theme_slug,
                'config': config,
            }
        }

    except Exception as e:
        import traceback
        print(f"Error getting theme config: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


@router.get("/custom-css/{theme_slug}")
async def get_custom_css(
        theme_slug: str,
        current_user_id: int = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取自定义 CSS
    
    Args:
        theme_slug: 主题标识
        
    Returns:
        自定义 CSS 代码
    """
    try:
        from shared.services.theme_manager import ThemeCustomizerService

        service = ThemeCustomizerService()
        config = service.get_theme_config(theme_slug)

        custom_css = config.get('custom_css', '')

        return {
            'success': True,
            'data': {
                'css': custom_css,
            }
        }

    except Exception as e:
        import traceback
        print(f"Error getting custom CSS: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


@router.put("/config/{theme_slug}")
async def update_theme_config(
        theme_slug: str,
        request: Request,
        current_user_id: int = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    更新主题配置
    
    Args:
        theme_slug: 主题标识
        
    Body参数:
        updates: 配置更新对象(支持嵌套路径)
        
    Returns:
        更新后的配置
    """
    try:
        from shared.services.theme_manager import ThemeCustomizerService

        body = await request.json()
        updates = body.get('updates', {})

        service = ThemeCustomizerService()

        # 验证配置
        validation = service.validate_config(updates)
        if not validation['valid']:
            return {
                'success': False,
                'errors': validation['errors'],
            }

        # 更新配置
        updated_config = service.update_theme_config(theme_slug, updates)

        return {
            'success': True,
            'data': {
                'message': '主题配置已更新',
                'config': updated_config,
            }
        }

    except Exception as e:
        import traceback
        print(f"Error updating theme config: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


@router.post("/preview/css")
async def generate_preview_css(
        request: Request,
        current_user_id: int = Depends(jwt_required)
):
    """
    根据配置生成预览CSS
    
    Args:
        config: 主题配置对象
        
    Returns:
        CSS字符串
    """
    try:
        from shared.services.theme_manager import ThemeCustomizerService

        body = await request.json()
        config = body.get('config', {})

        service = ThemeCustomizerService()
        css = service.generate_preview_css(config)

        return {
            'success': True,
            'data': {
                'css': css,
            }
        }

    except Exception as e:
        import traceback
        print(f"Error generating preview CSS: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


@router.post("/validate")
async def validate_theme_config(
        request: Request,
        current_user_id: int = Depends(jwt_required)
):
    """
    验证主题配置
    
    Args:
        config: 待验证的配置对象
        
    Returns:
        验证结果
    """
    try:
        from shared.services.theme_manager import ThemeCustomizerService

        body = await request.json()
        config = body.get('config', {})

        service = ThemeCustomizerService()
        validation = service.validate_config(config)

        return {
            'success': True,
            'data': validation,
        }

    except Exception as e:
        import traceback
        print(f"Error validating config: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


@router.get("/export/{theme_slug}")
async def export_theme_config(
        theme_slug: str,
        current_user_id: int = Depends(jwt_required)
):
    """
    导出主题配置为JSON
    
    Args:
        theme_slug: 主题标识
        
    Returns:
        JSON配置文件
    """
    try:
        from shared.services.theme_manager import ThemeCustomizerService

        service = ThemeCustomizerService()
        config_json = service.export_config(theme_slug)

        return {
            'success': True,
            'data': {
                'theme_slug': theme_slug,
                'config': config_json,
            },
            'download_url': f'/api/v1/theme-customizer/download/{theme_slug}',
        }

    except Exception as e:
        import traceback
        print(f"Error exporting config: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


@router.post("/import/{theme_slug}")
async def import_theme_config(
        theme_slug: str,
        request: Request,
        current_user_id: int = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    从JSON导入主题配置
    
    Args:
        theme_slug: 主题标识
        
    Body参数:
        config_json: JSON配置字符串
        
    Returns:
        导入结果
    """
    try:
        from shared.services.theme_manager import ThemeCustomizerService

        body = await request.json()
        config_json = body.get('config_json', '')

        service = ThemeCustomizerService()
        result = service.import_config(theme_slug, config_json)

        return result

    except Exception as e:
        import traceback
        print(f"Error importing config: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


@router.get("/presets")
async def get_color_presets():
    """
    获取预定义的颜色方案
    
    Returns:
        颜色方案列表
    """
    presets = {
        'default': {
            'name': '默认',
            'colors': {
                'primary': '#3b82f6',
                'secondary': '#64748b',
                'accent': '#f59e0b',
            }
        },
        'dark': {
            'name': '深色',
            'colors': {
                'primary': '#60a5fa',
                'secondary': '#94a3b8',
                'accent': '#fbbf24',
                'background': '#1f2937',
                'foreground': '#f9fafb',
            }
        },
        'ocean': {
            'name': '海洋',
            'colors': {
                'primary': '#0ea5e9',
                'secondary': '#64748b',
                'accent': '#06b6d4',
            }
        },
        'sunset': {
            'name': '日落',
            'colors': {
                'primary': '#f97316',
                'secondary': '#64748b',
                'accent': '#ec4899',
            }
        },
        'forest': {
            'name': '森林',
            'colors': {
                'primary': '#22c55e',
                'secondary': '#64748b',
                'accent': '#84cc16',
            }
        },
        'purple': {
            'name': '紫色',
            'colors': {
                'primary': '#a855f7',
                'secondary': '#64748b',
                'accent': '#ec4899',
            }
        },
    }

    return {
        'success': True,
        'data': presets,
    }


@router.get("/font-presets")
async def get_font_presets():
    """
    获取预定义的字体组合
    
    Returns:
        字体组合列表
    """
    presets = {
        'modern': {
            'name': '现代',
            'fonts': {
                'heading': 'Inter, system-ui, sans-serif',
                'body': 'Inter, system-ui, sans-serif',
                'mono': 'Fira Code, monospace',
            }
        },
        'classic': {
            'name': '经典',
            'fonts': {
                'heading': 'Georgia, serif',
                'body': 'Georgia, serif',
                'mono': 'Consolas, monospace',
            }
        },
        'minimal': {
            'name': '极简',
            'fonts': {
                'heading': 'Helvetica Neue, sans-serif',
                'body': 'Helvetica Neue, sans-serif',
                'mono': 'Menlo, monospace',
            }
        },
        'elegant': {
            'name': '优雅',
            'fonts': {
                'heading': 'Playfair Display, serif',
                'body': 'Source Sans Pro, sans-serif',
                'mono': 'Fira Code, monospace',
            }
        },
    }

    return {
        'success': True,
        'data': presets,
    }


@router.post("/draft/{theme_slug}")
async def save_draft(
        theme_slug: str,
        request: Request,
        current_user_id: int = Depends(jwt_required)
):
    """
    保存配置草稿(不立即生效)
    
    Args:
        theme_slug: 主题标识
        config: 配置对象
        
    Returns:
        保存结果
    """
    try:
        from shared.services.theme_manager import ThemeCustomizerService

        body = await request.json()
        config = body.get('config', {})

        service = ThemeCustomizerService()
        success = service.save_draft(theme_slug, config)

        return {
            'success': success,
            'message': '草稿已保存' if success else '保存草稿失败',
        }

    except Exception as e:
        import traceback
        print(f"Error saving draft: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


@router.get("/draft/{theme_slug}")
async def load_draft(
        theme_slug: str,
        current_user_id: int = Depends(jwt_required)
):
    """
    加载配置草稿
    
    Args:
        theme_slug: 主题标识
        
    Returns:
        草稿配置
    """
    try:
        from shared.services.theme_manager import ThemeCustomizerService

        service = ThemeCustomizerService()
        draft = service.load_draft(theme_slug)

        return {
            'success': True,
            'data': {
                'draft': draft,
            }
        }

    except Exception as e:
        import traceback
        print(f"Error loading draft: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


@router.post("/draft/{theme_slug}/publish")
async def publish_draft(
        theme_slug: str,
        current_user_id: int = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    发布草稿配置(使其生效)
    
    Args:
        theme_slug: 主题标识
        
    Returns:
        发布结果
    """
    try:
        from shared.services.theme_manager import ThemeCustomizerService

        service = ThemeCustomizerService()
        success = service.publish_draft(theme_slug)

        return {
            'success': success,
            'message': '草稿已发布' if success else '发布失败',
        }

    except Exception as e:
        import traceback
        print(f"Error publishing draft: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


@router.get("/history/{theme_slug}")
async def get_version_history(
        theme_slug: str,
        limit: int = 10,
        current_user_id: int = Depends(jwt_required)
):
    """
    获取配置版本历史
    
    Args:
        theme_slug: 主题标识
        limit: 返回数量限制
        
    Returns:
        版本历史列表
    """
    try:
        from shared.services.theme_manager import ThemeCustomizerService

        service = ThemeCustomizerService()
        history = service.get_version_history(theme_slug, limit)

        return {
            'success': True,
            'data': {
                'history': history,
                'total': len(history),
            }
        }

    except Exception as e:
        import traceback
        print(f"Error getting version history: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


@router.post("/history/{theme_slug}/restore/{version_id}")
async def restore_version(
        theme_slug: str,
        version_id: int,
        current_user_id: int = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    恢复到指定版本
    
    Args:
        theme_slug: 主题标识
        version_id: 版本ID
        
    Returns:
        恢复结果
    """
    try:
        from shared.services.theme_manager import ThemeCustomizerService

        service = ThemeCustomizerService()
        success = service.restore_version(theme_slug, version_id)

        return {
            'success': success,
            'message': '版本已恢复' if success else '恢复失败',
        }

    except Exception as e:
        import traceback
        print(f"Error restoring version: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


@router.put("/custom-css/{theme_slug}")
async def save_custom_css(
        theme_slug: str,
        request: Request,
        current_user_id: int = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    保存自定义 CSS
    
    Args:
        theme_slug: 主题标识
        css: 自定义 CSS 代码
        
    Returns:
        保存结果
    """
    try:
        from shared.services.theme_manager import ThemeCustomizerService

        body = await request.json()
        custom_css = body.get('css', '')

        service = ThemeCustomizerService()

        # 获取当前配置
        config = service.get_theme_config(theme_slug)

        # 更新 custom_css 字段
        config['custom_css'] = custom_css

        # 保存配置
        updated_config = service.update_theme_config(theme_slug, service._flatten_dict(config))

        return {
            'success': True,
            'data': {
                'message': '自定义 CSS 已保存',
                'config': updated_config,
            }
        }

    except Exception as e:
        import traceback
        print(f"Error saving custom CSS: {str(e)}")
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }
