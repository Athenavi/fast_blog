/**
 * 前台（公开站点）API 出口
 *
 * ## 为什么不能直接 `import ... from '@/api'`
 *
 * `api/index.ts` 是给**后台**用的全量聚合出口：178 项导出，覆盖 admin / ai / ops /
 * commerce / system 等全部模块，并且 `export {default as http} from './request'`
 * 会带上 axios 客户端。
 *
 * 前台的 `layouts/*` 与 `components/site/*` 是**每个公开页面都会加载**的，
 * 它们一旦从那个聚合出口取一个 api，整个后台接口层就会跟着进前台首屏：
 * 实测（`npm run check:bundle`）首页 38 个 `<script>` 里就躺着 axios（约 20 KB gzip）
 * 与整套后台 API 模块（约 11 KB gzip），而前台一个都用不到 —— 它们本来是
 * `composables/useThemeSlots.ts` 里一行 `import {themeApi} from '@/api'` 带进来的。
 *
 * 所以前台走这个窄出口：
 *  - 只导出前台真的会调用的模块；
 *  - 模块本身仍是 axios 客户端（这些调用都发生在客户端交互里），但**只有用到它的
 *    组件所在的路由**才会加载到，不会再被布局钉在首屏关键路径上；
 *  - **服务端（SSR）取数请用 `composables/useApi.ts` 的 `apiGet` / `apiPage`**
 *    （基于 `$fetch`，服务端会自动使用绝对地址；axios 的 `baseURL` 是相对路径，
 *    在 Node 里会抛 `Invalid URL`）。
 *
 * 新增前台需要的能力时，在这里加一行导出，**不要**改回 `@/api`。
 */

// ---------------------------------------------------------------- 用户端（mobile）
export {mobileApi} from './modules/mobile'
export type {
  MobileArticlePayload,
  MobileCommentItem,
  MobileMediaFolder,
  MobileMediaItem,
  MobileMediaStats,
} from './modules/mobile'

// ---------------------------------------------------------------- 内容
export {categoryApi} from './modules/category'
export type {CategoryItem, CategoryPayload} from './modules/category'

export {articleApi} from './modules/article'
export type {ArticlePayload} from './modules/article'

// ---------------------------------------------------------------- 打赏
export {tippingApi} from './modules/tipping'
export type {PaymentLaunchInfo, TipConfig, TipItem} from './modules/tipping'

// ---------------------------------------------------------------- 浏览器推送
export {webPushApi} from './modules/webPush'
export type {WebPushSubscriptionIn} from './modules/webPush'

// ---------------------------------------------------------------- GraphQL（公开查询）
// GraphQL 端点与 REST 同源鉴权，其中 `publicArticles` / `publicArticle` /
// `categories` / `tags` 是**公开查询**（无需登录），属于前台能力；受保护的管理端
// 查询（`articles` / `article` / 两个写接口）要求登录与权限码，前台正常用不到。
// 与其他模块一样：只有真正 import 它的路由才会加载到 axios，不会被钉在首屏。
export {graphqlApi} from './modules/graphql'
export type {
  GqlArticle,
  GqlArticleConnection,
  GqlCategory,
  GqlPublicArticlesQuery,
  GqlTag,
  GqlViewer,
} from './modules/graphql'
