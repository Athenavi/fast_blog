"""
k6 性能基准测试 — 运行方式:

  # 安装 k6: https://k6.io/docs/get-started/installation/
  # 启动应用: uvicorn src.app:app --port 8000

  # 基本运行
  k6 run tests/load/benchmark.js

  # 自定义 URL 和用户
  BASE_URL=http://my-server.com ADMIN_USER=admin ADMIN_PASS=secret \\
    k6 run tests/load/benchmark.js

  # 输出 HTML 报告
  k6 run tests/load/benchmark.js --out json=results.json

测试场景:
  1. 权限检查 (POST /api/v3/admin/check-permission)
  2. 用户列表 (GET /api/v3/admin/users)
  3. 文章列表 (GET /api/v3/admin/articles)
  4. 仪表盘统计 (GET /api/v3/admin/dashboard/stats)
  5. 角色列表 (GET /api/v3/admin/roles)
  6. 缓存统计 (GET /api/v3/admin/cache-stats)

指标:
  - perm_check_ms: 权限检查响应时间 (p95 < 500ms)
  - errors: 错误率 (< 5%)
  - http_req_duration: 所有请求响应时间

负载配置:
  预热 30s (5并发) → 爬升 30s (20并发) → 稳定 1m (50并发) → 高峰 30s (100并发)
"""
