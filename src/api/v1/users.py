"""
用户相关 API
"""
import os

from fastapi import APIRouter, Depends, Query, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import User
from src.api.v1.responses import ApiResponse
from src.auth.auth_deps import admin_required as admin_required_api, jwt_required_dependency as jwt_required, \
    get_current_active_user
from src.extensions import get_async_db_session as get_async_db

router = APIRouter()


@router.get("/profile",
            summary="获取用户资料",
            description="获取当前认证用户的基本资料信息",
            response_description="返回用户资料信息")
async def get_user_profile_api(
        request: Request,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db)
):
    """
    获取用户资料API
    """
    try:
        # 安全地处理 profile_picture，防止特殊字符破坏 JSON
        avatar_url = None
        if current_user.profile_picture:
            # 清理文件名中的特殊字符
            safe_filename = current_user.profile_picture.replace('\\', '/').split('/')[-1]
            safe_filename = safe_filename.replace('"', '').replace("'", "").strip()
            if safe_filename:
                avatar_url = f"{str(request.url).split('/profile')[0].rsplit('/', 1)[0]}/static/avatar/{safe_filename}.webp"

        user_data = {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "avatar": avatar_url,
            "created_at": current_user.date_joined.isoformat() if hasattr(current_user,
                                                                          'date_joined') and current_user.date_joined else None,
            "last_login": getattr(current_user, 'last_login', None).isoformat() if getattr(current_user, 'last_login',
                                                                                           None) else None,
            "is_active": current_user.is_active,
            "is_superuser": current_user.is_superuser,
            "role": getattr(current_user, 'role', 'user')
        }

        return ApiResponse(
            success=True,
            data=user_data
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.put("/profile",
            summary="更新用户资料",
            description="更新当前认证用户的基本资料信息",
            response_description="返回更新后的用户资料信息")
async def update_user_profile_api(
        request: Request,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db)
):
    """
    更新用户资料API
    """
    try:
        data = await request.json()

        # 更新用户信息
        for field in ['username', 'email', 'avatar']:
            if field in data:
                setattr(current_user, field, data[field])

        await db.commit()
        await db.refresh(current_user)

        user_data = {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "avatar": current_user.profile_private,
            "last_login": getattr(current_user, 'last_login', None).isoformat() if getattr(current_user, 'last_login',
                                                                                           None) else None
        }

        return ApiResponse(
            success=True,
            data=user_data
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/",
            summary="获取用户列表",
            description="获取用户列表，支持分页和搜索功能（仅管理员）",
            response_description="返回用户列表和分页信息")
async def get_users_list_api(
        request: Request,
        page: int = Query(1, ge=1, description="页码，从 1 开始"),
        per_page: int = Query(10, ge=1, le=100, description="每页显示数量，1-100 之间"),
        search: str = Query("", description="搜索关键词，用于用户名或邮箱搜索"),
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(admin_required_api)
):
    """
    获取用户列表 API (仅管理员)
    """
    try:
        from sqlalchemy import select, func
        query = select(User)

        if search:
            query = query.filter(
                User.username.contains(search) |
                User.email.contains(search)
            )

        # 分页
        offset = (page - 1) * per_page
        # 获取总数
        total_query = select(func.count(User.id))
        if search:
            total_query = total_query.where(
                User.username.contains(search) |
                User.email.contains(search)
            )
        total_result = await db.execute(total_query)
        total = total_result.scalar()

        # 获取分页数据
        users_query = select(User)
        if search:
            users_query = users_query.where(
                User.username.contains(search) |
                User.email.contains(search)
            )
        users_query = users_query.offset(offset).limit(per_page)
        users_result = await db.execute(users_query)
        users = users_result.scalars().all()

        users_data = []
        for user in users:
            users_data.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "is_superuser": getattr(user, 'is_superuser', False),
                "created_at": user.date_joined.isoformat() if hasattr(user,
                                                                      'date_joined') and user.date_joined else None,
                "last_login": getattr(user, 'last_login', None).isoformat() if getattr(user, 'last_login',
                                                                                       None) else None
            })

        return ApiResponse(
            success=True,
            data=users_data,
            pagination={
                "current_page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page,
                "has_next": page < (total + per_page - 1) // per_page,
                "has_prev": page > 1
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in get_users_list_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/me",
            summary="获取当前用户信息",
            description="获取当前认证用户的详细信息，如果访问令牌即将过期则自动刷新",
            response_description="返回当前用户信息及可能的新访问令牌")
async def get_current_user_api(
        request: Request,
        current_user: User = Depends(get_current_active_user)
):
    """
    获取当前用户信息，支持自动刷新即将过期的访问令牌
    """
    try:
        # 检查是否在请求处理过程中生成了新的访问令牌
        new_access_token = getattr(request.state, 'new_access_token', None)

        # 构建基础 URL
        base_url = str(request.url).split('/me')[0]
        if base_url.endswith('/'):
            base_url = base_url.rsplit('/', 1)[0]

        # 安全地构建头像 URL，确保路径正确
        avatar_url = None
        if current_user.profile_picture:
            # 移除 profile_picture 中可能的路径分隔符和特殊字符
            safe_filename = current_user.profile_picture.replace('\\', '/').split('/')[-1]
            # 确保文件名不包含可能破坏 JSON 的特殊字符
            safe_filename = safe_filename.replace('"', '').replace("'", "").strip()
            if safe_filename:  # 只有在处理后仍有内容时才使用
                avatar_url = f"{base_url}/static/avatar/{safe_filename}.webp"

        user_data = {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "avatar": avatar_url,
            "is_active": current_user.is_active,
            "is_superuser": current_user.is_superuser,
            "created_at": current_user.date_joined.isoformat() if hasattr(current_user,
                                                                          'date_joined') and current_user.date_joined else None,
            "last_login": getattr(current_user, 'last_login', None).isoformat() if getattr(current_user, 'last_login',
                                                                                           None) else None
        }

        response_data = {
            "success": True,
            "data": user_data
        }

        # 如果有新的访问令牌，将其添加到响应中
        if new_access_token:
            response_data["new_access_token"] = new_access_token

        # 返回JSONResponse以便设置响应头
        response = JSONResponse(content=response_data)

        # 如果有新的访问令牌，将其设置在响应头中
        if new_access_token:
            # 根据环境自动设置 Cookie 安全标志
            from src.setting import app_config
            is_https = str(app_config.domain).startswith('https://') or os.environ.get('DEBUG', 'False').lower() == 'false'
            response.set_cookie(
                key="access_token",
                value=new_access_token,
                httponly=True,
                secure=is_https,  # 生产环境（HTTPS）设为 True
                samesite="strict",
                max_age=3600  # 1 小时
            )

        return response
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)})


@router.put("/me/security/change-password",
            summary="修改密码",
            description="修改当前认证用户的密码",
            response_description="返回密码修改结果")
async def change_password_api(
        request: Request,
        current_user: User = Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """
    修改密码 API
    """
    try:
        from src.utils.security.forms import ChangePasswordForm
        from src.api.v1.user_utils.password_utils import validate_password_async, update_password
        from src.utils.security.ip_utils import get_client_ip

        form_data = await request.form()
        form = ChangePasswordForm(data=dict(form_data))

        if not form.validate():
            return ApiResponse(
                success=False,
                error=' '.join(error for errors in form.errors.values() for error in errors)
            )

        # 验证当前密码是否正确
        is_valid = await validate_password_async(
            current_user.id,
            form.current_password.data,
            db
        )
        
        if not is_valid:
            return ApiResponse(success=False, error='当前密码不正确')

        ip = get_client_ip(request)
        success = await update_password(
            current_user.id,
            new_password=form.new_password.data,
            confirm_password=form.confirm_password.data,
            ip=ip,
            db=db
        )

        if not success:
            return ApiResponse(success=False, error='密码修改失败')

        # 清除临时标记
        from src.extensions import cache
        cache_key = f"password_change_verified_{current_user.id}"
        cache.delete(cache_key)

        return ApiResponse(
            success=True,
            data={'message': '密码修改成功！现在需要重新登录。'}
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error in change_password_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=f"密码修改失败: {str(e)}")


@router.get("/export-csv",
            summary="导出用户CSV",
            description="导出用户列表为CSV格式（仅管理员）",
            response_description="返回CSV文件内容")
async def export_users_csv_api(
        request: Request,
        fields: str = Query(None, description="要导出的字段，逗号分隔"),
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(admin_required_api)
):
    """
    导出用户列表为CSV
    """
    try:
        from sqlalchemy import select
        from shared.services.user_manager import user_csv_service
        
        # 获取所有用户
        users_query = select(User)
        users_result = await db.execute(users_query)
        users = users_result.scalars().all()
        
        # 转换为字典
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': getattr(user, 'first_name', ''),
                'last_name': getattr(user, 'last_name', ''),
                'role': getattr(user, 'role', 'user'),
                'is_active': user.is_active,
                'date_joined': user.date_joined,
                'last_login': getattr(user, 'last_login', None),
            })
        
        # 解析字段
        field_list = fields.split(',') if fields else None
        
        # 生成CSV
        csv_content = user_csv_service.export_users_to_csv(users_data, field_list)
        
        # 返回CSV文件
        from fastapi.responses import Response
        return Response(
            content=csv_content,
            media_type='text/csv; charset=utf-8-sig',
            headers={
                'Content-Disposition': 'attachment; filename=users.csv'
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in export_users_csv_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/import-csv",
             summary="导入用户CSV",
             description="从CSV文件导入用户（仅管理员）",
             response_description="返回导入结果")
async def import_users_csv_api(
        request: Request,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(admin_required_api)
):
    """
    从CSV文件导入用户
    """
    try:
        from shared.services.user_manager import user_csv_service
        
        # 读取上传的文件
        form_data = await request.form()
        csv_file = form_data.get('file')
        
        if not csv_file:
            return ApiResponse(success=False, error='未提供CSV文件')
        
        # 读取文件内容
        csv_content = await csv_file.read()
        csv_text = csv_content.decode('utf-8-sig')
        
        # 解析CSV
        result = user_csv_service.parse_csv_import(csv_text)
        
        if result['errors']:
            return ApiResponse(
                success=False,
                error='CSV解析错误',
                data={
                    'errors': result['errors'],
                    'valid_count': result.get('valid_count', 0),
                    'error_count': result.get('error_count', 0)
                }
            )
        
        # 实际创建用户
        from sqlalchemy import select
        created_count = 0
        failed_count = 0
        failed_users = []
        
        for user_data in result['users']:
            try:
                # 检查用户名是否已存在
                existing_user_query = select(User).where(User.username == user_data['username'])
                existing_user_result = await db.execute(existing_user_query)
                if existing_user_result.scalar_one_or_none():
                    failed_users.append(f"用户名已存在: {user_data['username']}")
                    failed_count += 1
                    continue
                
                # 检查邮箱是否已存在
                existing_email_query = select(User).where(User.email == user_data['email'])
                existing_email_result = await db.execute(existing_email_query)
                if existing_email_result.scalar_one_or_none():
                    failed_users.append(f"邮箱已存在: {user_data['email']}")
                    failed_count += 1
                    continue
                
                # 创建新用户
                from datetime import datetime
                new_user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    first_name=user_data.get('first_name', ''),
                    last_name=user_data.get('last_name', ''),
                    is_active=True,
                    date_joined=datetime.now(),
                )
                
                # 设置密码(如果提供)
                if user_data.get('password'):
                    new_user.set_password(user_data['password'])
                else:
                    # 生成随机密码
                    import secrets
                    random_password = secrets.token_urlsafe(8)
                    new_user.set_password(random_password)
                
                db.add(new_user)
                created_count += 1
                
            except Exception as e:
                failed_users.append(f"{user_data.get('username', 'Unknown')}: {str(e)}")
                failed_count += 1
        
        # 提交事务
        if created_count > 0:
            await db.commit()
        
        message = f'成功导入{created_count}个用户'
        if failed_count > 0:
            message += f', {failed_count}个失败'
        
        return ApiResponse(
            success=True,
            data={
                'message': message,
                'created_count': created_count,
                'failed_count': failed_count,
                'failed_users': failed_users[:10],  # 只返回前10个错误
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in import_users_csv_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/download-sample-csv",
            summary="下载示例CSV文件",
            description="下载用户导入的示例CSV模板")
async def download_sample_csv_api(
        request: Request,
):
    """
    下载示例CSV文件API
    提供最小化的CSV模板供用户参考
    """
    try:
        from shared.services.user_manager import user_csv_service
        
        # 生成示例CSV
        csv_content = user_csv_service.generate_sample_csv()
        
        # 返回CSV文件
        from fastapi.responses import Response
        return Response(
            content=csv_content,
            media_type='text/csv; charset=utf-8',
            headers={
                'Content-Disposition': 'attachment; filename=user_import_sample.csv'
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in download_sample_csv_api: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))
