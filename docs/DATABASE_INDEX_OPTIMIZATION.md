# 数据库索引优化指南

## 概述

FastBlog 已针对常见查询场景进行了全面的数据库索引优化，以提升查询性能和用户体验。

## 索引优化策略

### 1. 唯一性约束索引

确保数据完整性的同时提供快速查找：

- `idx_users_username` - 用户名唯一索引
- `idx_users_email` - 邮箱唯一索引
- `idx_articles_slug` - 文章 slug 唯一索引
- `idx_categories_slug` - 分类 slug 唯一索引
- `idx_media_hash` - 文件哈希唯一索引（去重）

### 2. 外键索引

加速关联查询：

- `idx_articles_user_id` - 文章作者查询
- `idx_articles_category` - 分类文章查询
- `idx_comments_article_id` - 文章评论查询
- `idx_comments_user_id` - 用户评论查询
- `idx_media_user` - 用户媒体查询
- `idx_media_folder` - 文件夹媒体查询

### 3. 复合索引

针对常用查询组合优化：

#### Article 模型

```sql
-- 最新文章列表
idx_articles_status_created (status, created_at DESC)

-- 分类文章列表
idx_articles_category_status_created (category, status, created_at DESC)

-- 用户文章列表
idx_articles_user_status_created (user, status, created_at DESC)

-- 推荐文章
idx_articles_status_featured (status, is_featured)

-- 热门文章
idx_articles_status_views (status, views DESC)

-- 按类型和状态查询
idx_articles_post_type_status (post_type, status)
```

#### Comment 模型

```sql
-- 文章评论列表（最常用）
idx_comments_article_approved_created (article_id, is_approved, created_at DESC)

-- 用户评论历史
idx_comments_user_created (user_id, created_at DESC)
```

### 4. 排序索引

优化 ORDER BY 查询：

- `idx_articles_created_at DESC` - 文章时间排序
- `idx_comments_created_at DESC` - 评论时间排序
- `idx_users_date_joined DESC` - 用户注册时间排序
- `idx_users_last_login_at DESC` - 最后登录时间排序
- `idx_media_created_at DESC` - 媒体创建时间排序

### 5. 状态过滤索引

加速 WHERE 条件查询：

- `idx_articles_status` - 文章状态过滤
- `idx_articles_is_sticky` - 置顶文章过滤
- `idx_comments_is_approved` - 评论审核状态
- `idx_users_is_active` - 用户激活状态
- `idx_users_is_superuser` - 管理员查询
- `idx_media_is_public` - 媒体公开状态
- `idx_categories_is_visible` - 分类可见性

### 6. 特殊用途索引

#### VIP 相关

- `idx_users_vip_level` - VIP 等级查询

#### 垃圾检测

- `idx_comments_spam_score` - 垃圾评分查询

#### 订阅通知

- `idx_comments_email` - 邮箱查询（用于订阅通知）

#### 层级结构

- `idx_categories_parent` - 父分类查询（用于层级遍历）
- `idx_comments_parent_id` - 父评论查询（用于回复链）

#### 排序

- `idx_categories_sort_order` - 分类排序
- `idx_articles_sticky_until` - 置顶过期时间

## 性能提升预期

### 查询性能对比

| 查询类型          | 优化前   | 优化后  | 提升  |
|---------------|-------|------|-----|
| 最新文章列表        | ~50ms | ~5ms | 10x |
| 分类文章查询        | ~80ms | ~8ms | 10x |
| 文章详情（by slug） | ~30ms | ~2ms | 15x |
| 用户文章列表        | ~60ms | ~6ms | 10x |
| 文章评论列表        | ~40ms | ~4ms | 10x |
| 热门推荐文章        | ~70ms | ~7ms | 10x |

### 索引大小估算

假设数据量：

- Articles: 10,000 条
- Comments: 50,000 条
- Users: 5,000 条
- Media: 20,000 条

总索引大小：约 50-100 MB（取决于具体字段长度）

## 索引维护建议

### 1. 定期分析

```sql
-- PostgreSQL
ANALYZE articles;
ANALYZE comments;
ANALYZE users;

-- MySQL
ANALYZE TABLE articles;
ANALYZE TABLE comments;
ANALYZE TABLE users;
```

### 2. 监控未使用的索引

```sql
-- PostgreSQL
SELECT
    schemaname,
    relname AS table_name,
    indexrelname AS index_name,
    idx_scan AS times_used,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;

-- MySQL
SELECT
    table_schema,
    table_name,
    index_name,
    stat_value AS pages_used
FROM mysql.innodb_index_stats
WHERE stat_name = 'size'
AND stat_value = 0;
```

### 3. 重建碎片化索引

```sql
-- PostgreSQL
REINDEX INDEX idx_articles_status_created;

-- MySQL
ALTER TABLE articles FORCE;
```

## 查询优化最佳实践

### ✅ 正确使用索引

```python
# ✅ 利用复合索引
articles = await session.execute(
    select(Article)
    .where(Article.status == 1)
    .order_by(Article.created_at.desc())
    .limit(20)
)

# ✅ 使用覆盖索引
articles = await session.execute(
    select(Article.id, Article.title, Article.slug)
    .where(Article.status == 1)
    .where(Article.category == category_id)
    .order_by(Article.created_at.desc())
)
```

### ❌ 避免索引失效

```python
# ❌ 函数调用导致索引失效
articles = await session.execute(
    select(Article)
    .where(func.lower(Article.title) == "hello")  # 无法使用索引
)

# ❌ 类型转换导致索引失效
articles = await session.execute(
    select(Article)
    .where(cast(Article.id, String) == "123")  # 无法使用索引
)

# ❌ LIKE 前缀通配符
articles = await session.execute(
    select(Article)
    .where(Article.title.like("%keyword%"))  # 无法使用索引
)
```

## 索引添加流程

### 1. 在 models.yaml 中定义

```yaml
Article:
  table: articles
  indexes:
    - name: idx_articles_custom
      columns: [status, created_at]
      order: DESC
      comment: "自定义索引"
```

### 2. 生成迁移文件

```bash
# 使用 Alembic 自动生成迁移
alembic revision --autogenerate -m "Add custom index"
```

### 3. 审查迁移文件

检查生成的迁移脚本，确保索引定义正确。

### 4. 执行迁移

```bash
alembic upgrade head
```

### 5. 验证索引

```sql
-- PostgreSQL
SELECT * FROM pg_indexes WHERE tablename = 'articles';

-- MySQL
SHOW INDEX FROM articles;
```

## 常见问题

### Q1: 索引越多越好吗？

**不是**。索引会带来以下成本：

- 存储空间增加
- INSERT/UPDATE/DELETE 操作变慢（需要更新索引）
- 维护成本增加

**建议**：只为频繁查询的字段创建索引。

### Q2: 如何判断是否需要索引？

通过以下指标判断：

1. 查询频率高
2. 查询速度慢（> 50ms）
3. EXPLAIN 显示全表扫描
4. 返回结果集小（选择性高）

### Q3: 复合索引的顺序重要吗？

**非常重要**。遵循以下原则：

1. 等值查询字段在前
2. 范围查询字段在后
3. 选择性高的字段在前

示例：

```sql
-- ✅ 好的顺序
(status, created_at DESC)  -- status 是等值，created_at 是范围

-- ❌ 差的顺序
(created_at DESC, status)  -- 范围查询在前，等值在后
```

### Q4: 如何处理大表索引？

对于大表（> 100万行）：

1. 使用 CONCURRENTLY 创建索引（PostgreSQL）
2. 在低峰期执行
3. 分批创建，避免锁表时间过长

```sql
-- PostgreSQL
CREATE INDEX CONCURRENTLY idx_large_table_column
ON large_table (column);
```

### Q5: 索引会影响写入性能吗？

会。每个索引都会：

- 增加 INSERT 时间约 5-10%
- 增加 UPDATE 时间（如果更新索引字段）
- 增加 DELETE 时间约 5-10%

**权衡**：读多写少的表可以多加索引，写多读少的表要谨慎。

## 监控工具

### 1. PostgreSQL

```sql
-- 查看索引使用情况
SELECT
    relname AS table_name,
    indexrelname AS index_name,
    idx_scan AS times_used,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- 查看慢查询
SELECT
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 20;
```

### 2. MySQL

```sql
-- 查看索引使用情况
SHOW INDEX FROM articles;

-- 查看慢查询日志
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;

-- 使用 EXPLAIN 分析查询
EXPLAIN SELECT * FROM articles WHERE status = 1 ORDER BY created_at DESC;
```

## 未来优化方向

- [ ] 部分索引（Partial Indexes）
- [ ] 表达式索引（Expression Indexes）
- [ ] GIN 索引（全文搜索）
- [ ] BRIN 索引（大数据块范围索引）
- [ ] 自动索引推荐系统

---

**维护者**: FastBlog Core Team  
**最后更新**: 2026-05-01
