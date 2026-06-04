"""
integration 子模块 - 模型定义
由代码生成器自动生成 - 请勿手动修改
"""
from .email_service_config import EmailServiceConfig
from .ldap_config import LDAPConfig
from .notification_integration import NotificationIntegration
from .saml_config import SAMLConfig
from .sso_provider import SSOProvider

__all__ = ['EmailServiceConfig', 'LDAPConfig', 'NotificationIntegration', 'SAMLConfig', 'SSOProvider']
