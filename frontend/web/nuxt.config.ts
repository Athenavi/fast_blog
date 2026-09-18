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
  modules: ['@pinia/nuxt'],

  css: ['~/styles/index.css'],

  // shadcn-vue 风格的组件目录：文件名即组件名（<Button>/<Card>），不加目录前缀
  // 只扫描 .vue（`ui/*/index.ts` 是给显式 import 用的聚合出口，不应被当作组件）
  components: [{path: '~/components', pathPrefix: false, extensions: ['vue']}],

  vite: {
    plugins: [tailwindcss()],
    build: {
      rollupOptions: {
        output: {
          // Vite 8（rolldown）要求 manualChunks 为函数；Element Plus 体积较大，单独分块
          manualChunks(id: string) {
            if (id.includes('element-plus') || id.includes('@element-plus/icons-vue')) {
              return 'vendor-element'
            }
            if (id.includes('echarts')) return 'vendor-echarts'
            return undefined
          },
        },
      },
    },
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
    // 用户中心依赖登录态（存于本地存储），关闭 SSR
    '/profile': {ssr: false},
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
