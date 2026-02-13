"""
杂项API - 包含各种杂项功能API
"""
import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.api.v1.user_settings import confirm_email_back
from src.api.v1.user_utils.user_entities import get_avatar
from src.api.v1.user_utils.user_profile import get_user_info
from src.api.v1.utils.article_utils import check_apw_form, get_apw_form
from src.auth import jwt_required_dependency as jwt_required, admin_required_api as admin_required
from src.extensions import cache
from src.extensions import get_async_db_session as get_async_db
from src.models import ArticleI18n, Article, User
from src.setting import app_config
from src.utils.filters import f2list
from src.utils.http.generate_response import send_chunk_md
from src.utils.security.safe import is_valid_iso_language_code
from src.utils.upload.public_upload import FileProcessor, process_single_file

router = APIRouter(tags=["misc"])

domain = app_config.domain

logger = logging.getLogger(__name__)


@router.get('/blog/{aid}/i18n/{iso}')
async def api_blog_i18n_content(
        aid: int,
        iso: str,
        db: AsyncSession = Depends(get_async_db)
):
    if not is_valid_iso_language_code(iso):
        raise HTTPException(status_code=400, detail="Invalid language code")

    from sqlalchemy import select
    content_query = select(ArticleI18n.content).where(
        ArticleI18n.article_id == aid, ArticleI18n.language_code == iso)
    content_result = await db.execute(content_query)
    content = content_result.scalar_one_or_none()

    if content:
        # content是一个元组，需要取出其中的实际内容
        content_text = content[0] if isinstance(content, tuple) else content.content
        return send_chunk_md(content_text, aid, iso)
    else:
        raise HTTPException(status_code=404, detail="Article not found")


@router.get('/user/avatar')
async def api_user_avatar(
        user_id: Optional[int] = Query(None),
        db: AsyncSession = Depends(get_async_db)
):
    user_identifier = user_id
    identifier_type = 'id'

    avatar_url = get_avatar(domain=domain, user_identifier=user_identifier,
                            identifier_type=identifier_type)
    if avatar_url:
        return avatar_url
    else:
        # 默认头像服务器地址
        avatar_url = getattr(app_config, 'AVATAR_SERVER', 'https://www.gravatar.com/avatar/')
        return avatar_url


@router.get('/tags/suggest')
async def suggest_tags(query: str = Query("", alias="q")):
    # logger.debug(f"prefix: {query}")

    # 使用带保护的缓存来存储去重后的标签列表
    cache_key = 'unique_tags'  # 使用明确的缓存键名
    unique_tags = cache.get_with_stale_data(
        cache_key,
        lambda: _generate_unique_tags(),
        fresh_timeout=600,  # 10分钟新鲜时间
        stale_timeout=1800  # 30分钟陈旧时间
    )

    # 过滤出匹配前缀的标签
    matched_tags = [tag for tag in unique_tags if tag.startswith(query)]
    # logger.debug(f"匹配前缀 '{query}' 的标签数量: {len(matched_tags)}")

    # 返回前五个匹配的标签
    return matched_tags[:5]


async def _generate_unique_tags():
    """生成唯一的标签列表"""
    logger.info("缓存未命中，从数据库加载标签...")
    db_session = await get_async_db()
    # 获取所有文章的标签字符串
    tags_results = db_session.query(Article.tags).all()

    # 处理标签数据
    all_tags = []
    for tag_string in tags_results:
        if tag_string and tag_string[0]:  # 确保不是空字符串  
            all_tags.extend(f2list(tag_string[0].strip()))

    # 去重并排序
    unique_tags = sorted(set(all_tags))
    logger.info(f"加载并处理完成，唯一标签数量: {len(unique_tags)}")
    return unique_tags


# 验证并执行换绑的路由
@router.get('/change-email/confirm/{token}')
async def confirm_email_change(
        token: str,
        current_user_obj=Depends(jwt_required)
):
    return confirm_email_back(current_user_obj.id, cache, token)


def get_all_users(db: Session):
    all_users = {}
    try:
        from sqlalchemy import select
        users_query = select(User.username, User.id)
        users_result = db.execute(users_query)
        users = users_result.all()
        for username, user_id in users:
            all_users[username] = str(user_id)
        return all_users
    except Exception as e:
        logger.error(f"An error occurred: {e}")


# 使用带陈旧数据支持的缓存装饰器
@cache
def get_all_emails(db: Session):
    all_emails = []
    try:
        # 查询所有用户邮箱
        from sqlalchemy import select
        results_query = select(User.email)
        results_result = db.execute(results_query)
        results = results_result.all()
        for result in results:
            email = result[0]
            all_emails.append(email)
        return all_emails
    except Exception as e:
        logger.error(f"An error occurred: {e}")


@router.get('/email-exists')
async def email_exists_back(
        email: str = Query(...),
        db: AsyncSession = Depends(get_async_db)
):
    all_emails = cache.get('all_emails')
    if all_emails is None:
        # 如果缓存中没有所有用户的邮箱，重新获取并缓存
        all_emails = get_all_emails(db)
    return {"exists": bool(email in all_emails)}


@router.get('/username-exists/{username}')
async def username_exists(
        username: str,
        db: AsyncSession = Depends(get_async_db)
):
    all_users = cache.get('all_users')
    if all_users is None:
        # 如果缓存中没有所有用户的信息，重新获取并缓存
        all_users = get_all_users(db)
    # 注意：这里应该根据实际情况调整逻辑
    return {"exists": bool(all_users.get(username))}


@router.get('/user/bio/{user_id}')
async def api_user_bio(
        user_id: int,
        db: AsyncSession = Depends(get_async_db)
):
    user_info = await api_user_profile_endpoint(user_id, db)
    bio = user_info[6] if len(user_info) > 6 and user_info[6] else ""
    return bio


@router.get('/user/profile/{user_id}')
async def api_user_profile_endpoint(
        user_id: int,
        db: AsyncSession = Depends(get_async_db)
):
    return get_user_info(user_id, db)


@router.post('/article/{article_id}/status')
async def update_article_status(
        article_id: int,
        request: Request,
        current_user_obj=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """更新文章状态"""
    from sqlalchemy import select
    article_query = select(Article).where(
        Article.article_id == article_id,
        Article.user_id == current_user_obj.id
    )
    article_result = await db.execute(article_query)
    article = article_result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    json_data = await request.json()
    new_status = int(json_data.get('status'))
    if not isinstance(new_status, int):
        raise HTTPException(status_code=400, detail="状态必须是整数类型")

    article.status = new_status
    # article.updated_at = datetime.now()
    db.commit()
    return {"success": True, "message": f"文章已{new_status}"}


@router.post('/upload/cover')
async def upload_cover(
        request: Request,
        current_user_obj=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)  # 添加数据库会话依赖
):
    from fastapi import UploadFile
    from fastapi.responses import JSONResponse

    try:
        # 检查是否有文件上传
        form = await request.form()
        if 'cover_image' not in form:
            return JSONResponse({'code': 400, 'msg': '未上传文件'}, status_code=400)

        file: UploadFile = form['cover_image']

        # 检查文件名是否为空
        if not file or not file.filename:
            return JSONResponse({'code': 400, 'msg': '文件名为空'}, status_code=400)

        # 读取文件内容
        file_data = await file.read()

        # 使用FileProcessor处理文件，支持常见的图片格式，最大8MB
        processor = FileProcessor(
            current_user_obj.id,
            allowed_mimes={'image/jpeg', 'image/png', 'image/gif', 'image/webp'},
            allowed_size=8 * 1024 * 1024
        )

        # 验证并处理文件
        is_valid, validation_result = processor.validate_file(file_data, file.filename)

        if not is_valid:
            return JSONResponse({'code': 400, 'msg': validation_result}, status_code=400)

        # 计算文件哈希
        file_hash = processor.calculate_hash(file_data)

        # 处理文件并在数据库中创建记录
        try:
            result = process_single_file(processor, file_data, file.filename, db)
        except Exception as e:
            db.rollback()  # 确保在失败时回滚事务
            import traceback
            traceback.print_exc()
            return JSONResponse({'code': 500, 'msg': '文件处理失败', 'error': str(e)}, status_code=500)

        if not result['success']:
            db.rollback()  # 确保在失败时回滚事务
            return JSONResponse({'code': 500, 'msg': '文件处理失败', 'error': result['error']}, status_code=500)

        if result['success']:
            from src.setting import app_config
            domain = app_config.domain
            # 确保domain以/结尾
            if not domain.endswith('/'):
                domain += '/'

            # 创建特殊URL用于访问缩略图
            thumbnail_url = domain + "thumbnail?data=" + result['hash']

            # s_url = create_special_url(thumbnail_url, current_user_id)
            s_url = thumbnail_url

            if s_url:
                cover_url = "/s/" + s_url
                return JSONResponse({'code': 200, 'msg': '上传成功', 'data': cover_url})
            else:
                # 即使创建短链接失败，也返回文件哈希，让前端可以构造URL
                cover_url = "/thumbnail?data=" + result['hash']
                return JSONResponse({'code': 200, 'msg': '上传成功', 'data': cover_url})
        else:
            return JSONResponse({'code': 500, 'msg': '文件处理失败', 'error': result['error']}, status_code=500)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({'code': 500, 'msg': '上传失败', 'error': str(e)}, status_code=500)


@router.get('/article/password-form/{aid}')
async def get_password_form(
        aid: int,
        current_user_id: int = Depends(lambda: 1)  # 模拟登录要求
):
    return get_apw_form(aid)


# 密码更改 API
@router.post('/article/password/{aid}')
async def api_update_article_password(
        aid: int,
        request: Request,
        current_user_id: int = Depends(lambda: 1),  # 模拟登录要求
        db: AsyncSession = Depends(get_async_db)
):
    form_data = await request.form()
    new_password = form_data.get('new-password')
    return check_apw_form(aid, new_password, db)


@router.get('/routes')
async def list_all_routes():
    # FastAPI不使用Flask的url_map，这个路由可能不再适用
    # 返回一个示例结构
    return {"routes": []}


# 点赞文章功能
@router.post('/article/{article_id}/like')
async def like_article(
        article_id: int,
        request: Request,
        current_user_obj=Depends(jwt_required),
        db: AsyncSession = Depends(get_async_db)
):
    """用户点赞文章"""
    try:
        # 获取文章
        from src.models.article import ArticleLike
        from sqlalchemy import select
        article_query = select(Article).where(
            Article.article_id == article_id,
            Article.status != -1  # 排除已删除的文章
        )
        article_result = await db.execute(article_query)
        article = article_result.scalar_one_or_none()
        if not article:
            raise HTTPException(status_code=404, detail="文章不存在")

        # 检查用户是否已经点过赞
        from sqlalchemy import select
        existing_like_query = select(ArticleLike).where(
            ArticleLike.user_id == current_user_obj.id,
            ArticleLike.article_id == article_id
        )
        existing_like_result = await db.execute(existing_like_query)
        existing_like = existing_like_result.scalar_one_or_none()
        if existing_like:
            raise HTTPException(status_code=400, detail="您已经点过赞了")

        # 增加点赞数
        article.likes += 1

        # 记录用户点赞
        new_like = ArticleLike(user_id=current_user_obj.id, article_id=article_id)
        db.add(new_like)

        db.commit()

        return {
            'success': True,
            'message': '点赞成功',
            'likes': article.likes
        }
    except HTTPException:
        raise
    except Exception as e:
        if db is not None:
            db.rollback()
        raise HTTPException(status_code=500, detail="点赞失败")


@router.post('/article/{article_id}/view')
async def record_article_view(
        article_id: int,
        db: AsyncSession = Depends(get_async_db)
):
    """记录文章浏览量（使用缓存异步更新数据库）"""
    try:
        # 检查文章是否存在
        from sqlalchemy import select
        article_query = select(Article).where(
            Article.article_id == article_id,
            Article.status != -1  # 排除已删除的文章
        )
        article_result = await db.execute(article_query)
        article = article_result.scalar_one_or_none()
        if not article:
            raise HTTPException(status_code=404, detail="文章不存在")

        # 使用缓存来记录浏览量，避免频繁写入数据库
        cache_key = f"article_views_{article_id}"
        current_views = cache.get(cache_key)

        if current_views is None:
            # 如果缓存中没有，则从数据库获取当前浏览量
            current_views = article.views

        # 增加浏览量计数
        current_views += 1

        # 将新的浏览量存回缓存
        cache.set(cache_key, current_views, timeout=300)  # 缓存5分钟

        return {'success': True, 'message': '浏览量记录成功'}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"记录浏览量失败: {str(e)}")


# 管理员相关路由
@router.get('/admin/dashboard')
async def admin_dashboard(current_user_id: int = Depends(admin_required)):
    return {'message': '管理员面板'}


# 检查用户登录状态
@router.get('/user/check-login')
async def check_login_status():
    """检查用户登录状态"""
    # 在FastAPI中，JWT认证通过依赖项处理
    # 如果到达这里说明用户已通过认证
    return {
        'logged_in': True,
        'message': 'User is logged in'
    }


@router.get('/check-username')
async def check_username(username: str = Query(...), db: AsyncSession = Depends(get_async_db)):
    try:
        from sqlalchemy import select
        exists_query = select(User).where(User.username == username)
        exists_result = await db.execute(exists_query)
        exists = exists_result.scalar_one_or_none() is not None
        return {'exists': exists}
    except Exception as e:
        import traceback
        print(f"Check username error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/check-email')
async def check_email(email: str = Query(...), db: AsyncSession = Depends(get_async_db)):
    try:
        from sqlalchemy import select
        exists_query = select(User).where(User.email == email)
        exists_result = await db.execute(exists_query)
        exists = exists_result.scalar_one_or_none() is not None
        return {'exists': exists}
    except Exception as e:
        import traceback
        print(f"Check email error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


def convert_storage_size(total_bytes):
    """
    将字节数转换为GB、MB或KB的字符串表示。
    :param total_bytes: 存储大小的字节数
    :return: 存储大小的字符串表示，单位为GB、MB或KB
    """
    gb_factor = Decimal('1073741824')  # 1024 * 1024 * 1024
    mb_factor = Decimal('1048576')  # 1024 * 1024
    kb_factor = Decimal('1024')  # 1024

    # 统一转换为 Decimal
    total_bytes = Decimal(str(total_bytes))

    if total_bytes >= gb_factor:
        size_in_gb = total_bytes / gb_factor
        return f"{int(size_in_gb)} GB"
    elif total_bytes >= mb_factor:
        size_in_mb = total_bytes / mb_factor
        return f"{int(size_in_mb)} MB"
    else:
        size_in_kb = total_bytes / kb_factor
        return f"{int(size_in_kb)} KB"


# ==================== 版本管理相关API ====================

# 导入IPC通信模块
try:
    from ipc import get_process_manager, MessageType
    IPC_AVAILABLE = True
except ImportError as e:
    logger.warning(f"IPC模块导入失败: {e}")
    IPC_AVAILABLE = False


def get_version_from_update_server(request_type: str):
    """从更新服务器获取版本信息"""
    import requests
    
    try:
        # 更新服务器地址
        update_server_url = "http://127.0.0.1:8001"
        endpoint_map = {
            'full': '/api/v1/version/full',
            'frontend': '/api/v1/version/frontend',
            'backend': '/api/v1/version/backend'
        }
        
        endpoint = endpoint_map.get(request_type, '/api/v1/version/full')
        url = f"{update_server_url}{endpoint}"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        return {
            'success': True,
            'data': response.json()
        }
    except Exception as e:
        logger.error(f"从更新服务器获取版本信息失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'data': None
        }


@router.get('/version/info')
async def get_version_info():
    """获取完整的版本信息"""
    return get_version_from_update_server('full')


@router.get('/version/frontend')
async def get_frontend_version():
    """获取前端版本信息"""
    return get_version_from_update_server('frontend')


@router.get('/version/backend')
async def get_backend_version():
    """获取后端版本信息"""
    return get_version_from_update_server('backend')


# ==================== 系统更新相关API ====================

# 移除了前端更新页面相关的API，更新操作应通过IPC或独立的更新管理界面进行
# 前端可以直接与更新服务器通信获取版本信息
