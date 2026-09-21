# fastblog-web

FastBlog 前端：**Nuxt 4.5 单工程**同时承载

- **博客前台**（`/`、`/articles`、`/p/{slug}`、`/categories`、`/search`、`/experts`、`/home/{username}`、`/feed`、`/chat`、`/vip`、
  `/profile`…）—— SSR，面向 SEO；
- **管理后台**（`/dashboard`、`/system/**`、`/content/**`、`/analytics/**`、`/extension/**`、`/ops/**`、`/marketing/**`、
  `/commerce/**`、`/gamification/**`、`/my/**`…）—— `ssr: false`，SPA 行为。

当前规模：**87 个页面**、**63 个 `api/modules/*.ts`**、9 个 composable、i18n **3067 个 key**（中英对称）。

## 环境要求

- **Node ≥ 22.19**（或 ≥ 24.11 / ≥ 26）：Nuxt 4.5 的 `@nuxt/nitro-server`、`@nuxt/vite-builder`、cssnano 都声明了该范围，Node
  25 会被拒（EBADENGINE）。`Dockerfile` 使用 `node:22-alpine`。
- 依赖安装必须走锁文件：`npm ci`（CI 与镜像构建用的都是它）。

## 快速开始

```bash
npm ci                 # 触发 postinstall → nuxt prepare
npm run dev            # http://localhost:5173（/api 代理到后端 :9421）
npm run build          # 产物 .output/，用 node .output/server/index.mjs 启动
npm run type-check     # prescan + nuxt typecheck
npm run check:i18n     # i18n 校验（改文案后必跑）
npm run test:e2e       # Playwright（7 个 spec）
```

脚本一览（`package.json`）：

| 脚本            | 说明                                                                                                                                                      |
|---------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| `prescan`     | 扫描 `../../plugins/*/frontend/`，生成 `src/.plugin-pages/**` 与 `src/.plugin-registry.ts`（由 `predev` / `prebuild` 自动触发，`type-check` 与 `build:check` 里显式再跑一次） |
| `dev`         | `nuxt dev --dotenv .env.development`                                                                                                                    |
| `build`       | `nuxt build --dotenv .env.production`                                                                                                                   |
| `build:check` | prescan + `nuxt typecheck` + build                                                                                                                      |
| `generate`    | 静态导出（Capacitor 打包用）                                                                                                                                     |
| `preview`     | 预览构建产物                                                                                                                                                  |
| `type-check`  | `nuxt typecheck`                                                                                                                                        |
| `check:i18n`  | `node scripts/check-i18n.mjs`                                                                                                                           |
| `test:e2e`    | `playwright test`                                                                                                                                       |

## 环境变量

`.env.development`：

```
VITE_PORT=5173                                 # 开发端口
VITE_PROXY_TARGET=http://localhost:9421        # dev 期 /api 代理目标（同时供 SSR 服务端请求）
NUXT_PUBLIC_API_BASE_URL=http://localhost:9421 # SSR 阶段请求后端的绝对地址；浏览器侧留空走同源
NUXT_PUBLIC_WS_BASE_URL=ws://127.0.0.1:9421    # 浏览器侧 WebSocket 基址；仅 dev 需要
```

`.env.production`：`NUXT_PUBLIC_API_BASE_URL` 与 `NUXT_PUBLIC_WS_BASE_URL` 都**留空**——浏览器走同源，SSR
的绝对地址由部署环境注入（Compose 里是 `http://backend:9421`）。

> WS 的 `Upgrade` 在 dev 下**不经任何代理**（`nitro.devProxy` 与 Vite 的 `server.proxy` 都不处理 upgrade），所以必须用
`NUXT_PUBLIC_WS_BASE_URL` 直连后端；生产由 nginx 转发。另外 dev 用 `127.0.0.1` 而非 `localhost`：Windows 上 `localhost`
> 先解析到 `::1`，而后端只监听 IPv4。

## 目录

```
src/
  app.vue / error.vue      根组件（写入 data-theme / data-accent）/ 全局错误页（404、500）
  layouts/                 default.vue（前台）、admin.vue（后台，Element Plus 懒加载）
  middleware/auth.ts       后台鉴权：登录态 + definePageMeta({permission}) → /403
  pages/                   87 个页面：前台在根路径，后台在 /dashboard、/system/** 等
  components/              ui/（shadcn 风格基础件）、site/（前台业务）、admin/、Placeholder.vue
  composables/             useApi（$fetch：SSR 绝对地址 / 浏览器同源）、useSiteInfo、useTheme、
                           useJsonLd、useHreflang、useWebVitals、useThemeSlots…
  api/request.ts           axios 客户端：/api/v3 前缀、注入 Bearer、code===200 成功、401 静默续期
  api/modules/             62 个按后端模块切分的接口封装（api/index.ts 聚合导出）
  store/modules/           user / permission / app（Pinia，客户端持久化）
  hooks/                   useTable 等
  lib/                     utils.ts（cn）、icons.ts（内联 SVG 图标表）
  utils/menus.ts           后台菜单结构（name 必须与后端 admin_menus.code 一致）
  styles/index.css         设计令牌（Tailwind 4 @theme）+ 深浅色 + 自选配色
i18n/locales/{zh-CN,en}.json   文案（两语言必须对称）
e2e/*.spec.ts              Playwright 回归用例
scripts/check-i18n.mjs     i18n 校验；scripts/i18n_tool.py 批量抽取/替换
Dockerfile                 node:22-alpine 多阶段：npm ci → nuxt build → 只带 .output 运行
```

## 约定

- **路由**：Nuxt 文件路由。页面**始终存在**，越权由 `middleware/auth.ts` 依 `definePageMeta({permission})` 拦截 → `/403`。
- **SSR 开关**：集中在 `nuxt.config.ts::routeRules`（后台、用户中心、消息、积分/勋章、认证/打赏、群聊等全部 `ssr: false`），列表页
  `swr: 60`。
- **菜单**：结构在前端（`utils/menus.ts`），**授权在后端**（`admin_menus` + `role_admin_menus`），两者 AND；后端未下发
  `menu_codes` 时不做菜单过滤，避免"已迁移未 seed"导致菜单全空。
- **权限码**：三段式 `module_{域}:{模块}:{动作}`，与后端 `capabilities.code` 一致；按钮级用 `v-auth`，超管直通。
- **UI 边界**：前台只用 `components/ui` 与 Tailwind；后台只用 `el-*`。前台页面会走 SSR，不要在非后台路由里直接使用 Element
  Plus；后台不要静态 `import {ElMessage}`，统一用 `@/utils/feedback`。
- **设计令牌**：颜色/圆角/宽度只能用 `styles/index.css` 的语义令牌（`--color-*`、`--radius-*`、`--container-*`
  ），禁止硬编码色值；换主题覆盖 `[data-theme='dark']`，自选配色切 `[data-accent='violet'|'emerald'|'rose'|'amber']`
  （唯一例外是主题切换器的色板）。
- **i18n**：文案放 locale 文件；**不要写 `{...}` 字面量**（vue-i18n 会当插值编译导致白屏），`check:i18n` 会用
  `@intlify/core-base` 逐条编译兜底。
- **组件命名**：Nuxt 保留 `Lazy*` 前缀，组件不要取名 `LazyXxx`；`<script setup>` 内不能 `export`，类型外置到
  `src/types/*.ts`。
- **图标**：用 `src/lib/icons.ts` + `components/ui/Icon.vue`（`<Icon name="search" class="h-4 w-4"/>`）；不要引入
  `@lucide/vue`。

## 相关文档

- [`docs/DEVELOPMENT.md`](../../docs/DEVELOPMENT.md)：整体架构、后端域模块与硬约定、测试与质量门。
- [`docs/DEPLOYMENT.md`](../../docs/DEPLOYMENT.md)：Compose / nginx / 环境变量 / 备份升级。
