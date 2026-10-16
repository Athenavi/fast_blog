"""system/oauth：OAuth 第三方登录（GitHub / Google / 微信 / QQ / 微博）。

接线自进程内服务 ``shared/services/integrations/oauth_service.py``（``OAuthService``）：把它的
**纯逻辑**（provider 元数据、授权 URL 构造、用户信息标准化、token 交换请求体）提升为可测的
纯函数，并用**真实表** ``oauth_accounts``（与 ``system/social`` 模块同一张表）落绑定关系。

能力的真实落点：

  - **provider 元数据**：``src/.../oauth/service.py`` 的 ``PROVIDERS`` 常量，端点为各厂商
    官方授权 / 令牌 / 用户信息 URL（与源服务一致，微信额外补了权威要求的 ``#wechat_redirect``）。
  - **授权 URL**：真实拼接 ``scope`` / ``state``（HMAC 签名、带过期，无需服务端存储）/
    PKCE 的 ``code_challenge``（S256），见 ``build_authorize_url``。
  - **回调**：校验 ``state`` → 用 ``httpx`` 真实调用厂商令牌端点 → 真实拉取用户信息 →
    在 ``oauth_accounts`` 上绑定 / 关联（或新建）本地 ``users`` 记录 → 复用
    ``auth_service.grant_tokens`` 签发与 v3 登录一致的登录态。
  - **解绑 / 绑定列表**：只操作**本人**数据（``oauth_accounts`` 的 ``user_id`` 归属由登录用户决定）。

**凭据来自``system_settings``**（键 ``oauth.providers``，JSON 文本）—— 这是源服务没有的部分：
源服务的 ``client_id`` / ``client_secret`` 由调用方外部传入，本模块改为从系统配置读取。
**配置缺失时一律如实返回"未配置"错误，绝不伪造第三方登录成功**（铁律）。
"""
