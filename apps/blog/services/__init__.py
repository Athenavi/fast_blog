"""
博客应用服务层
"""
from .author_service import (
    add_author,
    remove_author,
    update_author_order,
    update_author_contribution,
    set_authors,
    get_article_authors,
    get_user_articles,
    is_author_of_article,
    get_author_count
)

__all__ = [
    'add_author',
    'remove_author',
    'update_author_order',
    'update_author_contribution',
    'set_authors',
    'get_article_authors',
    'get_user_articles',
    'is_author_of_article',
    'get_author_count'
]
