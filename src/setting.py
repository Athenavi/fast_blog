"""
应用配置 — src 入口（兼容层）

从 shared.config.settings 导入，保持旧路径兼容性。
新代码应直接从 shared.config.settings 导入。

 已废弃：此模块仅作为向后兼容的 re-export 层。
请迁移到: from shared.config.settings import settings

注意：所有大写配置变量（DB_ENGINE, DB_HOST, MAIL_SERVER 等）
均为 BaseConfig/AppConfig 的类属性/实例属性，不是模块级变量。
需要访问时请通过 settings 对象：settings.DB_ENGINE, settings.DB_HOST 等。
"""
from shared.config.settings import (  # noqa: F401
    settings, app_config, BaseConfig, AppConfig,
    ProductionConfig, DevelopmentConfig, TestingConfig,
    get_app_config, get_config_by_env, get_sqlalchemy_uri, _get_worker_info,
)
