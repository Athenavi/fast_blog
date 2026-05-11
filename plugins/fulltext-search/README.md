# 全文搜索引擎插件

基于 Meilisearch 的高性能全文搜索引擎，为 FastBlog 提供毫秒级的搜索体验。

## 功能特性

- ✅ **高性能搜索**: 基于 Meilisearch，搜索响应时间 < 100ms
- ✅ **全文搜索**: 支持标题、内容、摘要的全文检索
- ✅ **拼音搜索**: 支持中文拼音搜索（需配置）
- ✅ **模糊匹配**: 自动纠错和容错搜索
- ✅ **结果高亮**: 搜索结果关键词高亮显示
- ✅ **高级过滤**: 按分类、作者、日期范围过滤
- ✅ **自动同步**: 文章发布/更新时自动同步索引
- ✅ **搜索建议**: 实时搜索自动完成
- ✅ **搜索统计**: 热门搜索、搜索历史分析

## 安装步骤

### 1. 安装 Meilisearch 服务器

#### Docker 方式（推荐）

```bash
docker run -d \
  --name meilisearch \
  -p 7700:7700 \
  -v $(pwd)/meili_data:/meili_data \
  getmeili/meilisearch:latest
```

#### Linux/macOS 直接安装

```bash
curl -L https://install.meilisearch.com | sh
./meilisearch
```

#### Windows 安装

从 [Meilisearch Releases](https://github.com/meilisearch/meilisearch/releases) 下载最新版本并解压运行。

### 2. 安装 Python 依赖

```bash
pip install meilisearch-python-sdk
```

或者在项目根目录执行：

```bash
pip install -r requirements.txt
```

### 3. 激活插件

1. 进入后台管理 → 插件市场
2. 找到"全文搜索引擎"插件
3. 点击"激活"

### 4. 配置插件

在插件设置页面配置：

- **Meilisearch 服务器地址**: `http://localhost:7700` (默认)
- **API 密钥**: 可选，如果设置了认证
- **启用自动同步**: 建议开启
- **发布时索引**: 建议开启

### 5. 重建索引（首次使用）

如果是首次使用或已有大量文章，需要重建索引：

```bash
# 方法1: 通过 API
curl -X POST http://localhost:8000/api/v1/search/rebuild-index \
  -H "Authorization: Bearer YOUR_TOKEN"

# 方法2: 通过后台管理
进入后台 → 插件 → 全文搜索引擎 → 重建索引
```

## 使用方法

### 前端搜索

用户可以在网站顶部的搜索框进行搜索，系统会自动使用 Meilisearch 进行搜索。

### API 调用

#### 搜索文章

```bash
GET /api/v1/search/articles?q=关键词&page=1&per_page=20
```

参数：

- `q`: 搜索关键词（必填）
- `category_id`: 分类ID过滤
- `author_id`: 作者ID过滤
- `date_from`: 起始日期 (YYYY-MM-DD)
- `date_to`: 结束日期 (YYYY-MM-DD)
- `status`: 文章状态 (published/draft)
- `page`: 页码
- `per_page`: 每页数量
- `sort_by`: 排序方式 (relevance/date/views)

#### 获取搜索建议

```bash
GET /api/v1/search/suggestions?q=关键
```

返回基于前缀的搜索建议列表。

#### 手动同步文章

```bash
POST /api/v1/search/sync-article/{article_id}
```

手动将指定文章同步到搜索索引。

#### 获取索引统计

```bash
GET /api/v1/search/stats
```

返回索引中的文章数量、索引大小等统计信息。

## 性能优化

### 1. 调整 Meilisearch 配置

编辑 Meilisearch 配置文件，根据服务器资源调整：

```bash
# 限制内存使用
MEILI_MAX_INDEXING_MEMORY=2GB

# 限制CPU使用
MEILI_MAX_INDEXING_THREADS=2
```

### 2. 增量索引

插件会自动检测文章内容变化，只更新有变化的文章，避免全量重建。

### 3. 缓存策略

搜索结果可以配合 Redis 缓存，进一步减少搜索延迟。

## 故障排查

### 问题1: 连接失败

**症状**: 无法连接到 Meilisearch 服务器

**解决**:

1. 检查 Meilisearch 是否运行: `docker ps | grep meilisearch`
2. 检查端口是否正确: `http://localhost:7700`
3. 检查防火墙设置

### 问题2: 搜索无结果

**症状**: 搜索返回空结果

**解决**:

1. 检查索引是否已建立: `GET /api/v1/search/stats`
2. 如果没有数据，执行重建索引
3. 检查文章状态是否为"已发布"

### 问题3: 索引不同步

**症状**: 新发布的文章搜不到

**解决**:

1. 检查插件是否激活
2. 检查"自动同步"设置是否开启
3. 手动同步: `POST /api/v1/search/sync-article/{id}`

## 高级配置

### 启用拼音搜索

Meilisearch 本身不支持拼音搜索，需要额外配置：

1. 安装拼音转换库:

```bash
pip install pypinyin
```

2. 在索引数据中添加拼音字段（需修改插件代码）

### 自定义分词

对于中文搜索，可以配置自定义分词器以提高准确度。

## 技术架构

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   FastBlog  │─────▶│  Plugin Hook │─────▶│ Meilisearch │
│   Article   │      │   System     │      │   Server    │
└─────────────┘      └──────────────┘      └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Search Index │
                    │   Status DB  │
                    └──────────────┘
```

## 开发指南

### 扩展搜索功能

可以通过钩子系统扩展搜索功能：

```python
from shared.services.plugin_manager import plugin_hooks

# 在搜索前处理关键词
plugin_hooks.add_filter('pre_search_query', my_keyword_processor)

# 在搜索后处理结果
plugin_hooks.add_filter('post_search_results', my_result_enhancer)
```

### 自定义索引字段

修改 `plugin.py` 中的 `_prepare_article_data` 方法，添加需要索引的字段。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v1.0.0 (2026-05-09)

- ✨ 初始版本发布
- ✅ 基础搜索功能
- ✅ 自动索引同步
- ✅ 搜索结果高亮
- ✅ 搜索建议
- ✅ 批量索引重建
