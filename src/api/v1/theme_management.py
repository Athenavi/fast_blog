"""
主题管理API端点
提供主题的完整管理功能
"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.theme import Theme
from shared.services.theme_manager import theme_installer, theme_loader, theme_manager
from src.api.v1.responses import ApiResponse
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(prefix="/themes", tags=["themes"])


@router.get("")
async def list_themes(
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取所有主题列表
    """
    try:
        # 从数据库获取已安装的主题
        query = select(Theme).order_by(Theme.created_at.desc())
        result = await db.execute(query)
        installed_themes = result.scalars().all()

        installed_dict = {t.slug: t for t in installed_themes}

        # 扫描可用主题
        available_themes = theme_manager.discover_themes()

        themes_list = []

        # 添加已安装的主题
        for theme in installed_themes:
            theme_info = {
                "id": theme.id,
                "name": theme.name,
                "slug": theme.slug,
                "version": theme.version,
                "description": theme.description,
                "author": theme.author,
                "author_url": theme.author_url,
                "theme_url": theme.theme_url,
                "screenshot": theme.screenshot,
                "is_active": theme.is_active,
                "is_installed": True,
                "settings": json.loads(theme.settings) if theme.settings else {},
                "supports": json.loads(theme.supports) if theme.supports else [],
                "created_at": theme.created_at.isoformat() if theme.created_at else None,
                "updated_at": theme.updated_at.isoformat() if theme.updated_at else None
            }
            themes_list.append(theme_info)

        # 添加未安装但可用的主题
        for available in available_themes:
            if available['slug'] not in installed_dict:
                theme_info = {
                    "id": None,
                    "name": available.get('name', ''),
                    "slug": available.get('slug', ''),
                    "version": available.get('version', ''),
                    "description": available.get('description', ''),
                    "author": available.get('author', ''),
                    "author_url": available.get('author_url', ''),
                    "theme_url": available.get('theme_url', ''),
                    "screenshot": available.get('screenshot_url', ''),
                    "is_active": False,
                    "is_installed": False,
                    "settings": {},
                    "supports": available.get('supports', []),
                    "created_at": None,
                    "updated_at": None
                }
                themes_list.append(theme_info)

        return ApiResponse(
            success=True,
            data={"themes": themes_list}
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/upload")
async def upload_theme(
        request: Request,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    上传并安装主题ZIP包
    
    Form参数:
        file: ZIP文件
    """
    try:
        # 获取上传的文件
        form = await request.form()
        file = form.get('file')

        if not file or not hasattr(file, 'filename'):
            return ApiResponse(
                success=False,
                error="请上传ZIP文件"
            )

        # 验证文件类型
        filename = file.filename
        if not filename.endswith('.zip'):
            return ApiResponse(
                success=False,
                error="只支持ZIP格式的主题包"
            )

        # 保存临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            # 安装主题
            success, message, metadata = theme_installer.install_from_zip(tmp_path)

            if not success:
                return ApiResponse(success=False, error=message)

            # 在数据库中创建主题记录
            now = datetime.now()
            theme = Theme(
                name=metadata.get('name', ''),
                slug=metadata.get('slug', ''),
                version=metadata.get('version', ''),
                description=metadata.get('description', ''),
                author=metadata.get('author', ''),
                author_url=metadata.get('author_url', ''),
                theme_url=metadata.get('theme_url', ''),
                screenshot=metadata.get('screenshot_url', ''),
                is_active=False,
                is_installed=True,
                settings=json.dumps({}),
                supports=json.dumps(metadata.get('supports', [])),
                created_at=now,
                updated_at=now
            )

            db.add(theme)
            await db.commit()
            await db.refresh(theme)

            return ApiResponse(
                success=True,
                data={
                    "message": message,
                    "theme_id": theme.id,
                    "metadata": metadata
                }
            )
        finally:
            # 清理临时文件
            import os
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        await db.rollback()
        return ApiResponse(success=False, error=f"上传失败: {str(e)}")


@router.post("/install")
async def install_theme(
        request: Request,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    安装主题
    
    Body参数:
        slug: 主题slug（必填）
    """
    try:
        body = await request.json()
        slug = body.get('slug')

        if not slug:
            return ApiResponse(
                success=False,
                error="请指定要安装的主题"
            )

        # 检查是否已安装
        existing_query = select(Theme).where(Theme.slug == slug)
        existing_result = await db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            return ApiResponse(
                success=False,
                error="主题已安装"
            )

        # 读取主题元数据
        metadata_path = theme_manager.themes_dir / slug / "metadata.json"
        if not metadata_path.exists():
            return ApiResponse(
                success=False,
                error="主题元数据不存在"
            )

        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        # 使用不带时区的 datetime
        now = datetime.now()

        # 创建主题记录
        theme = Theme(
            name=metadata.get('name', ''),
            slug=slug,
            version=metadata.get('version', ''),
            description=metadata.get('description', ''),
            author=metadata.get('author', ''),
            author_url=metadata.get('author_url', ''),
            theme_url=metadata.get('theme_url', ''),
            screenshot=metadata.get('screenshot_url', ''),
            is_active=False,
            is_installed=True,
            settings=json.dumps({}),
            supports=json.dumps(metadata.get('supports', [])),
            created_at=now,
            updated_at=now
        )

        db.add(theme)
        await db.commit()
        await db.refresh(theme)

        return ApiResponse(
            success=True,
            data={
                "message": "主题安装成功",
                "theme_id": theme.id
            }
        )

    except Exception as e:
        await db.rollback()
        return ApiResponse(success=False, error=str(e))


@router.post("/scan-and-fix")
async def scan_and_fix_themes(
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    扫描主题目录并修复数据库记录
    将文件系统中存在但数据库中缺失的主题添加到数据库
    """
    try:
        # 获取所有已安装的主题
        query = select(Theme)
        result = await db.execute(query)
        installed_themes = result.scalars().all()
        installed_slugs = {t.slug for t in installed_themes}

        # 扫描文件系统中的所有主题
        available_themes = theme_manager.discover_themes()

        added_count = 0
        skipped_count = 0
        added_themes = []

        # 使用不带时区的 datetime
        now = datetime.now()

        for theme_info in available_themes:
            slug = theme_info.get('slug')

            # 如果主题已在数据库中，跳过
            if slug in installed_slugs:
                skipped_count += 1
                continue

            # 检查元数据文件是否存在
            metadata_path = theme_manager.themes_dir / slug / "metadata.json"
            if not metadata_path.exists():
                continue

            # 创建主题记录
            theme = Theme(
                name=theme_info.get('name', ''),
                slug=slug,
                version=theme_info.get('version', ''),
                description=theme_info.get('description', ''),
                author=theme_info.get('author', ''),
                author_url=theme_info.get('author_url', ''),
                theme_url=theme_info.get('theme_url', ''),
                screenshot=theme_info.get('screenshot_url', ''),
                is_active=False,
                is_installed=True,
                settings=json.dumps({}),
                supports=json.dumps(theme_info.get('supports', [])),
                created_at=now,
                updated_at=now
            )

            db.add(theme)
            added_count += 1
            added_themes.append({
                'slug': slug,
                'name': theme_info.get('name', '')
            })

        # 提交所有新增的主题
        if added_count > 0:
            await db.commit()

        return ApiResponse(
            success=True,
            data={
                "message": f"扫描完成：新增 {added_count} 个主题，跳过 {skipped_count} 个已存在的主题",
                "added_count": added_count,
                "skipped_count": skipped_count,
                "added_themes": added_themes
            }
        )

    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        return ApiResponse(success=False, error=f"扫描失败: {str(e)}")


@router.post("/{theme_slug}/activate")
async def activate_theme(
        theme_slug: str,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    激活主题
    
    Args:
        theme_slug: 主题slug
    """
    try:
        query = select(Theme).where(Theme.slug == theme_slug)
        result = await db.execute(query)
        theme = result.scalar_one_or_none()

        if not theme:
            return ApiResponse(
                success=False,
                error="主题不存在"
            )

        # 激活主题
        success = await theme_manager.activate_theme(theme.slug, db)

        if not success:
            return ApiResponse(
                success=False,
                error="激活主题失败"
            )

        return ApiResponse(
            success=True,
            data={"message": "主题已激活"}
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/{theme_slug}/deactivate")
async def deactivate_theme(
        theme_slug: str,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    停用主题（切换到默认主题）
    
    Args:
        theme_slug: 主题slug
    """
    try:
        # 查找默认主题
        query = select(Theme).where(Theme.slug == 'default')
        result = await db.execute(query)
        default_theme = result.scalar_one_or_none()

        if not default_theme:
            return ApiResponse(
                success=False,
                error="默认主题不存在"
            )

        # 激活默认主题
        success = await theme_manager.activate_theme('default', db)

        if not success:
            return ApiResponse(
                success=False,
                error="切换主题失败"
            )

        return ApiResponse(
            success=True,
            data={"message": "已切换到默认主题"}
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/{theme_slug}/preview")
async def preview_theme(
        theme_slug: str,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    预览主题
    
    Args:
        theme_slug: 主题slug
    """
    try:
        query = select(Theme).where(Theme.slug == theme_slug)
        result = await db.execute(query)
        theme = result.scalar_one_or_none()

        if not theme:
            return ApiResponse(
                success=False,
                error="主题不存在"
            )

        preview_url = theme_manager.preview_theme(theme.slug)

        if not preview_url:
            return ApiResponse(
                success=False,
                error="无法生成预览"
            )

        return ApiResponse(
            success=True,
            data={
                "preview_url": preview_url,
                "theme": {
                    "slug": theme.slug,
                    "name": theme.name,
                }
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/{theme_slug}/generate-screenshot")
async def generate_theme_screenshot(
        theme_slug: str,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    为主题生成截图
    
    Args:
        theme_slug: 主题slug
    """
    try:
        query = select(Theme).where(Theme.slug == theme_slug)
        result = await db.execute(query)
        theme = result.scalar_one_or_none()

        if not theme:
            return ApiResponse(
                success=False,
                error="主题不存在"
            )

        # 生成截图
        success = theme_manager.generate_screenshot(theme.slug)

        if not success:
            return ApiResponse(
                success=False,
                error="生成截图失败"
            )

        # 更新数据库中的截图路径
        theme.screenshot = f"/themes/{theme.slug}/screenshot.png"
        theme.updated_at = datetime.now()
        await db.commit()

        return ApiResponse(
            success=True,
            data={
                "message": "截图已生成",
                "screenshot_url": theme.screenshot
            }
        )

    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        return ApiResponse(success=False, error=str(e))


@router.get("/{theme_slug}/settings")
async def get_theme_settings(
        theme_slug: str,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取主题设置
    
    Args:
        theme_slug: 主题slug
    """
    try:
        query = select(Theme).where(Theme.slug == theme_slug)
        result = await db.execute(query)
        theme = result.scalar_one_or_none()

        if not theme:
            return ApiResponse(
                success=False,
                error="主题不存在"
            )

        settings = json.loads(theme.settings) if theme.settings else {}

        return ApiResponse(
            success=True,
            data={
                "theme_id": theme.id,
                "slug": theme.slug,
                "settings": settings
            }
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.delete("/{theme_slug}")
async def uninstall_theme(
        theme_slug: str,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    卸载主题
    
    Args:
        theme_slug: 主题slug
    """
    try:
        query = select(Theme).where(Theme.slug == theme_slug)
        result = await db.execute(query)
        theme = result.scalar_one_or_none()

        if not theme:
            return ApiResponse(
                success=False,
                error="主题不存在"
            )

        # 不能卸载当前激活的主题
        if theme.is_active:
            return ApiResponse(
                success=False,
                error="不能卸载当前激活的主题，请先切换到其他主题"
            )

        # 从文件系统删除主题
        success, message = theme_installer.uninstall_theme(theme.slug)

        if not success:
            return ApiResponse(success=False, error=message)

        # 从数据库删除记录
        await db.delete(theme)
        await db.commit()

        # 清除缓存
        theme_loader.clear_cache(theme.slug)

        return ApiResponse(
            success=True,
            data={"message": f"主题 '{theme.name}' 已卸载"}
        )

    except Exception as e:
        await db.rollback()
        return ApiResponse(success=False, error=str(e))


@router.get("/active")
async def get_active_theme(
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取当前激活的主题
    """
    try:
        query = select(Theme).where(Theme.is_active == True)
        result = await db.execute(query)
        theme = result.scalar_one_or_none()

        if not theme:
            return ApiResponse(
                success=True,
                data={"theme": None}
            )

        theme_info = {
            "id": theme.id,
            "name": theme.name,
            "slug": theme.slug,
            "version": theme.version,
            "description": theme.description,
            "author": theme.author,
            "screenshot": theme.screenshot,
            "settings": json.loads(theme.settings) if theme.settings else {}
        }

        return ApiResponse(
            success=True,
            data={"theme": theme_info}
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/active/config")
async def get_active_theme_config():
    """
    获取当前激活主题的完整配置(包括CSS变量)
    公开接口,无需认证
    """
    try:
        config = theme_loader.get_active_theme_config()

        if not config:
            return ApiResponse(
                success=True,
                data={"config": None}
            )

        # 获取主题slug（从metadata或config中）
        theme_slug = config.get('metadata', {}).get('slug') or config.get('slug', '')

        if not theme_slug:
            return ApiResponse(
                success=False,
                error="无法获取主题slug"
            )

        # 生成CSS变量
        css_variables = theme_loader.generate_css_variables(theme_slug)
        stylesheet_url = theme_loader.get_theme_stylesheet_url(theme_slug)

        return ApiResponse(
            success=True,
            data={
                "config": config,
                "css_variables": css_variables,
                "stylesheet_url": stylesheet_url
            }
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return ApiResponse(success=False, error=str(e))


@router.post("/{theme_slug}/settings")
async def update_theme_settings(
        theme_slug: str,
        request: Request,
        current_user=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    更新主题设置
    
    Args:
        theme_slug: 主题slug
    
    Body参数:
        settings: 设置对象（JSON）
    """
    try:
        body = await request.json()
        settings = body.get('settings', {})

        query = select(Theme).where(Theme.slug == theme_slug)
        result = await db.execute(query)
        theme = result.scalar_one_or_none()

        if not theme:
            return ApiResponse(
                success=False,
                error="主题不存在"
            )

        success = await theme_manager.update_theme_settings(theme.slug, settings, db)

        if not success:
            return ApiResponse(
                success=False,
                error="更新主题设置失败"
            )

        # 清除缓存
        theme_loader.clear_cache(theme.slug)

        return ApiResponse(
            success=True,
            data={"message": "主题设置已更新"}
        )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/validate")
async def validate_theme(
        request: Request,
        current_user=Depends(jwt_required)
):
    """
    验证主题包结构
    
    Body参数:
        slug: 主题slug
    """
    try:
        body = await request.json()
        slug = body.get('slug')

        if not slug:
            return ApiResponse(
                success=False,
                error="请指定要验证的主题"
            )

        theme_dir = theme_manager.themes_dir / slug

        if not theme_dir.exists():
            return ApiResponse(
                success=False,
                error=f"主题 '{slug}' 不存在"
            )

        # 验证主题结构
        is_valid, message = theme_installer.validate_theme_structure(theme_dir)

        if is_valid:
            # 获取主题信息
            theme_info = theme_installer.get_theme_info(slug)
            return ApiResponse(
                success=True,
                data={
                    "valid": True,
                    "message": message,
                    "theme_info": theme_info
                }
            )
        else:
            return ApiResponse(
                success=False,
                error=message
            )

    except Exception as e:
        return ApiResponse(success=False, error=str(e))
