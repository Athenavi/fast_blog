# FastBlog API v2 迁移指南

## 概述

根据 TODO.md 中的建议，我们执行了"路由清零"行动，创建了规范的 API v2，同时通过自动重定向中间件保持 v1 的向后兼容性。

## 主要改进

### 1. 路径规范化

所有 v2 路径遵循以下原则：

- ✅ 使用 kebab-case 命名（如 `/api/v2/user-blocks`）
- ✅ 清晰的领域前缀（如 `/api/v2/seo/`, `/api/v2/cache/`）
- ✅ 避免通用路径冲突（不再有多个模块使用 `/stats`、`/config`）
- ✅ 资源层级清晰（如 `/api/v2/articles/{id}/revisions`）

### 2. 模块合并

以下重复模块已合并到统一入口：

| 功能领域   | v2 统一路径                  | 原 v1 模块                                                                                               |
|--------|--------------------------|-------------------------------------------------------------------------------------------------------|
| SEO 优化 | `/api/v2/seo/*`          | seo, seo_management, seo_optimization, breadcrumbs, hreflang_api, internal_links, redirect_management |
| 缓存管理   | `/api/v2/cache/*`        | cache_management, object_cache, page_cache                                                            |
| 备份管理   | `/api/v2/backup/*`       | backup_management, incremental_backup                                                                 |
| 性能监控   | `/api/v2/monitoring/*`   | performance_monitor, performance_tracking, query_monitor, slow_query_log                              |
| 广告管理   | `/api/v2/ads/*`          | advertisement_system (ad_management 已废弃)                                                              |
| 翻译服务   | `/api/v2/translations/*` | i18n, translation_io, translation_progress, translation_service, translations                         |

### 3. 自动重定向

v1 到 v2 的自动重定向中间件已启用：

- 所有 `/api/v1/*` 请求会自动重定向到对应的 `/api/v2/*` 路径
- 使用 301 永久重定向（SEO 友好）
- 保留查询参数和 HTTP 方法
- 记录重定向日志用于后续清理

## 常用路径映射示例

### 文章相关

```
V1: /api/v1/articles                  → V2: /api/v2/home/articles
V1: /api/v1/revisions                 → V2: /api/v2/articles/revisions
V1: /api/v1/{article_id}/access       → V2: /api/v2/articles/{article_id}/access-check
```

### 用户相关

```
V1: /api/v1/users/profile             → V2: /api/v2/users/me
V1: /api/v1/admin/user/me/profile     → V2: /api/v2/users/me
V1: /api/v1/profiles                  → V2: /api/v2/users/settings
```

### SEO 相关

```
V1: /api/v1/admin/seo                 → V2: /api/v2/seo/management
V1: /api/v1/breadcrumbs               → V2: /api/v2/seo/breadcrumbs
V1: /api/v1/redirect                  → V2: /api/v2/seo/redirects
```

### 缓存相关

```
V1: /api/v1/admin/caches              → V2: /api/v2/cache
V1: /api/v1/clear-all                 → V2: /api/v2/cache/clear-all
```

### GDPR 合规

```
V1: /api/v1/delete                    → V2: /api/v2/gdpr/data-deletion
V1: /api/v1/export                    → V2: /api/v2/gdpr/data-export
V1: /api/v1/rights                    → V2: /api/v2/gdpr/user-rights
```

## 完整的路径映射表

详见 `src/api/v2/__init__.py` 中的 `V1_TO_V2_REDIRECT_MAP`。

## 如何测试

### 1. 启动服务器

```bash
python main.py
```

### 2. 测试 v2 新路由

```bash
# 测试 v2 用户接口
curl http://localhost:9421/api/v2/users/me

# 测试 v2 SEO 接口
curl http://localhost:9421/api/v2/seo

# 测试 v2 缓存接口
curl http://localhost:9421/api/v2/cache
```

### 3. 测试 v1 自动重定向

```bash
# 这个请求会自动重定向到 v2
curl -v http://localhost:9421/api/v1/delete

# 查看响应头中的重定向信息
# X-Redirect-From: /api/v1/delete
# X-Redirect-To: /api/v2/gdpr/data-deletion
# X-API-Version-Migration: v1-to-v2
```

### 4. 查看重定向统计

在服务器日志中可以看到重定向计数：

```
[V1->V2 Redirect #1] GET /api/v1/delete -> /api/v2/gdpr/data-deletion
[V1->V2 Redirect #2] POST /api/v1/export?format=json -> /api/v2/gdpr/data-export?format=json
```

## 开发者注意事项

### 1. 新功能开发

**强烈建议**所有新功能直接使用 v2 路径规范：

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/v2/your-module", tags=["your-module"])

@router.get("/items")
async def get_items():
    return {"items": []}
```

### 2. 旧代码迁移

逐步将现有代码从 v1 迁移到 v2：

```python
# 旧代码（v1）
@router.post("/delete")
async def delete_data():
    ...

# 新代码（v2）
@router.delete("/data")  # 使用正确的 HTTP 方法
async def delete_data():
    ...
```

### 3. 前端调用更新

前端代码应逐步更新为使用 v2 API：

```javascript
// 旧代码
fetch('/api/v1/delete', {method: 'POST'})

// 新代码
fetch('/api/v2/gdpr/data-deletion', {method: 'DELETE'})
```

## 重定向中间件配置

可以在 `src/app.py` 中配置重定向行为：

```python
# V1 到 V2 重定向中间件
from src.middleware.v1_to_v2_redirect import create_v1_to_v2_middleware

# 参数说明：
# - redirect_type: 301 (永久) 或 302 (临时)
# - enable_logging: 是否记录重定向日志
create_v1_to_v2_middleware(app, redirect_type=301, enable_logging=True)
```

## 清理计划

随着时间推移，可以逐步废弃 v1 路由：

1. **阶段 1**（当前）：v1 和 v2 并存，v1 自动重定向到 v2
2. **阶段 2**（3个月后）：在文档中标记 v1 为 deprecated
3. **阶段 3**（6个月后）：移除 v1 路由，仅保留重定向提示
4. **阶段 4**（12个月后）：完全移除 v1 支持

## 常见问题

### Q: v1 路由还能用吗？

A: 是的，v1 路由仍然可用，但会自动重定向到 v2。建议在方便时更新为 v2。

### Q: 重定向会影响性能吗？

A: 301 重定向会被浏览器和 CDN 缓存，实际影响很小。长期来看，直接调用 v2 更好。

### Q: 如何禁用重定向？

A: 在 `src/app.py` 中注释掉重定向中间件的注册代码即可。

### Q: 我的自定义 v1 路由会重定向吗？

A: 只有配置在 `V1_TO_V2_REDIRECT_MAP` 中的路径会重定向。未配置的路径会继续按原样工作。

## 相关文件

- `src/api/v2/__init__.py` - v2 路由注册表和映射表
- `src/middleware/v1_to_v2_redirect.py` - 重定向中间件实现
- `src/app.py` - 应用入口，注册 v2 路由和中间件
- `scripts/check_route_conflicts.py` - 路由冲突检测工具
- `debug/route_conflict_report.md` - 冲突检测报告

## 总结

通过这次"路由清零"行动，我们：

- ✅ 创建了规范的 v2 API 路径体系
- ✅ 解决了所有已知的路径冲突问题
- ✅ 实现了平滑的向后兼容过渡
- ✅ 统一了资源命名风格
- ✅ 合并了重复的模块功能

这将为未来的维护和扩展奠定坚实基础。
