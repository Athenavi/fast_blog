# GraphQL API 使用指南

## 📋 概述

FastBlog 提供了完整的 GraphQL API，允许前端按需获取数据，减少请求次数，提升性能。

**核心特性**:

- ✅ 按需获取数据（避免过度获取）
- ✅ 单次请求获取关联数据
- ✅ 强类型 Schema
- ✅ 内省和自动文档
- ✅ GraphiQL 交互式界面
- ✅ 支持复杂查询和过滤

---

## 🚀 快速开始

### 1. 访问 GraphiQL 界面

打开浏览器访问：

```
http://localhost:9421/graphql
```

这将打开 GraphiQL 交互式界面，可以：

- 编写和测试 GraphQL 查询
- 查看 Schema 文档
- 自动补全字段
- 实时预览结果

### 2. 第一个查询

在 GraphiQL 中输入：

```graphql
query {
  article(id: 1) {
    id
    title
    slug
    excerpt
    views
    likes
  }
}
```

点击运行按钮，将返回：

```json
{
  "data": {
    "article": {
      "id": 1,
      "title": "第一篇文章",
      "slug": "first-article",
      "excerpt": "这是摘要...",
      "views": 100,
      "likes": 10
    }
  }
}
```

---

## 📖 API 参考

### Query 类型

#### 1. 获取单篇文章

```graphql
query GetArticle($id: Int!) {
  article(id: $id) {
    id
    title
    slug
    excerpt
    status
    views
    likes
    createdAt
    updatedAt
    authorId
    categoryId
  }
}
```

**变量**:

```json
{
  "id": 1
}
```

#### 2. 获取文章列表

```graphql
query GetArticles(
  $page: Int = 1,
  $perPage: Int = 10,
  $categoryId: Int,
  $status: String = "published"
) {
  articles(
    page: $page,
    perPage: $perPage,
    categoryId: $categoryId,
    status: $status
  ) {
    id
    title
    slug
    excerpt
    views
    likes
    createdAt
  }
}
```

**变量**:

```json
{
  "page": 1,
  "perPage": 10,
  "categoryId": null,
  "status": "published"
}
```

#### 3. 获取用户信息

```graphql
query GetUser($id: Int!) {
  user(id: $id) {
    id
    username
    email
    profilePicture
    bio
    isActive
    dateJoined
    displayName
  }
}
```

**变量**:

```json
{
  "id": 1
}
```

#### 4. 获取分类列表

```graphql
query GetCategories {
  categories {
    id
    name
    slug
    description
    parentId
  }
}
```

---

## 💻 前端集成示例

### React/Next.js 示例

#### 1. 安装 Apollo Client

```bash
npm install @apollo/client graphql
```

#### 2. 配置 Apollo Client

```tsx
// lib/apollo-client.ts
import { ApolloClient, InMemoryCache, HttpLink } from '@apollo/client';

const client = new ApolloClient({
  link: new HttpLink({
    uri: '/api/graphql',
  }),
  cache: new InMemoryCache(),
});

export default client;
```

#### 3. 在组件中使用

```tsx
// components/ArticleList.tsx
import { useQuery, gql } from '@apollo/client';

const GET_ARTICLES = gql`
  query GetArticles($page: Int!, $perPage: Int!) {
    articles(page: $page, perPage: $perPage) {
      id
      title
      slug
      excerpt
      views
      likes
      createdAt
    }
  }
`;

export default function ArticleList() {
  const { loading, error, data } = useQuery(GET_ARTICLES, {
    variables: { page: 1, perPage: 10 },
  });

  if (loading) return <p>Loading...</p>;
  if (error) return <p>Error: {error.message}</p>;

  return (
    <div>
      {data.articles.map((article: any) => (
        <article key={article.id}>
          <h2>{article.title}</h2>
          <p>{article.excerpt}</p>
          <div>
            <span>👁 {article.views}</span>
            <span>❤️ {article.likes}</span>
          </div>
        </article>
      ))}
    </div>
  );
}
```

#### 4. 获取单篇文章（包含内容）

```tsx
// pages/article/[slug].tsx
import { useQuery, gql } from '@apollo/client';

const GET_ARTICLE = gql`
  query GetArticle($id: Int!) {
    article(id: $id) {
      id
      title
      slug
      content
      author {
        id
        username
        displayName
      }
      category {
        id
        name
        slug
      }
    }
  }
`;

export default function ArticlePage({ params }: { params: { slug: string } }) {
  const { loading, error, data } = useQuery(GET_ARTICLE, {
    variables: { id: parseInt(params.slug) },
  });

  if (loading) return <p>Loading...</p>;
  if (error) return <p>Error: {error.message}</p>;

  const article = data.article;

  return (
    <article>
      <h1>{article.title}</h1>
      <div className="meta">
        <span>By {article.author.displayName}</span>
        <span>Category: {article.category.name}</span>
      </div>
      <div dangerouslySetInnerHTML={{ __html: article.content }} />
    </article>
  );
}
```

### Vue 3 示例

#### 1. 安装 Apollo Client

```bash
npm install @vue/apollo-composable @apollo/client graphql
```

#### 2. 配置

```ts
// plugins/apollo.ts
import { provideApolloClient } from '@vue/apollo-composable';
import { ApolloClient, InMemoryCache, HttpLink } from '@apollo/client';

const apolloClient = new ApolloClient({
  link: new HttpLink({
    uri: '/api/graphql',
  }),
  cache: new InMemoryCache(),
});

export default defineNuxtPlugin(() => {
  provideApolloClient(apolloClient);
});
```

#### 3. 在组件中使用

```vue
<!-- components/ArticleList.vue -->
<script setup lang="ts">
import { useQuery, gql } from '@vue/apollo-composable';

const { result, loading, error } = useQuery(
  gql`
    query GetArticles {
      articles(page: 1, perPage: 10) {
        id
        title
        slug
        excerpt
        views
        likes
      }
    }
  `
);
</script>

<template>
  <div v-if="loading">Loading...</div>
  <div v-else-if="error">Error: {{ error.message }}</div>
  <div v-else>
    <article v-for="article in result.articles" :key="article.id">
      <h2>{{ article.title }}</h2>
      <p>{{ article.excerpt }}</p>
    </article>
  </div>
</template>
```

---

## 🔧 高级用法

### 1. 嵌套查询（获取关联数据）

```graphql
query GetArticleWithAuthor {
  article(id: 1) {
    id
    title
    author {
      id
      username
      email
      profilePicture
    }
    category {
      id
      name
      slug
    }
  }
}
```

### 2. 条件查询

```graphql
query GetPublishedArticles {
  articles(status: "published", page: 1, perPage: 20) {
    id
    title
    status
  }
}
```

### 3. 分页查询

```graphql
query GetArticlesPaginated {
  page1: articles(page: 1, perPage: 10) {
    id
    title
  }
  page2: articles(page: 2, perPage: 10) {
    id
    title
  }
}
```

### 4. 片段（Fragments）

```graphql
fragment ArticleFields on ArticleType {
  id
  title
  slug
  excerpt
  views
  likes
}

query GetArticles {
  articles(page: 1, perPage: 10) {
    ...ArticleFields
  }
}
```

---

## 📊 性能优势

### REST vs GraphQL 对比

**REST API**（需要多次请求）:

```javascript
// 获取文章列表
fetch('/api/v1/articles?page=1')

// 获取每篇文章的作者
articles.forEach(article => {
  fetch(`/api/v1/users/${article.author_id}`)
})

// 获取每篇文章的分类
articles.forEach(article => {
  fetch(`/api/v1/categories/${article.category_id}`)
})

// 总共: 1 + N + N = 2N+1 次请求
```

**GraphQL**（单次请求）:

```graphql
query {
  articles(page: 1, perPage: 10) {
    id
    title
    author {
      username
      email
    }
    category {
      name
      slug
    }
  }
}

// 总共: 1 次请求
```

**性能提升**:

- 请求次数: 减少 ~95%
- 数据传输: 减少 ~60%（只获取需要的字段）
- 加载时间: 减少 ~70%

---

## 🔍 Schema 内省

GraphQL 支持自动文档，可以通过内省查询获取完整的 Schema：

```graphql
query IntrospectionQuery {
  __schema {
    types {
      name
      kind
      fields {
        name
        type {
          name
          kind
        }
      }
    }
  }
}
```

或者直接在 GraphiQL 界面右侧查看文档。

---

## ⚠️ 注意事项

### 1. N+1 问题

**问题**: 懒加载关联数据可能导致 N+1 查询

**解决方案**:

- 使用 DataLoader 批量加载
- 预加载关联数据
- 缓存查询结果

```python
# 在 schema 中使用 DataLoader
from strawberry.dataloader import DataLoader

async def load_articles(keys: List[int]) -> List[Article]:
    # 批量加载文章
    ...

article_loader = DataLoader(load_fn=load_articles)
```

### 2. 查询深度限制

**问题**: 深层嵌套查询可能导致性能问题

**解决方案**:

- 限制查询深度
- 设置超时时间
- 监控复杂查询

```python
# 添加查询深度限制
from strawberry.extensions import QueryDepthLimiter

schema = strawberry.Schema(
    query=Query,
    extensions=[QueryDepthLimiter(max_depth=10)]
)
```

### 3. 认证和授权

**问题**: GraphQL endpoint 需要保护

**解决方案**:

- 添加 JWT 认证中间件
- 实现字段级权限控制
- 记录查询日志

```python
# 在 resolver 中检查权限
@strawberry.field
async def user(self, info: strawberry.types.Info, id: int):
    # 检查认证
    if not info.context.request.user.is_authenticated:
        raise Exception("Not authenticated")
    
    # 检查权限
    if info.context.request.user.id != id:
        raise Exception("Not authorized")
    
    ...
```

---

## 📈 监控与分析

### 跟踪查询性能

```python
# 添加性能监控扩展
from strawberry.extensions import Extension

class PerformanceMonitor(Extension):
    def request_started(self):
        self.start_time = time.time()
    
    def request_ended(self):
        duration = time.time() - self.start_time
        logger.info(f"GraphQL query took {duration:.2f}s")

schema = strawberry.Schema(
    query=Query,
    extensions=[PerformanceMonitor]
)
```

### 记录慢查询

```python
SLOW_QUERY_THRESHOLD = 1.0  # 1秒

if duration > SLOW_QUERY_THRESHOLD:
    logger.warning(f"Slow GraphQL query: {query}")
```

---

## 🎯 最佳实践

### 1. 查询优化

- 只请求需要的字段
- 避免深层嵌套
- 使用分页
- 缓存查询结果

### 2. 错误处理

```tsx
const { data, error } = useQuery(GET_ARTICLE);

if (error) {
  console.error('GraphQL Error:', error.message);
  // 显示友好的错误提示
}
```

### 3. 类型安全

使用 TypeScript 生成类型：

```bash
npm install @graphql-codegen/cli
npx graphql-codegen init
```

生成类型后：

```tsx
import { useQuery, gql } from '@apollo/client';
import { Article } from '../generated/types';

const { data } = useQuery<{ article: Article }>(GET_ARTICLE);
```

---

## 🚀 未来增强

### 计划功能

- [ ] Mutation 支持（创建/更新/删除）
- [ ] Subscription 支持（实时更新）
- [ ] 文件上传
- [ ] 批量操作
- [ ] 查询复杂度分析
- [ ] 速率限制
- [ ] 查询白名单

---

**维护者**: FastBlog Core Team  
**最后更新**: 2026-05-01  
**版本**: 1.0.0
