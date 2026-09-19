"""ops.cdn 模块（T5-11 批次 4）：CDN 配置管理。

无独立表：配置以 JSON 持久化在 ``system_settings`` 的 ``cdn.config`` 键（setting_type=json），
复用 system/setting 服务。能力参考共享服务 ``shared/services/performance/cdn_integration.py``
（cloudflare / aws_cloudfront / aliyun_cdn / tencent_cdn / custom）。
凭据（api_token 等）只写不读，响应仅含 ``has_api_token`` 布尔位；更新留空保持原值。
实际清缓存/预热等远端动作为二期。
"""
