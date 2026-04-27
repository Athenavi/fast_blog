"""
一键安装向导API
"""
import asyncio
import json

from fastapi import APIRouter, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from shared.services.install_manager.installation_wizard import installation_wizard_service
from shared.services.install_manager.migration_service import migration_service
from src.api.v1.responses import ApiResponse

router = APIRouter()


@router.get("/prerequisites",
            summary="检查安装前置条件",
            description="检查系统环境是否满足安装要求",
            response_description="返回前置条件检查结果")
async def check_prerequisites_api():
    """检查安装前置条件"""
    try:
        result = installation_wizard_service.check_prerequisites()
        
        return ApiResponse(
            success=True,
            data=result
        )
    except Exception as e:
        import traceback
        print(f"Error in check_prerequisites_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


class DatabaseConfigRequest(BaseModel):
    """数据库配置请求"""
    db_url: str


class AdminUserRequest(BaseModel):
    """管理员账户请求"""
    username: str
    email: str
    password: str
    password_confirm: str = ''  # 可选,前端已验证


class SiteSettingsRequest(BaseModel):
    """站点设置请求"""
    site_name: str
    site_url: str
    admin_email: str
    site_description: str = ''
    language: str = 'zh_CN'


class DatabaseConfigFullRequest(BaseModel):
    """数据库完整配置请求"""
    db_type: str = 'sqlite'
    host: str = ''
    port: str = ''
    database: str = 'blog.db'
    username: str = ''
    password: str = ''


class SampleDataRequest(BaseModel):
    """示例数据导入请求"""
    import_articles: bool = True
    import_categories: bool = True


@router.post("/configure-database",
             summary="配置数据库",
             description="配置数据库连接信息",
             response_description="返回配置结果")
async def configure_database_api(
        request: DatabaseConfigFullRequest
):
    """配置数据库"""
    try:
        # 检查是否已安装
        if installation_wizard_service.is_installed():
            return ApiResponse(
                success=False,
                error="System already installed"
            )
        
        config = {
            'db_type': request.db_type,
            'host': request.host,
            'port': request.port,
            'database': request.database,
            'username': request.username,
            'password': request.password
        }

        result = installation_wizard_service.configure_database(config)
        
        return ApiResponse(
            success=result['success'],
            data=result
        )
    except Exception as e:
        import traceback
        print(f"Error in configure_database_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/import-sample-data",
             summary="导入示例数据",
             description="导入示例文章和分类",
             response_description="返回导入结果")
async def import_sample_data_api(
        request: SampleDataRequest
):
    """导入示例数据"""
    try:
        # 检查是否已安装
        if installation_wizard_service.is_installed():
            return ApiResponse(
                success=False,
                error="System already installed"
            )

        result = installation_wizard_service.import_sample_data(
            import_articles=request.import_articles,
            import_categories=request.import_categories
        )
        
        return ApiResponse(
            success=result['success'],
            data=result
        )
    except Exception as e:
        import traceback
        print(f"Error in import_sample_data_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/status",
            summary="获取安装状态",
            description="检查系统是否已安装及当前进度",
            response_description="返回安装状态")
async def get_installation_status_api():
    """获取安装状态"""
    try:
        status = installation_wizard_service.get_installation_status()
        
        return ApiResponse(
            success=True,
            data=status
        )
    except Exception as e:
        import traceback
        print(f"Error in get_installation_status_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/steps",
            summary="获取安装步骤",
            description="获取完整的安装步骤列表",
            response_description="返回安装步骤")
async def get_installation_steps_api():
    """获取安装步骤"""
    try:
        steps = installation_wizard_service.get_installation_steps()
        
        return ApiResponse(
            success=True,
            data={
                "steps": steps,
                "total_steps": len(steps)
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in get_installation_steps_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/check-database",
             summary="检查数据库连接",
             description="验证数据库连接配置是否正确",
             response_description="返回检查结果")
async def check_database_connection_api(
        request: DatabaseConfigRequest
):
    """检查数据库连接"""
    try:
        result = installation_wizard_service.check_database_connection(request.db_url)
        
        return ApiResponse(
            success=result['success'],
            data=result
        )
    except Exception as e:
        import traceback
        print(f"Error in check_database_connection_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/create-admin",
             summary="创建管理员账户",
             description="创建第一个管理员账户",
             response_description="返回创建结果")
async def create_admin_user_api(
        request: AdminUserRequest
):
    """创建管理员账户"""
    try:
        # 检查是否已安装
        if installation_wizard_service.is_installed():
            return ApiResponse(
                success=False,
                error="System already installed"
            )
        
        result = installation_wizard_service.create_admin_user(
            username=request.username,
            email=request.email,
            password=request.password
        )
        
        return ApiResponse(
            success=result['success'],
            data=result
        )
    except Exception as e:
        import traceback
        print(f"Error in create_admin_user_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/configure-site",
             summary="配置站点设置",
             description="配置站点基本信息",
             response_description="返回配置结果")
async def configure_site_settings_api(
        request: SiteSettingsRequest
):
    """配置站点设置"""
    try:
        # 检查是否已安装
        if installation_wizard_service.is_installed():
            return ApiResponse(
                success=False,
                error="System already installed"
            )
        
        config = {
            'site_name': request.site_name,
            'site_url': request.site_url,
            'site_description': request.site_description,
            'admin_email': request.admin_email,
            'language': request.language
        }

        result = installation_wizard_service.configure_site_settings(
            site_name=request.site_name,
            site_url=request.site_url,
            admin_email=request.admin_email,
            site_description=request.site_description,
            language=request.language
        )
        
        return ApiResponse(
            success=result['success'],
            data=result
        )
    except Exception as e:
        import traceback
        print(f"Error in configure_site_settings_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/complete",
             summary="完成安装",
             description="确认所有配置并完成安装",
             response_description="返回完成结果")
async def complete_installation_api(
        install_info: dict = Body(default={}, description="安装信息")
):
    """完成安装"""
    try:
        # 检查是否已安装
        if installation_wizard_service.is_installed():
            return ApiResponse(
                success=False,
                error="System already installed"
            )
        
        result = installation_wizard_service.complete_installation(install_info)
        
        return ApiResponse(
            success=result['success'],
            data=result
        )
    except Exception as e:
        import traceback
        print(f"Error in complete_installation_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/confirm-database-and-migrate",
             summary="确认数据库配置并执行迁移",
             description="二次确认数据库配置并自动执行 Alembic 迁移",
             response_description="返回确认和迁移结果")
async def confirm_database_and_migrate_api():
    """确认数据库配置并执行迁移"""
    try:
        # 检查是否已安装
        if installation_wizard_service.is_installed():
            return ApiResponse(
                success=False,
                error="System already installed"
            )

        result = installation_wizard_service.confirm_database_and_migrate()

        return ApiResponse(
            success=result['success'],
            data=result
        )
    except Exception as e:
        import traceback
        print(f"Error in confirm_database_and_migrate_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/reset",
             summary="重置安装状态",
             description="重置安装状态（仅用于开发/测试）",
             response_description="返回重置结果")
async def reset_installation_api():
    """重置安装状态"""
    try:
        result = installation_wizard_service.reset_installation()
        
        return ApiResponse(
            success=result['success'],
            data=result
        )
    except Exception as e:
        import traceback
        print(f"Error in reset_installation_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/migration/stream",
            summary="数据库迁移实时日志流",
            description="通过 SSE 实时推送 Alembic 迁移日志到前端",
            response_description="SSE 流式响应")
async def stream_migration_logs():
    """
    Server-Sent Events (SSE) 端点，实时推送迁移日志
    参考 Django migrations 和 Flask-Migrate 的设计
    """

    async def event_generator():
        """生成 SSE 事件"""
        try:
            import sys
            print(f"\n[SSE] 开始迁移日志流", file=sys.stderr)

            # 检查 Alembic 是否可用
            if not migration_service.check_alembic_available():
                error_msg = {'type': 'error', 'message': 'Alembic 未安装或不可用'}
                print(f"[SSE] {error_msg}", file=sys.stderr)
                yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                return

            # 获取迁移状态
            status = migration_service.get_migration_status()
            print(f"[SSE] 当前版本: {status['current']}, 目标版本: {status['head']}", file=sys.stderr)

            yield f"data: {json.dumps({'type': 'info', 'message': f'当前版本: {status["current"]}'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'info', 'message': f'目标版本: {status["head"]}'}, ensure_ascii=False)}\n\n"

            if status.get('is_up_to_date'):
                yield f"data: {json.dumps({'type': 'info', 'message': '数据库已是最新版本，无需迁移'}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'success', 'message': '✓ 数据库已就绪'}, ensure_ascii=False)}\n\n"
                return

            # 执行迁移并实时推送日志
            print(f"[SSE] 开始执行迁移...", file=sys.stderr)
            async for log_entry in migration_service.run_migration():
                yield f"data: {json.dumps(log_entry, ensure_ascii=False)}\n\n"
                # 给前端一点时间处理
                await asyncio.sleep(0.05)

            print(f"[SSE] 迁移完成", file=sys.stderr)

        except Exception as e:
            import traceback
            import sys
            error_msg = {
                'type': 'error',
                'message': f'SSE 端点出错: {str(e)}',
                'traceback': traceback.format_exc()
            }
            print(f"[SSE ERROR] {error_msg}", file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx 禁用缓冲
        }
    )
