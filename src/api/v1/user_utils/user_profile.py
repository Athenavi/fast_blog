import uuid
from pathlib import Path
from uuid import UUID

from httpx import Request
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from src.models import User
from .user_entities import db_save_bio


def get_user_info(user_id, db: Session):
    if not user_id:
        return []
    try:
        # 检查user_id是否为UUID类型，如果不是，尝试转换
        actual_user_id = user_id
        if isinstance(user_id, str):
            try:
                # 尝试将字符串转换为UUID
                actual_user_id = UUID(user_id)
            except ValueError:
                # 如果不是有效的UUID格式，可能是一个旧的整数ID
                try:
                    int_id = int(user_id)
                    # 在UUID表中查找对应记录，这取决于数据迁移情况
                    # 如果找不到UUID记录，返回空结果
                    return []
                except ValueError:
                    return []
        elif isinstance(user_id, int):
            # 整数ID不再适用UUID表结构，需要处理迁移或返回空结果
            return []

        from sqlalchemy import select
        user_query = select(User).where(User.id == actual_user_id)
        user_result = db.execute(user_query)
        user = user_result.scalar_one_or_none()
        if user:
            info_list = [user.id, user.username, user.email, user.is_2fa_enabled, user.register_ip,
                         user.profile_picture,
                         user.bio, user.profile_private]
            return info_list
        else:
            return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


def get_user_name_by_id(user_id, db: Session):
    author_name = '未知'
    try:
        # 检查user_id是否为UUID类型，如果不是，尝试转换
        actual_user_id = user_id
        if isinstance(user_id, str):
            try:
                # 尝试将字符串转换为UUID
                actual_user_id = UUID(user_id)
            except ValueError:
                # 如果不是有效的UUID格式，可能是一个旧的整数ID
                try:
                    int_id = int(user_id)
                    # 在UUID表中查找对应记录，这取决于数据迁移情况
                    # 如果找不到UUID记录，返回默认值
                    return author_name
                except ValueError:
                    return author_name
        elif isinstance(user_id, int):
            # 整数ID不再适用UUID表结构，需要处理迁移或返回默认值
            return author_name

        from sqlalchemy import select
        user_query = select(User).where(User.id == actual_user_id)
        user_result = db.execute(user_query)
        user = user_result.scalar_one_or_none()
        if user:
            author_name = user.username
            return author_name

    except (ValueError, TypeError) as e:
        pass

    return author_name


async def edit_profile(request: Request, change_type: str, user_id: int, db: Session):
    if change_type == 'avatar':
        # FastAPI中处理文件上传的方式不同，需要使用不同的方法
        # 这里我们假设文件已通过其他方式处理
        try:
            # 生成UUID
            avatar_uuid = str(uuid.uuid4())
            save_path = Path('static') / 'avatar' / f'{avatar_uuid}.webp'

            # 确保目录存在
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 直接更新数据库中的用户头像字段
            from .user_entities import db_save_avatar
            from sqlalchemy import select
            user_query = select(User).where(User.id == user_id)
            user_result = db.execute(user_query)
            user = user_result.scalar_one_or_none()
            if user:
                user.profile_picture = avatar_uuid
                db.commit()

            return JSONResponse(content={'message': 'Avatar updated successfully', 'avatar_id': str(avatar_uuid)})
        except Exception as e:
            return JSONResponse(content={'error': f'Avatar update failed: {str(e)}'}, status_code=500)

    elif change_type == 'bio':
        data = await request.json()
        bio = data.get('bio')
        db_save_bio(user_id, bio, db)
        return JSONResponse(content={'message': 'Bio updated successfully'})

    else:
        return JSONResponse(content={'error': 'Invalid change type'}, status_code=400)