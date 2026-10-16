"""article 模块的数据访问层（唯一 DB 访问点）"""

from shared.models.article.article import Article
from shared.models.article.article_content import ArticleContent
from shared.models.article.article_seo import ArticleSEO
from src.api.v3.core.base_crud import CRUDBase


class ArticleCRUD(CRUDBase[Article, dict, dict]):
    """文章 CRUD

    软删除：``status = -1``（``articles.status`` 的三态语义），因此基类的
    ``soft_delete_field`` 直接复用 ``status``，所有查询自动排除已删除文章。
    """

    model = Article
    keyword_fields = ("title", "slug", "excerpt")
    default_order_by = "id"
    soft_delete_field = "status"
    soft_delete_value = -1


class ArticleContentCRUD(CRUDBase[ArticleContent, dict, dict]):
    """正文 CRUD（一篇文章按 language_code 可有多行）"""

    model = ArticleContent
    default_order_by = "id"


class ArticleSEOCrud(CRUDBase[ArticleSEO, dict, dict]):
    """SEO CRUD（与文章 1:1）"""

    model = ArticleSEO
    default_order_by = "id"


article_crud = ArticleCRUD()
article_content_crud = ArticleContentCRUD()
article_seo_crud = ArticleSEOCrud()
