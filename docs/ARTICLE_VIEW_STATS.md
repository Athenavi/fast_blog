# 文章阅读统计优化指南

## 📋 概述

FastBlog 实现了高性能的文章阅读统计系统，使用 Redis 缓存计数、防刷机制和异步批量同步，显著降低数据库压力。

**核心特性**:

- ✅ Redis 缓存计数（减少数据库写入）
- ✅ 防刷机制（5分钟内同一用户/IP只计一次）
- ✅ 异步批量同步（每5分钟自动同步到数据库）
- ✅ 实时查询支持
- ✅ 热门文章排行
- ✅ 管理员手动同步功能

---

## 🏗️ 架构设计

### 工作流程

```
用户访问文章
    ↓
检查防刷记录 (Redis)
    ↓
如果未过期 → 跳过计数
如果已过期 → 继续
    ↓
增加 Redis 计数
    ↓
设置防刷记录 (5分钟过期)
    ↓
定时任务 (每5分钟)
    ↓
批量同步到数据库
    ↓
清空 Redis 计数
```

### 数据结构

**Redis Keys**:

- `article:view_count:{article_id}` - 阅读计数
- `article:view_record:{article_id}:{user:ID|ip:IP}` - 防刷记录

---

## 🚀 API 使用

### 1. 记录文章阅读

**Endpoint**: `POST /api/v1/article-stats/view/{article_id}`

**说明**: 每次用户访问文章时调用此接口

**Response**:

```json
{
  "success": true,
  "recorded": true,
  "message": "View recorded"
}
```

**注意**:

- 如果返回 `"recorded": false`，表示被防刷机制拦截
- 同一用户/IP 在 5 分钟内多次访问只计一次

### 2. 获取文章阅读量

**Endpoint**: `GET /api/v1/article-stats/view/{article_id}`

**Response**:

```json
{
  "success": true,
  "data": {
    "article_id": 123,
    "views": 1580
  }
}
```

### 3. 获取热门文章

**Endpoint**: `GET /api/v1/article-stats/top-articles?limit=10`

**Response**:

```json
{
  "success": true,
  "data": [
    {"article_id": 123, "views": 1580},
    {"article_id": 456, "views": 1200},
    ...
  ]
}
```

### 4. 手动同步（管理员）

**单篇文章同步**:

```bash
POST /api/v1/article-stats/sync/{article_id}
```

**批量同步所有文章**:

```bash
POST /api/v1/article-stats/sync-all
```

**Response**:

```json
{
  "success": true,
  "data": {
    "synced": 50,
    "errors": []
  },
  "message": "Synced 50 articles"
}
```

### 5. 重置阅读计数（管理员）

**Endpoint**: `DELETE /api/v1/article-stats/reset/{article_id}`

**Response**:

```json
{
  "success": true,
  "message": "Article 123 view count reset"
}
```

---

## ⚙️ 配置说明

### 防刷时间窗口

默认 5 分钟，可在代码中修改：

```python
# shared/services/article_view_stats.py
self.ANTI_SPAM_WINDOW = 300  # 秒
```

### 同步间隔

默认 5 分钟，可在调度器中修改：

```python
# src/scheduler.py
self.scheduler.add_job(
    sync_article_views_job,
    trigger=IntervalTrigger(minutes=5),  # 修改此处
    ...
)
```

---

## 💡 前端集成示例

### React/Next.js 示例

```tsx
import { useEffect } from 'react';

function ArticlePage({ articleId }) {
  useEffect(() => {
    // 记录阅读
    fetch(`/api/v1/article-stats/view/${articleId}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getToken()}`,
      },
    });
  }, [articleId]);

  return <div>文章内容...</div>;
}
```

### 显示阅读量

```tsx
async function getArticleViews(articleId: number) {
  const response = await fetch(`/api/v1/article-stats/view/${articleId}`);
  const data = await response.json();
  return data.data.views;
}

// 使用
const views = await getArticleViews(articleId);
console.log(`阅读量: ${views}`);
```

---

## 📊 性能优势

### 传统方式 vs 优化后

| 指标        | 传统方式 | 优化后    | 提升   |
|-----------|------|--------|------|
| 每次访问数据库写入 | 1次   | 0次     | 100% |
| 数据库写入频率   | 每次访问 | 每5分钟批量 | ~99% |
| 防刷能力      | 无    | 有      | -    |
| 并发支持      | 低    | 高      | 10x+ |

### 实际场景

假设某文章每小时有 1000 次阅读：

**传统方式**:

- 数据库写入: 1000 次/小时
- 数据库负载: 高

**优化后**:

- 数据库写入: 12 次/小时（每5分钟1次）
- 数据库负载: 极低
- 减少: 98.8%

---

## 🔍 监控与维护

### 查看 Redis 计数

```bash
# 连接 Redis
redis-cli

# 查看所有文章阅读计数
KEYS article:view_count:*

# 查看特定文章计数
GET article:view_count:123

# 查看防刷记录
KEYS article:view_record:123:*
```

### 手动触发同步

```bash
# 通过 API
curl -X POST "http://localhost:9421/api/v1/article-stats/sync-all" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 日志查看

```bash
# 查看同步日志
tail -f logs/app.log | grep "成功同步"
```

---

## ⚠️ 注意事项

### 1. 数据一致性

- Redis 计数和数据库可能存在短暂不一致（最多5分钟）
- 如需实时准确数据，手动触发同步

### 2. 防刷机制

- 基于用户ID或IP地址
- 5分钟窗口内只计一次
- 清除浏览器 Cookie 无法绕过（仍会记录IP）

### 3. Redis 依赖

- 需要 Redis 服务运行
- 如 Redis 不可用，阅读计数将失效
- 建议配置 Redis 持久化

### 4. 内存管理

- Redis key 会自动过期（防刷记录5分钟）
- 阅读计数在同步后自动清空
- 无需手动清理

---

## 🎯 最佳实践

### 1. 前端调用时机

```tsx
// ✅ 好的做法：页面加载完成后调用
useEffect(() => {
  recordView();
}, []);

// ❌ 不好的做法：每次渲染都调用
recordView(); // 会在每次 state 变化时调用
```

### 2. 错误处理

```tsx
try {
  await recordView(articleId);
} catch (error) {
  console.error('记录阅读失败:', error);
  // 不影响用户体验，静默失败
}
```

### 3. 定期同步

- 保持默认的 5 分钟同步间隔
- 高流量站点可缩短至 1-2 分钟
- 低流量站点可延长至 10-15 分钟

---

## 🔧 故障排除

### 问题 1: 阅读量不增加

**检查**:

1. Redis 是否正常运行
2. API 是否正确调用
3. 是否在防刷时间窗口内

**解决**:

```bash
# 检查 Redis
redis-cli ping

# 查看计数
redis-cli GET article:view_count:123
```

### 问题 2: 同步失败

**检查日志**:

```bash
tail -f logs/app.log | grep "同步错误"
```

**手动同步**:

```bash
curl -X POST "http://localhost:9421/api/v1/article-stats/sync-all" \
  -H "Authorization: Bearer TOKEN"
```

### 问题 3: Redis 内存占用过高

**检查**:

```bash
redis-cli INFO memory
```

**清理**:

```bash
# 清理过期的防刷记录（应该自动过期）
redis-cli KEYS "article:view_record:*" | xargs redis-cli DEL
```

---

## 📈 扩展功能

### 未来计划

- [ ] 阅读时长统计
- [ ] 阅读来源分析
- [ ] 实时阅读人数
- [ ] 阅读热力图
- [ ] 导出统计数据

---

**维护者**: FastBlog Core Team  
**最后更新**: 2026-05-01  
**版本**: 1.0.0
