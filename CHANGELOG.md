# 更新日志

本项目版本号格式为 `主.次.年份.月日`（例如 `0.8.26.0921` = 第 8
次发布、2026-09-21），遵循[语义化版本](https://semver.org/lang/zh-CN/)
思路；日志结构参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

> 条目按该版本的 git 提交归纳。历史版本的逐条变更可用 `git log <旧tag>..<新tag> --oneline` 或 GitHub Releases 查询。

## [Unreleased]

### 变更

- **文档全面重构**：README.md 改为中文（英文版迁移到 README.en.md，原 README_zh.md 移除）；`docs/` 精简为
  [DEPLOYMENT.md](docs/DEPLOYMENT.md) 与 [DEVELOPMENT.md](docs/DEVELOPMENT.md) 两篇（原 `DEPLOYMENT_GUIDE.md`
  的云平台通用内容与 `docs/refactor/HANDOVER.md` 不再单独维护）；子项目 README（前端、移动端、SDK、测试、插件、主题）
  与 `CHANGELOG` / `CONTRIBUTING` / `SECURITY` / Issue 与 PR 模板一并按当前代码事实重写

### 修复

- `frontend/web`：显式声明 `vite` 依赖并重建 lockfile，修复 `npm ci --legacy-peer-deps` 下 `nuxt prepare`
  报 `Cannot find module 'vite'` 导致的安装失败（顶层 vite 升为 8.3.0，与 `@nuxt/vite-builder` 对齐）
- CI：`release.yml` 的 Node 版本由 25 调整为 22，与 `ci.yml`、前端 Dockerfile 保持一致
- `Dockerfile`：`CMD` 去掉已被移除的 `--backend fastapi` 参数（此前容器内后端会因 argparse 报错无法启动）；
  `HEALTHCHECK` 由 `/api/v2/health` 改为 `/api/v3/health`
- `Makefile`：修正 `.env_example` 拼写（实际文件为 `.env.example`）、`--backend` 参数、
  `/api/v1/health` 探活地址与 `docker-compose exec app` 服务名；`create-admin` / `routes` 目标改用 Typer CLI
- `tests/load/benchmark.js`：迁移到 API v3 的路径、分页参数（`page_size`）与 `{code, msg, data, pagination}` 响应约定

### 新增

- `install.py`：**跨平台交互式安装 / 初始化脚本**（仅依赖标准库）—— 环境自检 → 生成 `.env` 并写入 4 个强随机密钥
  （已存在则备份后补齐占位项）→ 检查/下载静态 ffmpeg → `docker compose up -d --build` 并等待 `/api/v3/health`
  → `alembic upgrade head` → 选装种子数据（RBAC / 后台菜单与授权 / 成长体系 / 历史批次菜单）→ 按内置角色创建用户。
  支持 `--yes` 非交互、`--mode docker|init`、`--check` 仅自检、`--install-deps` 自动装依赖
- `scripts/create_user.py`：按角色创建用户并写入 `user_role_assignments`（内置 `superadmin` / `admin` / `editor` /
  `user`），
  支持 `--password-env`（避免密码出现在进程列表）、`--list-roles`、`--force`（重置密码并覆盖角色）

### 移除

- `sdk/`（Python 与 JavaScript SDK）：两者都指向已下线的 v2 API，已整体移除；调用 v3 请直接用 HTTP 客户端
  （开发环境可在 `/api/v3/docs` 交互查看）
- `install.sh` 与 `install.bat`：由跨平台的 `install.py` 取代（原有 `.env_example`、`/api/v1/health`、
  `%RANDOM%` 弱密钥等问题一并消除）

## [0.8.26.0921] - 2026-09-21

### 新增

- **云存储备份**：S3 / 阿里云 OSS 上传（`httpx` + 自实现 SigV4 单次 PUT，可离线验签），凭据加密存储，读接口只回 `has_secret`
- **增量 / 差异备份**：以表级 `xmin` 上界做变更检测；恢复走「基准全量 → 逐表 `TRUNCATE ... CASCADE` +
  `pg_restore --data-only --table=`」
- **进程监督**：`/api/v3/ops/supervisor/*`（进程登记、三层健康检查、受控启停、日志）
- **在线升级**：预检 → 快照 → 备份 → 执行 → 回滚的完整流程
- **CDN 远端操作**：阿里云 / 腾讯云 / CloudFront，签名与端点均可用 `settings.endpoint` 覆盖
- **数据迁移**：真实导入（WordPress WXR 等）
- **多平台内容发布**：`content/third_party_publish`（接有官方 API 的平台；无官方写接口的平台如实失败）
- **群聊消息**（`chat/message`，WebSocket 实时通道）与**关注流**（`mobile/feed`、`mobile/follow`）
- **VIP**：支付订单模型 + 前台自助开通
- **打赏与提现**（`commerce/tipping`、`commerce/revenue`）
- **用户成长**：积分、勋章、专家认证（`gamification/*`）
- **系统监控中心**（`system/monitor`：总览、在线会话、告警管理）
- **内容协作**（`content/collaboration`：Yjs 协同编辑 + WebSocket）
- **报表中心**（`analytics/report`）
- 页面构建器、内容审批、GDPR 同意记录、第三方集成、安全中心、社交账号管理
- 移动端媒体库与个人投稿

### 变更

- 媒体文件服务迁移到 v3：`/api/v3/content/media/{id}/file` 与受控的 `/api/v3/assets/storage/**`（校验目录遍历 + 私密媒体鉴权）
- RBAC 重构：菜单级授权（`admin_menus` + `role_admin_menus`）、权限用户组与数据范围；权限码统一为三段式
  `module_{域}:{模块}:{动作}`
- API v3 路由注册机制与统一响应结构 `{code, msg, data, pagination}` 落地
- 前端迁移为 Nuxt 4.5 单工程（前台 SSR + 后台 CSR），Element Plus 改为按需动态加载
- i18n 体系完善：locale 两语言对称校验、菜单动态 key 校验、文案可编译校验
- PWA 与前端打包结构优化

### 移除

- 独立进程监督器模块（能力整合进 `ops/supervisor`）
- OpenAPI 基线文档

## [0.7.26.0918] - 2026-09-18

### 新增

- 两个主题插件：`magazine`（杂志风）、`modern-minimal`（现代简约）
- 完整的 SEO 能力（sitemap、meta、结构化数据）

### 变更

- 权限控制系统重构，引入三重缓存机制
- 多个模块的数据统计与缓存实现优化
- CI：Node 20 → 22（适配前端构建）

### 测试

- 更新性能测试工具与数据库会话模拟

## 版本时间线

| 版本            | 日期         |
|---------------|------------|
| `0.8.26.0921` | 2026-09-21 |
| `0.7.26.0918` | 2026-09-18 |
| `0.7.26.0906` | 2026-09-06 |
| `0.7.26.0905` | 2026-09-06 |
| `0.7.26.0904` | 2026-09-04 |
| `0.6.26.0831` | 2026-08-31 |
| `0.6.26.0824` | 2026-08-24 |
| `0.6.26.0705` | 2026-07-05 |
| `0.5.26.0617` | 2026-06-17 |
| `0.5.26.0615` | 2026-06-15 |
| `0.5.26.0613` | 2026-06-13 |
| `0.5.26.0612` | 2026-06-12 |
| `0.4.26.0610` | 2026-06-10 |
| `0.4.26.0604` | 2026-06-04 |
| `0.3.26.0603` | 2026-06-03 |
| `0.3.26.0602` | 2026-06-03 |
| `0.3.26.0601` | 2026-06-01 |
| `0.3.26.0530` | 2026-05-30 |
| `0.3.26.0525` | 2026-05-25 |
| `0.3.26.0523` | 2026-05-23 |
| `0.3.26.0521` | 2026-05-21 |
| `0.3.26.0520` | 2026-05-20 |
| `0.2.26.0519` | 2026-05-19 |

`0.2` – `0.7.26.0906` 的逐条变更未在本文件维护，请按上文方式从 git 历史或 GitHub Releases 查询。
