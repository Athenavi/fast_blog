# 安全策略

## 支持的版本

| 版本                                                | 支持状态   |
|---------------------------------------------------|--------|
| 最新 release（见 `version.txt` 的 `[RELEASE] version`） | ✅ 积极维护 |
| 其他历史版本                                            | ❌ 不再维护 |

## 报告漏洞

**请不要通过公开 Issue 报告安全漏洞。**

请发送邮件到 **athenavi@qq.com**，我们会在 **48 小时内**回复。

邮件中请尽量包含：

- 漏洞类型（SQL 注入、XSS、越权、信息泄露等）
- 受影响的文件与位置（分支 / 提交 / 版本号，版本见 `version.txt`）
- 复现步骤与 PoC（如有可能）
- 影响评估

### 响应时限

| 严重级别  | 处理时限     |
|-------|----------|
| 🔴 严重 | 24–48 小时 |
| 🟠 高  | 7 天      |
| 🟡 中  | 30 天     |
| 🟢 低  | 下一个常规版本  |

### 安全港

我们支持负责任的披露，不会对善意研究采取法律行动。请勿在测试过程中访问、修改或删除他人数据。

## 部署安全检查清单

- [ ] 修改所有默认口令；`SECRET_KEY`、`JWT_SECRET_KEY`、`DB_PASSWORD`、`REDIS_PASSWORD` 均为 ≥32 位随机值（生产 compose 对后两项是
  **强制**的，缺失直接启动失败）
- [ ] `ENVIRONMENT=production`（同时会关闭 `/api/v3/docs`、`/api/v3/redoc`、`/api/v3/openapi.json`，并把 Cookie 置为
  `Secure`）
- [ ] `DEBUG=False`（`DEBUG=True` 会打印请求头与请求体）
- [ ] 配置 HTTPS 证书并启用 TLS（证书放 `nginx/ssl/`，HSTS 只在 443 server 块下发）
- [ ] 按实际域名设置 `CORS_ORIGINS`（不设则使用内置的 localhost 白名单）
- [ ] 保持 nginx 限流开启（`api` 30r/s、`login` 5r/m、`general` 50r/s），并按业务调整
- [ ] `WORKERS>1` 时必须配置 Redis（否则限流/缓存各进程独立、定时任务重复执行）
- [ ] 确认审计日志可用（写操作经 `OperationLogRoute` 落 `audit_logs`）
- [ ] 配置自动化备份并验证恢复流程（见 `docs/DEPLOYMENT.md` 第 10 节）
- [ ] 定期更新依赖：`pip-audit --strict`、`npm audit`（CI 的 `security` job 已包含，当前为非阻塞）
- [ ] 谨慎开放端口：生产形态只对外暴露 nginx（80/443），后端/数据库/Redis 均绑 127.0.0.1

## 内置安全能力

**认证与会话**

- JWT（HS256）访问令牌 + 刷新令牌，支持 Cookie 与 Bearer 双模式
- 刷新与登出配合 Token 黑名单中间件（`src/middleware/token_blacklist_middleware.py`）
- TOTP 两步验证（`pyotp` + `qrcode`）
- 密码哈希 Argon2（`argon2-cffi`）
- 暴力破解防护中间件：默认 10 次/15 分钟/IP、5 次/用户名，可用 `BRUTE_FORCE_MAX_PER_IP` / `BRUTE_FORCE_MAX_PER_USER` 调整
- 账号锁定：数据库 + Redis 双层

**授权**

- 角色 → 权限码（三段式 `module_{域}:{模块}:{动作}`，共 194 条），路由级 `AuthControl` / `AuthPermission` 校验
- 菜单级授权：`admin_menus` + `role_admin_menus`（前端只负责结构，授权在后端）
- 权限用户组 + 数据范围（`data_scope`，仅作用于管理端；公开读不过滤）
- 启动期权限审计：写操作必须声明权限码、码必须已登记，`PERMISSION_AUDIT_STRICT=1` 时问题即拒绝启动

**数据与凭据**

- 通用凭据加密：AES-256-GCM（`src/api/v3/core/secret_box.py`，密钥 `SHA256(SECRET_KEY)`），密文永不回传，出参只给 `has_xxx`
- 用户级凭据加密：`HKDF(SECRET_KEY, salt=用户密码哈希)`（`core/user_secret_box.py`），服务端无需明文密码
- 云存储/供应商凭据统一走加密存储，不新增明文字段

**输入与文件**

- SQL 注入防护：全部经 SQLAlchemy ORM / 参数化查询
- 上传校验：MIME 白名单（`ALLOWED_MIMES`）与大小上限（`UPLOAD_LIMIT`，默认 60MB）
- 受控文件下载：`/api/v3/assets/storage/**` 校验路径（防目录遍历）并按 sha256 反查媒体公开性，私密媒体仅作者可见
- 敏感词过滤模块（`/api/v3/system/sensitive-word`）
- 内容安全响应头与 CSP（应用层中间件 + nginx 双层）

**审计与合规**

- 写操作审计日志（`audit_logs`），含未认证请求的失败尝试
- GDPR 同意记录模块（`/api/v3/system/gdpr`）
- 请求速率限制（应用层 + nginx 双层）
- 依赖版本锁定（`requirements.txt` 使用 `==`；前端以 `package-lock.json` 为准）

## 已知偏差（与安全相关的待修项）

- `.pre-commit-config.yaml` 的 `detect-secrets` 依赖 `.secrets.baseline`，仓库中不存在该文件；`model-lifecycle` hook 调用的
  `scripts/model_lifecycle_check.py` 也不存在。
