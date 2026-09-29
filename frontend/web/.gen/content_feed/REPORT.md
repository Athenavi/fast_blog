# content/feed 前端接线报告

**模块**：后端 `src/api/v3/modules/content/feed`（v3 动态流）
**前端产出**：`frontend/web/.gen/content_feed/`
**边界**：仅新增 `frontend/web/.gen/content_feed/` 下的文件；未改动仓库任何其它文件。

> 注意：`content/feed` 与 `mobile/feed` **不是同一个模块**。
> `mobile/feed`（关注流）只按登录用户关注关系聚合**已发布文章**（一页文章，`page_size ≤ 50`）；
> `content/feed` 把 `articles` / `article_likes` / `comments` 三类事件 `UNION ALL` 成**事件流**，
> 含关注时间线、全站发现流、用户公开动态与流概览。二者语义不同，故新建独立的 `contentFeed.ts`，
> 不并入既有 `feed.ts`。

---

## 1. 端点映射表

| 后端端点                                      | 方法 / 鉴权        | 承载页                                   | 调用                          | 分页                            |
|-------------------------------------------|----------------|---------------------------------------|-----------------------------|-------------------------------|
| `GET /api/v3/content/feed/timeline`       | GET · **仅需认证** | `src/pages/feed.vue`（前台「关注动态」页）       | `contentFeedApi.timeline()` | `http.page` + `PaginationBar` |
| `GET /api/v3/content/feed/discover`       | GET · **公开**   | `src/pages/discover.vue`（新建公开页）       | `contentFeedApi.discover()` | `http.page` + `PaginationBar` |
| `GET /api/v3/content/feed/user/{user_id}` | GET · **公开**   | `src/pages/home/[username].vue`（用户主页） | `contentFeedApi.userFeed()` | `http.page` + `PaginationBar` |
| `GET /api/v3/content/feed/stats`          | GET · **仅需认证** | `src/pages/feed.vue`（顶部「我的流概览」卡）      | `contentFeedApi.stats()`    | 无（聚合对象）                       |

- `timeline` / `stats` 均为登录态，落在 `feed.vue`（既有 `middleware: 'auth'` + `ssr: false`）。
- `discover` / `user` 为公开端点，落在公开页；实现走 `contentFeedApi`（CSR）。
- 四个端点**均无权限码**（后端只用 `CurrentUser` / 公开），`user_id` 由登录态或路径提供。

**页面逐字保留说明**：`feed.vue` 与 `home/[username].vue` 是**完整替换版**——原有 `<script>` 与 `<template>`
内容逐字保留，仅在其上追加：

- `feed.vue`：追加「我的流概览」卡片（stats）与「关注动态 · 事件时间线」区块（timeline）；原有 `mobile/feed` 关注流文章列表原样保留。
- `home/[username].vue`：追加「TA 的动态」区块（user feed）；原有资料、统计、文章列表、关注/打赏原样保留。
- `discover.vue` 为**新页面**（仓库中确无公开「发现流」承载页，故新建）。

---

## 2. 字段来源（每个前端类型的后端出处）

均为 `src/api/v3/modules/content/feed/service.py` 的返回体（本模块**无 `schema.py`**，契约即 service）：

| 前端类型                                                                         | 后端构造处                                                                                                             |
|------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------|
| `FeedEvent {type, at, actor_id, extra, article}`                             | `FeedService._page_events()` 的 `items.append({...})`                                                              |
| `FeedArticle {id,title,slug,excerpt,user,category,views,likes,published_at}` | `FeedService._article_out()`                                                                                      |
| `FeedStats {user_id, following, timeline_events, by_type, hint?}`            | `FeedService.stats()` 两个 return 分支                                                                                |
| `FeedEventType = 'article' \| 'like' \| 'comment'`                           | `service.EVENT_TYPES`                                                                                             |
| 查询参数 `page`/`page_size`                                                      | `core/deps.PageDep` → `common/request.PageQuery`（默认 `page=1`、`page_size=20`，`ge=1`；`page_size` 服务端再 `min(x,100)`） |
| 查询参数 `include_interactions`                                                  | `controller.discover` 的 `Query(default=False, bool)`                                                              |
| 查询参数 `event_types`                                                           | `controller.timeline` 的 `Query(default=None, str)`，逗号分隔；未知类型后端抛 `BadRequestError`                                 |
| 分页信封 `{items,total,page,pageSize,pages}`                                     | `req.success_page` → `http.page()` 组装                                                                             |

---

## 3. 未接线及原因

- **无**。本模块的 4 个端点已全部接线。
- `content/feed/user/{user_id}` 的 `user_id` 取自用户主页已解析的 `profile.id`（`mobile/user/public/{username}`
  的返回），不再额外请求。
- 后端 `timeline` / `user_feed` 对**未知 `event_types`** 抛 400：前端过滤按钮只在 `article|like|comment` 中取值，不会触发。

---

## 4. 存疑（需父 agent / 评审确认）

1. **csr vs ssr（最重要）**：
    - `contentFeedApi` 基于 `@/api/request`（axios，`baseURL = /api/v3`，相对路径）。**SSR 下无法直接用相对 URL 发请求**，故
      `discover.vue` 与 `home/[username].vue` 的 user feed **走客户端加载**（`onMounted`）。
    - 任务硬性要求「页面用 `from '@/api'`」，故统一走 `contentFeedApi`；但前台公开页的既有惯例是 `apiGet`/`apiPage`（`$fetch`
      ，SSR 直出、SEO 友好，见 `pages/index.vue`、`pages/search.vue`）。
    - **若需要公开页 SEO/首屏直出**：把 `discover.vue` 与 `home/[username].vue` 的 user-feed 请求换成
      `apiPage<FeedEvent>('/content/feed/discover' | '/content/feed/user/'+id, {...})` 即可（字段结构一致），
      `contentFeedApi` 中对应的 `discover`/`userFeed` 方法则无页面承载。**本实现选择了 `from '@/api'` 以满足硬性要求。**
2. **`EVENT_TYPES` 顺序 / 文案**：`typesHint` 文案中的可选值列表为硬编码（与 `EVENT_TYPES` 一致），后端若新增事件类型需同步。当前仅三类。
3. **`hint` 字段**：`stats` 在「关注为空」时返回中文 `hint`；前端直接渲染后端原文（未做 i18n，因为文案由后端下发）。
4. **`actor_id` 展示**：事件流只返回 `actor_id`（数字），未带作者名，界面按 `来自用户 #{id}` 展示；如需用户名，需后端在事件里补充
   author 字段。
5. **`at` 为 null**：`comment` 事件的 `at = Comment.created_at`、`article` 事件的 `at = Article.published_at`，理论上非空；前端
   `formatDateTime(null)` 兜底为 `-`。
6. **`stats.by_type`** 为 `Record<string, number>`，模板中以 `by_type.article/like/comment | 0` 取值，缺失类型按 0 显示。

---

## 5. 未编译声明（务必）

**本产物未经任何编译 / 类型检查 / 构建验证**：本子任务**没有 shell 权限**，`.gen/` 下文件亦不在仓库 tsconfig 路径内。
因此：

- 未运行 `vue-tsc` / `nuxt build` / `eslint`；
- `ArticleItem` 与 `FeedArticle` 字段不同（前者 `summary/cover_image/tags`，后者 `excerpt`），故事件卡片**未复用**
  `ThemeArticleCard`，而是内联渲染，避免类型不匹配；
- 模板内 `event.article.title` 等访问依赖 `v-if="event.article"` 的类型收窄（与既有 `home/[username].vue` 的
  `v-if="profile"` 同款写法）；
- 未新增任何 `as` 断言；未使用 `any`；
- 所有文件行尾为 LF。

**落地前请在真实工程内跑一次**：`cd frontend/web && npx vue-tsc --noEmit`（或 `pnpm typecheck`）与 `pnpm build`。

---

## 6. re-export 块（合并到 `frontend/web/src/api/index.ts` 末尾）

```ts
// ---------------------------------------------------------------- 批次 19（content 动态流）
export {contentFeedApi} from './modules/contentFeed'
export type {
  FeedArticle,
  FeedEvent,
  FeedEventType,
  FeedStats,
  FeedStreamQuery,
} from './modules/contentFeed'
```

**其它合并位置**：

- API 模块文件：`frontend/web/.gen/content_feed/api/contentFeed.ts` → `frontend/web/src/api/modules/contentFeed.ts`（其
  `import http from '../request'` 相对路径即为 `modules/` 下的正确层级）。
- 页面：
    - `.gen/content_feed/pages/feed.vue` → `frontend/web/src/pages/feed.vue`（**完整替换**）
    - `.gen/content_feed/pages/discover.vue` → `frontend/web/src/pages/discover.vue`（**新增文件**）
    - `.gen/content_feed/pages/home/[username].vue` → `frontend/web/src/pages/home/[username].vue`（**完整替换**）
- i18n：把 `i18n.json` 中 `zh-CN.contentFeed` 合并进 `frontend/web/i18n/locales/zh-CN.json`，`en.contentFeed` 合并进
  `frontend/web/i18n/locales/en.json`（两份对称，均为新增 namespace，不改动既有键）。
- 新页 `discover.vue` 的 `definePageMeta` 未设 `ssr:false`；若希望与 `/feed`、`/fans` 一致走纯 CSR，可在 `nuxt.config.ts` 的
  route rules 中为 `/discover` 配置 `ssr: false`（本子任务不改 `nuxt.config.ts`）。
