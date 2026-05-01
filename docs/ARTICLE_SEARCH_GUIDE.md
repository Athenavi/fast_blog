# 文章搜索优化指南

## 📋 概述

FastBlog 实现了高性能的文章搜索系统，支持全文搜索、结果高亮、高级过滤和搜索建议。

**核心功能**:

- ✅ 全文搜索（标题、摘要、内容）
- ✅ 搜索结果高亮显示
- ✅ 高级过滤（分类、作者、日期）
- ✅ 搜索建议（自动完成）
- ✅ 热门搜索统计
- ✅ 搜索历史记录
- ✅ 多种排序方式

---

## 🚀 API 使用

### 1. 搜索文章

**Endpoint**: `GET /api/v1/search/articles`

**Query Parameters**:

- `q` (必需): 搜索关键词
- `category_id`: 分类ID过滤
- `author_id`: 作者ID过滤
- `date_from`: 起始日期 (YYYY-MM-DD)
- `date_to`: 结束日期 (YYYY-MM-DD)
- `status`: 文章状态 (默认: published)
- `page`: 页码 (默认: 1)
- `per_page`: 每页数量 (默认: 20, 最大: 100)
- `sort_by`: 排序方式 (relevance, date, views)

**Response**:

```json
{
  "success": true,
  "data": {
    "articles": [
      {
        "id": 1,
        "title": "文章标题",
        "highlighted_title": "文章<mark>标题</mark>",
        "excerpt": "文章摘要...",
        "highlighted_excerpt": "文章<mark>摘要</mark>...",
        "views": 100,
        "likes": 10,
        "created_at": "2026-05-01T10:00:00"
      }
    ],
    "total": 50,
    "page": 1,
    "per_page": 20,
    "total_pages": 3,
    "query": "关键词"
  }
}
```

**示例**:

```bash
# 基本搜索
curl "http://localhost:9421/api/v1/search/articles?q=Python"

# 带过滤的搜索
curl "http://localhost:9421/api/v1/search/articles?q=Python&category_id=1&sort_by=date"

# 日期范围搜索
curl "http://localhost:9421/api/v1/search/articles?q=教程&date_from=2026-01-01&date_to=2026-12-31"
```

### 2. 获取搜索建议

**Endpoint**: `GET /api/v1/search/suggestions`

**Query Parameters**:

- `q` (必需): 搜索前缀
- `limit`: 返回数量 (默认: 5, 最大: 10)

**Response**:

```json
{
  "success": true,
  "data": {
    "query": "py",
    "suggestions": [
      "Python 入门教程",
      "Python 高级技巧",
      "PyTorch 深度学习"
    ]
  }
}
```

**示例**:

```bash
curl "http://localhost:9421/api/v1/search/suggestions?q=py&limit=5"
```

### 3. 获取热门搜索

**Endpoint**: `GET /api/v1/search/popular`

**Query Parameters**:

- `days`: 统计天数 (默认: 7, 最大: 30)
- `limit`: 返回数量 (默认: 10, 最大: 20)

**Response**:

```json
{
  "success": true,
  "data": [
    {
      "query": "Python",
      "count": 150
    },
    {
      "query": "React",
      "count": 120
    },
    {
      "query": "Docker",
      "count": 95
    }
  ]
}
```

**示例**:

```bash
curl "http://localhost:9421/api/v1/search/popular?days=7&limit=10"
```

### 4. 清理搜索历史

**Endpoint**: `POST /api/v1/search/history/clear`

**Headers**:

```
Authorization: Bearer YOUR_TOKEN
```

**Query Parameters**:

- `days`: 清理多少天前的记录 (默认: 30)

**Response**:

```json
{
  "success": true,
  "message": "已清理 30 天前的搜索历史"
}
```

---

## 💻 前端集成示例

### React/Next.js 示例

#### 1. 搜索组件

```tsx
import {useState, useEffect} from 'react';
import {useDebounce} from 'use-debounce';

interface SearchResult {
    id: number;
    title: string;
    highlighted_title: string;
    excerpt: string;
    highlighted_excerpt: string;
    views: number;
    likes: number;
}

export default function ArticleSearch() {
    const [query, setQuery] = useState('');
    const [debouncedQuery] = useDebounce(query, 300);
    const [results, setResults] = useState<SearchResult[]>([]);
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);

    // 获取搜索建议
    useEffect(() => {
        if (debouncedQuery.length >= 2) {
            fetchSuggestions(debouncedQuery);
        } else {
            setSuggestions([]);
        }
    }, [debouncedQuery]);

    const fetchSuggestions = async (q: string) => {
        try {
            const response = await fetch(`/api/v1/search/suggestions?q=${q}&limit=5`);
            const data = await response.json();
            setSuggestions(data.data.suggestions);
        } catch (error) {
            console.error('Failed to fetch suggestions:', error);
        }
    };

    // 执行搜索
    const handleSearch = async (pageNum: number = 1) => {
        if (!query.trim()) return;

        setLoading(true);
        try {
            const response = await fetch(
                `/api/v1/search/articles?q=${encodeURIComponent(query)}&page=${pageNum}`
            );
            const data = await response.json();

            setResults(data.data.articles);
            setPage(data.data.page);
            setTotalPages(data.data.total_pages);
        } catch (error) {
            console.error('Search failed:', error);
        } finally {
            setLoading(false);
        }
    };

    // 点击建议
    const handleSuggestionClick = (suggestion: string) => {
        setQuery(suggestion);
        setSuggestions([]);
        handleSearch(1);
    };

    return (
        <div className="search-container">
            {/* 搜索框 */}
            <div className="relative">
                <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSearch(1)}
                    placeholder="搜索文章..."
                    className="w-full px-4 py-2 border rounded-lg"
                />

                {/* 搜索建议下拉框 */}
                {suggestions.length > 0 && (
                    <div className="absolute top-full left-0 right-0 bg-white border rounded-lg shadow-lg mt-1 z-10">
                        {suggestions.map((suggestion, index) => (
                            <div
                                key={index}
                                onClick={() => handleSuggestionClick(suggestion)}
                                className="px-4 py-2 hover:bg-gray-100 cursor-pointer"
                            >
                                {suggestion}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* 搜索按钮 */}
            <button
                onClick={() => handleSearch(1)}
                disabled={loading}
                className="mt-2 px-4 py-2 bg-blue-600 text-white rounded-lg"
            >
                {loading ? '搜索中...' : '搜索'}
            </button>

            {/* 搜索结果 */}
            {results.length > 0 && (
                <div className="mt-4">
                    <h2 className="text-xl font-bold mb-4">
                        找到 {results.length} 个结果
                    </h2>

                    {results.map((article) => (
                        <article key={article.id} className="mb-4 p-4 border rounded-lg">
                            <h3
                                dangerouslySetInnerHTML={{__html: article.highlighted_title}}
                                className="text-lg font-semibold mb-2"
                            />
                            <p
                                dangerouslySetInnerHTML={{__html: article.highlighted_excerpt}}
                                className="text-gray-600 mb-2"
                            />
                            <div className="text-sm text-gray-500">
                                <span>👁 {article.views}</span>
                                <span className="ml-2">❤️ {article.likes}</span>
                            </div>
                        </article>
                    ))}

                    {/* 分页 */}
                    <div className="flex justify-center mt-4 space-x-2">
                        <button
                            onClick={() => handleSearch(page - 1)}
                            disabled={page <= 1}
                            className="px-3 py-1 border rounded"
                        >
                            上一页
                        </button>
                        <span className="px-3 py-1">
              {page} / {totalPages}
            </span>
                        <button
                            onClick={() => handleSearch(page + 1)}
                            disabled={page >= totalPages}
                            className="px-3 py-1 border rounded"
                        >
                            下一页
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
```

#### 2. 热门搜索组件

```tsx
import {useState, useEffect} from 'react';

export default function PopularSearches() {
    const [popular, setPopular] = useState<{ query: string, count: number }[]>([]);

    useEffect(() => {
        fetchPopularSearches();
    }, []);

    const fetchPopularSearches = async () => {
        try {
            const response = await fetch('/api/v1/search/popular?days=7&limit=10');
            const data = await response.json();
            setPopular(data.data);
        } catch (error) {
            console.error('Failed to fetch popular searches:', error);
        }
    };

    return (
        <div className="popular-searches">
            <h3 className="text-lg font-bold mb-3">热门搜索</h3>
            <div className="space-y-2">
                {popular.map((item, index) => (
                    <div key={index} className="flex items-center justify-between">
            <span className="text-blue-600 hover:underline cursor-pointer">
              {item.query}
            </span>
                        <span className="text-gray-500 text-sm">{item.count} 次</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
```

---

## 🔧 高级用法

### 1. 组合过滤

```typescript
// 搜索特定分类、特定作者、特定日期范围的文章
const searchWithFilters = async () => {
    const params = new URLSearchParams({
        q: 'Python',
        category_id: '1',
        author_id: '5',
        date_from: '2026-01-01',
        date_to: '2026-12-31',
        sort_by: 'views',
        page: '1',
        per_page: '20',
    });

    const response = await fetch(`/api/v1/search/articles?${params}`);
    const data = await response.json();

    return data.data;
};
```

### 2. 实时搜索（防抖）

```typescript
import {useDebounce} from 'use-debounce';

function SearchInput() {
    const [query, setQuery] = useState('');
    const [debouncedQuery] = useDebounce(query, 300);

    useEffect(() => {
        if (debouncedQuery) {
            performSearch(debouncedQuery);
        }
    }, [debouncedQuery]);

    return (
        <input
            value = {query}
    onChange = {(e)
=>
    setQuery(e.target.value)
}
    placeholder = "搜索..."
        / >
)
    ;
}
```

### 3. 搜索结果缓存

```typescript
import {useQuery} from '@tanstack/react-query';

function useArticleSearch(query: string, page: number) {
    return useQuery({
        queryKey: ['search', query, page],
        queryFn: () => fetchSearchResults(query, page),
        enabled: !!query,
        keepPreviousData: true,
    });
}
```

---

## 📊 性能优化

### 1. 数据库索引

确保以下字段有索引：

```sql
-- 文章表
CREATE INDEX idx_articles_title ON articles (title);
CREATE INDEX idx_articles_status ON articles (status);
CREATE INDEX idx_articles_category_id ON articles (category_id);
CREATE INDEX idx_articles_author_id ON articles (author_id);
CREATE INDEX idx_articles_created_at ON articles (created_at);

-- 搜索历史表
CREATE INDEX idx_search_history_query ON search_history (query);
CREATE INDEX idx_search_history_created_at ON search_history (created_at);
```

### 2. 缓存策略

```python
# 缓存热门搜索（Redis）
async def get_popular_searches_cached():
    cache_key = "popular_searches:7days"
    cached = await cache.get(cache_key)

    if cached:
        return json.loads(cached)

    # 从数据库查询
    popular = await query_database()

    # 缓存 1 小时
    await cache.set(cache_key, json.dumps(popular), ex=3600)

    return popular
```

### 3. 搜索限制

```python
# 限制最小搜索长度
if len(query) < 2:
    raise HTTPException(status_code=400, detail="搜索关键词至少2个字符")

# 限制每页最大数量
per_page = min(per_page, 100)
```

---

## ⚠️ 注意事项

### 1. SQL 注入防护

使用参数化查询，避免直接拼接 SQL：

```python
# ✅ 好的做法
stmt = select(Article).where(Article.title.ilike(f"%{query}%"))

# ❌ 不好的做法
sql = f"SELECT * FROM articles WHERE title LIKE '%{query}%'"
```

### 2. XSS 防护

前端渲染高亮内容时使用 `dangerouslySetInnerHTML` 要小心：

```tsx
// 确保后端返回的高亮标签是安全的
<div dangerouslySetInnerHTML={{__html: highlightedTitle}}/>
```

### 3. 性能考虑

- 避免搜索过短的关键词（< 2 字符）
- 限制搜索结果数量
- 使用分页
- 缓存热门搜索

---

## 🎯 最佳实践

### 1. 用户体验

- 提供搜索建议（自动完成）
- 显示搜索耗时
- 高亮匹配关键词
- 提供"无结果"友好提示
- 保存搜索历史

### 2. 性能优化

- 使用防抖减少请求
- 缓存热门搜索
- 限制搜索结果数量
- 异步加载搜索结果

### 3. SEO 优化

- 为搜索结果页面生成 meta 标签
- 使用语义化 URL
- 提供结构化数据

---

## 🚀 未来增强

### 计划功能

- [ ] Elasticsearch 集成（更强大的全文搜索）
- [ ] 拼音搜索支持
- [ ] 模糊匹配
- [ ] 同义词扩展
- [ ] 搜索 analytics
- [ ] 个性化搜索推荐
- [ ] 语音搜索

---

**维护者**: FastBlog Core Team  
**最后更新**: 2026-05-01  
**版本**: 1.0.0
