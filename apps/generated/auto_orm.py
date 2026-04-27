"""
Django ORM 抽象基类定义
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-04-26 19:54:29
"""

from django.db import models

# ==================== 表名前缀配置 ====================
# 注意：如果使用了表名前缀（如 fb_），请在具体模型类的 Meta 中设置 db_table
# 例如：db_table = "users" (对于 User 模型)
TABLE_PREFIX = ""


def get_table_name(base_name: str) -> str:
    """
    获取带前缀的表名
    
    Args:
        base_name: 基础表名（不带前缀）
    
    Returns:
        带前缀的完整表名
    """
    if TABLE_PREFIX and not base_name.startswith(TABLE_PREFIX):
        return f"{TABLE_PREFIX}{base_name}"
    return base_name


# ==================== 通用 Mixin 类 ====================

class TimestampMixin(models.Model):
    """时间戳混合类（包含创建和更新时间）"""
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    """软删除混合类"""
    is_deleted = models.BooleanField('是否删除', default=False)
    deleted_at = models.DateTimeField('删除时间', blank=True, null=True)

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """重写删除方法为软删除"""
        self.is_deleted = True
        from django.utils import timezone
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

# ==================== 自动生成的模型 Mixin ====================


class UserMixin(models.Model):
    """用户模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # username
    username = models.CharField(
        'username', max_length=255, unique=True)
    # email
    email = models.CharField(
        'email', max_length=255)
    # password
    password = models.CharField(
        'password', max_length=255)
    # profile_picture
    profile_picture = models.CharField(
        'profile_picture', max_length=255, blank=True, null=True)
    # bio
    bio = models.CharField(
        'bio', max_length=255, blank=True, null=True)
    # profile_private
    profile_private = models.BooleanField(
        'profile_private', default=False)
    # vip_level
    vip_level = models.BigIntegerField(
        'vip_level', default=0)
    # vip_expires_at
    vip_expires_at = models.DateTimeField(
        'vip_expires_at', blank=True, null=True)
    # is_active
    is_active = models.BooleanField(
        'is_active', default=True)
    # is_superuser
    is_superuser = models.BooleanField(
        'is_superuser', default=False)
    # date_joined
    date_joined = models.DateTimeField(
        'date_joined')
    # last_login_at
    last_login_at = models.DateTimeField(
        'last_login_at', blank=True, null=True)
    # locale
    locale = models.CharField(
        'locale', max_length=255, default='zh_CN')
    # is_staff
    is_staff = models.BooleanField(
        'is_staff', default=False)
    # last_login_ip
    last_login_ip = models.CharField(
        'last_login_ip', max_length=255, blank=True, null=True)
    # register_ip
    register_ip = models.CharField(
        'register_ip', max_length=255, blank=True, null=True)
    # is_2fa_enabled
    is_2fa_enabled = models.BooleanField(
        'is_2fa_enabled', default=False)
    # totp_secret
    totp_secret = models.CharField(
        'totp_secret', max_length=255, blank=True, null=True)
    # backup_codes
    backup_codes = models.CharField(
        'backup_codes', max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '用户模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("users")



class UserCreateMixin(models.Model):
    """用户创建请求模型 Mixin"""

    # username
    username = models.CharField(
        'username', max_length=150)
    # email
    email = models.CharField(
        'email', max_length=255)
    # password
    password = models.CharField(
        'password', max_length=255)
    # password_confirm
    password_confirm = models.CharField(
        'password_confirm', max_length=255)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '用户创建请求模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("usercreate")



class UserUpdateMixin(models.Model):
    """用户更新请求模型 Mixin"""

    # username
    username = models.CharField(
        'username', max_length=150)
    # email
    email = models.CharField(
        'email', max_length=255)
    # profile_picture
    profile_picture = models.CharField(
        'profile_picture', max_length=255, blank=True, null=True)
    # bio
    bio = models.CharField(
        'bio', max_length=255, blank=True, null=True)
    # locale
    locale = models.CharField(
        'locale', max_length=255, default='zh_CN')
    # profile_private
    profile_private = models.BooleanField(
        'profile_private', default=False)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '用户更新请求模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("userupdate")



class ProfileUpdateRequestMixin(models.Model):
    """用户资料更新请求 Mixin"""

    # username
    username = models.CharField(
        'username', max_length=255, blank=True, null=True)
    # email
    email = models.CharField(
        'email', max_length=255, blank=True, null=True)
    # bio
    bio = models.CharField(
        'bio', max_length=255, blank=True, null=True)
    # profile_private
    profile_private = models.BooleanField(
        'profile_private', default=False)
    # locale
    locale = models.CharField(
        'locale', max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '用户资料更新请求'
        # 注意：请在具体模型类中设置 db_table = get_table_name("profileupdaterequest")



class PasswordChangeMixin(models.Model):
    """密码修改请求模型 Mixin"""

    # old_password
    old_password = models.CharField(
        'old_password', max_length=255)
    # new_password
    new_password = models.CharField(
        'new_password', max_length=255)
    # new_password_confirm
    new_password_confirm = models.CharField(
        'new_password_confirm', max_length=255)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '密码修改请求模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("passwordchange")



class ArticleMixin(models.Model):
    """文章模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # title
    title = models.CharField(
        'title', max_length=255)
    # slug
    slug = models.CharField(
        'slug', max_length=255)
    # excerpt
    excerpt = models.CharField(
        'excerpt', max_length=255, blank=True, null=True)
    # cover_image
    cover_image = models.CharField(
        'cover_image', max_length=255, blank=True, null=True)
    # category
    category = models.IntegerField(
        'category (暂为 IntegerField，等待 Category 模型实现)', null=True, blank=True)
    # tags_list
    tags_list = models.CharField(
        'tags_list', max_length=255)
    # views
    views = models.BigIntegerField(
        'views', default=0)
    # user
    user = models.IntegerField(
        'user (暂为 IntegerField，等待 User 模型实现)', )
    # likes
    likes = models.BigIntegerField(
        'likes', default=0)
    # status
    status = models.IntegerField(
        'status')
    # hidden
    hidden = models.BooleanField(
        'hidden', default=False)
    # is_featured
    is_featured = models.BooleanField(
        'is_featured', default=False)
    # is_vip_only
    is_vip_only = models.BooleanField(
        'is_vip_only', default=False)
    # required_vip_level
    required_vip_level = models.IntegerField(
        'required_vip_level', default=0)
    # article_ad
    article_ad = models.CharField(
        'article_ad', max_length=255, blank=True, null=True)
    # scheduled_publish_at
    scheduled_publish_at = models.DateTimeField(
        'scheduled_publish_at', blank=True, null=True)
    # post_type
    post_type = models.CharField(
        'post_type', max_length=50, default='article')
    # is_sticky
    is_sticky = models.BooleanField(
        'is_sticky', default=False)
    # sticky_until
    sticky_until = models.DateTimeField(
        'sticky_until', blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '文章模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("articles")



class ArticleListMixin(models.Model):
    """文章列表模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # title
    title = models.CharField(
        'title', max_length=255)
    # slug
    slug = models.CharField(
        'slug', max_length=255)
    # excerpt
    excerpt = models.CharField(
        'excerpt', max_length=255, blank=True, null=True)
    # cover_image
    cover_image = models.CharField(
        'cover_image', max_length=255, blank=True, null=True)
    # category_id
    category_id = models.BigIntegerField(
        'category_id', blank=True, null=True)
    # tags_list
    tags_list = models.CharField(
        'tags_list', max_length=255)
    # views
    views = models.BigIntegerField(
        'views', default=0)
    # likes
    likes = models.BigIntegerField(
        'likes', default=0)
    # status
    status = models.IntegerField(
        'status')
    # is_featured
    is_featured = models.BooleanField(
        'is_featured', default=False)
    # is_vip_only
    is_vip_only = models.BooleanField(
        'is_vip_only', default=False)
    # required_vip_level
    required_vip_level = models.IntegerField(
        'required_vip_level', default=0)
    # is_sticky
    is_sticky = models.BooleanField(
        'is_sticky', default=False)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '文章列表模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("articlelist")



class AuthorSimpleMixin(models.Model):
    """作者简化信息 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # username
    username = models.CharField(
        'username', max_length=255)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '作者简化信息'
        # 注意：请在具体模型类中设置 db_table = get_table_name("authorsimple")



class ArticleCreateUpdateMixin(models.Model):
    """文章创建/更新请求模型 Mixin"""

    # title
    title = models.CharField(
        'title', max_length=255)
    # slug
    slug = models.CharField(
        'slug', max_length=255)
    # excerpt
    excerpt = models.CharField(
        'excerpt', max_length=255, blank=True, null=True)
    # cover_image
    cover_image = models.CharField(
        'cover_image', max_length=255, blank=True, null=True)
    # category_id
    category_id = models.BigIntegerField(
        'category_id', blank=True, null=True)
    # tags
    tags = models.CharField(
        'tags', max_length=255, blank=True, null=True)
    # status
    status = models.BigIntegerField(
        'status', default=1)
    # hidden
    hidden = models.BooleanField(
        'hidden', default=False)
    # is_featured
    is_featured = models.BooleanField(
        'is_featured', default=False)
    # is_vip_only
    is_vip_only = models.BooleanField(
        'is_vip_only', default=False)
    # required_vip_level
    required_vip_level = models.BigIntegerField(
        'required_vip_level', default=0)
    # article_ad
    article_ad = models.CharField(
        'article_ad', max_length=255, blank=True, null=True)
    # scheduled_publish_at
    scheduled_publish_at = models.DateTimeField(
        'scheduled_publish_at', blank=True, null=True)
    # is_sticky
    is_sticky = models.BooleanField(
        'is_sticky', default=False)
    # sticky_until
    sticky_until = models.DateTimeField(
        'sticky_until', blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '文章创建/更新请求模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("articlecreateupdate")



class CategoryMixin(models.Model):
    """分类模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # name
    name = models.CharField(
        'name', max_length=100)
    # slug
    slug = models.CharField(
        'slug', max_length=255, blank=True, null=True)
    # description
    description = models.CharField(
        'description', max_length=255, blank=True, null=True)
    # parent_id
    parent_id = models.BigIntegerField(
        'parent_id', blank=True, null=True)
    # sort_order
    sort_order = models.BigIntegerField(
        'sort_order', default=0)
    # icon
    icon = models.CharField(
        'icon', max_length=255, blank=True, null=True)
    # color
    color = models.CharField(
        'color', max_length=255, blank=True, null=True)
    # is_visible
    is_visible = models.BooleanField(
        'is_visible', default=True)
    # articles_count
    articles_count = models.BigIntegerField(
        'articles_count')

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '分类模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("categories")



class CategoryCreateUpdateMixin(models.Model):
    """分类创建/更新请求模型 Mixin"""

    # name
    name = models.CharField(
        'name', max_length=100)
    # slug
    slug = models.CharField(
        'slug', max_length=255, blank=True, null=True)
    # description
    description = models.CharField(
        'description', max_length=255, blank=True, null=True)
    # parent_id
    parent_id = models.BigIntegerField(
        'parent_id', blank=True, null=True)
    # sort_order
    sort_order = models.BigIntegerField(
        'sort_order', default=0)
    # icon
    icon = models.CharField(
        'icon', max_length=255, blank=True, null=True)
    # color
    color = models.CharField(
        'color', max_length=255, blank=True, null=True)
    # is_visible
    is_visible = models.BooleanField(
        'is_visible', default=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '分类创建/更新请求模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("categorycreateupdate")



class CategorySubscriptionMixin(models.Model):
    """分类订阅模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # category
    category = models.IntegerField(
        'category (暂为 IntegerField，等待 Category 模型实现)', )
    # subscriber
    subscriber = models.IntegerField(
        'subscriber (暂为 IntegerField，等待 User 模型实现)', )

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '分类订阅模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("category_subscriptions")



class MediaMixin(models.Model):
    """媒体文件模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # user
    user = models.IntegerField(
        'user (暂为 IntegerField，等待 User 模型实现)', )
    # hash
    hash = models.CharField(
        'hash', max_length=64)
    # filename
    filename = models.CharField(
        'filename', max_length=255)
    # original_filename
    original_filename = models.CharField(
        'original_filename', max_length=255, blank=True, null=True)
    # file_path
    file_path = models.CharField(
        'file_path', max_length=500)
    # file_url
    file_url = models.CharField(
        'file_url', max_length=500)
    # file_size
    file_size = models.BigIntegerField(
        'file_size', default=0)
    # file_type
    file_type = models.CharField(
        'file_type', max_length=255, default='other')
    # mime_type
    mime_type = models.CharField(
        'mime_type', max_length=255, blank=True, null=True)
    # width
    width = models.BigIntegerField(
        'width', blank=True, null=True)
    # height
    height = models.BigIntegerField(
        'height', blank=True, null=True)
    # duration
    duration = models.BigIntegerField(
        'duration', blank=True, null=True)
    # thumbnail_path
    thumbnail_path = models.CharField(
        'thumbnail_path', max_length=255, blank=True, null=True)
    # thumbnail_url
    thumbnail_url = models.CharField(
        'thumbnail_url', max_length=255, blank=True, null=True)
    # description
    description = models.CharField(
        'description', max_length=255, blank=True, null=True)
    # alt_text
    alt_text = models.CharField(
        'alt_text', max_length=255, blank=True, null=True)
    # is_public
    is_public = models.BooleanField(
        'is_public', default=True)
    # download_count
    download_count = models.BigIntegerField(
        'download_count', default=0)
    # category
    category = models.CharField(
        'category', max_length=100, blank=True, null=True)
    # tags
    tags = models.CharField(
        'tags', max_length=500, blank=True, null=True)
    # folder_id
    folder_id = models.IntegerField(
        'folder_id (暂为 IntegerField，等待 MediaFolder 模型实现)', null=True, blank=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '媒体文件模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("media")



class MediaFolderMixin(models.Model):
    """媒体文件夹模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # name
    name = models.CharField(
        'name', max_length=255)
    # parent_id
    parent_id = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        verbose_name='parent_id', null=True, blank=True)
    # user
    user = models.IntegerField(
        'user (暂为 IntegerField，等待 User 模型实现)', )
    # description
    description = models.CharField(
        'description', max_length=255, blank=True, null=True)
    # sort_order
    sort_order = models.BigIntegerField(
        'sort_order', default=0)
    # is_public
    is_public = models.BooleanField(
        'is_public', default=True)
    # media_count
    media_count = models.BigIntegerField(
        'media_count', default=0)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '媒体文件夹模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("media_folders")



class SystemSettingsMixin(models.Model):
    """系统设置模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # setting_key
    setting_key = models.CharField(
        'setting_key', max_length=100)
    # setting_value
    setting_value = models.CharField(
        'setting_value', max_length=255)
    # setting_type
    setting_type = models.CharField(
        'setting_type', max_length=255, default='string')
    # description
    description = models.CharField(
        'description', max_length=255, blank=True, null=True)
    # is_public
    is_public = models.BooleanField(
        'is_public', default=False)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '系统设置模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("system_settings")



class AdminSettingsMixin(models.Model):
    """管理员设置模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # user
    user = models.IntegerField(
        'user (暂为 IntegerField，等待 User 模型实现)', )
    # settings_data
    settings_data = models.TextField(
        'settings_data')

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '管理员设置模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("adminsettings")



class ArticleContentMixin(models.Model):
    """文章内容模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # article
    article = models.IntegerField(
        'article (暂为 IntegerField，等待 Article 模型实现)', )
    # passwd
    passwd = models.CharField(
        'passwd', max_length=255, blank=True, null=True)
    # content
    content = models.TextField(
        'content')
    # language_code
    language_code = models.CharField(
        'language_code', max_length=255, default='zh-CN')

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '文章内容模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("article_content")



class ArticleI18nMixin(models.Model):
    """文章国际化模型 Mixin"""

    # i18n_id
    i18n_id = models.BigAutoField(
        'i18n_id', primary_key=True)
    # article
    article = models.IntegerField(
        'article (暂为 IntegerField，等待 Article 模型实现)', )
    # language_id
    language_id = models.CharField(
        'language_id', max_length=10)
    # title
    title = models.CharField(
        'title', max_length=255)
    # slug
    slug = models.CharField(
        'slug', max_length=255)
    # content
    content = models.TextField(
        'content')
    # excerpt
    excerpt = models.CharField(
        'excerpt', max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '文章国际化模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("article_i18n")



class ArticleLikeMixin(models.Model):
    """文章点赞模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # user
    user = models.IntegerField(
        'user (暂为 IntegerField，等待 User 模型实现)', )
    # article
    article = models.IntegerField(
        'article (暂为 IntegerField，等待 Article 模型实现)', )

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '文章点赞模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("article_likes")



class FileHashMixin(models.Model):
    """文件哈希模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # hash
    hash = models.CharField(
        'hash', max_length=64)
    # filename
    filename = models.CharField(
        'filename', max_length=255)
    # reference_count
    reference_count = models.BigIntegerField(
        'reference_count', default=1)
    # file_size
    file_size = models.BigIntegerField(
        'file_size')
    # mime_type
    mime_type = models.CharField(
        'mime_type', max_length=100)
    # storage_path
    storage_path = models.CharField(
        'storage_path', max_length=512)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '文件哈希模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("file_hashs")



class MenusMixin(models.Model):
    """菜单模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # name
    name = models.CharField(
        'name', max_length=100)
    # slug
    slug = models.CharField(
        'slug', max_length=100)
    # description
    description = models.CharField(
        'description', max_length=255, blank=True, null=True)
    # is_active
    is_active = models.BooleanField(
        'is_active', default=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '菜单模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("menus")



class MenuItemsMixin(models.Model):
    """菜单项模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # menu_id
    menu_id = models.IntegerField(
        'menu_id')
    # parent_id
    parent_id = models.IntegerField(
        'parent_id', blank=True, null=True)
    # title
    title = models.CharField(
        'title', max_length=255)
    # url
    url = models.CharField(
        'url', max_length=500)
    # target
    target = models.CharField(
        'target', max_length=255, default='_self')
    # order_index
    order_index = models.IntegerField(
        'order_index', default=0)
    # is_active
    is_active = models.BooleanField(
        'is_active', default=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '菜单项模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("menu_items")



class MenuLocationMixin(models.Model):
    """菜单位置模型（主菜单、页脚菜单等） Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # name
    name = models.CharField(
        'name', max_length=100)
    # slug
    slug = models.CharField(
        'slug', max_length=100, unique=True)
    # description
    description = models.CharField(
        'description', max_length=255, blank=True, null=True)
    # theme_supports
    theme_supports = models.CharField(
        'theme_supports', max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '菜单位置模型（主菜单、页脚菜单等）'
        # 注意：请在具体模型类中设置 db_table = get_table_name("menu_locations")



class MenuLocationAssignmentMixin(models.Model):
    """菜单-位置关联表 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # menu_id
    menu_id = models.IntegerField(
        'menu_id (暂为 IntegerField，等待 Menus 模型实现)', )
    # location_id
    location_id = models.IntegerField(
        'location_id (暂为 IntegerField，等待 MenuLocation 模型实现)', )

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '菜单-位置关联表'
        # 注意：请在具体模型类中设置 db_table = get_table_name("menu_location_assignments")



class PagesMixin(models.Model):
    """页面模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # title
    title = models.CharField(
        'title', max_length=255)
    # slug
    slug = models.CharField(
        'slug', max_length=255)
    # content
    content = models.CharField(
        'content', max_length=255)
    # excerpt
    excerpt = models.CharField(
        'excerpt', max_length=255, blank=True, null=True)
    # template
    template = models.CharField(
        'template', max_length=255, blank=True, null=True)
    # status
    status = models.BigIntegerField(
        'status', default=0)
    # author_id
    author_id = models.BigIntegerField(
        'author_id', blank=True, null=True)
    # parent_id
    parent_id = models.BigIntegerField(
        'parent_id', blank=True, null=True)
    # order_index
    order_index = models.IntegerField(
        'order_index', default=0)
    # meta_title
    meta_title = models.CharField(
        'meta_title', max_length=255, blank=True, null=True)
    # meta_description
    meta_description = models.CharField(
        'meta_description', max_length=255, blank=True, null=True)
    # meta_keywords
    meta_keywords = models.CharField(
        'meta_keywords', max_length=255, blank=True, null=True)
    # published_at
    published_at = models.DateTimeField(
        'published_at', blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '页面模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("pages")



class UploadTaskMixin(models.Model):
    """上传任务模型 Mixin"""

    # id
    id = models.CharField(
        'id', max_length=36)
    # user_id
    user_id = models.BigIntegerField(
        'user_id')
    # filename
    filename = models.CharField(
        'filename', max_length=255)
    # total_size
    total_size = models.BigIntegerField(
        'total_size')
    # total_chunks
    total_chunks = models.BigIntegerField(
        'total_chunks')
    # uploaded_chunks
    uploaded_chunks = models.BigIntegerField(
        'uploaded_chunks', default=0)
    # file_hash
    file_hash = models.CharField(
        'file_hash', max_length=64, blank=True, null=True)
    # status
    status = models.CharField(
        'status', max_length=255, default='initialized')

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '上传任务模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("upload_tasks")



class UploadChunkMixin(models.Model):
    """上传分块模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # upload_id
    upload_id = models.CharField(
        'upload_id', max_length=36)
    # chunk_index
    chunk_index = models.BigIntegerField(
        'chunk_index')
    # chunk_hash
    chunk_hash = models.CharField(
        'chunk_hash', max_length=64)
    # chunk_size
    chunk_size = models.BigIntegerField(
        'chunk_size')
    # chunk_path
    chunk_path = models.CharField(
        'chunk_path', max_length=500)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '上传分块模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("upload_chunks")



class NotificationMixin(models.Model):
    """通知模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # recipient
    recipient = models.IntegerField(
        'recipient (暂为 IntegerField，等待 User 模型实现)', )
    # type
    type = models.CharField(
        'type', max_length=100)
    # title
    title = models.CharField(
        'title', max_length=200)
    # message
    message = models.CharField(
        'message', max_length=255)
    # is_read
    is_read = models.BooleanField(
        'is_read', default=False)
    # read_at
    read_at = models.DateTimeField(
        'read_at', blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '通知模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("notifications")



class SearchHistoryMixin(models.Model):
    """搜索历史模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # user
    user = models.IntegerField(
        'user (暂为 IntegerField，等待 User 模型实现)', )
    # keyword
    keyword = models.CharField(
        'keyword', max_length=255)
    # results_count
    results_count = models.BigIntegerField(
        'results_count')

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '搜索历史模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("search_history")



class PageViewMixin(models.Model):
    """页面浏览模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # user
    user = models.IntegerField(
        'user (暂为 IntegerField，等待 User 模型实现)', null=True, blank=True)
    # session_id
    session_id = models.CharField(
        'session_id', max_length=255, blank=True, null=True)
    # page_url
    page_url = models.CharField(
        'page_url', max_length=500)
    # page_title
    page_title = models.CharField(
        'page_title', max_length=500, blank=True, null=True)
    # referrer
    referrer = models.CharField(
        'referrer', max_length=500, blank=True, null=True)
    # user_agent
    user_agent = models.CharField(
        'user_agent', max_length=500, blank=True, null=True)
    # ip_address
    ip_address = models.CharField(
        'ip_address', max_length=45, blank=True, null=True)
    # device_type
    device_type = models.CharField(
        'device_type', max_length=50, blank=True, null=True)
    # browser
    browser = models.CharField(
        'browser', max_length=100, blank=True, null=True)
    # platform
    platform = models.CharField(
        'platform', max_length=100, blank=True, null=True)
    # country
    country = models.CharField(
        'country', max_length=100, blank=True, null=True)
    # city
    city = models.CharField(
        'city', max_length=100, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '页面浏览模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("page_views")



class UserActivityMixin(models.Model):
    """用户活动模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # user
    user = models.IntegerField(
        'user (暂为 IntegerField，等待 User 模型实现)', )
    # activity_type
    activity_type = models.CharField(
        'activity_type', max_length=100)
    # target_type
    target_type = models.CharField(
        'target_type', max_length=50)
    # target_id
    target_id = models.BigIntegerField(
        'target_id')
    # details
    details = models.CharField(
        'details', max_length=255, blank=True, null=True)
    # ip_address
    ip_address = models.CharField(
        'ip_address', max_length=45, blank=True, null=True)
    # user_agent
    user_agent = models.CharField(
        'user_agent', max_length=500, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '用户活动模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("user_activities")



class VIPPlanMixin(models.Model):
    """VIP 套餐模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # name
    name = models.CharField(
        'name', max_length=100)
    # description
    description = models.CharField(
        'description', max_length=255, blank=True, null=True)
    # price
    price = models.DecimalField(
        'price', max_digits=10, decimal_places=2)
    # original_price
    original_price = models.DecimalField(
        'original_price', max_digits=10, decimal_places=2, blank=True, null=True)
    # duration_days
    duration_days = models.IntegerField(
        'duration_days')
    # level
    level = models.BigIntegerField(
        'level', default=1)
    # features
    features = models.CharField(
        'features', max_length=255, blank=True, null=True)
    # is_active
    is_active = models.BooleanField(
        'is_active', default=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = 'VIP 套餐模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("vip_plans")



class VIPSubscriptionMixin(models.Model):
    """VIP 订阅模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # user
    user = models.IntegerField(
        'user (暂为 IntegerField，等待 User 模型实现)', )
    # plan
    plan = models.IntegerField(
        'plan (暂为 IntegerField，等待 VIPPlan 模型实现)', )
    # starts_at
    starts_at = models.DateTimeField(
        'starts_at')
    # expires_at
    expires_at = models.DateTimeField(
        'expires_at')
    # status
    status = models.BigIntegerField(
        'status', default=0)
    # payment_amount
    payment_amount = models.DecimalField(
        'payment_amount', max_digits=10, decimal_places=2, blank=True, null=True)
    # transaction_id
    transaction_id = models.CharField(
        'transaction_id', max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = 'VIP 订阅模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("vip_subscriptions")



class VIPFeatureMixin(models.Model):
    """VIP 功能特权模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # code
    code = models.CharField(
        'code', max_length=50)
    # name
    name = models.CharField(
        'name', max_length=100)
    # description
    description = models.CharField(
        'description', max_length=255, blank=True, null=True)
    # required_level
    required_level = models.IntegerField(
        'required_level', default=1)
    # is_active
    is_active = models.BooleanField(
        'is_active', default=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = 'VIP 功能特权模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("vip_features")



class CustomFieldMixin(models.Model):
    """自定义字段模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # user
    user = models.IntegerField(
        'user (暂为 IntegerField，等待 User 模型实现)', )
    # field_name
    field_name = models.CharField(
        'field_name', max_length=100)
    # field_value
    field_value = models.CharField(
        'field_value', max_length=255)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '自定义字段模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("custom_fields")



class EmailSubscriptionMixin(models.Model):
    """邮件订阅模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # user
    user = models.IntegerField(
        'user (暂为 IntegerField，等待 User 模型实现)', )
    # subscribed
    subscribed = models.BooleanField(
        'subscribed', default=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '邮件订阅模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("email_subscriptions")



class ArticleRevisionMixin(models.Model):
    """文章修订历史模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # article_id
    article_id = models.IntegerField(
        'article_id (暂为 IntegerField，等待 Article 模型实现)', )
    # revision_number
    revision_number = models.BigIntegerField(
        'revision_number')
    # title
    title = models.CharField(
        'title', max_length=255)
    # excerpt
    excerpt = models.CharField(
        'excerpt', max_length=255, blank=True, null=True)
    # content
    content = models.TextField(
        'content')
    # cover_image
    cover_image = models.CharField(
        'cover_image', max_length=255, blank=True, null=True)
    # tags_list
    tags_list = models.CharField(
        'tags_list', max_length=255, blank=True, null=True)
    # category_id
    category_id = models.BigIntegerField(
        'category_id', blank=True, null=True)
    # status
    status = models.BigIntegerField(
        'status', default=0)
    # hidden
    hidden = models.BooleanField(
        'hidden', default=False)
    # is_featured
    is_featured = models.BooleanField(
        'is_featured', default=False)
    # is_vip_only
    is_vip_only = models.BooleanField(
        'is_vip_only', default=False)
    # required_vip_level
    required_vip_level = models.BigIntegerField(
        'required_vip_level', default=0)
    # author_id
    author_id = models.IntegerField(
        'author_id (暂为 IntegerField，等待 User 模型实现)', null=True, blank=True)
    # change_summary
    change_summary = models.CharField(
        'change_summary', max_length=500, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '文章修订历史模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("article_revisions")



class PluginMixin(models.Model):
    """插件模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # name
    name = models.CharField(
        'name', max_length=100)
    # slug
    slug = models.CharField(
        'slug', max_length=100, unique=True)
    # version
    version = models.CharField(
        'version', max_length=20)
    # description
    description = models.CharField(
        'description', max_length=255, blank=True, null=True)
    # author
    author = models.CharField(
        'author', max_length=100, blank=True, null=True)
    # author_url
    author_url = models.CharField(
        'author_url', max_length=255, blank=True, null=True)
    # plugin_url
    plugin_url = models.CharField(
        'plugin_url', max_length=255, blank=True, null=True)
    # is_active
    is_active = models.BooleanField(
        'is_active', default=False)
    # is_installed
    is_installed = models.BooleanField(
        'is_installed', default=True)
    # settings
    settings = models.TextField(
        'settings', blank=True, null=True)
    # priority
    priority = models.IntegerField(
        'priority', default=0)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '插件模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("plugins")



class ThemeMixin(models.Model):
    """主题模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # name
    name = models.CharField(
        'name', max_length=100)
    # slug
    slug = models.CharField(
        'slug', max_length=100, unique=True)
    # version
    version = models.CharField(
        'version', max_length=20)
    # description
    description = models.CharField(
        'description', max_length=255, blank=True, null=True)
    # author
    author = models.CharField(
        'author', max_length=100, blank=True, null=True)
    # author_url
    author_url = models.CharField(
        'author_url', max_length=255, blank=True, null=True)
    # theme_url
    theme_url = models.CharField(
        'theme_url', max_length=255, blank=True, null=True)
    # screenshot
    screenshot = models.CharField(
        'screenshot', max_length=500, blank=True, null=True)
    # tags
    tags = models.CharField(
        'tags', max_length=255, blank=True, null=True)
    # requires
    requires = models.CharField(
        'requires', max_length=255, blank=True, null=True)
    # settings_schema
    settings_schema = models.CharField(
        'settings_schema', max_length=255, blank=True, null=True)
    # theme_path
    theme_path = models.CharField(
        'theme_path', max_length=500, blank=True, null=True)
    # is_active
    is_active = models.BooleanField(
        'is_active', default=False)
    # is_installed
    is_installed = models.BooleanField(
        'is_installed', default=True)
    # settings
    settings = models.CharField(
        'settings', max_length=255, blank=True, null=True)
    # supports
    supports = models.CharField(
        'supports', max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '主题模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("themes")



class FormMixin(models.Model):
    """表单模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # title
    title = models.CharField(
        'title', max_length=255)
    # slug
    slug = models.CharField(
        'slug', max_length=255, unique=True)
    # description
    description = models.CharField(
        'description', max_length=255, blank=True, null=True)
    # status
    status = models.CharField(
        'status', max_length=255, default='draft')
    # submit_message
    submit_message = models.CharField(
        'submit_message', max_length=255, blank=True, null=True)
    # email_notification
    email_notification = models.BooleanField(
        'email_notification', default=False)
    # notification_email
    notification_email = models.CharField(
        'notification_email', max_length=255, blank=True, null=True)
    # store_submissions
    store_submissions = models.BooleanField(
        'store_submissions', default=True)
    # published_at
    published_at = models.DateTimeField(
        'published_at', blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '表单模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("forms")



class FormFieldMixin(models.Model):
    """表单字段模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # form_id
    form_id = models.IntegerField(
        'form_id (暂为 IntegerField，等待 Form 模型实现)', )
    # label
    label = models.CharField(
        'label', max_length=255)
    # field_type
    field_type = models.CharField(
        'field_type', max_length=50)
    # placeholder
    placeholder = models.CharField(
        'placeholder', max_length=255, blank=True, null=True)
    # help_text
    help_text = models.CharField(
        'help_text', max_length=255, blank=True, null=True)
    # required
    required = models.BooleanField(
        'required', default=False)
    # options
    options = models.CharField(
        'options', max_length=255, blank=True, null=True)
    # validation_rules
    validation_rules = models.CharField(
        'validation_rules', max_length=255, blank=True, null=True)
    # default_value
    default_value = models.CharField(
        'default_value', max_length=255, blank=True, null=True)
    # order_index
    order_index = models.BigIntegerField(
        'order_index', default=0)
    # is_active
    is_active = models.BooleanField(
        'is_active', default=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '表单字段模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("form_fields")



class FormSubmissionMixin(models.Model):
    """表单提交记录模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # form_id
    form_id = models.IntegerField(
        'form_id (暂为 IntegerField，等待 Form 模型实现)', )
    # data
    data = models.CharField(
        'data', max_length=255)
    # ip_address
    ip_address = models.CharField(
        'ip_address', max_length=45, blank=True, null=True)
    # user_agent
    user_agent = models.CharField(
        'user_agent', max_length=255, blank=True, null=True)
    # user_id
    user_id = models.IntegerField(
        'user_id (暂为 IntegerField，等待 User 模型实现)', null=True, blank=True)
    # status
    status = models.CharField(
        'status', max_length=255, default='new')

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '表单提交记录模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("form_submissions")



class WidgetInstanceMixin(models.Model):
    """Widget实例模型（持久化存储） Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # widget_type
    widget_type = models.CharField(
        'widget_type', max_length=50)
    # area
    area = models.CharField(
        'area', max_length=50)
    # title
    title = models.CharField(
        'title', max_length=255, blank=True, null=True)
    # config
    config = models.CharField(
        'config', max_length=255)
    # order_index
    order_index = models.BigIntegerField(
        'order_index', default=0)
    # is_active
    is_active = models.BooleanField(
        'is_active', default=True)
    # conditions
    conditions = models.CharField(
        'conditions', max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = 'Widget实例模型（持久化存储）'
        # 注意：请在具体模型类中设置 db_table = get_table_name("widget_instances")



class BlockPatternMixin(models.Model):
    """自定义块模式模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # name
    name = models.CharField(
        'name', max_length=100, unique=True)
    # title
    title = models.CharField(
        'title', max_length=255)
    # description
    description = models.TextField(
        'description', blank=True, null=True)
    # category
    category = models.CharField(
        'category', max_length=50, default='custom')
    # blocks
    blocks = models.TextField(
        'blocks')
    # keywords
    keywords = models.TextField(
        'keywords', blank=True, null=True)
    # thumbnail
    thumbnail = models.CharField(
        'thumbnail', max_length=500, blank=True, null=True)
    # is_public
    is_public = models.BooleanField(
        'is_public', default=False)
    # user_id
    user_id = models.IntegerField(
        'user_id (暂为 IntegerField，等待 User 模型实现)', null=True, blank=True)
    # viewport_width
    viewport_width = models.BigIntegerField(
        'viewport_width', default=800)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '自定义块模式模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("block_patterns")



class CustomPostTypeMixin(models.Model):
    """自定义内容类型模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # name
    name = models.CharField(
        'name', max_length=100)
    # slug
    slug = models.CharField(
        'slug', max_length=100, unique=True)
    # description
    description = models.CharField(
        'description', max_length=255, blank=True, null=True)
    # supports
    supports = models.CharField(
        'supports', max_length=255, blank=True, null=True)
    # has_archive
    has_archive = models.BooleanField(
        'has_archive', default=False)
    # menu_icon
    menu_icon = models.CharField(
        'menu_icon', max_length=255, blank=True, null=True)
    # menu_position
    menu_position = models.IntegerField(
        'menu_position', default=5)
    # is_active
    is_active = models.BooleanField(
        'is_active', default=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '自定义内容类型模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("custom_post_types")



class CommentVoteMixin(models.Model):
    """评论投票模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # comment_id
    comment_id = models.BigIntegerField(
        'comment_id')
    # user
    user = models.IntegerField(
        'user (暂为 IntegerField，等待 User 模型实现)', null=True, blank=True)
    # vote_type
    vote_type = models.IntegerField(
        'vote_type')
    # ip_address
    ip_address = models.CharField(
        'ip_address', max_length=45, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '评论投票模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("comment_votes")



class CommentSubscriptionMixin(models.Model):
    """评论订阅模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # article_id
    article_id = models.BigIntegerField(
        'article_id')
    # user_id
    user_id = models.IntegerField(
        'user_id (暂为 IntegerField，等待 User 模型实现)', null=True, blank=True)
    # email
    email = models.CharField(
        'email', max_length=255)
    # notify_type
    notify_type = models.CharField(
        'notify_type', max_length=255, default='new_comment')
    # is_active
    is_active = models.BooleanField(
        'is_active', default=True)
    # confirm_token
    confirm_token = models.CharField(
        'confirm_token', max_length=64, blank=True, null=True)
    # confirmed_at
    confirmed_at = models.DateTimeField(
        'confirmed_at', blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '评论订阅模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("comment_subscriptions")



class CommentMixin(models.Model):
    """评论模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # article_id
    article_id = models.IntegerField(
        'article_id (暂为 IntegerField，等待 Article 模型实现)', )
    # user_id
    user_id = models.IntegerField(
        'user_id (暂为 IntegerField，等待 User 模型实现)', null=True, blank=True)
    # parent_id
    parent_id = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        verbose_name='parent_id', null=True, blank=True)
    # content
    content = models.TextField(
        'content')
    # author_name
    author_name = models.CharField(
        'author_name', max_length=100, blank=True, null=True)
    # author_email
    author_email = models.CharField(
        'author_email', max_length=255, blank=True, null=True)
    # author_url
    author_url = models.CharField(
        'author_url', max_length=500, blank=True, null=True)
    # author_ip
    author_ip = models.CharField(
        'author_ip', max_length=45, blank=True, null=True)
    # user_agent
    user_agent = models.CharField(
        'user_agent', max_length=500, blank=True, null=True)
    # is_approved
    is_approved = models.BooleanField(
        'is_approved', default=True)
    # likes
    likes = models.BigIntegerField(
        'likes', default=0)
    # spam_score
    spam_score = models.DecimalField(
        'spam_score', max_digits=10, decimal_places=2, blank=True, null=True)
    # spam_reasons
    spam_reasons = models.CharField(
        'spam_reasons', max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '评论模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("comments")



class RoleMixin(models.Model):
    """角色模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # name
    name = models.CharField(
        'name', max_length=100)
    # slug
    slug = models.CharField(
        'slug', max_length=100, unique=True)
    # description
    description = models.CharField(
        'description', max_length=255, blank=True, null=True)
    # permissions
    permissions = models.CharField(
        'permissions', max_length=255, blank=True, null=True)
    # is_system
    is_system = models.BooleanField(
        'is_system', default=False)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '角色模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("roles")



class CapabilityMixin(models.Model):
    """权限能力模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # code
    code = models.CharField(
        'code', max_length=100, unique=True)
    # name
    name = models.CharField(
        'name', max_length=255)
    # description
    description = models.CharField(
        'description', max_length=255, blank=True, null=True)
    # resource_type
    resource_type = models.CharField(
        'resource_type', max_length=100, blank=True, null=True)
    # action
    action = models.CharField(
        'action', max_length=50, blank=True, null=True)
    # is_active
    is_active = models.BooleanField(
        'is_active', default=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '权限能力模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("capabilities")



class UserRoleMixin(models.Model):
    """用户角色关联模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # user_id
    user_id = models.IntegerField(
        'user_id (暂为 IntegerField，等待 User 模型实现)', )
    # role_id
    role_id = models.IntegerField(
        'role_id (暂为 IntegerField，等待 Role 模型实现)', )
    # assigned_by
    assigned_by = models.IntegerField(
        'assigned_by (暂为 IntegerField，等待 User 模型实现)', null=True, blank=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '用户角色关联模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("user_role_assignments")


class OAuthAccountMixin(models.Model):
    """OAuth 第三方登录账号关联模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # user_id
    user_id = models.IntegerField(
        'user_id (暂为 IntegerField，等待 User 模型实现)', )
    # provider
    provider = models.CharField(
        'provider', max_length=50)
    # provider_user_id
    provider_user_id = models.CharField(
        'provider_user_id', max_length=255)
    # access_token
    access_token = models.CharField(
        'access_token', max_length=255, blank=True, null=True)
    # refresh_token
    refresh_token = models.CharField(
        'refresh_token', max_length=255, blank=True, null=True)
    # token_expires_at
    token_expires_at = models.DateTimeField(
        'token_expires_at', blank=True, null=True)
    # extra_data
    extra_data = models.CharField(
        'extra_data', max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = 'OAuth 第三方登录账号关联模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("oauth_accounts")


class ArticleSEOMixin(models.Model):
    """文章SEO元数据模型 Mixin"""

    # id
    id = models.BigAutoField(
        'id', primary_key=True)
    # article_id
    article_id = models.IntegerField(
        'article_id (暂为 IntegerField，等待 Article 模型实现)', )
    # seo_title
    seo_title = models.CharField(
        'seo_title', max_length=255, blank=True, null=True)
    # seo_description
    seo_description = models.TextField(
        'seo_description', blank=True, null=True)
    # seo_keywords
    seo_keywords = models.CharField(
        'seo_keywords', max_length=500, blank=True, null=True)
    # og_title
    og_title = models.CharField(
        'og_title', max_length=255, blank=True, null=True)
    # og_description
    og_description = models.TextField(
        'og_description', blank=True, null=True)
    # og_image
    og_image = models.CharField(
        'og_image', max_length=500, blank=True, null=True)
    # og_type
    og_type = models.CharField(
        'og_type', max_length=50, default='article')
    # twitter_title
    twitter_title = models.CharField(
        'twitter_title', max_length=255, blank=True, null=True)
    # twitter_description
    twitter_description = models.TextField(
        'twitter_description', blank=True, null=True)
    # twitter_image
    twitter_image = models.CharField(
        'twitter_image', max_length=500, blank=True, null=True)
    # twitter_card
    twitter_card = models.CharField(
        'twitter_card', max_length=50, default='summary_large_image')
    # canonical_url
    canonical_url = models.CharField(
        'canonical_url', max_length=500, blank=True, null=True)
    # robots_meta
    robots_meta = models.CharField(
        'robots_meta', max_length=100, default='index,follow')
    # schema_org_enabled
    schema_org_enabled = models.BooleanField(
        'schema_org_enabled', default=True)
    # schema_org_type
    schema_org_type = models.CharField(
        'schema_org_type', max_length=50, default='BlogPosting')

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '文章SEO元数据模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("article_seo")
