"""
文章相关的工具函数
"""
from typing import List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.models import Article, Category, ArticleContent


async def get_articles_with_filters(filters: List, db: AsyncSession, page: int, page_size: int) -> Tuple[List[tuple], int]:
    """
    通用函数：根据提供的过滤器获取文章
    """
    try:
        # 使用数据库会话
        # 基本查询
        query = select(
            Article.article_id,
            Article.title,
            Article.user_id,
            Article.views,
            Article.likes,
            Article.cover_image,
            Article.category_id,
            Article.excerpt,
            Article.is_featured,
            Article.tags,
            Article.slug,
            Article.updated_at
        ).outerjoin(Category, Article.category_id == Category.id).where(
            Article.hidden == False,
            Article.status == 1,
            Article.is_vip_only == False,
        )

        # 添加额外过滤器
        for filter_cond in filters:
            query = query.where(filter_cond)

        # 获取当前页的文章
        offset_val = (page - 1) * page_size
        articles_result = await db.execute(query.order_by(
            Article.article_id.desc()
        ).offset(offset_val).limit(page_size))
        articles = articles_result.all()

        # 获取总文章数
        count_query = select(Article).where(
            Article.hidden == False,
            Article.status == 1
        )
        for filter_cond in filters:
            count_query = count_query.where(filter_cond)

        total_articles_result = await db.execute(count_query)
        total_articles = len(total_articles_result.scalars().all())

        return [tuple(article) for article in articles], total_articles

    except Exception as e:
        # 在FastAPI中使用logging而不是current_app.logger
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Database error: {e}")
        raise


def set_article_password(aid: int, passwd: str, db: Session):
    """
    设置文章密码

    Args:
        aid: 文章ID
        passwd: 密码
        db: 数据库会话

    Returns:
        bool: 设置成功返回True，否则返回False
    """
    import logging
    from datetime import datetime, timezone

    logger = logging.getLogger(__name__)
    try:
        # 查询是否存在该aid的记录
        from src.models import ArticleContent
        article_content_query = select(ArticleContent).where(ArticleContent.aid == aid)
        article_content_result = db.execute(article_content_query)
        article_content = article_content_result.scalar_one_or_none()
        if article_content:
            # 更新密码
            article_content.passwd = passwd
            article_content.updated_at = datetime.now(timezone.utc)
        else:
            # 插入新记录
            new_content = ArticleContent(aid=aid, passwd=passwd, updated_at=datetime.now(timezone.utc))
            db.add(new_content)

        db.commit()
        return True
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        db.rollback()
        return False


def get_article_password(aid: int, db: Session):
    """
    获取文章密码

    Args:
        aid: 文章ID
        db: 数据库会话

    Returns:
        str or None: 返回密码或None
    """
    import logging

    logger = logging.getLogger(__name__)
    try:
        # 查询密码
        article_content_query = select(ArticleContent).where(ArticleContent.aid == aid)
        article_content_result = db.execute(article_content_query)
        article_content = article_content_result.scalar_one_or_none()
        if article_content:
            return article_content.passwd
        return None
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return None


def get_article_slugs(db: Session):
    """
    获取文章ID和slug的映射

    Args:
        db: 数据库会话

    Returns:
        dict: 文章ID和slug的映射
    """
    results = db.query(Article.article_id, Article.slug).filter(
        Article.status == 1,
        Article.hidden == False
    ).all()
    # 组合成字典返回
    article_dict = {row[0]: row[1] for row in results}
    return article_dict


import re
def get_apw_form(aid: int):
    """
    获取文章密码表单HTML

    Args:
        aid: 文章ID

    Returns:
        str: HTML表单
    """
    return '''
        <div id="password-modal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full">
            <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
                <div class="mt-3 text-center">
                    <h3 class="text-lg leading-6 font-medium text-gray-900">更改文章密码</h3>
                    <div class="mt-2 px-7 py-3">
                        <p class="text-sm text-gray-500 mb-3">
                            请输入新的文章访问密码（至少4位，包含字母和数字）
                        </p>
                        <input type="password" id="new-password" name="new-password"
                               class="w-full px-3 py-2 border border-gray-300 rounded-md" 
                               placeholder="输入新密码">
                    </div>
                    <div class="flex justify-center gap-4 px-4 py-3">
                        <button id="cancel-password" 
                                class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300"
                                onclick="document.getElementById('password-modal').remove()">
                            取消
                        </button>
                        <button id="confirm-password" 
                                hx-post="/api/article/password/''' + str(aid) + '''"
                                hx-include="#new-password"
                                hx-target="#password-modal"
                                hx-swap="innerHTML"
                                class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
                            确认更改
                        </button>
                    </div>
                </div>
            </div>
        </div>
        '''


def check_apw_form(aid: int, new_password: str, db: Session):
    """
    检查并处理文章密码表单

    Args:
        aid: 文章ID
        new_password: 新密码
        db: 数据库会话

    Returns:
        str: HTML响应
    """
    import logging
    logger = logging.getLogger(__name__)
    try:
        # 验证密码格式
        if not re.match(r'^(?=.*[A-Za-z])(?=.*\\d).{4,}$', new_password):
            return '''
            <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
                <div class="mt-3 text-center">
                    <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
                        <svg class="h-6 w-6 text-red-600" stroke="currentColor" fill="none" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </div>
                    <h3 class="text-lg leading-6 font-medium text-gray-900">密码格式错误</h3>
                    <div class="mt-2 px-7 py-3">
                        <p class="text-sm text-gray-500">
                            密码需要至少4位且包含字母和数字！
                        </p>
                    </div>
                    <div class="px-4 py-3">
                        <button onclick="document.getElementById('password-modal').remove()"
                                class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
                            关闭
                        </button>
                    </div>
                </div>
            </div>
            '''

        # 更新密码
        set_article_password(aid, new_password, db)

        # 返回成功响应
        return '''
        <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100">
                <svg class="h-6 w-6 text-green-600" stroke="currentColor" fill="none" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
            </div>
            <div class="mt-3 text-center">
                <h3 class="text-lg leading-6 font-medium text-gray-900">密码更新成功</h3>
                <div class="mt-2 px-7 py-3">
                    <p class="text-sm text-gray-500">
                        新密码将在10分钟内生效
                    </p>
                </div>
                <div class="px-4 py-3">
                    <button onclick="document.getElementById('password-modal').remove()"
                            class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
                        关闭
                    </button>
                </div>
            </div>
        </div>
        '''
    except (TypeError, AttributeError) as e:
        logger.error(e)
        return '''
        <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
                <svg class="h-6 w-6 text-red-600" stroke="currentColor" fill="none" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </div>
            <h3 class="text-lg leading-6 font-medium text-gray-900">操作失败</h3>
            <div class="mt-2 px-7 py-3">
                <p class="text-sm text-gray-500">
                    服务器内部错误，请稍后再试
                </p>
            </div>
            <div class="px-4 py-3">
                <button onclick="document.getElementById('password-modal').remove()"
                        class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
                    关闭
                </button>
            </div>
        </div>
        ''', 500