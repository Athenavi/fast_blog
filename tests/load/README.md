# 负载/性能基准（k6）

针对 **API v3** 的 K6 脚本：`benchmark.js`。压测前请确认目标环境已装好数据（至少有一个管理员账号与若干文章）。

## 运行

```bash
# 默认直连后端
k6 run tests/load/benchmark.js

# 指定地址与账号
BASE_URL=http://localhost:9421 ADMIN_USER=admin ADMIN_PASS=secret k6 run tests/load/benchmark.js

# 压 nginx 入口（注意下方限流说明）
BASE_URL=http://localhost:4321 k6 run tests/load/benchmark.js
```

> 默认 `BASE_URL` 是后端直连地址 `http://localhost:9421`。走 nginx（`:4321`）时要注意配置里的限流：
> `/api/` 为 30r/s、登录为 5r/m、其余 50r/s（`nginx/conf.d/fastblog.conf`），高并发下出现 429/503 是限流生效而非应用错误。

## 场景

| # | 场景        | 请求                                                                                                             |
|---|-----------|----------------------------------------------------------------------------------------------------------------|
| 0 | 登录（每次迭代）  | `POST /api/v3/system/auth/login`（`{username, password}`，从 `data.access_token` 或 `access_token` cookie 取 token） |
| 1 | 权限校验（最频繁） | `POST /api/v3/system/permission/check`（`{codes: ["module_content:article:view"]}`）                             |
| 2 | 用户列表      | `GET /api/v3/system/user?page=1&page_size=10`                                                                  |
| 3 | 文章列表      | `GET /api/v3/content/article?page=1&page_size=10`                                                              |
| 4 | 仪表盘统计     | `GET /api/v3/analytics/dashboard/overview`                                                                     |
| 5 | 角色列表      | `GET /api/v3/system/role?page=1&page_size=10`                                                                  |
| 6 | 缓存统计      | `GET /api/v3/system/cache/stats`                                                                               |

响应判定遵循 v3 约定：HTTP 200 **且** 响应体 `code === 200` 才算成功（`{code, msg, data, pagination}`）。

## 指标与负载

- 自定义指标：`perm_check_ms`（权限校验耗时）、`errors`（失败率）
- 阈值：`http_req_duration: p(95) < 500ms`、`errors: rate < 0.05`
- 负载曲线：预热 30s（5 VU）→ 爬升 30s（20 VU）→ 稳定 1m（50 VU）→ 高峰 30s（100 VU）

## 注意

- 压测请针对**专用测试环境**；脚本只做读操作与登录，但要避免在真实生产库上跑高并发登录（会触发防爆破与账号锁定）。
- 若在压测中出现登录失败，先确认账号密码、`ENVIRONMENT` 与 Redis 是否可用（限流/防爆破依赖 Redis）。
