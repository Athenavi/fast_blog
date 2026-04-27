"""
文章作者管理服务
"""
from django.db import transaction

from apps.blog.models import Article, ArticleAuthor


def add_author(article: Article, user, author_order: int = 1, contribution: str = None):
    """
    为文章添加作者
    
    Args:
        article: 文章对象
        user: 用户对象
        author_order: 作者顺序 (1=第一作者，2=第二作者，以此类推)
        contribution: 贡献描述
    
    Returns:
        ArticleAuthor: 创建的作者关系对象
    
    Raises:
        ValueError: 如果该用户已经是文章的作者
    """
    if ArticleAuthor.objects.filter(article=article, user=user).exists():
        raise ValueError(f"用户 {user.username} 已经是文章 {article.title} 的作者")

    return ArticleAuthor.objects.create(
        article=article,
        user=user,
        author_order=author_order,
        contribution=contribution
    )


def remove_author(article: Article, user):
    """
    移除文章的作者
    
    Args:
        article: 文章对象
        user: 用户对象
    
    Raises:
        ValueError: 如果该用户不是文章的作者
    """
    try:
        author_rel = ArticleAuthor.objects.get(article=article, user=user)
        author_rel.delete()
    except ArticleAuthor.DoesNotExist:
        raise ValueError(f"用户 {user.username} 不是文章 {article.title} 的作者")


def update_author_order(article: Article, user, new_order: int):
    """
    更新作者在文章中的顺序
    
    Args:
        article: 文章对象
        user: 用户对象
        new_order: 新的作者顺序
    """
    author_rel = ArticleAuthor.objects.get(article=article, user=user)
    author_rel.author_order = new_order
    author_rel.save(update_fields=['author_order'])


def update_author_contribution(article: Article, user, contribution: str):
    """
    更新作者的贡献描述
    
    Args:
        article: 文章对象
        user: 用户对象
        contribution: 贡献描述
    """
    author_rel = ArticleAuthor.objects.get(article=article, user=user)
    author_rel.contribution = contribution
    author_rel.save(update_fields=['contribution'])


@transaction.atomic
def set_authors(article: Article, authors_data: list):
    """
    设置文章的所有作者（会替换现有作者列表）
    
    Args:
        article: 文章对象
        authors_data: 作者数据列表，每个元素为字典：
                     {
                         'user': User 对象或 user_id,
                         'author_order': int,
                         'contribution': str (可选)
                     }
    
    Example:
        >>> set_authors(article, [
        ...     {'user': user1, 'author_order': 1, 'contribution': '主要撰写'},
        ...     {'user': user2, 'author_order': 2, 'contribution': '数据收集'}
        ... ])
    """
    # 删除现有作者关系
    ArticleAuthor.objects.filter(article=article).delete()

    # 添加新作者
    for author_data in authors_data:
        user = author_data['user']
        if isinstance(user, int):
            from apps.user.models import User
            user = User.objects.get(id=user)

        ArticleAuthor.objects.create(
            article=article,
            user=user,
            author_order=author_data.get('author_order', 1),
            contribution=author_data.get('contribution')
        )


def get_article_authors(article: Article):
    """
    获取文章的所有作者（按作者顺序排序）
    
    Args:
        article: 文章对象
    
    Returns:
        QuerySet[ArticleAuthor]: 作者关系查询集
    """
    return ArticleAuthor.objects.filter(article=article).select_related('user').order_by('author_order')


def get_user_articles(user, as_main_author_only=False):
    """
    获取用户参与的所有文章
    
    Args:
        user: 用户对象
        as_main_author_only: 如果为 True，只返回用户作为第一作者的文章
    
    Returns:
        QuerySet[Article]: 文章查询集
    """
    if as_main_author_only:
        # 只返回用户作为第一作者（user_id）的文章
        return Article.objects.filter(user=user)
    else:
        # 返回用户作为任何角色作者的文章
        authored_article_ids = ArticleAuthor.objects.filter(user=user).values_list('article_id', flat=True)
        main_author_article_ids = Article.objects.filter(user=user).values_list('article_id', flat=True)

        all_article_ids = set(authored_article_ids) | set(main_author_article_ids)
        return Article.objects.filter(article_id__in=all_article_ids)


def is_author_of_article(user, article: Article) -> bool:
    """
    检查用户是否是文章的作者（包括任何顺序的作者）
    
    Args:
        user: 用户对象
        article: 文章对象
    
    Returns:
        bool: 如果是作者返回 True
    """
    # 检查是否是第一作者
    if article.user == user:
        return True

    # 检查是否是其他顺序的作者
    return ArticleAuthor.objects.filter(article=article, user=user).exists()


def get_author_count(article: Article) -> int:
    """
    获取文章的作者总数
    
    Args:
        article: 文章对象
    
    Returns:
        int: 作者数量
    """
    # 第一作者 + 其他作者
    other_authors_count = ArticleAuthor.objects.filter(article=article).count()
    return 1 + other_authors_count  # 1 是第一作者
