# fastblog-web

FastBlog 前端：**Nuxt 4.5** 单工程同时承载

- **博客前台**（`/`、`/articles`、`/categories`、`/search`、`/about` …）—— SSR，面向 SEO；
- **管理后台**（`/dashboard`、`/system/**`、`/content/**` …）—— `ssr: false`，SPA 行为。

## 快速开始

```bash
npm install          # 触发 nuxt prepare
npm run dev          # http://localhost:5173（/api 与 /media 代理到 :9421）
npm run build        # 产物 .output/，用 node .output/server/index.mjs 启动
npm run type-check   # nuxt typecheck
```

环境变量见 `.env.development` / `.env.production`：

```
VITE_PORT=5173                                 # 开发端口
VITE_PROXY_TARGET=http://localhost:9421        # dev 代理目标（同时供 SSR 服务端请求）
NUXT_PUBLIC_API_BASE_URL=http://localhost:9421 # SSR 阶段请求后端的绝对地址；浏览器侧留空走同源
```

## 目录

```
src/
  app.vue / error.vue      Nuxt 根组件 / 全局错误页（404、500）
  layouts/                 default.vue（前台）、admin.vue（后台）
  middleware/auth.ts       后台鉴权：登录态 + 页面级权限
  plugins/                 Element Plus、v-auth 指令、pinia 持久化（均 .client）
  components/ui/           shadcn-vue 基础组件（Button、Card、Input、Badge、Skeleton）
  components/site/         前台组件（SiteHeader、ArticleCard、ArticleListSection …）
  composables/             useApi（apiGet / apiPage）、useSiteInfo
  pages/                   前台在根路径；后台在 /dashboard、/system/** 等
  store/modules/           user / permission / app
  utils/menus.ts           后台菜单结构（name 与后端 admin_menus.code 对应）
  types/content.ts         前台内容类型
```

## 约定

- **路由**：Nuxt 文件路由。页面**始终存在**，越权由 `middleware/auth.ts` 依
  `definePageMeta({permission})` 拦截 → `/403`。
- **菜单**：结构在前端（`utils/menus.ts`），**授权在后端**（`admin_menus` + `role_admin_menus`），
  两者 AND；`store/modules/permission.ts` 负责过滤。后端未下发 `menu_codes` 时不做菜单过滤，
  避免"已迁移未 seed"导致菜单全空。
- **权限码**：三段式 `module_{域}:{模块}:{动作}`，与后端 `capabilities.code` 一致；
  按钮级用 `v-auth`，超管直通。
- **UI 边界**：前台只用 `components/ui` 与 Tailwind；后台只用 `el-*`。
  前台页面会走 SSR，**不要**在 `pages/`（非后台路由）里直接使用 Element Plus。

## 相关文档

- `docs/refactor/FRONTEND_NUXT_MIGRATION.md`：迁移决策、映射表、进度与待办
- `docs/refactor/PERMISSION_REFACTOR_PLAN.md`：后端权限体系（三段码、数据范围、菜单授权）
