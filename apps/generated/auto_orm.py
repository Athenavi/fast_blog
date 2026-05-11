"""
Django ORM 抽象基类定义
由 routes.yaml 自动生成 - 请勿手动修改
生成时间：2026-05-09 17:27:45
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

    # 用户 ID
    id = models.BigAutoField(
        '用户 ID'        , primary_key=True)
    # 用户名
    username = models.CharField(
        '用户名', max_length=255, unique=True)
    # 邮箱
    email = models.CharField(
        '邮箱', max_length=255)
    # 密码(哈希后存储)
    password = models.CharField(
        '密码(哈希后存储)', max_length=255)
    # 个人资料图片
    profile_picture = models.CharField(
        '个人资料图片', max_length=255, blank=True, null=True)
    # 个人简介
    bio = models.CharField(
        '个人简介', max_length=255, blank=True, null=True)
    # 是否私密资料
    profile_private = models.BooleanField(
        '是否私密资料',default=False)
    # VIP 等级
    vip_level = models.BigIntegerField(
        'VIP 等级', default=0)
    # VIP 过期时间
    vip_expires_at = models.DateTimeField(
        'VIP 过期时间', blank=True, null=True)
    # 是否激活
    is_active = models.BooleanField(
        '是否激活',default=True)
    # 是否为超级管理员
    is_superuser = models.BooleanField(
        '是否为超级管理员',default=False)
    # 注册时间
    date_joined = models.DateTimeField(
        '注册时间')
    # 上次登录时间
    last_login_at = models.DateTimeField(
        '上次登录时间', blank=True, null=True)
    # 语言设置
    locale = models.CharField(
        '语言设置', max_length=255, default='zh_CN')
    # 是否为工作人员
    is_staff = models.BooleanField(
        '是否为工作人员',default=False)
    # 上次登录 IP
    last_login_ip = models.CharField(
        '上次登录 IP', max_length=255, blank=True, null=True)
    # 注册 IP
    register_ip = models.CharField(
        '注册 IP', max_length=255, blank=True, null=True)
    # 是否启用双因素认证
    is_2fa_enabled = models.BooleanField(
        '是否启用双因素认证',default=False)
    # TOTP 密钥
    totp_secret = models.CharField(
        'TOTP 密钥', max_length=32, blank=True, null=True)
    # 备用码(JSON格式存储)
    backup_codes = models.TextField(
        '备用码(JSON格式存储)', blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '用户模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("users")



class UserCreateMixin(models.Model):
    """用户创建请求模型 Mixin"""

    # 用户名
    username = models.CharField(
        '用户名', max_length=150)
    # 邮箱
    email = models.CharField(
        '邮箱', max_length=255)
    # 密码
    password = models.CharField(
        '密码', max_length=255)
    # 确认密码
    password_confirm = models.CharField(
        '确认密码', max_length=255)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '用户创建请求模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("usercreate")



class UserUpdateMixin(models.Model):
    """用户更新请求模型 Mixin"""

    # 用户名
    username = models.CharField(
        '用户名', max_length=150)
    # 邮箱
    email = models.CharField(
        '邮箱', max_length=255)
    # 个人资料图片
    profile_picture = models.CharField(
        '个人资料图片', max_length=255, blank=True, null=True)
    # 个人简介
    bio = models.CharField(
        '个人简介', max_length=255, blank=True, null=True)
    # 语言设置
    locale = models.CharField(
        '语言设置', max_length=255, default='zh_CN')
    # 是否私密资料
    profile_private = models.BooleanField(
        '是否私密资料',default=False)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '用户更新请求模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("userupdate")



class ProfileUpdateRequestMixin(models.Model):
    """用户资料更新请求 Mixin"""

    # 用户名
    username = models.CharField(
        '用户名', max_length=255, blank=True, null=True)
    # 邮箱
    email = models.CharField(
        '邮箱', max_length=255, blank=True, null=True)
    # 个人简介
    bio = models.CharField(
        '个人简介', max_length=255, blank=True, null=True)
    # 是否私密资料
    profile_private = models.BooleanField(
        '是否私密资料',default = False)
    # 语言设置
    locale = models.CharField(
        '语言设置', max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '用户资料更新请求'
        # 注意：请在具体模型类中设置 db_table = get_table_name("profileupdaterequest")



class PasswordChangeMixin(models.Model):
    """密码修改请求模型 Mixin"""

    # 当前密码
    old_password = models.CharField(
        '当前密码', max_length=255)
    # 新密码
    new_password = models.CharField(
        '新密码', max_length=255)
    # 确认新密码
    new_password_confirm = models.CharField(
        '确认新密码', max_length=255)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '密码修改请求模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("passwordchange")



class ArticleMixin(models.Model):
    """文章模型 Mixin"""

    # 文章 ID
    id = models.BigAutoField(
        '文章 ID'        , primary_key=True)
    # 标题
    title = models.CharField(
        '标题', max_length=255)
    # 文章 slug
    slug = models.CharField(
        '文章 slug', max_length=255)
    # 摘要
    excerpt = models.CharField(
        '摘要', max_length=255, blank=True, null=True)
    # 封面图 URL
    cover_image = models.CharField(
        '封面图 URL', max_length=255, blank=True, null=True)
    # 分类
    category = models.IntegerField(
        '分类 (暂为 IntegerField，等待 Category 模型实现)',null=True, blank=True)
    # 标签列表
    tags_list = models.CharField(
        '标签列表', max_length=255)
    # 浏览量
    views = models.BigIntegerField(
        '浏览量', default=0)
    # 用户
    user = models.IntegerField(
        '用户 (暂为 IntegerField，等待 User 模型实现)',)
    # 点赞数
    likes = models.BigIntegerField(
        '点赞数', default=0)
    # 状态 (-1:已删除，0:草稿，1:已发布)
    status = models.IntegerField(
        '状态 (-1:已删除，0:草稿，1:已发布)')
    # 是否隐藏
    hidden = models.BooleanField(
        '是否隐藏',default=False)
    # 是否推荐
    is_featured = models.BooleanField(
        '是否推荐',default=False)
    # 是否仅 VIP 可见
    is_vip_only = models.BooleanField(
        '是否仅 VIP 可见',default=False)
    # 所需 VIP 等级
    required_vip_level = models.IntegerField(
        '所需 VIP 等级', default=0)
    # 广告内容
    article_ad = models.CharField(
        '广告内容', max_length=255, blank=True, null=True)
    # 定时发布时间(设置为未来时间后自动发布)
    scheduled_publish_at = models.DateTimeField(
        '定时发布时间(设置为未来时间后自动发布)', blank=True, null=True)
    # 内容类型(article/book/product等)
    post_type = models.CharField(
        '内容类型(article/book/product等)', max_length=50, default='article')
    # 是否置顶(粘性文章)
    is_sticky = models.BooleanField(
        '是否置顶(粘性文章)',default=False)
    # 置顶过期时间(可选，过期后自动取消置顶)
    sticky_until = models.DateTimeField(
        '置顶过期时间(可选，过期后自动取消置顶)', blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '文章模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("articles")



class ArticleListMixin(models.Model):
    """文章列表模型 Mixin"""

    # 文章 ID
    id = models.BigAutoField(
        '文章 ID'        , primary_key=True)
    # 标题
    title = models.CharField(
        '标题', max_length=255)
    # 文章 slug
    slug = models.CharField(
        '文章 slug', max_length=255)
    # 摘要
    excerpt = models.CharField(
        '摘要', max_length=255, blank=True, null=True)
    # 封面图 URL
    cover_image = models.CharField(
        '封面图 URL', max_length=255, blank=True, null=True)
    # 分类 ID
    category_id = models.BigIntegerField(
        '分类 ID', blank=True, null=True)
    # 标签列表
    tags_list = models.CharField(
        '标签列表', max_length=255)
    # 浏览量
    views = models.BigIntegerField(
        '浏览量', default=0)
    # 点赞数
    likes = models.BigIntegerField(
        '点赞数', default=0)
    # 状态
    status = models.IntegerField(
        '状态')
    # 是否推荐
    is_featured = models.BooleanField(
        '是否推荐',default=False)
    # 是否仅 VIP 可见
    is_vip_only = models.BooleanField(
        '是否仅 VIP 可见',default=False)
    # 所需 VIP 等级
    required_vip_level = models.IntegerField(
        '所需 VIP 等级', default=0)
    # 是否置顶
    is_sticky = models.BooleanField(
        '是否置顶',default=False)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '文章列表模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("articlelist")



class AuthorSimpleMixin(models.Model):
    """作者简化信息 Mixin"""

    # 用户 ID
    id = models.BigAutoField(
        '用户 ID'        , primary_key=True)
    # 用户名
    username = models.CharField(
        '用户名', max_length=255)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '作者简化信息'
        # 注意：请在具体模型类中设置 db_table = get_table_name("authorsimple")



class ArticleCreateUpdateMixin(models.Model):
    """文章创建/更新请求模型 Mixin"""

    # 标题
    title = models.CharField(
        '标题', max_length=255)
    # 文章 slug
    slug = models.CharField(
        '文章 slug', max_length=255)
    # 摘要
    excerpt = models.CharField(
        '摘要', max_length=255, blank=True, null=True)
    # 封面图 URL
    cover_image = models.CharField(
        '封面图 URL', max_length=255, blank=True, null=True)
    # 分类 ID
    category_id = models.BigIntegerField(
        '分类 ID', blank=True, null=True)
    # 标签 (逗号分隔)
    tags = models.CharField(
        '标签 (逗号分隔)', max_length=255, blank=True, null=True)
    # 状态
    status = models.BigIntegerField(
        '状态', default=1)
    # 是否隐藏
    hidden = models.BooleanField(
        '是否隐藏',default=False)
    # 是否推荐
    is_featured = models.BooleanField(
        '是否推荐',default=False)
    # 是否仅 VIP 可见
    is_vip_only = models.BooleanField(
        '是否仅 VIP 可见',default=False)
    # 所需 VIP 等级
    required_vip_level = models.BigIntegerField(
        '所需 VIP 等级', default=0)
    # 广告内容
    article_ad = models.CharField(
        '广告内容', max_length=255, blank=True, null=True)
    # 定时发布时间
    scheduled_publish_at = models.DateTimeField(
        '定时发布时间', blank=True, null=True)
    # 是否置顶
    is_sticky = models.BooleanField(
        '是否置顶',default=False)
    # 置顶过期时间
    sticky_until = models.DateTimeField(
        '置顶过期时间', blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '文章创建/更新请求模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("articlecreateupdate")



class CategoryMixin(models.Model):
    """分类模型 Mixin"""

    # 分类 ID
    id = models.BigAutoField(
        '分类 ID'        , primary_key=True)
    # 分类名
    name = models.CharField(
        '分类名', max_length=100)
    # 分类 slug
    slug = models.CharField(
        '分类 slug', max_length=255, blank=True, null=True)
    # 分类描述
    description = models.CharField(
        '分类描述', max_length=255, blank=True, null=True)
    # 父分类 ID
    parent_id = models.BigIntegerField(
        '父分类 ID', blank=True, null=True)
    # 排序
    sort_order = models.BigIntegerField(
        '排序', default=0)
    # 图标
    icon = models.CharField(
        '图标', max_length=255, blank=True, null=True)
    # 颜色
    color = models.CharField(
        '颜色', max_length=255, blank=True, null=True)
    # 是否可见
    is_visible = models.BooleanField(
        '是否可见',default=True)
    # 分类下的文章数量
    articles_count = models.BigIntegerField(
        '分类下的文章数量')

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '分类模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("categories")



class CategoryCreateUpdateMixin(models.Model):
    """分类创建/更新请求模型 Mixin"""

    # 分类名
    name = models.CharField(
        '分类名', max_length=100)
    # 分类 slug
    slug = models.CharField(
        '分类 slug', max_length=255, blank=True, null=True)
    # 分类描述
    description = models.CharField(
        '分类描述', max_length=255, blank=True, null=True)
    # 父分类 ID
    parent_id = models.BigIntegerField(
        '父分类 ID', blank=True, null=True)
    # 排序
    sort_order = models.BigIntegerField(
        '排序', default=0)
    # 图标
    icon = models.CharField(
        '图标', max_length=255, blank=True, null=True)
    # 颜色
    color = models.CharField(
        '颜色', max_length=255, blank=True, null=True)
    # 是否可见
    is_visible = models.BooleanField(
        '是否可见',default=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '分类创建/更新请求模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("categorycreateupdate")



class CategorySubscriptionMixin(models.Model):
    """分类订阅模型 Mixin"""

    # 订阅 ID
    id = models.BigAutoField(
        '订阅 ID'        , primary_key=True)
    # 分类
    category = models.IntegerField(
        '分类 (暂为 IntegerField，等待 Category 模型实现)',)
    # 订阅用户
    subscriber = models.IntegerField(
        '订阅用户 (暂为 IntegerField，等待 User 模型实现)',)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '分类订阅模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("category_subscriptions")



class MediaMixin(models.Model):
    """媒体文件模型 Mixin"""

    # 媒体 ID
    id = models.BigAutoField(
        '媒体 ID'        , primary_key=True)
    # 上传用户
    user = models.IntegerField(
        '上传用户 (暂为 IntegerField，等待 User 模型实现)',)
    # 文件哈希
    hash = models.CharField(
        '文件哈希', max_length=64)
    # 文件名
    filename = models.CharField(
        '文件名', max_length=255)
    # 原始文件名
    original_filename = models.CharField(
        '原始文件名', max_length=255, blank=True, null=True)
    # 文件路径
    file_path = models.CharField(
        '文件路径', max_length=500)
    # 文件 URL
    file_url = models.CharField(
        '文件 URL', max_length=500)
    # 文件大小 (字节)
    file_size = models.BigIntegerField(
        '文件大小 (字节)', default=0)
    # 文件类型
    file_type = models.CharField(
        '文件类型', max_length=255, default='other')
    # MIME 类型
    mime_type = models.CharField(
        'MIME 类型', max_length=255, blank=True, null=True)
    # 宽度
    width = models.BigIntegerField(
        '宽度', blank=True, null=True)
    # 高度
    height = models.BigIntegerField(
        '高度', blank=True, null=True)
    # 时长 (秒)
    duration = models.BigIntegerField(
        '时长 (秒)', blank=True, null=True)
    # 缩略图路径
    thumbnail_path = models.CharField(
        '缩略图路径', max_length=255, blank=True, null=True)
    # 缩略图 URL
    thumbnail_url = models.CharField(
        '缩略图 URL', max_length=255, blank=True, null=True)
    # 描述
    description = models.CharField(
        '描述', max_length=255, blank=True, null=True)
    # 替代文本
    alt_text = models.CharField(
        '替代文本', max_length=255, blank=True, null=True)
    # 是否公开
    is_public = models.BooleanField(
        '是否公开',default=True)
    # 下载次数
    download_count = models.BigIntegerField(
        '下载次数', default=0)
    # 媒体分类
    category = models.CharField(
        '媒体分类', max_length=100, blank=True, null=True)
    # 标签(逗号分隔)
    tags = models.CharField(
        '标签(逗号分隔)', max_length=500, blank=True, null=True)
    # 所属文件夹 ID
    folder_id = models.IntegerField(
        '所属文件夹 ID (暂为 IntegerField，等待 MediaFolder 模型实现)',null=True, blank=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '媒体文件模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("media")



class MediaFolderMixin(models.Model):
    """媒体文件夹模型 Mixin"""

    # 文件夹 ID
    id = models.BigAutoField(
        '文件夹 ID'        , primary_key=True)
    # 文件夹名称
    name = models.CharField(
        '文件夹名称', max_length=255)
    # 父文件夹 ID
    parent_id = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        verbose_name='父文件夹 ID',null=True, blank=True)
    # 所属用户
    user = models.IntegerField(
        '所属用户 (暂为 IntegerField，等待 User 模型实现)',)
    # 文件夹描述
    description = models.CharField(
        '文件夹描述', max_length=255, blank=True, null=True)
    # 排序顺序
    sort_order = models.BigIntegerField(
        '排序顺序', default=0)
    # 是否公开
    is_public = models.BooleanField(
        '是否公开',default=True)
    # 文件夹内媒体数量
    media_count = models.BigIntegerField(
        '文件夹内媒体数量', default=0)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '媒体文件夹模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("media_folders")



class SystemSettingsMixin(models.Model):
    """系统设置模型 Mixin"""

    # 设置 ID
    id = models.BigAutoField(
        '设置 ID'        , primary_key=True)
    # 设置键
    setting_key = models.CharField(
        '设置键', max_length=100)
    # 设置值
    setting_value = models.CharField(
        '设置值', max_length=255)
    # 设置类型
    setting_type = models.CharField(
        '设置类型', max_length=255, default='string')
    # 描述
    description = models.CharField(
        '描述', max_length=255, blank=True, null=True)
    # 是否公开
    is_public = models.BooleanField(
        '是否公开',default=False)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '系统设置模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("system_settings")



class AdminSettingsMixin(models.Model):
    """管理员设置模型 Mixin"""

    # 设置 ID
    id = models.BigAutoField(
        '设置 ID'        , primary_key=True)
    # 用户
    user = models.IntegerField(
        '用户 (暂为 IntegerField，等待 User 模型实现)',)
    # 设置数据
    settings_data = models.TextField(
        '设置数据')

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '管理员设置模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("adminsettings")



class ArticleContentMixin(models.Model):
    """文章内容模型 Mixin"""

    # ID
    id = models.BigAutoField(
        'ID'        , primary_key=True)
    # 文章
    article = models.IntegerField(
        '文章 (暂为 IntegerField，等待 Article 模型实现)',)
    # 访问密码
    passwd = models.CharField(
        '访问密码', max_length=255, blank=True, null=True)
    # 文章内容
    content = models.TextField(
        '文章内容')
    # 语言代码
    language_code = models.CharField(
        '语言代码', max_length=255, default='zh-CN')

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '文章内容模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("article_content")



class ArticleI18nMixin(models.Model):
    """文章国际化模型 Mixin"""

    # 国际化 ID
    i18n_id = models.BigIntegerField(
        '国际化 ID')
    # 文章
    article = models.IntegerField(
        '文章 (暂为 IntegerField，等待 Article 模型实现)',)
    # 语言 ID
    language_id = models.CharField(
        '语言 ID', max_length=10)
    # 标题
    title = models.CharField(
        '标题', max_length=255)
    # 文章 slug
    slug = models.CharField(
        '文章 slug', max_length=255)
    # 文章内容
    content = models.TextField(
        '文章内容')
    # 摘要
    excerpt = models.CharField(
        '摘要', max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '文章国际化模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("article_i18n")



class ArticleLikeMixin(models.Model):
    """文章点赞模型 Mixin"""

    # 点赞 ID
    id = models.BigAutoField(
        '点赞 ID'        , primary_key=True)
    # 用户
    user = models.IntegerField(
        '用户 (暂为 IntegerField，等待 User 模型实现)',)
    # 文章
    article = models.IntegerField(
        '文章 (暂为 IntegerField，等待 Article 模型实现)',)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '文章点赞模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("article_likes")



class FileHashMixin(models.Model):
    """文件哈希模型 Mixin"""

    # 哈希 ID
    id = models.BigAutoField(
        '哈希 ID'        , primary_key=True)
    # 文件哈希
    hash = models.CharField(
        '文件哈希', max_length=64)
    # 文件名
    filename = models.CharField(
        '文件名', max_length=255)
    # 引用计数
    reference_count = models.BigIntegerField(
        '引用计数', default=1)
    # 文件大小
    file_size = models.BigIntegerField(
        '文件大小')
    # MIME 类型
    mime_type = models.CharField(
        'MIME 类型', max_length=100)
    # 存储路径
    storage_path = models.CharField(
        '存储路径', max_length=512)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '文件哈希模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("file_hashs")



class MenusMixin(models.Model):
    """菜单模型 Mixin"""

    # 菜单 ID
    id = models.BigAutoField(
        '菜单 ID'        , primary_key=True)
    # 菜单名
    name = models.CharField(
        '菜单名', max_length=100)
    # 菜单 slug
    slug = models.CharField(
        '菜单 slug', max_length=100)
    # 菜单描述
    description = models.CharField(
        '菜单描述', max_length=255, blank=True, null=True)
    # 是否激活
    is_active = models.BooleanField(
        '是否激活',default=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '菜单模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("menus")



class MenuItemsMixin(models.Model):
    """菜单项模型 Mixin"""

    # 菜单项 ID
    id = models.BigAutoField(
        '菜单项 ID'        , primary_key=True)
    # 菜单 ID
    menu_id = models.IntegerField(
        '菜单 ID')
    # 父菜单项 ID
    parent_id = models.IntegerField(
        '父菜单项 ID', blank=True, null=True)
    # 标题
    title = models.CharField(
        '标题', max_length=255)
    # URL
    url = models.CharField(
        'URL', max_length=500)
    # 打开方式
    target = models.CharField(
        '打开方式', max_length=255, default='_self')
    # 排序索引
    order_index = models.IntegerField(
        '排序索引', default=0)
    # 是否激活
    is_active = models.BooleanField(
        '是否激活',default=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '菜单项模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("menu_items")



class MenuLocationMixin(models.Model):
    """菜单位置模型（主菜单、页脚菜单等） Mixin"""

    # 位置 ID
    id = models.BigAutoField(
        '位置 ID'        , primary_key=True)
    # 位置显示名称
    name = models.CharField(
        '位置显示名称', max_length=100)
    # 位置标识(primary-menu, footer-menu等)
    slug = models.CharField(
        '位置标识(primary-menu, footer-menu等)', max_length=100, unique=True)
    # 位置描述
    description = models.CharField(
        '位置描述', max_length=255, blank=True, null=True)
    # 支持的主题列表(JSON格式)
    theme_supports = models.CharField(
        '支持的主题列表(JSON格式)', max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '菜单位置模型（主菜单、页脚菜单等）'
        # 注意：请在具体模型类中设置 db_table = get_table_name("menu_locations")



class MenuLocationAssignmentMixin(models.Model):
    """菜单-位置关联表 Mixin"""

    # 关联 ID
    id = models.BigAutoField(
        '关联 ID'        , primary_key=True)
    # 菜单 ID
    menu_id = models.IntegerField(
        '菜单 ID (暂为 IntegerField，等待 Menus 模型实现)',)
    # 位置 ID
    location_id = models.IntegerField(
        '位置 ID (暂为 IntegerField，等待 MenuLocation 模型实现)',)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '菜单-位置关联表'
        # 注意：请在具体模型类中设置 db_table = get_table_name("menu_location_assignments")



class PagesMixin(models.Model):
    """页面模型 Mixin"""

    # 页面 ID
    id = models.BigAutoField(
        '页面 ID'        , primary_key=True)
    # 标题
    title = models.CharField(
        '标题', max_length=255)
    # 页面 slug
    slug = models.CharField(
        '页面 slug', max_length=255)
    # 页面内容
    content = models.CharField(
        '页面内容', max_length=255)
    # 摘要
    excerpt = models.CharField(
        '摘要', max_length=255, blank=True, null=True)
    # 模板
    template = models.CharField(
        '模板', max_length=255, blank=True, null=True)
    # 状态
    status = models.BigIntegerField(
        '状态', default=0)
    # 作者 ID
    author_id = models.BigIntegerField(
        '作者 ID', blank=True, null=True)
    # 父页面 ID
    parent_id = models.BigIntegerField(
        '父页面 ID', blank=True, null=True)
    # 排序索引
    order_index = models.IntegerField(
        '排序索引', default=0)
    # 元标题
    meta_title = models.CharField(
        '元标题', max_length=255, blank=True, null=True)
    # 元描述
    meta_description = models.CharField(
        '元描述', max_length=255, blank=True, null=True)
    # 元关键词
    meta_keywords = models.CharField(
        '元关键词', max_length=255, blank=True, null=True)
    # 发布时间
    published_at = models.DateTimeField(
        '发布时间', blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '页面模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("pages")



class UploadTaskMixin(models.Model):
    """上传任务模型 Mixin"""

    # 任务 ID (UUID)
    id = models.CharField(
        '任务 ID (UUID)', max_length=36)
    # 用户 ID
    user_id = models.BigIntegerField(
        '用户 ID')
    # 文件名
    filename = models.CharField(
        '文件名', max_length=255)
    # 文件总大小
    total_size = models.BigIntegerField(
        '文件总大小')
    # 总分块数
    total_chunks = models.BigIntegerField(
        '总分块数')
    # 已上传分块数
    uploaded_chunks = models.BigIntegerField(
        '已上传分块数', default=0)
    # 文件哈希
    file_hash = models.CharField(
        '文件哈希', max_length=64, blank=True, null=True)
    # 状态
    status = models.CharField(
        '状态', max_length=255, default='initialized')

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '上传任务模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("upload_tasks")



class UploadChunkMixin(models.Model):
    """上传分块模型 Mixin"""

    # 分块 ID
    id = models.BigAutoField(
        '分块 ID'        , primary_key=True)
    # 上传任务 ID
    upload_id = models.CharField(
        '上传任务 ID', max_length=36)
    # 分块索引
    chunk_index = models.BigIntegerField(
        '分块索引')
    # 分块哈希
    chunk_hash = models.CharField(
        '分块哈希', max_length=64)
    # 分块大小
    chunk_size = models.BigIntegerField(
        '分块大小')
    # 分块路径
    chunk_path = models.CharField(
        '分块路径', max_length=500)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '上传分块模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("upload_chunks")


class DownloadTaskMixin(models.Model):
    """外部资源下载任务模型 Mixin"""

    # 任务ID
    id = models.BigAutoField(
        '任务ID', primary_key=True)
    # 用户ID
    user_id = models.IntegerField(
        '用户ID (暂为 IntegerField，等待 User 模型实现)', )
    # 源URL地址
    source_url = models.CharField(
        '源URL地址', max_length=2048)
    # 资源类型
    resource_type = models.CharField(
        '资源类型', max_length=50, default='image')
    # 文件名
    filename = models.CharField(
        '文件名', max_length=255, blank=True, null=True)
    # 文件总大小(字节)
    total_size = models.BigIntegerField(
        '文件总大小(字节)', blank=True, null=True)
    # 已下载大小(字节)
    downloaded_size = models.BigIntegerField(
        '已下载大小(字节)', default=0)
    # 下载进度(0-100)
    progress = models.IntegerField(
        '下载进度(0-100)', default=0)
    # 任务状态
    status = models.CharField(
        '任务状态', max_length=50, default='pending')
    # 错误信息
    error_message = models.TextField(
        '错误信息', blank=True, null=True)
    # 关联的媒体ID
    media_id = models.IntegerField(
        '关联的媒体ID (暂为 IntegerField，等待 Media 模型实现)', null=True, blank=True)
    # 重试次数
    retry_count = models.BigIntegerField(
        '重试次数', default=0)
    # 最大重试次数
    max_retries = models.BigIntegerField(
        '最大重试次数', default=3)
    # 优先级(数字越小优先级越高)
    priority = models.BigIntegerField(
        '优先级(数字越小优先级越高)', default=0)
    # 开始下载时间
    started_at = models.DateTimeField(
        '开始下载时间', blank=True, null=True)
    # 完成时间
    completed_at = models.DateTimeField(
        '完成时间', blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '外部资源下载任务模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("download_tasks")



class NotificationMixin(models.Model):
    """通知模型 Mixin"""

    # 通知 ID
    id = models.BigAutoField(
        '通知 ID'        , primary_key=True)
    # 接收者
    recipient = models.IntegerField(
        '接收者 (暂为 IntegerField，等待 User 模型实现)',)
    # 通知类型
    type = models.CharField(
        '通知类型', max_length=100)
    # 标题
    title = models.CharField(
        '标题', max_length=200)
    # 消息内容
    message = models.CharField(
        '消息内容', max_length=255)
    # 是否已读
    is_read = models.BooleanField(
        '是否已读',default=False)
    # 阅读时间
    read_at = models.DateTimeField(
        '阅读时间', blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '通知模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("notifications")



class PrivateMessageMixin(models.Model):
    """站内私信模型 Mixin"""

    # 消息ID
    id = models.BigAutoField(
        '消息ID'        , primary_key=True)
    # 发送者
    sender = models.IntegerField(
        '发送者 (暂为 IntegerField，等待 User 模型实现)',)
    # 接收者
    recipient = models.IntegerField(
        '接收者 (暂为 IntegerField，等待 User 模型实现)',)
    # 消息内容
    content = models.TextField(
        '消息内容')
    # 消息类型
    message_type = models.CharField(
        '消息类型', max_length=50, default='text')
    # 附件URL(图片/文件)
    attachment_url = models.CharField(
        '附件URL(图片/文件)', max_length=500, blank=True, null=True)
    # 是否已读
    is_read = models.BooleanField(
        '是否已读',default=False)
    # 阅读时间
    read_at = models.DateTimeField(
        '阅读时间', blank=True, null=True)
    # 发送者是否删除
    is_deleted_by_sender = models.BooleanField(
        '发送者是否删除',default=False)
    # 接收者是否删除
    is_deleted_by_recipient = models.BooleanField(
        '接收者是否删除',default=False)
    # 父消息ID(用于回复)
    parent_message = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        verbose_name='父消息ID(用于回复)',null=True, blank=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '站内私信模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("private_messages")



class UserBlockMixin(models.Model):
    """用户屏蔽/拉黑模型 Mixin"""

    # 屏蔽记录ID
    id = models.BigAutoField(
        '屏蔽记录ID'        , primary_key=True)
    # 屏蔽者用户ID
    blocker = models.IntegerField(
        '屏蔽者用户ID (暂为 IntegerField，等待 User 模型实现)',)
    # 被屏蔽用户ID
    blocked_user = models.IntegerField(
        '被屏蔽用户ID (暂为 IntegerField，等待 User 模型实现)',)
    # 屏蔽原因
    reason = models.CharField(
        '屏蔽原因', max_length=500, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '用户屏蔽/拉黑模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("user_blocks")



class SearchHistoryMixin(models.Model):
    """搜索历史模型 Mixin"""

    # 搜索历史 ID
    id = models.BigAutoField(
        '搜索历史 ID'        , primary_key=True)
    # 用户
    user = models.IntegerField(
        '用户 (暂为 IntegerField，等待 User 模型实现)',)
    # 搜索关键词
    keyword = models.CharField(
        '搜索关键词', max_length=255)
    # 结果数量
    results_count = models.BigIntegerField(
        '结果数量')

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '搜索历史模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("search_history")


class SearchIndexMixin(models.Model):
    """搜索索引状态模型 Mixin"""

    # 索引记录ID
    id = models.BigAutoField(
        '索引记录ID', primary_key=True)
    # 文章ID
    article_id = models.IntegerField(
        '文章ID (暂为 IntegerField，等待 Article 模型实现)', )
    # 是否已索引
    indexed = models.BooleanField(
        '是否已索引', default=False)
    # 最后索引时间
    last_indexed_at = models.DateTimeField(
        '最后索引时间', blank=True, null=True)
    # 索引内容哈希(用于检测变更)
    index_hash = models.CharField(
        '索引内容哈希(用于检测变更)', max_length=64, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '搜索索引状态模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("search_index")



class PageViewMixin(models.Model):
    """页面浏览模型 Mixin"""

    # 浏览 ID
    id = models.BigAutoField(
        '浏览 ID'        , primary_key=True)
    # 用户
    user = models.IntegerField(
        '用户 (暂为 IntegerField，等待 User 模型实现)',null=True, blank=True)
    # 会话 ID
    session_id = models.CharField(
        '会话 ID', max_length=255, blank=True, null=True)
    # 页面 URL
    page_url = models.CharField(
        '页面 URL', max_length=500)
    # 页面标题
    page_title = models.CharField(
        '页面标题', max_length=500, blank=True, null=True)
    # 来源页面
    referrer = models.CharField(
        '来源页面', max_length=500, blank=True, null=True)
    # 用户代理
    user_agent = models.CharField(
        '用户代理', max_length=500, blank=True, null=True)
    # IP 地址
    ip_address = models.CharField(
        'IP 地址', max_length=45, blank=True, null=True)
    # 设备类型
    device_type = models.CharField(
        '设备类型', max_length=50, blank=True, null=True)
    # 浏览器类型
    browser = models.CharField(
        '浏览器类型', max_length=100, blank=True, null=True)
    # 操作系统平台
    platform = models.CharField(
        '操作系统平台', max_length=100, blank=True, null=True)
    # 国家
    country = models.CharField(
        '国家', max_length=100, blank=True, null=True)
    # 城市
    city = models.CharField(
        '城市', max_length=100, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '页面浏览模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("page_views")



class UserActivityMixin(models.Model):
    """用户活动模型 Mixin"""

    # 活动 ID
    id = models.BigAutoField(
        '活动 ID'        , primary_key=True)
    # 用户
    user = models.IntegerField(
        '用户 (暂为 IntegerField，等待 User 模型实现)',)
    # 活动类型
    activity_type = models.CharField(
        '活动类型', max_length=100)
    # 目标类型
    target_type = models.CharField(
        '目标类型', max_length=50)
    # 目标 ID
    target_id = models.BigIntegerField(
        '目标 ID')
    # 活动详情
    details = models.CharField(
        '活动详情', max_length=255, blank=True, null=True)
    # IP 地址
    ip_address = models.CharField(
        'IP 地址', max_length=45, blank=True, null=True)
    # 用户代理
    user_agent = models.CharField(
        '用户代理', max_length=500, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '用户活动模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("user_activities")



class VIPPlanMixin(models.Model):
    """VIP 套餐模型 Mixin"""

    # 套餐 ID
    id = models.BigAutoField(
        '套餐 ID'        , primary_key=True)
    # 套餐名称
    name = models.CharField(
        '套餐名称', max_length=100)
    # 套餐描述
    description = models.CharField(
        '套餐描述', max_length=255, blank=True, null=True)
    # 价格
    price = models.DecimalField(
        '价格', max_digits=10, decimal_places=2)
    # 原价
    original_price = models.DecimalField(
        '原价', max_digits=10, decimal_places=2, blank=True, null=True)
    # 有效期天数
    duration_days = models.IntegerField(
        '有效期天数')
    # VIP 等级
    level = models.BigIntegerField(
        'VIP 等级', default=1)
    # 特权功能 JSON
    features = models.CharField(
        '特权功能 JSON', max_length=255, blank=True, null=True)
    # 是否激活
    is_active = models.BooleanField(
        '是否激活',default=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = 'VIP 套餐模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("vip_plans")



class VIPSubscriptionMixin(models.Model):
    """VIP 订阅模型 Mixin"""

    # 订阅 ID
    id = models.BigAutoField(
        '订阅 ID'        , primary_key=True)
    # 用户
    user = models.IntegerField(
        '用户 (暂为 IntegerField，等待 User 模型实现)',)
    # 套餐
    plan = models.IntegerField(
        '套餐 (暂为 IntegerField，等待 VIPPlan 模型实现)',)
    # 开始时间
    starts_at = models.DateTimeField(
        '开始时间')
    # 过期时间
    expires_at = models.DateTimeField(
        '过期时间')
    # 状态
    status = models.BigIntegerField(
        '状态', default=0)
    # 实际支付金额
    payment_amount = models.DecimalField(
        '实际支付金额', max_digits=10, decimal_places=2, blank=True, null=True)
    # 支付交易 ID
    transaction_id = models.CharField(
        '支付交易 ID', max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = 'VIP 订阅模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("vip_subscriptions")



class VIPFeatureMixin(models.Model):
    """VIP 功能特权模型 Mixin"""

    # 功能 ID
    id = models.BigAutoField(
        '功能 ID'        , primary_key=True)
    # 功能代码
    code = models.CharField(
        '功能代码', max_length=50)
    # 功能名称
    name = models.CharField(
        '功能名称', max_length=100)
    # 功能描述
    description = models.CharField(
        '功能描述', max_length=255, blank=True, null=True)
    # 所需 VIP 等级
    required_level = models.IntegerField(
        '所需 VIP 等级', default=1)
    # 是否激活
    is_active = models.BooleanField(
        '是否激活',default=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = 'VIP 功能特权模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("vip_features")



class CustomFieldMixin(models.Model):
    """自定义字段模型 Mixin"""

    # 字段 ID
    id = models.BigAutoField(
        '字段 ID'        , primary_key=True)
    # 用户
    user = models.IntegerField(
        '用户 (暂为 IntegerField，等待 User 模型实现)',)
    # 字段名称
    field_name = models.CharField(
        '字段名称', max_length=100)
    # 字段值
    field_value = models.CharField(
        '字段值', max_length=255)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '自定义字段模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("custom_fields")



class EmailSubscriptionMixin(models.Model):
    """邮件订阅模型 Mixin"""

    # 订阅 ID
    id = models.BigAutoField(
        '订阅 ID'        , primary_key=True)
    # 用户
    user = models.IntegerField(
        '用户 (暂为 IntegerField，等待 User 模型实现)',)
    # 是否订阅邮件
    subscribed = models.BooleanField(
        '是否订阅邮件',default=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '邮件订阅模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("email_subscriptions")



class ArticleRevisionMixin(models.Model):
    """文章修订历史模型 Mixin"""

    # 修订ID
    id = models.BigAutoField(
        '修订ID'        , primary_key=True)
    # 关联的文章ID
    article_id = models.IntegerField(
        '关联的文章ID (暂为 IntegerField，等待 Article 模型实现)',)
    # 修订版本号
    revision_number = models.BigIntegerField(
        '修订版本号')
    # 修订时的标题
    title = models.CharField(
        '修订时的标题', max_length=255)
    # 修订时的摘要
    excerpt = models.CharField(
        '修订时的摘要', max_length=255, blank=True, null=True)
    # 修订时的文章内容
    content = models.TextField(
        '修订时的文章内容')
    # 修订时的封面图
    cover_image = models.CharField(
        '修订时的封面图', max_length=255, blank=True, null=True)
    # 修订时的标签
    tags_list = models.CharField(
        '修订时的标签', max_length=255, blank=True, null=True)
    # 修订时的分类ID
    category_id = models.BigIntegerField(
        '修订时的分类ID', blank=True, null=True)
    # 修订时的文章状态
    status = models.BigIntegerField(
        '修订时的文章状态', default=0)
    # 修订时的隐藏状态
    hidden = models.BooleanField(
        '修订时的隐藏状态',default=False)
    # 修订时的精选状态
    is_featured = models.BooleanField(
        '修订时的精选状态',default=False)
    # 修订时的VIP限制
    is_vip_only = models.BooleanField(
        '修订时的VIP限制',default=False)
    # 修订时的VIP等级要求
    required_vip_level = models.BigIntegerField(
        '修订时的VIP等级要求', default=0)
    # 执行修订的用户ID
    author_id = models.IntegerField(
        '执行修订的用户ID (暂为 IntegerField，等待 User 模型实现)',null=True, blank=True)
    # 修订说明/变更摘要
    change_summary = models.CharField(
        '修订说明/变更摘要', max_length=500, blank=True, null=True)
    # 内容哈希码(用于去重)
    hash_code = models.CharField(
        '内容哈希码(用于去重)', max_length=64, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '文章修订历史模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("article_revisions")



class PluginMixin(models.Model):
    """插件模型 Mixin"""

    # 插件ID
    id = models.BigAutoField(
        '插件ID'        , primary_key=True)
    # 插件名称
    name = models.CharField(
        '插件名称', max_length=100)
    # 插件唯一标识
    slug = models.CharField(
        '插件唯一标识', max_length=100, unique=True)
    # 插件版本
    version = models.CharField(
        '插件版本', max_length=20)
    # 插件描述
    description = models.CharField(
        '插件描述', max_length=255, blank=True, null=True)
    # 插件作者
    author = models.CharField(
        '插件作者', max_length=100, blank=True, null=True)
    # 作者网站
    author_url = models.CharField(
        '作者网站', max_length=255, blank=True, null=True)
    # 插件官网
    plugin_url = models.CharField(
        '插件官网', max_length=255, blank=True, null=True)
    # 是否激活
    is_active = models.BooleanField(
        '是否激活',default=False)
    # 是否已安装
    is_installed = models.BooleanField(
        '是否已安装',default=True)
    # 插件配置(JSON格式)
    settings = models.TextField(
        '插件配置(JSON格式)', blank=True, null=True)
    # 执行优先级
    priority = models.IntegerField(
        '执行优先级', default=0)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '插件模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("plugins")



class ThemeMixin(models.Model):
    """主题模型 Mixin"""

    # 主题ID
    id = models.BigAutoField(
        '主题ID'        , primary_key=True)
    # 主题名称
    name = models.CharField(
        '主题名称', max_length=100)
    # 主题唯一标识
    slug = models.CharField(
        '主题唯一标识', max_length=100, unique=True)
    # 主题版本
    version = models.CharField(
        '主题版本', max_length=20)
    # 主题描述
    description = models.CharField(
        '主题描述', max_length=255, blank=True, null=True)
    # 主题作者
    author = models.CharField(
        '主题作者', max_length=100, blank=True, null=True)
    # 作者网站
    author_url = models.CharField(
        '作者网站', max_length=255, blank=True, null=True)
    # 主题官网
    theme_url = models.CharField(
        '主题官网', max_length=255, blank=True, null=True)
    # 主题截图路径
    screenshot = models.CharField(
        '主题截图路径', max_length=500, blank=True, null=True)
    # 标签列表(JSON格式)
    tags = models.CharField(
        '标签列表(JSON格式)', max_length=255, blank=True, null=True)
    # 依赖要求(JSON格式)
    requires = models.CharField(
        '依赖要求(JSON格式)', max_length=255, blank=True, null=True)
    # 设置架构(JSON格式)
    settings_schema = models.CharField(
        '设置架构(JSON格式)', max_length=255, blank=True, null=True)
    # 主题文件路径
    theme_path = models.CharField(
        '主题文件路径', max_length=500, blank=True, null=True)
    # 是否为当前激活主题
    is_active = models.BooleanField(
        '是否为当前激活主题',default=False)
    # 是否已安装
    is_installed = models.BooleanField(
        '是否已安装',default=True)
    # 主题配置(JSON格式)
    settings = models.CharField(
        '主题配置(JSON格式)', max_length=255, blank=True, null=True)
    # 支持的功能(JSON数组)
    supports = models.CharField(
        '支持的功能(JSON数组)', max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '主题模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("themes")



class FormMixin(models.Model):
    """表单模型 Mixin"""

    # 表单 ID
    id = models.BigAutoField(
        '表单 ID'        , primary_key=True)
    # 表单标题
    title = models.CharField(
        '表单标题', max_length=255)
    # 表单标识
    slug = models.CharField(
        '表单标识', max_length=255, unique=True)
    # 表单描述
    description = models.CharField(
        '表单描述', max_length=255, blank=True, null=True)
    # 表单状态(draft, published, archived)
    status = models.CharField(
        '表单状态(draft, published, archived)', max_length=255, default='draft')
    # 提交成功消息
    submit_message = models.CharField(
        '提交成功消息', max_length=255, blank=True, null=True)
    # 是否启用邮件通知
    email_notification = models.BooleanField(
        '是否启用邮件通知',default=False)
    # 通知邮箱地址
    notification_email = models.CharField(
        '通知邮箱地址', max_length=255, blank=True, null=True)
    # 是否存储提交数据
    store_submissions = models.BooleanField(
        '是否存储提交数据',default=True)
    # 发布时间
    published_at = models.DateTimeField(
        '发布时间', blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '表单模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("forms")



class FormFieldMixin(models.Model):
    """表单字段模型 Mixin"""

    # 字段 ID
    id = models.BigAutoField(
        '字段 ID'        , primary_key=True)
    # 所属表单 ID
    form_id = models.IntegerField(
        '所属表单 ID (暂为 IntegerField，等待 Form 模型实现)',)
    # 字段标签
    label = models.CharField(
        '字段标签', max_length=255)
    # 字段类型(text, email, textarea, select, checkbox, radio, number, date, file)
    field_type = models.CharField(
        '字段类型(text, email, textarea, select, checkbox, radio, number, date, file)', max_length=50)
    # 占位符文本
    placeholder = models.CharField(
        '占位符文本', max_length=255, blank=True, null=True)
    # 帮助文本
    help_text = models.CharField(
        '帮助文本', max_length=255, blank=True, null=True)
    # 是否必填
    required = models.BooleanField(
        '是否必填',default=False)
    # 选项列表(JSON格式，用于select/radio/checkbox)
    options = models.CharField(
        '选项列表(JSON格式,用于select/radio/checkbox)', max_length=255, blank=True, null=True)
    # 验证规则(JSON格式)
    validation_rules = models.CharField(
        '验证规则(JSON格式)', max_length=255, blank=True, null=True)
    # 默认值
    default_value = models.CharField(
        '默认值', max_length=255, blank=True, null=True)
    # 显示顺序
    order_index = models.BigIntegerField(
        '显示顺序', default=0)
    # 是否启用
    is_active = models.BooleanField(
        '是否启用',default=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '表单字段模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("form_fields")



class FormSubmissionMixin(models.Model):
    """表单提交记录模型 Mixin"""

    # 提交 ID
    id = models.BigAutoField(
        '提交 ID'        , primary_key=True)
    # 所属表单 ID
    form_id = models.IntegerField(
        '所属表单 ID (暂为 IntegerField，等待 Form 模型实现)',)
    # 提交数据(JSON格式)
    data = models.CharField(
        '提交数据(JSON格式)', max_length=255)
    # 提交者 IP
    ip_address = models.CharField(
        '提交者 IP', max_length=45, blank=True, null=True)
    # 浏览器信息
    user_agent = models.CharField(
        '浏览器信息', max_length=255, blank=True, null=True)
    # 用户 ID(如果已登录)
    user_id = models.IntegerField(
        '用户 ID(如果已登录) (暂为 IntegerField，等待 User 模型实现)',null=True, blank=True)
    # 提交状态(new, read, replied, spam)
    status = models.CharField(
        '提交状态(new, read, replied, spam)', max_length=255, default='new')

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '表单提交记录模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("form_submissions")



class WidgetInstanceMixin(models.Model):
    """Widget实例模型（持久化存储） Mixin"""

    # Widget实例 ID
    id = models.BigAutoField(
        'Widget实例 ID'        , primary_key=True)
    # Widget类型(search, recent_posts, categories等)
    widget_type = models.CharField(
        'Widget类型(search, recent_posts, categories等)', max_length=50)
    # 显示区域(sidebar_primary, footer_1等)
    area = models.CharField(
        '显示区域(sidebar_primary, footer_1等)', max_length=50)
    # Widget标题
    title = models.CharField(
        'Widget标题', max_length=255, blank=True, null=True)
    # Widget配置(JSON格式)
    config = models.CharField(
        'Widget配置(JSON格式)', max_length=255)
    # 显示顺序
    order_index = models.BigIntegerField(
        '显示顺序', default=0)
    # 是否启用
    is_active = models.BooleanField(
        '是否启用',default=True)
    # 显示条件(JSON格式)
    conditions = models.CharField(
        '显示条件(JSON格式)', max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = 'Widget实例模型（持久化存储）'
        # 注意：请在具体模型类中设置 db_table = get_table_name("widget_instances")



class BlockPatternMixin(models.Model):
    """自定义块模式模型 Mixin"""

    # 模式ID
    id = models.BigAutoField(
        '模式ID'        , primary_key=True)
    # 模式名称(唯一标识)
    name = models.CharField(
        '模式名称(唯一标识)', max_length=100, unique=True)
    # 模式标题(显示名称)
    title = models.CharField(
        '模式标题(显示名称)', max_length=255)
    # 模式描述
    description = models.TextField(
        '模式描述', blank=True, null=True)
    # 分类(custom, hero, features等)
    category = models.CharField(
        '分类(custom, hero, features等)', max_length=50, default='custom')
    # 块数据(JSON格式)
    blocks = models.TextField(
        '块数据(JSON格式)')
    # 关键词(逗号分隔)
    keywords = models.TextField(
        '关键词(逗号分隔)', blank=True, null=True)
    # 缩略图URL
    thumbnail = models.CharField(
        '缩略图URL', max_length=500, blank=True, null=True)
    # 是否公开(false=私有，true=公开)
    is_public = models.BooleanField(
        '是否公开(false=私有,true=公开)',default=False)
    # 创建者用户ID
    user_id = models.IntegerField(
        '创建者用户ID (暂为 IntegerField，等待 User 模型实现)',null=True, blank=True)
    # 预览宽度
    viewport_width = models.BigIntegerField(
        '预览宽度', default=800)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '自定义块模式模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("block_patterns")



class CustomPostTypeMixin(models.Model):
    """自定义内容类型模型 Mixin"""

    # 内容类型ID
    id = models.BigAutoField(
        '内容类型ID'        , primary_key=True)
    # 内容类型名称
    name = models.CharField(
        '内容类型名称', max_length=100)
    # 内容类型标识
    slug = models.CharField(
        '内容类型标识', max_length=100, unique=True)
    # 描述
    description = models.CharField(
        '描述', max_length=255, blank=True, null=True)
    # 支持的功能(JSON数组)
    supports = models.CharField(
        '支持的功能(JSON数组)', max_length=255, blank=True, null=True)
    # 是否有归档页
    has_archive = models.BooleanField(
        '是否有归档页',default=False)
    # 菜单图标
    menu_icon = models.CharField(
        '菜单图标', max_length=255, blank=True, null=True)
    # 菜单位置
    menu_position = models.IntegerField(
        '菜单位置', default=5)
    # 是否激活
    is_active = models.BooleanField(
        '是否激活',default=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '自定义内容类型模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("custom_post_types")



class CommentVoteMixin(models.Model):
    """评论投票模型 Mixin"""

    # 投票 ID
    id = models.BigAutoField(
        '投票 ID'        , primary_key=True)
    # 评论 ID
    comment_id = models.BigIntegerField(
        '评论 ID')
    # 用户 ID(匿名投票可为空)
    user = models.IntegerField(
        '用户 ID(匿名投票可为空) (暂为 IntegerField，等待 User 模型实现)',null=True, blank=True)
    # 投票类型 (1: 赞, -1: 踩)
    vote_type = models.IntegerField(
        '投票类型 (1: 赞, -1: 踩)')
    # IP 地址(用于防刷)
    ip_address = models.CharField(
        'IP 地址(用于防刷)', max_length=45, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '评论投票模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("comment_votes")



class CommentSubscriptionMixin(models.Model):
    """评论订阅模型 Mixin"""

    # 订阅 ID
    id = models.BigAutoField(
        '订阅 ID'        , primary_key=True)
    # 文章 ID
    article_id = models.BigIntegerField(
        '文章 ID')
    # 用户 ID(访客订阅可为空)
    user_id = models.IntegerField(
        '用户 ID(访客订阅可为空) (暂为 IntegerField，等待 User 模型实现)',null=True, blank=True)
    # 订阅邮箱
    email = models.CharField(
        '订阅邮箱', max_length=255)
    # 通知类型 (new_comment: 新评论, reply_to_me: 回复我, all_replies: 所有回复)
    notify_type = models.CharField(
        '通知类型 (new_comment: 新评论, reply_to_me: 回复我, all_replies: 所有回复)', max_length=255, default='new_comment')
    # 是否激活
    is_active = models.BooleanField(
        '是否激活',default=True)
    # 确认token(用于访客验证)
    confirm_token = models.CharField(
        '确认token(用于访客验证)', max_length=64, blank=True, null=True)
    # 确认时间
    confirmed_at = models.DateTimeField(
        '确认时间', blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '评论订阅模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("comment_subscriptions")



class CommentMixin(models.Model):
    """评论模型 Mixin"""

    # 评论 ID
    id = models.BigAutoField(
        '评论 ID'        , primary_key=True)
    # 文章 ID
    article_id = models.IntegerField(
        '文章 ID (暂为 IntegerField，等待 Article 模型实现)',)
    # 用户 ID(访客评论可为空)
    user_id = models.IntegerField(
        '用户 ID(访客评论可为空) (暂为 IntegerField，等待 User 模型实现)',null=True, blank=True)
    # 父评论 ID(用于回复)
    parent_id = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        verbose_name='父评论 ID(用于回复)',null=True, blank=True)
    # 评论内容
    content = models.TextField(
        '评论内容')
    # 作者姓名(访客填写)
    author_name = models.CharField(
        '作者姓名(访客填写)', max_length=100, blank=True, null=True)
    # 作者邮箱(访客填写)
    author_email = models.CharField(
        '作者邮箱(访客填写)', max_length=255, blank=True, null=True)
    # 作者网站(访客填写)
    author_url = models.CharField(
        '作者网站(访客填写)', max_length=500, blank=True, null=True)
    # 作者 IP 地址
    author_ip = models.CharField(
        '作者 IP 地址', max_length=45, blank=True, null=True)
    # 用户代理
    user_agent = models.CharField(
        '用户代理', max_length=500, blank=True, null=True)
    # 是否已审核通过
    is_approved = models.BooleanField(
        '是否已审核通过',default=True)
    # 点赞数
    likes = models.BigIntegerField(
        '点赞数', default=0)
    # 垃圾评分
    spam_score = models.DecimalField(
        '垃圾评分', max_digits=10, decimal_places=2, blank=True, null=True)
    # 垃圾检测原因(JSON格式)
    spam_reasons = models.CharField(
        '垃圾检测原因(JSON格式)', max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '评论模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("comments")



class RoleMixin(models.Model):
    """角色模型 Mixin"""

    # 角色 ID
    id = models.BigAutoField(
        '角色 ID'        , primary_key=True)
    # 角色名称
    name = models.CharField(
        '角色名称', max_length=100)
    # 角色标识(唯一)
    slug = models.CharField(
        '角色标识(唯一)', max_length=100, unique=True)
    # 角色描述
    description = models.CharField(
        '角色描述', max_length=255, blank=True, null=True)
    # 权限列表(JSON格式)
    permissions = models.CharField(
        '权限列表(JSON格式)', max_length=255, blank=True, null=True)
    # 是否为系统角色(系统角色不可删除)
    is_system = models.BooleanField(
        '是否为系统角色(系统角色不可删除)',default=False)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '角色模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("roles")



class CapabilityMixin(models.Model):
    """权限能力模型 Mixin"""

    # 权限 ID
    id = models.BigAutoField(
        '权限 ID'        , primary_key=True)
    # 权限代码(唯一标识)
    code = models.CharField(
        '权限代码(唯一标识)', max_length=100, unique=True)
    # 权限名称
    name = models.CharField(
        '权限名称', max_length=255)
    # 权限描述
    description = models.CharField(
        '权限描述', max_length=255, blank=True, null=True)
    # 资源类型(article, user, category等)
    resource_type = models.CharField(
        '资源类型(article, user, category等)', max_length=100, blank=True, null=True)
    # 操作类型(create, read, update, delete)
    action = models.CharField(
        '操作类型(create, read, update, delete)', max_length=50, blank=True, null=True)
    # 是否激活
    is_active = models.BooleanField(
        '是否激活',default=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '权限能力模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("capabilities")



class UserRoleMixin(models.Model):
    """用户角色关联模型 Mixin"""

    # 关联 ID
    id = models.BigAutoField(
        '关联 ID'        , primary_key=True)
    # 用户 ID
    user_id = models.IntegerField(
        '用户 ID (暂为 IntegerField，等待 User 模型实现)',)
    # 角色 ID
    role_id = models.IntegerField(
        '角色 ID (暂为 IntegerField，等待 Role 模型实现)',)
    # 分配者用户 ID
    assigned_by = models.IntegerField(
        '分配者用户 ID (暂为 IntegerField，等待 User 模型实现)',null=True, blank=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '用户角色关联模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("user_role_assignments")



class OAuthAccountMixin(models.Model):
    """OAuth 第三方登录账号关联模型 Mixin"""

    # 主键ID
    id = models.BigAutoField(
        '主键ID'        , primary_key=True)
    # 关联的用户ID
    user_id = models.IntegerField(
        '关联的用户ID (暂为 IntegerField，等待 User 模型实现)',)
    # OAuth提供商(github/google/wechat/qq/weibo)
    provider = models.CharField(
        'OAuth提供商(github/google/wechat/qq/weibo)', max_length=50)
    # 第三方平台的用户ID
    provider_user_id = models.CharField(
        '第三方平台的用户ID', max_length=255)
    # 访问令牌(加密存储)
    access_token = models.CharField(
        '访问令牌(加密存储)', max_length=255, blank=True, null=True)
    # 刷新令牌(加密存储)
    refresh_token = models.CharField(
        '刷新令牌(加密存储)', max_length=255, blank=True, null=True)
    # Token过期时间
    token_expires_at = models.DateTimeField(
        'Token过期时间', blank=True, null=True)
    # 额外数据(JSON格式，存储头像、昵称等)
    extra_data = models.CharField(
        '额外数据(JSON格式,存储头像、昵称等)', max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = 'OAuth 第三方登录账号关联模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("oauth_accounts")



class ArticleSEOMixin(models.Model):
    """文章SEO元数据模型 Mixin"""

    # SEO记录ID
    id = models.BigAutoField(
        'SEO记录ID'        , primary_key=True)
    # 关联的文章ID
    article_id = models.IntegerField(
        '关联的文章ID (暂为 IntegerField，等待 Article 模型实现)',)
    # SEO标题
    seo_title = models.CharField(
        'SEO标题', max_length=255, blank=True, null=True)
    # SEO描述
    seo_description = models.TextField(
        'SEO描述', blank=True, null=True)
    # SEO关键词
    seo_keywords = models.CharField(
        'SEO关键词', max_length=500, blank=True, null=True)
    # Open Graph标题
    og_title = models.CharField(
        'Open Graph标题', max_length=255, blank=True, null=True)
    # Open Graph描述
    og_description = models.TextField(
        'Open Graph描述', blank=True, null=True)
    # Open Graph图片
    og_image = models.CharField(
        'Open Graph图片', max_length=500, blank=True, null=True)
    # Open Graph类型
    og_type = models.CharField(
        'Open Graph类型', max_length=50, default='article')
    # Twitter Card标题
    twitter_title = models.CharField(
        'Twitter Card标题', max_length=255, blank=True, null=True)
    # Twitter Card描述
    twitter_description = models.TextField(
        'Twitter Card描述', blank=True, null=True)
    # Twitter Card图片
    twitter_image = models.CharField(
        'Twitter Card图片', max_length=500, blank=True, null=True)
    # Twitter Card类型
    twitter_card = models.CharField(
        'Twitter Card类型', max_length=50, default='summary_large_image')
    # 规范URL
    canonical_url = models.CharField(
        '规范URL', max_length=500, blank=True, null=True)
    # Robots元标签
    robots_meta = models.CharField(
        'Robots元标签', max_length=100, default='index,follow')
    # 是否启用Schema.org
    schema_org_enabled = models.BooleanField(
        '是否启用Schema.org',default=True)
    # Schema.org类型
    schema_org_type = models.CharField(
        'Schema.org类型', max_length=50, default='BlogPosting')

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '文章SEO元数据模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("article_seo")



class ShareStatMixin(models.Model):
    """分享统计模型 Mixin"""

    # 统计 ID
    id = models.BigAutoField(
        '统计 ID'        , primary_key=True)
    # 文章 ID
    article_id = models.IntegerField(
        '文章 ID (暂为 IntegerField，等待 Article 模型实现)',)
    # 分享平台 (wechat, weibo, twitter, facebook, linkedin, zhihu, juejin, segmentfault, telegram, copy)
    platform = models.CharField(
        '分享平台 (wechat, weibo, twitter, facebook, linkedin, zhihu, juejin, segmentfault, telegram, copy)', max_length=50)
    # 分享者用户 ID
    shared_by = models.IntegerField(
        '分享者用户 ID (暂为 IntegerField，等待 User 模型实现)',null=True, blank=True)
    # 分享者 IP 地址
    ip_address = models.CharField(
        '分享者 IP 地址', max_length=45, blank=True, null=True)
    # 用户代理
    user_agent = models.CharField(
        '用户代理', max_length=500, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '分享统计模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("share_stats")



class ProductMixin(models.Model):
    """商品模型 Mixin"""

    # 商品 ID
    id = models.BigAutoField(
        '商品 ID'        , primary_key=True)
    # 商品名称
    name = models.CharField(
        '商品名称', max_length=255)
    # 商品标识
    slug = models.CharField(
        '商品标识', max_length=255, unique=True)
    # 商品描述
    description = models.TextField(
        '商品描述', blank=True, null=True)
    # 价格
    price = models.DecimalField(
        '价格', max_digits=10, decimal_places=2)
    # 原价
    original_price = models.DecimalField(
        '原价', max_digits=10, decimal_places=2, blank=True, null=True)
    # 库存数量
    stock = models.IntegerField(
        '库存数量', default=0)
    # SKU编码
    sku = models.CharField(
        'SKU编码', max_length=100, blank=True, null=True)
    # 商品图片(JSON数组)
    images = models.TextField(
        '商品图片(JSON数组)', blank=True, null=True)
    # 分类ID
    category_id = models.IntegerField(
        '分类ID (暂为 IntegerField，等待 Category 模型实现)',null=True, blank=True)
    # 是否上架
    is_active = models.BooleanField(
        '是否上架',default=True)
    # 是否推荐
    is_featured = models.BooleanField(
        '是否推荐',default=False)
    # 重量(kg)
    weight = models.DecimalField(
        '重量(kg)', max_digits=10, decimal_places=2, blank=True, null=True)
    # 尺寸(长x宽x高,JSON格式)
    dimensions = models.TextField(
        '尺寸(长x宽x高,JSON格式)', blank=True, null=True)
    # 商品属性(JSON格式)
    attributes = models.TextField(
        '商品属性(JSON格式)', blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '商品模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("products")



class CartMixin(models.Model):
    """购物车模型 Mixin"""

    # 购物车 ID
    id = models.BigAutoField(
        '购物车 ID'        , primary_key=True)
    # 用户ID(访客可为空)
    user_id = models.IntegerField(
        '用户ID(访客可为空) (暂为 IntegerField，等待 User 模型实现)',null=True, blank=True)
    # 会话ID(用于访客购物车)
    session_id = models.CharField(
        '会话ID(用于访客购物车)', max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '购物车模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("carts")



class CartItemMixin(models.Model):
    """购物车项模型 Mixin"""

    # 购物车项 ID
    id = models.BigAutoField(
        '购物车项 ID'        , primary_key=True)
    # 购物车ID
    cart_id = models.IntegerField(
        '购物车ID (暂为 IntegerField，等待 Cart 模型实现)',)
    # 商品ID
    product_id = models.IntegerField(
        '商品ID (暂为 IntegerField，等待 Product 模型实现)',)
    # 数量
    quantity = models.IntegerField(
        '数量', default=1)
    # 单价(加入购物车时的价格)
    price = models.DecimalField(
        '单价(加入购物车时的价格)', max_digits=10, decimal_places=2)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '购物车项模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("cart_items")



class OrderMixin(models.Model):
    """订单模型 Mixin"""

    # 订单 ID
    id = models.BigAutoField(
        '订单 ID'        , primary_key=True)
    # 订单号
    order_number = models.CharField(
        '订单号', max_length=50, unique=True)
    # 用户ID
    user_id = models.IntegerField(
        '用户ID (暂为 IntegerField，等待 User 模型实现)',)
    # 订单状态 (pending:待支付, paid:已支付, processing:处理中, shipped:已发货, delivered:已送达, cancelled:已取消, refunded:已退款)
    status = models.CharField(
        '订单状态 (pending:待支付, paid:已支付, processing:处理中, shipped:已发货, delivered:已送达, cancelled:已取消, refunded:已退款)', max_length=50, default='pending')
    # 订单总金额
    total_amount = models.DecimalField(
        '订单总金额', max_digits=10, decimal_places=2)
    # 运费
    shipping_amount = models.DecimalField(
        '运费', max_digits=10, decimal_places=2, default=0)
    # 折扣金额
    discount_amount = models.DecimalField(
        '折扣金额', max_digits=10, decimal_places=2, default=0)
    # 支付方式
    payment_method = models.CharField(
        '支付方式', max_length=50, blank=True, null=True)
    # 支付状态 (pending:待支付, paid:已支付, failed:支付失败, refunded:已退款)
    payment_status = models.CharField(
        '支付状态 (pending:待支付, paid:已支付, failed:支付失败, refunded:已退款)', max_length=50, default='pending')
    # 交易ID
    transaction_id = models.CharField(
        '交易ID', max_length=255, blank=True, null=True)
    # 收货地址(JSON格式)
    shipping_address = models.CharField(
        '收货地址(JSON格式)', max_length=255)
    # 账单地址(JSON格式)
    billing_address = models.CharField(
        '账单地址(JSON格式)', max_length=255, blank=True, null=True)
    # 订单备注
    notes = models.TextField(
        '订单备注', blank=True, null=True)
    # 支付时间
    paid_at = models.DateTimeField(
        '支付时间', blank=True, null=True)
    # 发货时间
    shipped_at = models.DateTimeField(
        '发货时间', blank=True, null=True)
    # 送达时间
    delivered_at = models.DateTimeField(
        '送达时间', blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '订单模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("orders")



class OrderItemMixin(models.Model):
    """订单项模型 Mixin"""

    # 订单项 ID
    id = models.BigAutoField(
        '订单项 ID'        , primary_key=True)
    # 订单ID
    order_id = models.IntegerField(
        '订单ID (暂为 IntegerField，等待 Order 模型实现)',)
    # 商品ID
    product_id = models.IntegerField(
        '商品ID (暂为 IntegerField，等待 Product 模型实现)',)
    # 商品名称(快照)
    product_name = models.CharField(
        '商品名称(快照)', max_length=255)
    # 数量
    quantity = models.IntegerField(
        '数量')
    # 单价
    price = models.DecimalField(
        '单价', max_digits=10, decimal_places=2)
    # 小计
    total = models.DecimalField(
        '小计', max_digits=10, decimal_places=2)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '订单项模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("order_items")



class SiteMixin(models.Model):
    """站点模型（多站点支持） Mixin"""

    # 站点 ID
    id = models.BigAutoField(
        '站点 ID'        , primary_key=True)
    # 站点名称
    name = models.CharField(
        '站点名称', max_length=200)
    # 站点标识
    slug = models.CharField(
        '站点标识', max_length=100, unique=True)
    # 域名(如 example.com)
    domain = models.CharField(
        '域名(如 example.com)', max_length=255, blank=True, null=True)
    # 路径前缀(如 /site1)
    path = models.CharField(
        '路径前缀(如 /site1)', max_length=255, blank=True, null=True, default='/')
    # 是否激活
    is_active = models.BooleanField(
        '是否激活',default=True)
    # 是否为默认站点
    is_default = models.BooleanField(
        '是否为默认站点',default=False)
    # 站点设置(JSON格式)
    settings = models.CharField(
        '站点设置(JSON格式)', max_length=255, blank=True, null=True)
    # 主题slug
    theme = models.CharField(
        '主题slug', max_length=100, default='default')
    # 语言代码
    language = models.CharField(
        '语言代码', max_length=10, default='zh-CN')
    # 时区
    timezone = models.CharField(
        '时区', max_length=50, default='Asia/Shanghai')
    # 站点标题
    title = models.CharField(
        '站点标题', max_length=200, blank=True, null=True)
    # 站点描述
    description = models.TextField(
        '站点描述', blank=True, null=True)
    # 关键词
    keywords = models.CharField(
        '关键词', max_length=500, blank=True, null=True)
    # 站点管理员ID
    admin_user_id = models.BigIntegerField(
        '站点管理员ID', blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '站点模型（多站点支持）'
        # 注意：请在具体模型类中设置 db_table = get_table_name("sites")



class SensitiveWordMixin(models.Model):
    """敏感词模型 Mixin"""

    # 敏感词 ID
    id = models.BigAutoField(
        '敏感词 ID'        , primary_key=True)
    # 敏感词内容
    word = models.CharField(
        '敏感词内容', max_length=100, unique=True)
    # 敏感级别 (1:低, 2:中, 3:高)
    level = models.IntegerField(
        '敏感级别 (1:低, 2:中, 3:高)', default=1)
    # 处理方式 (block:拦截, replace:替换, warn:警告)
    action = models.CharField(
        '处理方式 (block:拦截, replace:替换, warn:警告)', max_length=50, default='block')
    # 替换词(当action为replace时使用)
    replacement = models.CharField(
        '替换词(当action为replace时使用)', max_length=100, blank=True, null=True)
    # 分类(政治、色情、暴力等)
    category = models.CharField(
        '分类(政治、色情、暴力等)', max_length=50, blank=True, null=True)
    # 是否激活
    is_active = models.BooleanField(
        '是否激活',default=True)
    # 创建者用户ID
    created_by = models.IntegerField(
        '创建者用户ID (暂为 IntegerField，等待 User 模型实现)',null=True, blank=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '敏感词模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("sensitive_words")



class UserSessionMixin(models.Model):
    """用户会话模型 Mixin"""

    # 会话 ID
    id = models.BigAutoField(
        '会话 ID'        , primary_key=True)
    # 用户ID
    user_id = models.IntegerField(
        '用户ID (暂为 IntegerField，等待 User 模型实现)',)
    # 会话令牌
    access_token = models.CharField(
        '会话令牌', max_length=255, unique=True)
    # 会话刷新令牌(不唯一 扫码的登录依赖)
    refresh_token = models.CharField(
        '会话刷新令牌(不唯一 扫码的登录依赖)', max_length=255)
    # 设备信息(User-Agent)
    device_info = models.CharField(
        '设备信息(User-Agent)', max_length=500, blank=True, null=True)
    # IP地址
    ip_address = models.CharField(
        'IP地址', max_length=45, blank=True, null=True)
    # 地理位置
    location = models.CharField(
        '地理位置', max_length=100, blank=True, null=True)
    # 是否活跃
    is_active = models.BooleanField(
        '是否活跃',default=True)
    # 最后活动时间
    last_activity = models.DateTimeField(
        '最后活动时间')
    # 过期时间
    expires_at = models.DateTimeField(
        '过期时间')

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '用户会话模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("user_sessions")



class LoginAttemptMixin(models.Model):
    """登录尝试记录模型 Mixin"""

    # 记录 ID
    id = models.BigAutoField(
        '记录 ID'        , primary_key=True)
    # 尝试登录的用户名
    username = models.CharField(
        '尝试登录的用户名', max_length=255)
    # IP地址
    ip_address = models.CharField(
        'IP地址', max_length=45)
    # User-Agent
    user_agent = models.CharField(
        'User-Agent', max_length=500, blank=True, null=True)
    # 是否成功
    is_success = models.BooleanField(
        '是否成功',default=False)
    # 失败原因
    failure_reason = models.CharField(
        '失败原因', max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '登录尝试记录模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("login_attempts")



class TokenBlacklistMixin(models.Model):
    """Token 黑名单模型（UNLOGGED 表，用于存储被撤销的 JWT Token） Mixin"""

    # ID
    id = models.BigAutoField(
        'ID'        , primary_key=True)
    # Token 唯一标识符(token 前32个字符)
    token_identifier = models.CharField(
        'Token 唯一标识符(token 前32个字符)', max_length=64, unique=True)
    # Token 哈希值(用于调试和审计)
    token_hash = models.CharField(
        'Token 哈希值(用于调试和审计)', max_length=128, blank=True, null=True)
    # Token 过期时间
    expires_at = models.DateTimeField(
        'Token 过期时间')
    # 撤销原因
    reason = models.CharField(
        '撤销原因', max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = 'Token 黑名单模型（UNLOGGED 表，用于存储被撤销的 JWT Token）'
        # 注意：请在具体模型类中设置 db_table = get_table_name("token_blacklist")



class AdPlacementMixin(models.Model):
    """广告位模型 Mixin"""

    # 广告位 ID
    id = models.BigAutoField(
        '广告位 ID', primary_key=True)
    # 广告位名称
    name = models.CharField(
        '广告位名称', max_length=100)
    # 广告位代码
    code = models.CharField(
        '广告位代码', max_length=50, unique=True)
    # 广告位描述
    description = models.TextField(
        '广告位描述', blank=True, null=True)
    # 广告位置 (header, sidebar, footer, content等)
    position = models.CharField(
        '广告位置 (header, sidebar, footer, content等)', max_length=50)
    # 广告位宽度
    width = models.IntegerField(
        '广告位宽度', blank=True, null=True)
    # 广告位高度
    height = models.IntegerField(
        '广告位高度', blank=True, null=True)
    # 是否激活
    is_active = models.BooleanField(
        '是否激活', default=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '广告位模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("ad_placements")



class AdMixin(models.Model):
    """广告模型 Mixin"""

    # 广告 ID
    id = models.BigAutoField(
        '广告 ID', primary_key=True)
    # 广告标题
    title = models.CharField(
        '广告标题', max_length=200)
    # 广告内容 (HTML/JavaScript代码)
    content = models.TextField(
        '广告内容 (HTML/JavaScript代码)', blank=True, null=True)
    # 广告图片URL
    image_url = models.CharField(
        '广告图片URL', max_length=500, blank=True, null=True)
    # 广告链接URL
    link_url = models.CharField(
        '广告链接URL', max_length=500, blank=True, null=True)
    # 图片替代文本
    alt_text = models.CharField(
        '图片替代文本', max_length=200, blank=True, null=True)
    # 广告类型: html, image, google_adsense, baidu_union
    ad_type = models.CharField(
        '广告类型: html, image, google_adsense, baidu_union', max_length=20, default='html')
    # 广告位ID
    placement_id = models.IntegerField(
        '广告位ID (暂为 IntegerField，等待 AdPlacement 模型实现)', null=True, blank=True)
    # 广告开始时间
    start_date = models.DateTimeField(
        '广告开始时间', blank=True, null=True)
    # 广告结束时间
    end_date = models.DateTimeField(
        '广告结束时间', blank=True, null=True)
    # 点击次数
    click_count = models.BigIntegerField(
        '点击次数', default=0)
    # 展示次数
    impression_count = models.BigIntegerField(
        '展示次数', default=0)
    # 广告预算
    budget = models.DecimalField(
        '广告预算', max_digits=10, decimal_places=2, blank=True, null=True)
    # 每次点击费用
    cost_per_click = models.DecimalField(
        '每次点击费用', max_digits=10, decimal_places=2, blank=True, null=True)
    # 每千次展示费用
    cost_per_impression = models.DecimalField(
        '每千次展示费用', max_digits=10, decimal_places=2, blank=True, null=True)
    # 是否激活
    is_active = models.BooleanField(
        '是否激活', default=True)
    # 优先级 (数字越大优先级越高)
    priority = models.IntegerField(
        '优先级 (数字越大优先级越高)', default=0)
    # 目标受众 (all, registered, vip等)
    target_audience = models.CharField(
        '目标受众 (all, registered, vip等)', max_length=100, default='all')
    # 设备定位: all, desktop, mobile
    device_targeting = models.CharField(
        '设备定位: all, desktop, mobile', max_length=50, default='all')
    # 地理定位 (国家/地区代码，逗号分隔)
    geo_targeting = models.CharField(
        '地理定位 (国家/地区代码,逗号分隔)', max_length=200, blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '广告模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("ads")



class AdClickMixin(models.Model):
    """广告点击记录模型 Mixin"""

    # 点击记录 ID
    id = models.BigAutoField(
        '点击记录 ID', primary_key=True)
    # 广告ID
    ad_id = models.IntegerField(
        '广告ID (暂为 IntegerField，等待 Ad 模型实现)', )
    # 用户ID (如果已登录)
    user_id = models.BigIntegerField(
        '用户ID (如果已登录)', blank=True, null=True)
    # IP地址
    ip_address = models.CharField(
        'IP地址', max_length=45, blank=True, null=True)
    # 用户代理
    user_agent = models.TextField(
        '用户代理', blank=True, null=True)
    # 来源页面
    referrer = models.CharField(
        '来源页面', max_length=500, blank=True, null=True)
    # 点击时间
    clicked_at = models.DateTimeField(
        '点击时间')

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '广告点击记录模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("ad_clicks")



class AdImpressionMixin(models.Model):
    """广告展示记录模型 Mixin"""

    # 展示记录 ID
    id = models.BigAutoField(
        '展示记录 ID', primary_key=True)
    # 广告ID
    ad_id = models.IntegerField(
        '广告ID (暂为 IntegerField，等待 Ad 模型实现)', )
    # 用户ID (如果已登录)
    user_id = models.BigIntegerField(
        '用户ID (如果已登录)', blank=True, null=True)
    # IP地址
    ip_address = models.CharField(
        'IP地址', max_length=45, blank=True, null=True)
    # 用户代理
    user_agent = models.TextField(
        '用户代理', blank=True, null=True)
    # 页面URL
    page_url = models.CharField(
        '页面URL', max_length=500, blank=True, null=True)
    # 展示时间
    displayed_at = models.DateTimeField(
        '展示时间')

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '广告展示记录模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("ad_impressions")



class RevenueRecordMixin(models.Model):
    """收益记录模型 Mixin"""

    # 收益记录 ID
    id = models.BigAutoField(
        '收益记录 ID', primary_key=True)
    # 用户ID (创作者)
    user_id = models.BigIntegerField(
        '用户ID (创作者)')
    # 收益类型: advertisement, vip_subscription, article_purchase, donation, other
    revenue_type = models.CharField(
        '收益类型: advertisement, vip_subscription, article_purchase, donation, other', max_length=50)
    # 收益金额
    amount = models.DecimalField(
        '收益金额', max_digits=10, decimal_places=2)
    # 平台手续费
    platform_fee = models.DecimalField(
        '平台手续费', max_digits=10, decimal_places=2, default=0)
    # 创作者实际收益
    creator_earnings = models.DecimalField(
        '创作者实际收益', max_digits=10, decimal_places=2)
    # 收益描述
    description = models.TextField(
        '收益描述', blank=True, null=True)
    # 关联记录ID (如广告ID、订单ID等)
    reference_id = models.BigIntegerField(
        '关联记录ID (如广告ID、订单ID等)', blank=True, null=True)
    # 关联记录类型
    reference_type = models.CharField(
        '关联记录类型', max_length=50, blank=True, null=True)
    # 状态: pending, confirmed, paid
    status = models.CharField(
        '状态: pending, confirmed, paid', max_length=20, default='pending')

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '收益记录模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("revenue_records")


class RevenueSharingConfigMixin(models.Model):
    """收益分成配置模型 Mixin"""

    # 配置 ID
    id = models.BigAutoField(
        '配置 ID', primary_key=True)
    # 收益类型
    revenue_type = models.CharField(
        '收益类型', max_length=50, unique=True)
    # 平台分成百分比
    platform_percentage = models.DecimalField(
        '平台分成百分比', max_digits=10, decimal_places=2, default=30.0)
    # 创作者分成百分比
    creator_percentage = models.DecimalField(
        '创作者分成百分比', max_digits=10, decimal_places=2, default=70.0)
    # 最低提现金额
    min_payout_amount = models.DecimalField(
        '最低提现金额', max_digits=10, decimal_places=2, default=100.0)
    # 是否激活
    is_active = models.BooleanField(
        '是否激活', default=True)
    # 配置描述
    description = models.TextField(
        '配置描述', blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '收益分成配置模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("revenue_sharing_configs")


class PayoutRequestMixin(models.Model):
    """提现申请模型 Mixin"""

    # 提现申请 ID
    id = models.BigAutoField(
        '提现申请 ID', primary_key=True)
    # 用户ID
    user_id = models.BigIntegerField(
        '用户ID')
    # 提现金额
    amount = models.DecimalField(
        '提现金额', max_digits=10, decimal_places=2)
    # 支付方式: alipay, wechat, bank_transfer
    payment_method = models.CharField(
        '支付方式: alipay, wechat, bank_transfer', max_length=50)
    # 支付账号
    payment_account = models.CharField(
        '支付账号', max_length=200)
    # 账户姓名
    account_name = models.CharField(
        '账户姓名', max_length=100, blank=True, null=True)
    # 状态: pending, approved, rejected, completed
    status = models.CharField(
        '状态: pending, approved, rejected, completed', max_length=20, default='pending')
    # 管理员备注
    admin_notes = models.TextField(
        '管理员备注', blank=True, null=True)
    # 处理人ID
    processed_by = models.BigIntegerField(
        '处理人ID', blank=True, null=True)
    # 处理时间
    processed_at = models.DateTimeField(
        '处理时间', blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '提现申请模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("payout_requests")


class UserRevenueStatsMixin(models.Model):
    """用户收益统计模型 Mixin"""

    # 统计 ID
    id = models.BigAutoField(
        '统计 ID', primary_key=True)
    # 用户ID
    user_id = models.BigIntegerField(
        '用户ID', unique=True)
    # 总收益
    total_earnings = models.DecimalField(
        '总收益', max_digits=10, decimal_places=2, default=0)
    # 已支付金额
    total_paid = models.DecimalField(
        '已支付金额', max_digits=10, decimal_places=2, default=0)
    # 待结算收益
    pending_earnings = models.DecimalField(
        '待结算收益', max_digits=10, decimal_places=2, default=0)
    # 可用余额
    available_balance = models.DecimalField(
        '可用余额', max_digits=10, decimal_places=2, default=0)
    # 最后提现时间
    last_payout_at = models.DateTimeField(
        '最后提现时间', blank=True, null=True)

    class Meta:
        abstract = True
        app_label = 'generated'
        verbose_name = '用户收益统计模型'
        # 注意：请在具体模型类中设置 db_table = get_table_name("user_revenue_stats")
