"""
Django 6 博客项目配置

架构说明：
- 本项目采用 Django ORM + SQLAlchemy 双 ORM 架构
- Django ORM：负责用户认证、权限管理（与 Django SimpleJWT 集成）一
- SQLAlchemy：负责业务逻辑（文章、分类等），支持异步操作
- 两个 ORM 共享同一个数据库连接配置
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 环境检测
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development').lower()  # development/staging/production
BASE_DIR = Path(__file__).resolve().parent.parent
# 根据环境加载额外配置
env_file = BASE_DIR / f'.env.{ENVIRONMENT}'
if env_file.exists():
    load_dotenv(env_file, override=True)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')

# Debug模式增强配置
DEBUG_MODE = DEBUG  # 兼容旧配置
SHOW_ERRORS = os.getenv('SHOW_ERRORS', 'True').lower() in ('true', '1', 'yes')
LOG_QUERIES = os.getenv('LOG_QUERIES', 'False').lower() in ('true', '1', 'yes') and DEBUG
SAVEQUERIES = os.getenv('SAVEQUERIES', 'False').lower() in ('true', '1', 'yes') and DEBUG

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '*',
]

# Application definition
INSTALLED_APPS = [
    'simpleui',  # SimpleUI 主题必须在 django.contrib.admin 之前
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party apps
    'rest_framework',
    'corsheaders',

    # Local apps
    'apps.blog',
    'apps.user',
    'apps.category',
    'apps.media',
    'apps.settings',
    'apps.generated',  # 自动生成的 ORM Mixins
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # 添加 WhiteNoise 支持
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Debug模式下添加查询日志中间件
if LOG_QUERIES or SAVEQUERIES:
    MIDDLEWARE.append('django_blog.middleware.QueryLoggingMiddleware')

MIDDLEWARE.append('django_blog.fastapi_adapter.GeneratorDependencyCleanupMiddleware')  # 必须放在最后

ROOT_URLCONF = 'django_blog.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'frontend-next' / 'out',
            BASE_DIR / 'templates',  # 添加项目 templates 目录
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'django_blog.wsgi.application'

# Database（仅支持 PostgreSQL）
DB_ENGINE = 'django.db.backends.postgresql'

DATABASES = {
    'default': {
        'ENGINE': DB_ENGINE,
        'NAME': os.getenv('DB_NAME', 'fast_blog'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}

# Custom User Model
AUTH_USER_MODEL = 'user.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# Disable APPEND_SLASH for RESTful API (no trailing slashes)
APPEND_SLASH = False

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
    BASE_DIR / 'frontend-next' / 'out' / '_next',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Storage
UPLOAD_LIMIT = int(os.getenv('UPLOAD_LIMIT', 62914560))
USER_FREE_STORAGE_LIMIT = int(os.getenv('USER_FREE_STORAGE_LIMIT', 536870912))

# CORS configuration
CORS_ALLOW_ALL_ORIGINS = True  # 开发环境允许所有来源
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:9421",
    "http://127.0.0.1:9421",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

# CSRF configuration - 信任的来源（包括端口号）
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:9421",
    "http://127.0.0.1:9421",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'django_blog.exceptions.custom_exception_handler',
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
}

# JWT Settings
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(seconds=int(os.getenv('JWT_EXPIRATION_DELTA', 7200))),
    'REFRESH_TOKEN_LIFETIME': timedelta(seconds=int(os.getenv('REFRESH_TOKEN_EXPIRATION_DELTA', 64800))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')

# Use Redis cache (PostgreSQL environment)
if REDIS_HOST:
    # Production mode - use Redis cache
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': f'redis://{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}',
        }
    }
else:
    # No Redis configured - use local memory cache
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }

# Email configuration
EMAIL_HOST = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('MAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
EMAIL_HOST_USER = os.getenv('MAIL_USERNAME', '')
EMAIL_HOST_PASSWORD = os.getenv('MAIL_PASSWORD', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Site information
SITE_NAME = os.getenv('TITLE', 'Fast Blog')
DOMAIN = os.getenv('DOMAIN', 'http://localhost:8000')
BEIAN = os.getenv('BEIAN', '')

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django_app.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        # SQLAlchemy 日志配置 - 避免重复输出
        'sqlalchemy.engine': {
            'level': 'ERROR',  # 只输出错误，避免 INFO 和 WARNING 级别重复
            'handlers': ['file'],
            'propagate': False,
        },
        'sqlalchemy.pool': {
            'level': 'ERROR',  # 连接池错误
            'handlers': ['file'],
            'propagate': False,
        },
    },
}

# Ensure logs directory exists
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# SimpleUI 配置
SIMPLEUI_HOME_INFO = False  # 禁用首页信息
SIMPLEUI_ANALYSIS = False  # 禁用分析
SIMPLEUI_LOGO = None  # 使用默认 logo
SIMPLEUI_ICON = {  # 自定义模型图标
    '系统管理': 'fas fa-cog',
    '博客管理': 'fas fa-blog',
    '用户管理': 'fas fa-users',
    '分类管理': 'fas fa-folder',
    '媒体管理': 'fas fa-image',
    '设置': 'fas fa-tools',
}
SIMPLEUI_CONFIG = {
    'system': {
        'default-color': 'dark',  # 深色主题
        'name': 'Fast Blog 后台管理系统',  # 系统名称
    },
    'menu': [
        {
            'icon': 'fas fa-blog',
            'name': '博客管理',
            'models': [
                {'name': '文章', 'url': '/admin/blog/post/'},
                {'name': '标签', 'url': '/admin/blog/tag/'},
            ]
        },
        {
            'icon': 'fas fa-users',
            'name': '用户管理',
            'models': [
                {'name': '用户', 'url': '/admin/user/user/'},
            ]
        },
        {
            'icon': 'fas fa-folder',
            'name': '分类管理',
            'models': [
                {'name': '分类', 'url': '/admin/category/category/'},
            ]
        },
        {
            'icon': 'fas fa-image',
            'name': '媒体管理',
            'models': [
                {'name': '媒体文件', 'url': '/admin/media/media/'},
            ]
        },
        {
            'icon': 'fas fa-tools',
            'name': '设置',
            'models': [
                {'name': '站点设置', 'url': '/admin/settings/setting/'},
            ]
        },
    ]
}
