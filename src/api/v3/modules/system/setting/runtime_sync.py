"""把「系统设置」里的运行时配置同步到内存中的服务实例。

背景：后台的配置项是自由 key-value，但其中一部分（如 SMTP 邮件参数）需要**立刻**
作用于已经在内存里的服务实例，否则改完配置必须重启进程才生效。

历史实现 ``src/utils/config_manager.py`` 做这件事，但它用的是同步 ``Session``，而且
字段名与模型不符（``setting.key`` / ``setting.value``，实际是
``setting_key`` / ``setting_value``），一运行就 AttributeError —— 因此这里按当前架构重写。

约定：只有下表列出的键会触发刷新；其余键（前端允许自由增删）只落库。
"""

from typing import Dict, Iterable, List, Tuple

from shared.logging import default_logger as logger

#: 设置键 → EmailService 上的属性名。``mail_*`` 是历史键名（config_manager 时代的约定），
#: ``smtp_*`` / ``from_*`` 是 EmailService 当前读取的键名，两者都接受。
EMAIL_SETTINGS: Dict[str, str] = {
    "smtp_host": "smtp_host",
    "smtp_port": "smtp_port",
    "smtp_user": "smtp_user",
    "smtp_password": "smtp_password",
    "from_email": "from_email",
    "from_name": "from_name",
    "mail_server": "smtp_host",
    "mail_port": "smtp_port",
    "mail_username": "smtp_user",
    "mail_password": "smtp_password",
    "mail_from_address": "from_email",
}

#: 需要转成整数的属性
_INT_ATTRS = frozenset({"smtp_port"})


def _email_service():
    # 延迟导入：避免 core 层在导入期就拉起通知服务
    from shared.services.notifications.email_service import email_service

    return email_service


def apply_runtime_settings(items: Iterable[Tuple[str, object]]) -> List[str]:
    """把 ``(key, value)`` 序列应用到运行时实例，返回真正生效的键名。

    未知键、空值一律忽略（前端允许自由增删配置项）；失败只记日志，不影响配置落库。
    """
    applied: List[str] = []
    service = None

    for key, value in items:
        attr = EMAIL_SETTINGS.get(key)
        if attr is None or value is None:
            continue

        if attr in _INT_ATTRS:
            try:
                value = int(value)
            except (TypeError, ValueError):
                logger.warning("运行时配置 %s 需要整数，收到 %r，已忽略", key, value)
                continue

        if service is None:
            service = _email_service()
        setattr(service, attr, value)
        applied.append(key)

    if applied:
        logger.info("运行时配置已刷新：%s", ", ".join(applied))
    return applied
