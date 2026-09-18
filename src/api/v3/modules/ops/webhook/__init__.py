"""webhook 模块：Webhook 订阅管理

路由前缀：``/api/v3/ops/webhook``

数据模型：``webhooks(id, name, url, secret, events, is_active, created_at, updated_at)``。

**CRUD 是新写的**：项目里 ``WebhookService``（``shared/services/notifications/webhook_service.py``）
只有 ``trigger_event`` 一个方法（且是 ``@staticmethod``、类无 ``__init__``），所以 v2 的
webhook 端点全部 500 ——``WebhookService(db)`` 先 ``TypeError``，再 ``create_webhook`` 等
``AttributeError``。v3 用 ``CRUDBase`` 直接管表，派发仍复用 ``trigger_event``。

``secret`` 只写不回显（响应里只给 ``has_secret``），避免密钥泄露。

权限码：``settings:view`` / ``settings:edit``
"""
