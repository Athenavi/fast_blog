import logging
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 加载 .env 文件
# 优先加载根目录 .env（本地开发模式），再加载 config/.env 作为补充
# 在 Docker 模式下，环境变量由 docker-compose.yml 的 environment 注入，不会被覆盖
load_dotenv()  # 根目录 .env 优先（本地开发模式，DB_HOST=localhost 等）
load_dotenv(Path(__file__).parent.parent.parent / "config" / ".env")  # config/.env 作为补充，已加载的值不会被覆盖

# 全局标志：跟踪数据库 URI 是否已经打印过（当前进程内）
_db_uri_printed = False


def _get_worker_info():
    """获取当前 worker 进程信息"""
    import multiprocessing
    try:
        current_process = multiprocessing.current_process()
        # 如果是主进程
        if current_process.name == 'MainProcess':
            return "[Worker-Main]"
        # 如果是子进程，提取进程 ID
        identity = getattr(current_process, '_identity', None)
        if identity and len(identity) > 0:
            return f"[Worker-{identity[0]}]"
        return f"[Worker-{current_process.pid}]"
    except Exception:
        return "[Worker-?]"


def get_sqlalchemy_uri(db_config):
    """获取SQLAlchemy数据库URI，仅支持PostgreSQL"""
    db_engine = db_config.get('db_engine', 'postgresql').lower()
    db_host = db_config.get('db_host')
    db_user = db_config.get('db_user')
    db_port = db_config.get('db_port')
    db_name = db_config.get('db_name')
    db_password = db_config.get('db_password')

    # 检查必要配置
    if not all([db_host, db_user, db_port, db_name]):
        logger.error('数据库连接配置不完整，请检查 .env 文件或环境变量。')
        logger.error('如果在安装向导中，请通过安装程序进行配置。')
        return None

    # 对于IPv6地址，需要使用方括号包围主机地址
    if ':' in db_host and not db_host.startswith('[') and not db_host.endswith(']'):  # 检查是否为IPv6地址
        formatted_host = f"[{db_host}]"
    else:
        formatted_host = db_host
    password_part = f":{db_password}" if db_password else ""
    sqlalchemy_uri = f"postgresql+psycopg2://{db_user}{password_part}@{formatted_host}:{db_port}/{db_name}"

    # 安全日志，如果密码存在则隐藏
    if db_password:
        safe_uri = sqlalchemy_uri.replace(db_password, '***')
    else:
        safe_uri = sqlalchemy_uri

    # 使用环境变量标记当前进程是否已输出数据库信息
    import os
    worker_info = _get_worker_info()
    env_key = f"DB_INFO_PRINTED_{os.getpid()}"

    if not os.environ.get(env_key):
        logger.info("%s 数据库引擎：PostgreSQL", worker_info)
        logger.info("%s SQLAlchemy URI: %s", worker_info, safe_uri)
        os.environ[env_key] = "1"  # 标记为已打印

    return sqlalchemy_uri


class BaseConfig:
    """基础配置类"""
    global_encoding = 'utf-8'
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        if os.environ.get('ENVIRONMENT', '').lower() == 'production':
            raise RuntimeError(
                "SECRET_KEY 未设置！生产环境必须设置 SECRET_KEY 环境变量。\n"
                "  生成方法: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        import secrets
        SECRET_KEY = secrets.token_urlsafe(32)
        logger.warning("SECRET_KEY 未设置，已生成临时密钥（服务重启后所有 JWT token 将失效）")
    elif SECRET_KEY.startswith('change-this-to') or SECRET_KEY in ('your-secret-key-here', 'changeme'):
        raise RuntimeError(
            "SECRET_KEY 仍为占位值！请在环境变量中设置一个真实的密钥。\n"
            "  当前值已被日志记录，请检查后修改。\n"
            "  生成方法: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )

    # 使用条件判断处理可能的 None 值
    jwt_expiration = os.getenv('JWT_EXPIRATION_DELTA')
    JWT_EXPIRATION_DELTA = int(jwt_expiration) if jwt_expiration is not None else 7200

    refresh_expiration = os.getenv('REFRESH_TOKEN_EXPIRATION_DELTA')
    REFRESH_TOKEN_EXPIRATION_DELTA = int(refresh_expiration) if refresh_expiration is not None else 64800

    TIME_ZONE = os.getenv('TIME_ZONE') or 'Asia/Shanghai'

    domain_env = os.getenv('DOMAIN')
    domain = (domain_env.rstrip('/') + '/') if domain_env is not None else '/'

    sitename = os.getenv('TITLE') or 'zyblog'
    beian = os.getenv('BEIAN') or '京ICP备12345678号'

    # 数据库引擎配置（仅支持 PostgreSQL）
    DB_ENGINE = 'postgresql'

    # 注意：这里暂时设为None，在子类中具体设置
    SQLALCHEMY_DATABASE_URI = None
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 添加数据库回显选项，用于调试
    database_echo = os.getenv('DATABASE_ECHO', 'False').lower() == 'true'

    CACHE_TYPE = 'simple'
    SESSION_COOKIE_NAME = 'zb_session'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=48)
    TEMP_FOLDER = 'temp/upload'
    AVATAR_SERVER = "https://api.7trees.cn/avatar"
    ALLOWED_MIMES = [
        # ===== 图片 =====
        'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp', 'image/svg+xml', 'image/tiff',
        'image/avif', 'image/heic', 'image/heif',
        # ===== 视频 =====
        'video/mp4', 'video/mpeg', 'video/quicktime', 'video/x-msvideo', 'video/webm', 'video/x-matroska',
        'video/x-flv', 'video/x-ms-wmv', 'video/x-m4v', 'video/3gpp', 'video/x-ms-asf', 'video/mp2t',
        # ===== 音频 =====
        'audio/mpeg', 'audio/wav', 'audio/flac', 'audio/x-flac', 'audio/aac', 'audio/ogg', 'audio/oga',
        'audio/mp3', 'audio/x-wav', 'audio/mp4', 'audio/x-ms-wma', 'audio/opus', 'audio/webm', 'audio/weba', 'audio/x-aiff',
        # ===== Office Word =====
        'application/pdf', 'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.template',
        'application/vnd.ms-word.document.macroEnabled.12',
        'application/vnd.ms-word.template.macroEnabled.12',
        # ===== Office Excel =====
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.template',
        'application/vnd.ms-excel.sheet.macroEnabled.12',
        'application/vnd.ms-excel.sheet.binary.macroEnabled.12',
        'application/vnd.ms-excel.template.macroEnabled.12',
        'application/vnd.oasis.opendocument.spreadsheet',
        'application/x-iwork-numbers-sffnumbers',
        # ===== Office PowerPoint =====
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/vnd.openxmlformats-officedocument.presentationml.template',
        'application/vnd.openxmlformats-officedocument.presentationml.slideshow',
        'application/vnd.ms-powerpoint.presentation.macroEnabled.12',
        'application/vnd.ms-powerpoint.template.macroEnabled.12',
        'application/vnd.ms-powerpoint.slideshow.macroEnabled.12',
        # ===== 文档 & 文本 =====
        # 注意：禁止 text/html / text/xml / application/xml 等可内联执行或嵌套恶意内容类型，
        # 防止同源存储型 XSS（上传 HTML/XML 经静态挂载内联渲染）。
        'text/plain', 'text/markdown', 'text/csv',
        'application/json',
        # ===== 压缩包 & 归档 =====
        'application/zip', 'application/x-zip-compressed',
        'application/x-rar-compressed', 'application/x-7z-compressed',
        'application/gzip', 'application/x-tar', 'application/x-bzip2',
        'application/x-xz', 'application/zstd', 'application/x-lzma',
        'application/x-cab', 'application/x-cpio', 'application/x-iso9660-image',
        'application/x-lha', 'application/x-lzh', 'application/x-archive', 'application/x-xar',
        # ===== 电子书 =====
        'application/epub+zip',
        # ===== 邮件 =====
        'message/rfc822', 'application/vnd.ms-outlook',
        # ===== CAD & 设计 =====
        'image/vnd.dwg', 'image/vnd.dxf', 'application/dwf',
        'application/oxps', 'application/vnd.ms-xpsdocument',
        # ===== 3D 模型 =====
        'model/gltf-binary', 'model/gltf+json', 'model/obj', 'model/stl',
        'model/vnd.collada+xml', 'model/vrml', 'model/step',
        'model/step-xml', 'application/step', 'application/x-ifc',
        # ===== OFD & 国产格式 =====
        'application/ofd', 'application/vnd.ofd',
        # ===== Typst =====
        'text/typst', 'application/x-typst',
        # ===== Excalidraw & draw.io =====
        'application/x-excalidraw', 'application/x-drawio',
        # ===== 通用二进制 =====
        'application/octet-stream',
    ]
    UPLOAD_LIMIT = 60 * 1024 * 1024
    MAX_LINE = 1000
    MAX_CACHE_TIMESTAMP = 7200
    USER_FREE_STORAGE_LIMIT = 0.5 * 1024 * 1024 * 1024  # 512MB 用户免费空间限制
    RATELIMIT_DEFAULT = "10/second"

    # FFmpeg 配置（视频处理）
    FFMPEG_PATH = os.environ.get('FFMPEG_PATH', 'ffmpeg')
    FFPROBE_PATH = os.environ.get('FFPROBE_PATH', 'ffprobe')
    # 邮件配置
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')  # 默认使用 Gmail SMTP
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    BABEL_DEFAULT_LOCALE = 'zh_CN'
    BABEL_DEFAULT_TIMEZONE = 'Asia/Shanghai'
    BABEL_SUPPORTED_LOCALES = ['zh_CN', "en"]
    BABEL_TRANSLATION_DIRECTORIES = 'translations'
    # jwt
    _jwt_secret = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    if (not _jwt_secret
            or _jwt_secret.startswith('change-this-jwt')
            or _jwt_secret.startswith('change-this-to')
            or _jwt_secret.lower() in ('your-secret-key-here', 'changeme', 'change-this-jwt-secret-key')):
        raise RuntimeError(
            "JWT_SECRET_KEY 仍为占位值或未设置！请在环境变量中设置一个真实的密钥。\n"
            "生成方法: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )
    JWT_SECRET_KEY = _jwt_secret
    JWT_ALGORITHM = "HS256"  # JWT 算法
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=JWT_EXPIRATION_DELTA)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=REFRESH_TOKEN_EXPIRATION_DELTA)
    JWT_ACCESS_COOKIE_NAME = 'access_token'
    JWT_REFRESH_COOKIE_NAME = 'refresh_token'
    JWT_TOKEN_LOCATION = ['cookies']
    # Cookie 安全：非开发环境（生产/其余）默认强制 Secure（仅经 HTTPS 传输），
    # 开发环境(ENVIRONMENT=development)保持 False 便于本地 http 调试。
    _cookie_secure = os.environ.get('ENVIRONMENT', '').lower() != 'development'
    JWT_COOKIE_SECURE = _cookie_secure
    # CSRF 防护策略：
    # 本框架（FastAPI + JWT Bearer，前后端分离）未实现 JWT_COOKIE_CSRF_PROTECT 后端校验，
    # 且既有侵入式安全头 csrf 端点亦标记废弃（JWT + SameSite=Lax 已天然缓解 CSRF），
    # 故保持 False。
    #
    # 生产环境 CSRF 缓解依赖以下多层防护：
    # 1. JWT_COOKIE_SECURE=True（仅 HTTPS 传输 Cookie）
    # 2. JWT_COOKIE_SAMESITE='Lax'（同站策略，阻止跨站 POST/PUT/DELETE 携带 Cookie）
    # 3. 所有状态变更端点（POST/PUT/DELETE）依赖 JWT Bearer Token（Authorization 头）
    #    而非仅 Cookie 认证，因此即使 Cookie 被跨站携带，缺少 Bearer Token 仍无法操作
    # 4. OAuth 流程使用 state 参数（服务端存储和验证）防止 CSRF 授权码劫持
    #
    # 注意：JWT_COOKIE_SAMESITE='Lax' 仅阻止跨站顶级 POST 请求携带 Cookie，
    # 但不阻止 GET 请求。所有敏感操作应使用 POST/PUT/DELETE 方法。
    JWT_COOKIE_CSRF_PROTECT = False
    JWT_COOKIE_SAMESITE = 'Lax'  # SameSite 属性以防范 CSRF 攻击
    JWT_SESSION_COOKIE = False
    REMEMBER_COOKIE_DURATION = timedelta(days=30)  # 记住登录状态30天
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    # S3存储配置
    S3_ENABLED = os.environ.get('S3_ENABLED', 'True').lower() == 'true'
    S3_ENDPOINT_URL = os.environ.get('S3_ENDPOINT_URL')  # S3服务端点，如使用AWS S3可不设置
    S3_ACCESS_KEY = os.environ.get('S3_ACCESS_KEY')  # S3访问密钥
    S3_SECRET_KEY = os.environ.get('S3_SECRET_KEY')  # S3密钥
    S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'media-bucket')  # S3存储桶名称
    S3_REGION = os.environ.get('S3_REGION', 'us-east-1')  # S3区域
    S3_USE_SSL = os.environ.get('S3_USE_SSL', 'True').lower() == 'true'  # 是否使用SSL
    S3_SIGNATURE_VERSION = os.environ.get('S3_SIGNATURE_VERSION', 's3v4')  # 签名版本

    # 安全头配置（Talisman）
    # 注意：生产部署时请根据实际使用的 CDN 域名修改 script-src 中的白名单
    TALISMAN_CONTENT_SECURITY_POLICY = {
        'default-src': "'self'",
        'script-src': ["'self'"],
        'style-src': ["'self'", "'unsafe-inline'"]
    }


class AppConfig(BaseConfig):
    """应用配置类，可以继承基础配置并进行覆盖或添加"""

    def __init__(self):
        super().__init__()
        self.db_engine = os.environ.get('DB_ENGINE') or os.getenv('DB_ENGINE', 'postgresql')
        self.db_host = os.environ.get('DB_HOST') or os.getenv('DATABASE_HOST', 'localhost')
        self.db_user = os.environ.get('DB_USER') or os.getenv('DATABASE_USER', 'postgres')
        self.db_name = os.environ.get('DB_NAME') or os.getenv('DATABASE_NAME')
        self.db_password = os.environ.get('DB_PASSWORD') or os.getenv('DATABASE_PASSWORD')
        db_port_env = os.environ.get('DB_PORT') or os.getenv('DATABASE_PORT')
        self.db_port = int(db_port_env) if db_port_env is not None else 5432
        db_pool_size_env = os.environ.get('DB_POOL_SIZE') or os.getenv('DATABASE_POOL_SIZE')
        self.db_pool_size = int(db_pool_size_env) if db_pool_size_env is not None else 20
        db_pool_overflow_env = os.environ.get('DB_POOL_OVERFLOW') or os.getenv('DATABASE_POOL_OVERFLOW')
        self.db_pool_overflow = int(db_pool_overflow_env) if db_pool_overflow_env is not None else 30
        db_pool_timeout_env = os.environ.get('DB_POOL_TIMEOUT') or os.getenv('DATABASE_POOL_TIMEOUT')
        self.db_pool_timeout = int(db_pool_timeout_env) if db_pool_timeout_env is not None else 60
        self.db_table_prefix = os.environ.get('DB_TABLE_PREFIX') or os.getenv('DB_TABLE_PREFIX', '')
        # 初始化数据库URI（可能为 None，如果配置不完整）
        self.database_url = self._get_database_uri()
        # 为SQLAlchemy设置数据库URI
        self.SQLALCHEMY_DATABASE_URI = self.database_url

    def _get_database_uri(self):
        """获取数据库URI"""
        return get_sqlalchemy_uri({
            'db_engine': self.db_engine,
            'db_host': self.db_host,
            'db_user': self.db_user,
            'db_port': self.db_port,
            'db_name': self.db_name,
            'db_password': self.db_password
        })

    @property
    def database_pool_size(self):
        """动态获取连接池大小"""
        return self.db_pool_size

    @property
    def database_pool_overflow(self):
        """动态获取连接池溢出数"""
        return self.db_pool_overflow

    @property
    def database_pool_timeout(self):
        """动态获取连接池超时"""
        return self.db_pool_timeout

    @property
    def pool_config(self):
        """动态获取连接池配置（PostgreSQL）"""
        return {
            "pool_size": int(self.db_pool_size),
            "max_overflow": int(self.db_pool_overflow),
            "pool_timeout": int(self.db_pool_timeout),
            "pool_recycle": 1200,
            "pool_pre_ping": True,
        }

    # RedisConfig = {
    #    "host": os.environ.get('REDIS_HOST') or os.getenv('REDIS_HOST', 'localhost'),
    #    "port": os.environ.get('REDIS_PORT') or os.getenv('REDIS_PORT', 6379),
    #    "db": os.environ.get('REDIS_DB') or os.getenv('REDIS_DB', 0),
    #    "password": os.environ.get('REDIS_PASSWORD') or os.getenv('REDIS_PASSWORD') or None,
    #    "decode_responses": True,
    #    "socket_connect_timeout": 3,  # 连接超时3秒
    #    "socket_timeout": 3,  # 读写超时3秒
    #    "retry_on_timeout": True,  # 超时重试
    #    "max_connections": 10  # 连接池大小
    # }


#

def get_app_config():
    # 使用密码学安全的 secrets 模块生成密钥
    import secrets
    # 更新 BaseConfig 中的 SECRET_KEY
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        # 在生产环境必须强制设置 SECRET_KEY
        if os.environ.get('ENVIRONMENT', '').lower() == 'production':
            raise RuntimeError(
                "SECRET_KEY 未设置！生产环境必须设置 SECRET_KEY 环境变量。\n"
                "生成方法: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        # 未配置环境变量时，生成强随机密钥并警告用户
        secret_key = secrets.token_urlsafe(32)
        logger.warning("SECRET_KEY 未设置，已生成临时密钥（服务重启后所有 JWT token 将失效）")
        logger.warning("请在生产环境中设置 SECRET_KEY 环境变量以确保 Token 稳定性。")

    BaseConfig.SECRET_KEY = secret_key

    # 同步更新 JWT_SECRET_KEY：仅当环境变量 JWT_SECRET_KEY 未设置时，
    # 跟随 SECRET_KEY 保持同步，避免两者不一致导致 JWT 验证失败
    if not os.environ.get('JWT_SECRET_KEY'):
        BaseConfig.JWT_SECRET_KEY = secret_key

    # 获取domain环境变量
    domain_env = os.getenv('DOMAIN')
    BaseConfig.domain = (domain_env.rstrip('/') + '/') if domain_env is not None else '/'

    # 创建AppConfig实例并初始化数据库URI
    config = AppConfig()
    return config


app_config = get_app_config()
settings = app_config  # 为FastAPI兼容性创建别名


class ProductionConfig(AppConfig):
    """生产环境配置"""

    def __init__(self):
        super().__init__()
        self.DEBUG = False
        self.TESTING = False
        self._validate_required_env()

    def _validate_required_env(self):
        """校验生产环境必需的数据库配置，使用 AppConfig 已解析的属性（带默认值）。
        仅发出警告而不终止进程——应用设计为在数据库未配置时仍能启动（安装向导）。
        """
        missing = []
        # 使用 AppConfig 解析后的属性（有 fallback 默认值），而非原始 os.environ.get()
        if not self.db_name:
            missing.append('DB_NAME')
        if not self.db_host:
            missing.append('DB_HOST')
        if not self.db_user:
            missing.append('DB_USER')

        if missing:
            logger.warning("以下数据库环境变量未设置，应用将以安装向导模式启动")
            logger.warning("未设置的变量: %s", ', '.join(missing))
            logger.warning("请通过以下任一方式配置：")
            logger.warning("1. 创建 .env 文件（参考 .env.example）")
            logger.warning("2. 在 docker-compose.yml 的 environment 中设置")
            logger.warning("3. 直接设置系统环境变量")
            logger.warning("示例配置：")
            logger.warning("  - DB_HOST=postgres")
            logger.warning("  - DB_PORT=5432")
            logger.warning("  - DB_USER=postgres")
            logger.warning("  - DB_PASSWORD=your_password")
            logger.warning("  - DB_NAME=fast_blog")
            logger.warning("  - SECRET_KEY=your-secret-key-at-least-32-chars")
            logger.warning("应用将继续启动，请通过 /install 页面完成数据库配置。")
        else:
            # 警告：未设置密码（允许，但提示安全风险）
            if not self.db_password:
                logger.warning("警告：未设置 DB_PASSWORD，数据库将使用空密码连接")


class DevelopmentConfig(AppConfig):
    """开发环境配置"""

    def __init__(self):
        super().__init__()
        self.DEBUG = True
        self.TESTING = False


class TestingConfig(AppConfig):
    """测试环境配置"""

    def __init__(self):
        super().__init__()
        self.DEBUG = True
        self.TESTING = True


def get_config_by_env(env):
    """根据环境参数获取配置类"""
    # 支持简写和完整形式
    if env in ['prod', 'production']:
        return ProductionConfig()
    elif env in ['dev', 'development']:
        return DevelopmentConfig()
    elif env in ['test', 'testing']:
        return TestingConfig()
    else:
        return ProductionConfig()  # 默认使用生产环境配置
