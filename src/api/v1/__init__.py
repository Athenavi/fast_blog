import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, Request, Depends, Query, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User
from src.api.v1.misc import logger
from src.auth.auth_deps import _get_current_active_user
from src.extensions import cache, get_async_db_session as get_async_db
from src.setting import app_config
from src.utils.image.processing import generate_thumbnail, get_file_mime_type
from src.utils.security.safe import is_valid_hash


# ------------------------------------------------------------
# 1. 延迟导入子模块（避免循环依赖）
# ------------------------------------------------------------
def _import_modules():
    """延迟导入所有子模块，返回模块字典"""
    import importlib
    import traceback

    modules = {}
    # 所有需要导入的模块名称
    module_names = [
        "articles", "home", "responses", "users", "blog", "category_ext",
        "category_management", "admin_settings", "user_management", "user_settings",
        "media", "notifications", "misc", "comment_config", "comments",
        "cache_management", "two_factor_auth", "article_revisions",
        "scheduled_publish", "feed", "menu_management",
        "plugin_management", "theme_management", "seo",
        "form_builder", "i18n", "widgets",
        "wordpress_import", "webhook_management",
        "breadcrumbs", "maintenance", "article_password",
        "page_templates", "comment_subscriptions", "installation", "system", "screen_options", "query_monitor", "amp",
        "css_optimizer", "translation_memory", "translation_service", "internal_links", "migrations",
        "template_hierarchy",
    ]

    for name in module_names:
        try:
            module = importlib.import_module(f".{name}", package=__name__)
            modules[name] = module
        except Exception as e:
            print(f"Failed to import module {name}: {e}")
            print(traceback.format_exc())
            modules[name] = None  # 确保键存在
    return modules


# 对外暴露的模块符号（保持与原有 __all__ 一致）
__all__ = [
    "articles", "dashboard", "responses", "users", "blog", "category_ext",
    "category_management", "admin_settings", "user_settings", "media",
    "notifications", "misc", "comment_config", "comments", "cache_management",
    "two_factor_auth", "article_revisions", "scheduled_publish", "feed", "menu_management", "plugin_management",
    "theme_management", "seo", "form_builder",
    "i18n", "widgets", "theme_customizer",
    "webhook_management", "breadcrumbs",
    "maintenance", "article_password", "page_templates", "comment_subscriptions",
    "installation", "system", "screen_options", "query_monitor", "amp", "css_optimizer", "translation_memory",
    "translation_service", "internal_links", "migrations", "template_hierarchy",
]

api_v1_router = APIRouter(prefix="/api/v1", tags=["api-v1"])


# ------------------------------------------------------------
# 2. 配置驱动的路由注册
# ------------------------------------------------------------
def _include_routers():
    """使用配置驱动的方式注册所有子模块路由"""
    modules = _import_modules()

    # 路由注册配置： (模块名, 是否必须包含, prefix)
    router_configs = [
        ("articles", True, "/articles"),
        ("users", True, ""),
        ("blog", True, "/blog"),
        ("category_ext", True, ""),
        ("category_management", True, ""),
        ("admin_settings", True, ""),
        ("user_management", True, ""),
        ("user_settings", True, ""),
        ("media", True, "/media"),
        ("notifications", True, ""),
        ("misc", True, ""),
        ("comment_config", True, ""),
        ("comments", True, ""),
        ("cache_management", True, ""),
        ("two_factor_auth", True, ""),
        ("article_revisions", True, ""),
        ("scheduled_publish", True, ""),
        ("feed", True, ""),
        ("menu_management", True, ""),
        ("plugin_management", True, ""),
        ("theme_management", True, ""),
        ("seo", True, ""),
        ("form_builder", True, ""),
        ("i18n", True, ""),
        ("widgets", True, ""),
        ("wordpress_import", True, ""),
        ("webhook_management", True, ""),
        ("breadcrumbs", True, "/breadcrumbs"),
        ("maintenance", True, "/maintenance"),
        ("article_password", True, "/articles"),
        ("page_templates", True, "/page-templates"),
        ("comment_subscriptions", True, "/comment-subscriptions"),
        ("installation", True, "/install"),  # 安装向导
        ("system", True, "/system"),
        ("screen_options", True, "/screen-options"),  # 屏幕选项
        ("query_monitor", True, "/query-monitor"),
        ("amp", True, "/amp"),
        ("css_optimizer", True, "/css-optimizer"),
        ("translation_memory", True, "/translation-memory"),
        ("translation_service", True, "/translation-service"),
        ("internal_links", True, "/internal-links"),
        ("migrations", True, "/migrations"),
        ("template_hierarchy", True, "/template-hierarchy"),
    ]

    for name, required, prefix in router_configs:
        if modules.get(name):
            api_v1_router.include_router(modules[name].router, prefix=prefix)
        elif required:
            print(f"Warning: {name} module could not be imported, skipping router inclusion")

    # 特殊处理的 home 模块（尝试新版，失败回退旧版）
    try:
        import src.api.v1.home as home_module
        api_v1_router.include_router(home_module.router)
        # 可选：打印 worker 信息（此处省略环境变量控制以保持简洁）
    except ImportError:
        if modules.get("home"):
            api_v1_router.include_router(modules["home"].router)
            print("Warning: Using legacy home module")
        else:
            print("Warning: home module could not be imported, skipping")

    # 单独注册的额外模块列表（这些模块未在 module_names 中统一导入）
    extra_modules = [
        "block_patterns",
        "translation_management",
        "redirect_management",
        "oauth_login",
        "hreflang_api",
        "machine_translation",
        "plugin_dependencies",
        "custom_block_patterns",
        "dashboard",
    ]
    for mod_name in extra_modules:
        try:
            mod = __import__(f"src.api.v1.{mod_name}", fromlist=["router"])
            api_v1_router.include_router(mod.router)
        except ImportError as e:
            print(f"Failed to import {mod_name} module: {e}")
        except Exception as e:
            print(f"Error importing {mod_name} module: {e}")


_include_routers()


# ------------------------------------------------------------
# 3. 自定义端点（保持原有功能不变）
# ------------------------------------------------------------
# QR 登录相关
@api_v1_router.get("/qr/generate")
async def api_generate_qr(request: Request):
    from src.api.v1.user_utils.qrlogin_utils import qr_login
    try:
        return await qr_login(
            request,
            sys_version="1.0",
            global_encoding=app_config.global_encoding,
            domain=app_config.domain,
            cache_instance=cache,
        )
    except Exception as e:
        logger.error(f"QR generation failed: {e}", exc_info=True)
        return {"success": False, "message": f"Failed to generate QR code: {str(e)}"}


@api_v1_router.get("/qr/status")
async def api_check_qr_status(request: Request):
    from src.api.v1.user_utils.qrlogin_utils import check_qr_login_back
    try:
        return await check_qr_login_back(request, cache)
    except Exception as e:
        logger.error(f"QR status check failed: {e}")
        return {"success": False, "message": "Failed to check QR code status"}


@api_v1_router.get("/phone/scan")
async def api_phone_scan(request: Request):
    from src.api.v1.user_utils.qrlogin_utils import phone_scan_back
    try:
        current_user = await _get_current_active_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return {
                "success": False,
                "requires_auth": True,
                "message": "User not authenticated. Please log in to continue.",
                "action": "redirect_to_login",
            }
        raise e
    try:
        return await phone_scan_back(request, current_user=current_user, cache_instance=cache)
    except Exception as e:
        logger.error(f"Phone scan failed: {e}")
        return {"success": False, "message": f"Failed to handle phone scan: {str(e)}"}


# 用户名/邮箱可用性检查
@api_v1_router.get("/check-username")
async def api_check_username(username: str, db: AsyncSession = Depends(get_async_db)):
    try:
        existing = await db.scalar(
            select(User).where(func.lower(User.username) == func.lower(username))
        )
        return JSONResponse({"success": True, "available": existing is None, "exists": existing is not None})
    except Exception as e:
        logger.error(f"Check username error: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@api_v1_router.get("/check-email")
async def api_check_email(email: str, db: AsyncSession = Depends(get_async_db)):
    try:
        existing = await db.scalar(
            select(User).where(func.lower(User.email) == func.lower(email))
        )
        return JSONResponse({"success": True, "available": existing is None, "exists": existing is not None})
    except Exception as e:
        logger.error(f"Check email error: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# 公共缩略图
@api_v1_router.get("/thumbnail")
async def public_media_thumbnail(
        request: Request,
        data: str = Query(...)
):
    import traceback
    from fastapi.responses import Response
    from shared.utils.logger import get_logger

    logger = get_logger(__name__)

    try:
        logger.info("=" * 80)
        logger.info(f"收到缩略图请求")
        logger.info(f"  原始 data 参数: {data}")
        logger.info(f"  请求 URL: {request.url}")
        logger.info(f"  请求头: {dict(request.headers)}")

        clean_data = data.split(".")[0]
        logger.info(f"  清理后的 hash: {clean_data}")

        if not is_valid_hash(64, clean_data):
            logger.error(f"  [ERROR] Hash 验证失败: {clean_data}")
            raise HTTPException(status_code=400, detail="无效的文件哈希")

        data = clean_data
        thumb_path = Path(f"storage/thumbnails/{data[:2]}/{data}.jpg")
        logger.info(f"  缩略图路径: {thumb_path.absolute()}")
        logger.info(f"  缩略图存在: {thumb_path.exists()}")

        # 如果缩略图不存在，尝试生成
        if not thumb_path.exists():
            logger.info(f"  → 缩略图不存在，开始生成流程")
            original_path = Path(f"storage/objects/{data[:2]}/{data}")
            logger.info(f"  原始文件路径: {original_path.absolute()}")
            logger.info(f"  原始文件存在: {original_path.exists()}")

            if not original_path.exists():
                logger.error(f"  [ERROR] 原始文件不存在！")
                logger.error(f"     检查目录是否存在: {(original_path.parent).exists()}")
                if original_path.parent.exists():
                    logger.error(f"     目录内容: {list(original_path.parent.iterdir())}")
                raise HTTPException(status_code=404, detail=f"文件不存在: {data}")

            logger.info(f"  → 创建缩略图目录: {thumb_path.parent}")
            thumb_path.parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"  → 开始异步生成缩略图...")
            thumbnail_generated = await generate_thumbnail_async(original_path, thumb_path, filehash=data)
            logger.info(f"  → 生成完成，缩略图存在: {thumb_path.exists()}, 生成结果: {thumbnail_generated}")

            if thumb_path.exists():
                logger.info(f"     缩略图大小: {thumb_path.stat().st_size} bytes")

        # 再次检查缩略图是否存在
        if not thumb_path.exists():
            logger.warning(f"  [WARN] 缩略图不存在（可能是非图片/视频文件）")
            logger.warning(f"     路径: {thumb_path.absolute()}")
            # 对于不支持缩略图的文件，返回 404 而不是 500
            raise HTTPException(status_code=404, detail="该文件类型不支持缩略图")

        # 生成 ETag：直接使用文件修改时间
        try:
            stat = thumb_path.stat()
            etag = f'"{int(stat.st_mtime)}"'
            logger.info(f"  ETag: {etag}")
        except Exception as e:
            logger.error(f"  [ERROR] 生成 ETag 失败: {e}")
            logger.error(traceback.format_exc())
            etag = f'"0"'

        # 检查客户端是否有缓存（If-None-Match）
        if_none_match = request.headers.get("if-none-match")
        logger.info(f"  If-None-Match: {if_none_match}")
        logger.info(f"  匹配结果: {if_none_match == etag if if_none_match else 'N/A'}")

        if if_none_match and if_none_match == etag:
            logger.info(f"  [OK] 命中 ETag 缓存，返回 304")
            logger.info("=" * 80)
            return Response(
                status_code=304,
                headers={
                    "ETag": etag,
                    "Access-Control-Allow-Origin": "*",
                    "Vary": "Origin"
                }
            )

        # 返回缩略图文件
        file_size = thumb_path.stat().st_size
        logger.info(f"  [OK] 返回缩略图 - 大小: {file_size} bytes")
        logger.info("=" * 80)

        response = FileResponse(
            thumb_path,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=2592000",
                "ETag": etag,
                "Access-Control-Allow-Origin": "*",
                "Vary": "Origin"
            }
        )

        response.headers["ETag"] = etag
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Vary"] = "Origin"

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"[ERROR] 缩略图接口发生未预期错误")
        logger.error(f"  错误类型: {type(e).__name__}")
        logger.error(f"  错误信息: {str(e)}")
        logger.error(f"  堆栈跟踪:")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


async def generate_thumbnail_async(source_path: Path, thumb_path: Path, filehash: str) -> bool:
    """异步生成缩略图（在线程池中执行）
    
    Returns:
        bool: 是否成功生成缩略图
    """
    import os

    try:
        mime_type = await get_file_mime_type(filehash)
        logger.info(f"   [INFO] 文件 MIME 类型: {mime_type}")
    except Exception as e:
        logger.warning(f"   [WARN] 无法获取 MIME 类型: {e}")
        mime_type = "application/octet-stream"

    def sync_generate():
        try:
            # 只处理图片、视频和音频
            if mime_type.startswith("image/"):
                logger.info(f"   [IMAGE] 开始生成图片缩略图...")
                generate_thumbnail(str(source_path), str(thumb_path))
                success = os.path.exists(str(thumb_path))
                logger.info(f"   [{'OK' if success else 'FAIL'}] 图片缩略图生成{'成功' if success else '失败'}")
                return success
            elif mime_type.startswith("video/"):
                logger.info(f"   [VIDEO] 开始生成视频缩略图...")
                from src.utils.image.processing import create_video_thumbnail
                success = create_video_thumbnail(str(source_path), str(thumb_path))
                logger.info(f"   [{'OK' if success else 'FAIL'}] 视频缩略图生成{'成功' if success else '失败'}")
                return success
            elif mime_type.startswith("audio/"):
                logger.info(f"   [AUDIO] 开始生成音频缩略图（提取封面）...")
                from src.utils.image.audio_processor import create_audio_thumbnail
                success = create_audio_thumbnail(str(source_path), str(thumb_path))
                logger.info(f"   [{'OK' if success else 'FAIL'}] 音频缩略图生成{'成功' if success else '失败'}")
                return success
            else:
                # 对于不支持的文件类型（PDF、ZIP等），不生成缩略图
                logger.info(f"   [INFO] 文件类型 {mime_type} 不支持缩略图，跳过生成")
                return False
        except Exception as e:
            logger.error(f"   [ERROR] 缩略图生成失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, sync_generate)
        return result


# ------------------------------------------------------------
# 4. 最后注册 redirect 模块（包含通配符路由，必须在所有具体路由之后）
# ------------------------------------------------------------
try:
    pass
except Exception as e:
    print(f"Warning: Failed to import redirect module: {e}")
