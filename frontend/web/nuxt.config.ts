import tailwindcss from '@tailwindcss/vite'

/**
 * Nuxt 4.5 配置（前台 SSR + 管理后台 CSR 同项目）
 *
 * 目录约定：复用既有 `src/`（Nuxt 4 默认是 `app/`，这里显式指定 srcDir）。
 *  - `src/pages/**`      页面（前台在根路径，后台在 `/admin/**`）
 *  - `src/layouts/**`    布局（`site` 前台 / `admin` 后台）
 *  - `src/middleware/**` 路由中间件（凭据与权限校验）
 *  - `src/components/ui` shadcn-vue 基础组件
 */
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  srcDir: 'src',

  // 前台需要 SEO 与首屏直出；管理后台在 routeRules 里单独关掉 SSR
  ssr: true,

  devtools: {enabled: true},
  modules: ['@pinia/nuxt', '@nuxt/scripts', '@vite-pwa/nuxt', '@nuxtjs/i18n'],

  // i18n：文案在 i18n/locales/*.json（这两个文件是从迁移前的 frontend-astro 取回的）
  //
  // `strategy: 'no_prefix'` —— URL 不带语言前缀，**不改变现有路由**
  // （前台已有 /articles、/p/{slug} 等 SEO 路径，带前缀会连带影响 sitemap、PWA 与已收录链接）。
  // 切换语言走 `useI18n().setLocale()`，选择由模块记在 cookie 里。
  i18n: {
    // 文案目录指向**派生**目录：由 scripts/split-i18n.mjs 从真相源 `i18n/locales/*.json`
    // 生成，只含前台命名空间。后台专属的 `admin`（占全部文案的 77.5%）已拆到
    // `public/i18n/admin/`，由 layouts/admin.vue 按需加载。
    //
    // ⚠️ 这个路径是相对 `restructureDir`（默认 `i18n`）解析的，**不是**相对项目根 ——
    // 写成 'i18n/messages' 会被解析成 `<root>/i18n/i18n/messages`（实测报 ENOENT）。
    langDir: 'messages',

    // `dir` 由 app.vue 写入 `<html dir>`（当前都是 ltr，为将来接 RTL 语言预留）
    //
    // ⚠️ 默认语言 zh-CN 的 `file` 指向一个**空占位**（`i18n/messages/zh-CN.json` = `{}`），
    // 它的真实前台文案由 `i18n/i18n.config.ts` 直接 import 内联进 bundle。
    //
    // 为什么不能干脆不给 zh-CN 配 `file`：模块有硬校验「使用 `langDir` 时每个 locale
    // 都必须有 `file`/`files`」（`checkLayerOptions`），而客户端的 `loadMessagesFromServer`
    // 入口是 `if (locale in localeLoaders === false) return` —— 只要有 `file` 就必然发一次
    // `/_i18n/<hash>/<locale>/messages.json`，**躲不掉**。既然躲不掉，就让默认语言这次
    // 请求的响应体小到可忽略（空对象 merge 进去无影响）：
    // 193 KB raw / 66 KB gzip → 约 3 字节。真正的文案走构建期内联。
    //
    // `en` 是非默认语言（本站 `detectBrowserLanguage: false`），它的 `file` 是真正的前台文案，
    // 切到英文时才加载，不给每个访客的 bundle 加体积。
    locales: [
      // zh-CN 的 file 指向**空占位**（真实文案由 i18n/i18n.config.ts 内联，见上）
      {code: 'zh-CN', language: 'zh-CN', name: '简体中文', file: {path: 'zh-CN.json', cache: true}, dir: 'ltr'},
      {code: 'en', language: 'en-US', name: 'English', file: {path: 'en.json', cache: true}, dir: 'ltr'},
    ],
    defaultLocale: 'zh-CN',
    strategy: 'no_prefix',
    // 中文站默认不做浏览器语言自动跳转（要开时改成 {alwaysRedirect: true} 之类）
    detectBrowserLanguage: false,

    experimental: {
      // `en` 仍走 lazy file（Nitro 路由），给它一个显式长缓存。
      // 默认只有 10 秒，且模块的 `loadMessages` 会给请求带上 `Cache-Control: no-cache`
      // （`cacheable ? {} : {...}`）→ 等于每次都全量重下；上面 `cache: true` 关掉那个头。
      httpCacheDuration: 86400,
    },
  },

  // 说明：**不再使用 `@nuxt/image`**（该模块与曾经的 `image` 配置已移除）。
  // 全仓 `NuxtImg` / `NuxtPicture` 使用数为 0 —— 图片走的是
  // `components/site/ResponsiveImage.vue`，直接手写 `srcset` 对接后端的变体端点
  // （自带 200/480/800/1600 四档、`Accept` 协商 avif→webp→原格式、内容寻址落盘懒生成），
  // 比再套一层 ipx 更快也更可控。留着这个模块只会让构建无谓地带进 sharp。

  // 三方脚本：用 useScript() 管理加载时机与隐私（默认不加载第三方）
  scripts: {
    registry: {},
  },

  // PWA：提供 manifest 与 Service Worker（离线访问、安装到桌面）
  // 离线下载（OfflineDownloadDialog）复用同一套 Workbox 运行时缓存
  pwa: {
    registerType: 'autoUpdate',
    manifest: {
      name: 'FastBlog',
      short_name: 'FastBlog',
      description: 'FastBlog 博客',
      lang: 'zh-CN',
      start_url: '/',
      scope: '/',
      display: 'standalone',
      background_color: '#ffffff',
      theme_color: '#2f6fed',
      icons: [
        {src: '/icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any'},
      ],
    },
    workbox: {
      // 只预缓存静态资源；页面走网络优先，避免内容站拿到过期 HTML
      globPatterns: ['**/*.{js,css,html,svg,ico,woff2}'],
      navigateFallback: '/',
      // `/__site/` 是内部聚合接口（见 server/routes/__site/bootstrap.get.ts），
      // 不是页面：必须排除，否则 SW 会把它的请求回退成 HTML
      navigateFallbackDenylist: [/^\/api\//, /^\/admin\//, /^\/system\//, /^\/__site\//],
      runtimeCaching: [
        {
          // 媒体文件：缓存优先，方便离线查看已浏览过的图片
          // （媒体文件 URL 收敛在 /api/v3 之下：content/media/{id}/file 与 assets/storage）
          urlPattern: /^https?:\/\/.*\/api\/v3\/(content\/media\/[\w.-]+\/file|assets\/storage\/.*)/i,
          handler: 'CacheFirst',
          options: {
            cacheName: 'media-assets',
            expiration: {maxEntries: 200, maxAgeSeconds: 60 * 60 * 24 * 30},
          },
        },
      ],
    },
    // 开发期不启用 SW，避免缓存干扰调试
    devOptions: {enabled: false, suppressWarnings: true},
  },

  css: ['~/styles/index.css'],

  // shadcn-vue 风格的组件目录：文件名即组件名（<Button>/<Card>），不加目录前缀
  // 只扫描 .vue（`ui/*/index.ts` 是给显式 import 用的聚合出口，不应被当作组件）
  components: [{path: '~/components', pathPrefix: false, extensions: ['vue']}],

  vite: {
    plugins: [tailwindcss()],
  },

  devServer: {
    port: Number(process.env.VITE_PORT || 5173),
    host: '0.0.0.0',
  },

  // 开发期把 /api 代理到后端（生产由 nginx 反代）
  // 注意：devProxy 挂载前缀会被 h3 路由剥掉（req.url 不含 /api），
  // 因此 target 必须带同样的路径前缀，否则后端收到的是 /v3/** 而 404。
  // 媒体文件统一走 /api/v3/content/media/{id}/file 与 /api/v3/assets/storage/**，
  // 因此不再需要 /media 代理规则——它会把前台页面路由 /media 劫持给后端。
  //
  // **WebSocket 不走这里**：`Upgrade` 事件既不经过 nitro.devProxy（它是 HTTP 中间件），
  // 也不经过 Vite 的 `server.proxy`（dev 下 Vite 只是中间件，没有自己的 HTTP server，
  // 实测其 `configure` 回调收不到 upgrade）。因此浏览器侧的 WS 在 dev 下**直连后端**，
  // 由运行时配置 `NUXT_PUBLIC_WS_BASE_URL` 指定（见 .env.development）；生产留空，
  // 走同源，由 nginx 转发（`nginx.conf` 里 `map $http_upgrade $connection_upgrade`）。
  nitro: {
    devProxy: {
      '/api': {
        target: `${process.env.VITE_PROXY_TARGET || 'http://localhost:9421'}/api`,
        changeOrigin: true,
      },
    },
  },

  // 服务端渲染时不能使用相对路径请求，需要绝对后端地址；
  // 浏览器侧留空表示走同源，由 nginx / devProxy 转发。
  runtimeConfig: {
    public: {
      apiBaseUrl: process.env.NUXT_PUBLIC_API_BASE_URL || '',
      // 浏览器侧 WebSocket 基址。**dev 下必须显式指定**（如 ws://127.0.0.1:9421），
      // 因为 WS 的 upgrade 既不经 nitro.devProxy 也不经 Vite proxy（见上面的说明）；
      // 生产留空 → 同源，由 nginx 转发 Upgrade。
      wsBaseUrl: process.env.NUXT_PUBLIC_WS_BASE_URL || '',
      // RUM 上报端点：v3 已提供 `POST /api/v3/system/health/web-vitals`（同源、公开、无需鉴权）。
      // 要临时关闭上报，显式设 NUXT_PUBLIC_RUM_ENDPOINT=""（这里用 ?? 而非 ||，以保留空串语义）。
      rumEndpoint: process.env.NUXT_PUBLIC_RUM_ENDPOINT ?? '/api/v3/system/health/web-vitals',
    },
  },

  routeRules: {
    // 管理后台保持 SPA 行为（与原 Vite 版一致：登录态在本地存储，无需 SSR）
    '/dashboard': {ssr: false},
    '/system/**': {ssr: false},
    '/content/**': {ssr: false},
    '/analytics/**': {ssr: false},
    '/extension/**': {ssr: false},
    '/ops/**': {ssr: false},
    '/403': {ssr: false},
    // 用户中心与投稿依赖登录态（存于本地存储），关闭 SSR
    '/profile': {ssr: false},
    '/media': {ssr: false},
    '/my/**': {ssr: false},
    // 站内信依赖登录态，同样关闭 SSR
    '/messages': {ssr: false},
    // 关注 / 粉丝同样依赖登录态（存于本地存储），关闭 SSR
    '/fans': {ssr: false},
    // 积分 / 勋章中心：内容依赖登录态与实时统计，同样走 SPA
    '/points': {ssr: false},
    '/badges': {ssr: false},
    // 专家认证（我的认证）与打赏收益同样依赖登录态
    '/certification': {ssr: false},
    '/tipping': {ssr: false},
    // 后台新增：用户成长（积分 / 勋章 / 认证审核）与打赏提现审核
    '/gamification/**': {ssr: false},
    '/commerce/tipping': {ssr: false},
    // 关注流与群聊（批次 17）：依赖登录态 / 实时连接，统一走 SPA
    '/feed': {ssr: false},
    '/chat': {ssr: false},
    '/chat/**': {ssr: false},
    // 公开内容页做短缓存（swr = stale-while-revalidate：先给旧内容，后台再刷新）
    //
    // ⚠️ 前提是响应里**没有 set-cookie**：被缓存的响应若带着某个用户的偏好写回，
    // 就会污染其他访问者。app.vue 里已把主题/配色 cookie 改成服务端只读（见该文件说明）。
    '/': {swr: 60},
    '/about': {swr: 300},
    '/discover': {swr: 60},
    '/categories': {swr: 300},
    '/experts/**': {swr: 60},
    // 后台「单页管理」发布的固定页，内容变动极少
    '/p/**': {swr: 300},
    // 首页与文章页做短缓存
    '/articles/**': {swr: 60},
    '/category/**': {swr: 60},
    // 例外：`/articles/id/**` 是后台编辑器的预览入口（按 id 访问，草稿也能看）。
    // 刚保存就要能看到最新内容，所以不能吃上面那条 60s 的 swr 缓存；
    // 更具体的路径规则优先于 `/articles/**`。
    '/articles/id/**': {swr: false},
  },

  app: {
    head: {
      htmlAttrs: {lang: 'zh-CN'},
      meta: [
        {charset: 'utf-8'},
        {name: 'viewport', content: 'width=device-width, initial-scale=1'},
      ],
      link: [{rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg'}],
    },
  },

  typescript: {
    strict: true,
    typeCheck: false,
  },
})
