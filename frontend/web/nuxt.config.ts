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
  modules: ['@pinia/nuxt', '@nuxt/image', '@nuxt/scripts', '@vite-pwa/nuxt', '@nuxtjs/i18n'],

  // i18n：文案在 i18n/locales/*.json（这两个文件是从迁移前的 frontend-astro 取回的）
  //
  // `strategy: 'no_prefix'` —— URL 不带语言前缀，**不改变现有路由**
  // （前台已有 /articles、/p/{slug} 等 SEO 路径，带前缀会连带影响 sitemap、PWA 与已收录链接）。
  // 切换语言走 `useI18n().setLocale()`，选择由模块记在 cookie 里。
  i18n: {
    locales: [
      {code: 'zh-CN', language: 'zh-CN', name: '简体中文', file: 'zh-CN.json'},
      {code: 'en', language: 'en-US', name: 'English', file: 'en.json'},
    ],
    defaultLocale: 'zh-CN',
    strategy: 'no_prefix',
    // 中文站默认不做浏览器语言自动跳转（要开时改成 {alwaysRedirect: true} 之类）
    detectBrowserLanguage: false,
  },

  // 图片：使用本地 ipx 处理（自动 srcset / 格式转换），前台用 <NuxtImg>/<NuxtPicture>
  image: {
    format: ['webp', 'avif'],
    screens: {
      xs: 320,
      sm: 640,
      md: 768,
      lg: 1024,
      xl: 1280,
    },
  },

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
      navigateFallbackDenylist: [/^\/api\//, /^\/admin\//, /^\/system\//],
      runtimeCaching: [
        {
          // 媒体文件：缓存优先，方便离线查看已浏览过的图片
          urlPattern: /^https?:\/\/.*\/media\/.*/i,
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

  // 开发期把 /api 与 /media 代理到后端（生产由 nginx 反代）
  nitro: {
    devProxy: {
      '/api': {
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:9421',
        changeOrigin: true,
      },
      '/media': {
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:9421',
        changeOrigin: true,
      },
    },
  },

  // 服务端渲染时不能使用相对路径请求，需要绝对后端地址；
  // 浏览器侧留空表示走同源，由 nginx / devProxy 转发。
  runtimeConfig: {
    public: {
      apiBaseUrl: process.env.NUXT_PUBLIC_API_BASE_URL || '',
      // RUM 上报端点；留空表示只本地采集（后端 v3 暂无该端点）
      rumEndpoint: process.env.NUXT_PUBLIC_RUM_ENDPOINT || '',
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
    // 首页与文章页做短缓存
    '/articles/**': {swr: 60},
    '/category/**': {swr: 60},
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
