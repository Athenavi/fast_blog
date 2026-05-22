# 路由和静态资源路径迁移指南

## 概述

本文档记录了FastBlog系统中路由配置和静态资源路径的重要改进，旨在解决以下问题：

1. **全局catch-all路由拦截风险** - 确保API路由优先匹配
2. **示例/工具端点分散** - 集中管理所有示例端点
3. **静态资源路径未隔离** - 统一静态资源路径前缀，避免与业务路由冲突

## 主要更改

### 1. Catch-all路由修复

#### 问题

之前的SPA回退路由可能会拦截API请求，导致接口不可用。

#### 解决方案

- 优化了SPA回退逻辑，明确排除API、静态资源和系统路径
- 确保catch-all路由只在没有其他路由匹配时生效
- 改进了路径排除逻辑，使用更精确的前缀匹配

**修改文件**: `src/app.py`

```python
# 之前: 简单的字符串匹配，可能遗漏某些路径
excluded = ['api', 'static', 'local-storage', ...]

# 现在: 精确的前缀匹配，确保所有API和静态路径都被排除
excluded_prefixes = [
    'api/',           # 所有API路径
    'static/',        # 静态文件
    'assets/',        # 资源文件（包括storage和themes）
    'docs',           # API文档
    'redoc',          # ReDoc文档
    'openapi.json',   # OpenAPI规范
    'health',         # 健康检查
]
```

### 2. 静态资源路径统一

#### 问题

静态资源路径如 `/local-storage`, `/storage/objects`, `/themes` 没有统一前缀，容易与业务路由冲突。

#### 解决方案

将所有静态资源路径统一移到 `/assets/` 前缀下：

| 原路径                | 新路径                       | 说明           |
|--------------------|---------------------------|--------------|
| `/local-storage`   | `/assets/storage`         | 本地存储根目录      |
| `/storage/objects` | `/assets/storage/objects` | 对象存储目录       |
| `/themes`          | `/assets/themes`          | 主题文件目录       |
| `/static`          | `/static`                 | 保持不变（标准静态文件） |

**修改文件**:

- `src/app.py` - 静态文件挂载点
- `src/api/v1/media/routes_edit.py` - 媒体文件URL生成
- `shared/services/ai/core_skills.py` - AI服务中的主题预览URL

#### 迁移步骤

1. **更新前端引用**
   ```javascript
   // 之前
   const imageUrl = '/local-storage/images/photo.jpg';
   const themeUrl = '/themes/default/style.css';
   
   // 现在
   const imageUrl = '/assets/storage/images/photo.jpg';
   const themeUrl = '/assets/themes/default/style.css';
   ```

2. **更新数据库中的硬编码URL**（如果存在）
   ```sql
   -- 查找需要更新的记录
   SELECT * FROM articles WHERE content LIKE '%/local-storage/%';
   SELECT * FROM articles WHERE content LIKE '%/themes/%';
   
   -- 更新记录（谨慎操作，先备份）
   UPDATE articles SET content = REPLACE(content, '/local-storage/', '/assets/storage/');
   UPDATE articles SET content = REPLACE(content, '/themes/', '/assets/themes/');
   ```

3. **更新配置文件**
   检查并更新任何配置文件中的静态资源路径引用。

### 3. 示例端点集中管理

#### 问题

大量模块包含分散的 `/examples` 和 `/get_usage_examples` 端点，难以维护和管理。

#### 解决方案

创建统一的示例和工具端点模块，集中管理所有功能的使用示例。

**新增文件**: `src/api/v2/examples_tools/__init__.py`

**可用端点**:

- `GET /api/v2/examples/accessibility` - 无障碍性审计示例
- `GET /api/v2/examples/performance` - 性能优化示例
- `GET /api/v2/examples/security` - 安全功能示例
- `GET /api/v2/examples/seo` - SEO优化示例
- `GET /api/v2/examples/nlp` - 自然语言处理示例
- `GET /api/v2/examples/collaboration` - 协作功能示例
- `GET /api/v2/examples/all` - 所有示例汇总

**优势**:

- 统一的访问入口
- 更好的文档和维护
- 可以在生产环境中通过配置禁用
- 支持按功能模块分类访问

#### 迁移建议

对于仍然存在的旧版示例端点（在各V1模块中），建议：

1. **开发环境**: 保留旧端点以确保向后兼容
2. **生产环境**: 通过路由重定向将旧端点指向新的统一端点
3. **未来版本**: 逐步弃用并移除分散的示例端点

## 测试验证

### 1. API路由测试

```bash
# 测试API路由正常工作
curl http://localhost:9421/api/v2/home
curl http://localhost:9421/api/v2/articles

# 测试SPA回退不拦截API
curl http://localhost:9421/api/v2/nonexistent  # 应返回404 JSON
```

### 2. 静态资源测试

```bash
# 测试新的静态资源路径
curl http://localhost:9421/assets/storage/test.txt
curl http://localhost:9421/assets/themes/default/style.css
curl http://localhost:9421/static/logo.png

# 验证旧路径不再工作（应返回404）
curl http://localhost:9421/local-storage/test.txt  # 404
curl http://localhost:9421/themes/default/style.css  # 404
```

### 3. 示例端点测试

```bash
# 测试新的统一示例端点
curl http://localhost:9421/api/v2/examples/all
curl http://localhost:9421/api/v2/examples/performance
```

## 回滚方案

如果需要回滚这些更改：

1. **恢复静态资源路径**
   ```python
   # 在 src/app.py 中恢复旧的路径
   app.mount("/local-storage", StaticFiles(directory=local_storage), name="local-storage")
   app.mount("/storage/objects", StaticFiles(directory=objects_dir), name="storage-objects")
   app.mount("/themes", StaticFiles(directory=themes_dir), name="themes")
   ```

2. **恢复SPA回退逻辑**
   ```python
   # 恢复原来的排除列表
   excluded = ['api', 'static', 'local-storage', 'storage', ...]
   ```

3. **移除示例工具模块**
   ```python
   # 从 ROUTE_REGISTRY_V2 中移除
   # ("src.api.v2.examples_tools", "/api/v2/examples", ["examples-tools"], False),
   ```

## 注意事项

1. **缓存清理**: 路径更改后，请清理浏览器和CDN缓存
2. **SEO影响**: 如果有外部链接指向旧的静态资源路径，需要设置301重定向
3. **监控日志**: 密切关注404错误日志，发现未迁移的路径引用
4. **文档更新**: 确保API文档和使用指南中的路径已更新

## 后续改进建议

1. **添加路径重定向中间件**: 自动将旧路径重定向到新路径
2. **实现配置开关**: 允许通过配置启用/禁用示例端点
3. **添加路径验证**: 在部署时验证所有静态资源路径的正确性
4. **完善文档**: 在开发者文档中详细说明新的路径结构

## 相关文件和模块

### 核心修改

- `src/app.py` - 应用初始化和路由配置
- `src/api/v2/__init__.py` - V2路由注册表
- `src/api/v2/examples_tools/__init__.py` - 统一示例端点（新增）

### 引用更新

- `src/api/v1/media/routes_edit.py` - 媒体文件URL
- `shared/services/ai/core_skills.py` - AI服务URL

### 受影响的服务

- 媒体管理服务
- 主题管理系统
- 文件上传和存储
- 前端资源加载

---

**更新日期**: 2026-05-21  
**版本**: v2.0  
**作者**: FastBlog开发团队
