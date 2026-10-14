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

## 出站请求（SSRF）策略

统一入口：`src/utils/security/safe.py::validate_outbound_url`。默认**只允许公网 http/https**，
且**任何情况下都拒绝链路本地与云元数据地址**（`169.254.0.0/16`，可用于换取实例凭据）。

已接入校验的出口（都是**终端用户**可填写目标地址的）：

| 出口                           | 位置                                |
|------------------------------|-----------------------------------|
| AI 端点 `api_url`              | `ai/config/service.py`（创建与更新两处）   |
| Webhook 目标 URL               | `ops/webhook/service.py`（创建与更新两处） |
| 工作流 `http_request` 动作的 `url` | `system/workflow/service.py`      |
| 远程导入源站（WordPress / Halo）     | `shared/services/integrations/`   |

企业自建内网端点（内网 AI 网关、内网 Webhook）需由**部署者**设置
`ALLOW_PRIVATE_OUTBOUND_ENDPOINTS=true` 显式放行 —— 这个决定属于部署者，不应由终端用户绕过。

**有意不加校验的出口**：CDN 远端操作、Edge 部署目标、翻译 API、告警渠道、OAuth/LDAP provider、
插件市场。这些目标只由**管理员**配置（插件市场另有"可配置白名单而非硬拦"的设计），
管理员本就有配置出站的能力；企业若需统一限制，应在网络层（egress 策略 / 出站代理）收敛。

## 已知偏差（与安全相关的待修项）

- `.pre-commit-config.yaml` 的 `detect-secrets` 依赖 `.secrets.baseline`，仓库中不存在该文件；`model-lifecycle` hook 调用的
  `scripts/model_lifecycle_check.py` 也不存在。
- 依赖只锁版本、无 `--hash` 校验；`pip-audit` / `npm audit` 已在 CI 阻断（`ci.yml` 的 security job）。
- `mypy` 在 CI 中仍为**非阻塞**：历史上大量模块缺类型注解，直接阻断会让流水线长期变红；
  收敛方向是先清零 `src/` 的错误，再移除该例外。
- CSP 仍放行 `'unsafe-inline'` 与 `cdn.jsdelivr.net`（收紧需同步改前端内联脚本策略）。
- SAML 未实现（`system/integration` 的 schema 已如实标注）；LDAP 只有配置模型。
- 多租户隔离的**前端**未提供站点切换 UI（后端已具备 `X-Site-Scope: all` 能力）。
- 未接入 Prometheus/OpenTelemetry 指标出口（现有可观测性为应用内自建：慢查询、站点健康、Web Vitals）。
