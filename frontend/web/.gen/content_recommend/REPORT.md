# content/recommend 前端接线报告

> 本批把后端 v3 模块 `content/recommend` 的 5 个端点全部接到前端。
> 产物全部位于 `frontend/web/.gen/content_recommend/`，**未经编译验证**（子代理无 shell 权限）。

---

## 0. 契约核对（以 controller 为准）

权威来源：`src/api/v3/modules/content/recommend/controller.py`。

| 任务描述路径                                        | controller 实际路径                                | 说明                                                                                                                       |
|-----------------------------------------------|------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------|
| `GET /content/recommend/for-me`               | `GET /content/recommend/for-me`                | 一致；需登录（`CurrentUser`）。                                                                                                   |
| `GET /content/recommend/popular`              | `GET /content/recommend/popular`               | 一致；公开。查询参数 `days`（可选，1–365）、`limit`（默认 10，1–50）。                                                                         |
| `GET /content/recommend/related/{article_id}` | `GET /content/recommend/related/{article_id}`  | 一致；公开。查询参数 `limit`（默认 8，1–50）。                                                                                           |
| `GET /content/recommend/tags/{tag}`           | **`GET /content/recommend/tags/{article_id}`** | **不一致（以 controller 为准）**：路径参数是 `article_id`，端点是「标签建议」，需 `AuthControl(codes.ARTICLE_VIEW)` + 登录。查询参数 `limit`（默认 10，1–30）。 |
| `GET /content/recommend/trending-tags`        | `GET /content/recommend/trending-tags`         | 一致；公开。查询参数 `days`（默认 30，1–365）、`limit`（默认 20，1–100）。                                                                     |

补充：

- `schema.py` **不存在**（读取报 `FS_NOT_FOUND`）→ 返回体字段一律以 `service.py` 的实际构造为准（见第 2 节逐条对照）。
- controller 顶部 docstring 的 `tags/{article_id}` 行与真实实现一致（标签建议，需 `article:view`）。

---

## 1. 端点 → API 函数 → 页面承载位置

承载页面：**`frontend/web/src/pages/content/article/[id].vue`**（管理端「文章编辑」页）右侧「内容助手」卡片，用 `el-tabs` 分 5
个面板。

选它的理由：5 个端点里 `related` 依赖 `article_id`、`tags/*` 依赖 `article_id` 且**需 `module_content:article:view`**、
`for-me` 需登录态；只有管理端页面同时满足「axios 带 token（自动注入 Bearer）+ 已有文章上下文 + 已具备该权限」。

| 端点                                            | API 函数                                       | 页面承载位置（tab）            |
|-----------------------------------------------|----------------------------------------------|------------------------|
| `GET /content/recommend/related/{article_id}` | `recommendApi.related(articleId, 8)`         | 「相关文章」tab              |
| `GET /content/recommend/popular`              | `recommendApi.popular(undefined, 10)`        | 「热门文章」tab              |
| `GET /content/recommend/trending-tags`        | `recommendApi.trendingTags(30, 20)`          | 「热门标签」tab              |
| `GET /content/recommend/for-me`               | `recommendApi.forMe(10)`                     | 「为你推荐」tab              |
| `GET /content/recommend/tags/{article_id}`    | `recommendApi.tagSuggestions(articleId, 10)` | 「标签建议」tab（可「采纳」写入表单标签） |

加载时机：`onMounted` 触发 `popular` / `trending-tags` / `for-me`；`watch(articleId)` 在拿到文章 id 后（含新建保存后
`router.replace` 进入编辑态）触发 `tags/{id}` 与 `related/{id}`；两者在 `articleId === null`（新建未保存）时清空，面板提示「保存文章后可获取该项推荐」。

---

## 2. 字段来源逐条对照（均取自 `service.py`，未编造）

### 公共文章字段 `_article_out()`（`RecommendService._article_out`，service.py 行 501–514）

| 前端字段           | 后端字段                                     | 备注                 |
|----------------|------------------------------------------|--------------------|
| `id`           | `int(row.id)`                            |                    |
| `title`        | `row.title`                              | 可空                 |
| `slug`         | `row.slug`                               | 可空                 |
| `excerpt`      | `row.excerpt`                            | 前端卡片未使用，类型保留       |
| `category`     | `row.category`                           | 分类 **id**（int），非对象 |
| `tags`         | `split_tags(row.tags_list)`              | 归一为字符串数组           |
| `views`        | `int(row.views or 0)`                    |                    |
| `likes`        | `int(row.likes or 0)`                    |                    |
| `is_featured`  | `bool(row.is_featured)`                  |                    |
| `published_at` | `row.published_at.isoformat()`，无则 `null` |                    |

### `related`（`service.related`，行 194–231）

| 前端字段                 | 后端字段          | 备注                              |
|----------------------|---------------|---------------------------------|
| `article_id`         | `article_id`  | 基准文章 id                         |
| `base_tags`          | `base_tags`   | 基准文章标签集合                        |
| `total`              | `len(scored)` | 命中候选数（截断前）                      |
| `items[].similarity` | `similarity`  | 标签 Jaccard 相似度                  |
| `items[].score`      | `score`       | = 相似度 ×0.7 + 同分类 ×0.2 + 热度 ×0.1 |

### `popular`（`service.popular`，行 234–289）

| 前端字段                   | 后端字段                 | 备注                            |
|------------------------|----------------------|-------------------------------|
| `window_days`          | `None`（累计）或 `window` |                               |
| `source`               | `source`             | 后端中文说明文案，页面原样展示               |
| `items[].window_views` | `window_views`       | **仅指定 days 时出现**（页面仅在窗口模式下渲染） |

### `trending-tags`（`service.trending_tags`，行 372–395）

| 前端字段                            | 后端字段                 |
|---------------------------------|----------------------|
| `window_days`                   | `window`             |
| `total_tags`                    | `len(counter)`       |
| `items[].tag` / `items[].count` | `tag` / `int(count)` |

### `for-me`（`service.for_user`，行 292–327）

| 前端字段                                                                    | 后端字段                             | 备注                                |
|-------------------------------------------------------------------------|----------------------------------|-----------------------------------|
| `user_id`                                                               | `user_id`                        |                                   |
| `behavior_samples`                                                      | `len(actions)`                   |                                   |
| `interest_tags`                                                         | `sorted(interests.items(), ...)` | 序列化为 `[tag, weight]` 二元组数组        |
| `cold_start`                                                            | `not interests`                  |                                   |
| `items[].score/tag_score/category_score/recency_score/popularity_score` | 同名字段                             | 来自 `score_candidate()`（行 150–178） |

### `tags/{article_id}`（`service.tag_suggestions`，行 330–370）

| 前端字段                               | 后端字段                         | 备注            |
|------------------------------------|------------------------------|---------------|
| `article_id`                       | `article_id`                 |               |
| `current_tags`                     | `current`                    |               |
| `known_tags`                       | `sorted(known)[:50]`         | 前端类型保留，界面暂未展示 |
| `suggestions[].tag`                | `item["keyword"]`            |               |
| `suggestions[].count`              | `item["count"]`              |               |
| `suggestions[].score`              | `item["score"]`              |               |
| `suggestions[].in_use`             | `item["keyword"] in known`   |               |
| `suggestions[].already_on_article` | `item["keyword"] in current` |               |

---

## 3. 未接线端点 / 未接字段及原因

- **无未接端点**：5 条路由全部接线。
- 未在界面上展示、但在 TS 类型中保留的字段：`excerpt`、`interest_tags`、`behavior_samples`、`cold_start`（`cold_start`
  有展示为提示文案）、`known_tags`、`total`、`total_tags`、`window_days`、`similarity`
  、各分项分。保留是为了「类型即契约」，避免后续又要改类型；页面仅渲染其中必要的部分。

---

## 4. 存疑项（需注意）

1. **任务描述与 controller 不一致**：任务写的 `GET .../tags/{tag}` 实际是 `GET .../tags/{article_id}`（标签建议）。已按
   controller 处理为 `tagSuggestions(articleId)`。若父代理/上层期望的是「按标签取文章」的端点，则后端并不存在该路由。
2. **承载页面选择**：任务候选清单以「最合适的一个」表述，但 5 个端点天然分层（公开/登录/需 `article:view` + `article_id`
   上下文）。本批统一承载于管理端「文章编辑」页，作为写作时的「内容助手」。若产品意图是**前台阅读体验**
   （详情页「相关文章」、首页「热门/标签云」），则需将 `related`/`popular`/`trending-tags` 迁到前台 SSR 页面（用
   `composables/useApi.ts` 的 `apiGet`，`for-me` 因 `apiGet` 用 `credentials: 'omit'` 需另走 CSR+auth 页如
   `pages/feed.vue`）。请父代理确认承载策略。
3. **`related` 在前台已有旧实现**：`components/site/ArticleDetailView.vue`（行 207–222）已用
   `/content/article/public/list?category_id=...` 自行「凑」相关文章，**并未调用**新的 `recommend/related`
   。本批未改动该组件（超出「页面」承载范围）；若要让前台真正用上后端算法，需另批替换该组件的 `loadRelated`。
4. **`popular.source` 为后端中文字面量**，在 en 语言下会原样显示中文（属数据而非 UI 文案，故未纳入 i18n）。
5. **`for-me` 返回的 `interest_tags` 序列化为二元组数组**：TS 类型标注为 `Array<[string, number]>`，与 FastAPI/JSON
   序列化一致；前端未渲染，仅类型保留。
6. `category` 字段是**分类 id（数字）**而非分类对象；如后续要在助手面板显示分类名，需要额外解析。

---

## 5. 「未经编译验证」声明

本产物在**无 shell 权限**（不能运行 `npm`/`pnpm`/`tsc`/`vite`/`git`）的子代理环境中生成，**未经过类型检查、构建或运行验证**
。已通过人工复核：所有模板标识符均有 import/定义来源、未使用 `as` 断言、未 mock/占位、i18n 两份 key 完全对称、行尾
LF。仍请父代理在收口后运行项目自带的 typecheck/build 校验。

---

## 6. 需要父代理在 `src/api/index.ts` 追加的 re-export

`api/recommend.ts` 内部使用 `import http from '../request'`，因此*
*目标落位必须是 `frontend/web/src/api/modules/recommend.ts`**（与其它模块同级；若放到 `src/api/recommend.ts` 则
`../request` 路径不成立）。请在 `src/api/index.ts` 的 `// ---- content` 段落附近追加：

```ts
export {recommendApi} from './modules/recommend'
export type {
  RecommendArticleItem,
  RecommendForMeResult,
  RecommendPopularItem,
  RecommendPopularResult,
  RecommendRelatedItem,
  RecommendRelatedResult,
  RecommendScoredItem,
  RecommendTagSuggestion,
  RecommendTagSuggestionsResult,
  RecommendTrendingTag,
  RecommendTrendingTagsResult,
} from './modules/recommend'
```

## 7. 需要父代理处理的其它收口事项

- **i18n 合并**：把 `i18n.json` 的 `zh-CN.admin.content.article.recommend` 与 `en.admin.content.article.recommend` 两段并入
  `frontend/web/i18n/locales/{zh-CN,en}.json` 的 `admin.content.article` 对象内（该对象在 zh-CN.json 约 2357–2430 行）。两份
  key 完全对称。
- **菜单**：本批**不需要**新增菜单项（推荐能力挂在既有「文章编辑」页，路由 `/content/article/{id}` 已存在）。
- **权限码**：页面 `definePageMeta.permission` 沿用既有 `'module_content:article:view'`；`tags/{article_id}` 端点后端要求
  `codes.ARTICLE_VIEW`（字符串形式 `'module_content:article:view'`），一致。面板内「采纳标签」按钮用
  `v-auth="'module_content:article:edit'"` 控制（写标签属编辑动作）。**未新增权限码**。

## 8. 产物清单（.gen 路径 → 目标路径）

| .gen 产物                          | 目标落位                                                    |
|----------------------------------|---------------------------------------------------------|
| `api/recommend.ts`               | `frontend/web/src/api/modules/recommend.ts`             |
| `pages/content/article/[id].vue` | `frontend/web/src/pages/content/article/[id].vue`（完整替换） |
| `i18n.json`                      | 合并进 `frontend/web/i18n/locales/zh-CN.json` 与 `en.json`  |
| `REPORT.md`                      | 本文件（无需落位）                                               |
