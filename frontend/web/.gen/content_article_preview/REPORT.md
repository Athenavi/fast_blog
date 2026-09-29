# 前端接线报告：草稿预览令牌（content/article preview-token）

产物目录：`frontend/web/.gen/content_article_preview/`（本子代理仅允许写该目录）

## 0. 产物清单与安装位置

| 产物（.gen 内路径）                         | 仓库目标位置                                                 | 形态                                |
|--------------------------------------|--------------------------------------------------------|-----------------------------------|
| `api/article.ts`                     | `frontend/web/src/api/modules/article.ts`              | **完整替换**（逐字保留既有 97 行 + 追加预览令牌部分）  |
| `pages/content/article/[id].vue`     | `frontend/web/src/pages/content/article/[id].vue`      | **完整替换**（逐字保留既有 + 右栏追加「草稿预览令牌」卡片） |
| `pages/articles/preview/[token].vue` | `frontend/web/src/pages/articles/preview/[token].vue`  | **新建**（公开预览承载页）                   |
| `i18n.json`                          | 合并进 `frontend/web/i18n/locales/zh-CN.json` 与 `en.json` | 仅新增键，双语对称                         |

---

## 1. 映射表（端点 → 前端函数 / 承载）

后端以 `src/api/v3/modules/content/article/controller.py` 为准。

| 后端端点（权限码）                                                          | articleApi 函数                              | 承载 UI                                                         |
|--------------------------------------------------------------------|--------------------------------------------|---------------------------------------------------------------|
| `POST /content/article/{article_id}/preview-token`（`article:edit`） | `createPreviewToken(articleId, data)`      | `pages/content/article/[id].vue` 右栏「草稿预览令牌」→「生成令牌」            |
| `GET /content/article/{article_id}/preview-tokens`（`article:view`） | `listPreviewTokens(articleId)`             | 同上，令牌列表                                                       |
| `POST /content/article/preview-token/cleanup`（`article:edit`）      | `cleanupPreviewTokens()`                   | 同上，「清理过期令牌」                                                   |
| `DELETE /content/article/preview-token/{token_id}`（`article:edit`） | `revokePreviewToken(tokenId)`              | 同上，每行「撤销」                                                     |
| `GET /content/article/public/preview/{token}`（**公开，无鉴权**）          | `publicPreview(token, password?)`（axios 版） | 前台新页 `pages/articles/preview/[token].vue`（用 `$fetch` 直连，见 §3） |

请求/响应结构对齐 `preview_service.py`：

- 生成/列表返回 `_token_out`：
  `{id, article_id, token, max_views, view_count, is_active, has_password, expires_at, created_by, created_at}`。
- 生成入参对齐 `ArticlePreviewTokenCreate`：
  `{expires_hours(1..720, 默认 24), password(4..64 可选), max_views(1..10000 可选)}`。
- 清理返回 `{removed: number}`；撤销返回 `null`。
- 公开预览返回 `resp.success({article, preview})`：`article` 取 `_PREVIEW_FIELDS` 白名单，
  `preview = {view_count, max_views, expires_at}`；口令走请求头 `X-Preview-Password`。

## 2. 字段来源

| 前端类型                               | 字段                                                                                                                | 来源                                                          |
|------------------------------------|-------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------|
| `ArticlePreviewToken`              | 全部                                                                                                                | `preview_service._token_out()`（`password_hash` 永不下发）        |
| `ArticlePreviewTokenCreatePayload` | `expires_hours/password/max_views`                                                                                | `schema.ArticlePreviewTokenCreate`                          |
| `ArticlePreviewPublicArticle`      | `id/title/slug/excerpt/cover_image/category/tags/content/language_code/status/published_at/created_at/updated_at` | `preview_service._PREVIEW_FIELDS` 白名单（下标见 §4 存疑，`category`） |
| `ArticlePreviewMeta`               | `view_count/max_views/expires_at`                                                                                 | `preview_service.resolve_preview()` 返回的 `preview`           |

前置既有类型（`ArticleItem/ArticleDetail/ArticleQuery/ArticlePayload`）逐字保留，未改动。

## 3. 未接线及原因

1. **后台「并排预览」iframe 未改用令牌**：`pages/content/article/[id].vue` 既有 `previewUrl` 仍指向 `/articles/id/{id}`
   （保存态前台详情）。该行为属既有实现，且草稿直出前台详情对未发布文章会 404；令牌预览已由新页 `/articles/preview/{token}`
   承担，故不改动既有 iframe 逻辑（任务仅要求接入 5 个令牌端点）。
2. **公开预览未走 `articleApi.publicPreview`，而是前台页 `$fetch` 直连**：`articleApi` 基于后台 axios 客户端（
   `@/api/request`，CSR + 本地 token），而前台需要 SSR/SEO，数据层是 `$fetch`（`composables/useApi.ts` 的 `apiGet`/`apiPage`，
   `credentials: 'omit'`）。令牌端点需要自定义请求头 `X-Preview-Password`，`apiGet`（无 headers）与 `http.get`（无
   headers）都不支持，因此：
    - `articleApi.publicPreview` 用 `http.raw`（`http.get` 不支持自定义头）供后台侧复用，已接入并真实调用；
    - 前台页直接用 `$fetch` + `API_PREFIX` 直连（同 `pages/articles/[slug].vue` 里浏览量上报的既有直连写法）。
      两者调用的是同一端点，不存在 mock。
3. **`publicPreview` 在后台 UI 中暂无调用点**：仅作为 articleApi 的完整端点映射存在；后台生成令牌后靠「复制链接」跳前台新页预览，符合「令牌即凭证」的设计。

## 4. 存疑

1. **`article.category` 字段名**：`preview_service._PREVIEW_FIELDS` 白名单含 `"category"`，但 `service.get_article()` 走
   `to_out()`，其返回键是 **`category_id`**（`service.py:53`），并不存在 `category` 键。因此 `resolve_preview` 里
   `detail.get("category")` 实际取到 `None`，公开预览的 `article.category` 恒为 `null`。前端类型暂记
   `category?: number | null`，并在页面渲染中未依赖该字段。建议后端把白名单改为 `category_id`（或让 `to_out` 同时输出
   `category`）。
2. **公开预览失败不可区分原因**：后端对「令牌不存在 / 过期 / 超访问上限 / 口令错误 /
   文章已删」统一抛同一文案（安全设计）。因此预览页无法判断「是否只是缺口令」，故失败态一律展示可选口令输入 + 重试（用户知道口令即可重试）。
3. **`articleApi.publicPreview` 的错误提示**：`http.raw` 不经 `unwrap`，故该函数自行
   `throw new Error(body?.msg || String(body?.code))`，不会触发 request 拦截器的统一冒泡提示；调用方需自行 catch
   提示。当前后台无调用点，影响面为零。
4. **令牌明文在列表接口下发**：`_token_out` 含 `token` 明文，前端列表直接展示/复制。是否应仅在创建响应返回明文、列表只给摘要，属后端安全策略，前端按当前契约实现。

## 5. 未编译声明

本产物**未在真实工程中编译/类型检查/lint**。子代理无 shell 权限，`vue-tsc`、`eslint`、Nuxt build 均未运行。已做的人工核对：

- `article.ts` 保持 `import http from '../request'` 与 `articleApi` 导出名不变；新类型与函数均为新增。
- `[id].vue` 逐字保留既有 script/模板/样式，仅在 script tail 追加令牌逻辑、在 `@/api` 导入行追加 `articleApi`
  与两个类型、在右栏「内容助手」卡片后追加令牌卡片、在 `<style scoped>` 末尾追加 `.token-new*` / `.token-list__head` 规则；
  `vue` 导入由 `{computed, ref, watch}` 扩为 `{computed, reactive, ref, watch}`。
- 预览页复用的 `Badge`、`Button`、`formatDateTime`、`API_PREFIX`、`CODE_SUCCESS`、`i18n` `site.noContent` 均已确认存在（自动导入/工具模块）。
- 行尾统一 LF；无 `as` 断言掩盖类型（既有 `row as ArticleItem` 为原文保留，非本次新增）。

## 6. 需父代理补的 re-export 块

在 `frontend/web/src/api/index.ts` 的 `// ---------------- content` 段（当前第 246-252 行）把新增类型并入 type 导出：

```ts
// ---------------------------------------------------------------- content
export {articleApi} from './modules/article'
export type {
  ArticleDetail,
  ArticleItem,
  ArticlePayload,
  ArticlePreviewMeta,
  ArticlePreviewPublicArticle,
  ArticlePreviewResult,
  ArticlePreviewToken,
  ArticlePreviewTokenCreatePayload,
  ArticleQuery,
} from './modules/article'
```

其余导出（`categoryApi` 及以下）保持原样，勿动。

## 7. 新增 i18n 键（i18n.json 内，双语言对称）

- `admin.content.article.previewToken.*`：
  `title/desc/expiresHours/password/passwordPlaceholder/maxViews/create/created/newTokenHint/list/empty/viewCount/active/inactive/hasPassword/unlimited/copyLink/copied/revoke/revokeConfirm/revoked/cleanup/cleanupDone`
- `article.preview.*`：
  `badge/toolbar/views/maxViews/expiresAt/loading/invalidTitle/invalidDesc/passwordLabel/passwordPlaceholder/retry`

已核对：`admin.content.article` 段（zh-CN.json 2357 起）无 `previewToken` 子键；`article` 段（zh-CN.json 383-444）无 `preview`
子键（第 498 行的 `preview` 属 `media` 命名空间），二者均无冲突。
