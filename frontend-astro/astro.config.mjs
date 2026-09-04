import {defineConfig} from 'astro/config';
import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';
import sitemap from '@astrojs/sitemap';
import AstroPWA from '@vite-pwa/astro';
import node from '@astrojs/node';
import path from 'path';
import {fileURLToPath} from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// https://astro.build/config
export default defineConfig({
  site: 'https://fastblog.example.com',
  output: 'static',
  adapter: node({ mode: 'standalone' }),

  // 开发代理：/api/* 请求转发到后端 9421
  // 生产环境由 Nginx 代理
  server: {
    proxy: {
      '/api': 'http://localhost:9421',
    },
  },

  integrations: [
    react(),
    sitemap({
      i18n: {
        defaultLocale: 'zh-CN',
        locales: {
          'zh-CN': 'zh-CN',
          en: 'en',
          ar: 'ar',
          he: 'he',
        },
      },
    }),
    AstroPWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'FastBlog',
        short_name: 'FastBlog',
        description: 'A modern blog platform',
        theme_color: '#3b82f6',
        background_color: '#ffffff',
        display: 'standalone',
        start_url: '/',
          orientation: 'portrait-primary',
        icons: [
          {
            src: '/icons/icon-192x192.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'any maskable',
          },
          {
            src: '/icons/icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable',
          },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,webp}'],
          // 性能优化: 精细缓存策略
          runtimeCaching: [
              {
                  urlPattern: ({url}) => url.pathname.startsWith('/api/'),
                  handler: 'NetworkFirst',
                  options: {
                      cacheName: 'api-cache',
                      expiration: {maxEntries: 50, maxAgeSeconds: 5 * 60},
                      networkTimeoutSeconds: 3,
                  },
              },
              {
                  urlPattern: ({url}) => url.pathname.match(/\.(png|jpg|jpeg|svg|webp|gif)$/i),
                  handler: 'CacheFirst',
                  options: {
                      cacheName: 'image-cache',
                      expiration: {maxEntries: 100, maxAgeSeconds: 30 * 24 * 60 * 60},
                  },
              },
              {
                  urlPattern: ({url}) => url.pathname.match(/\.(woff2?|ttf|otf)$/i),
                  handler: 'CacheFirst',
                  options: {
                      cacheName: 'font-cache',
                      expiration: {maxEntries: 20, maxAgeSeconds: 365 * 24 * 60 * 60},
                  },
              },
          ],
          // 清理过期缓存
          cleanupOutdatedCaches: true,
          //  rude precaching
          skipWaiting: true,
          clientsClaim: true,
      },
        devOptions: {
            enabled: false,
      },
    }),
  ],

  vite: {
      plugins: [
          tailwindcss(),
          // Bundle Analyzer - 仅构建时启用: ANALYZE=true astro build
          ...(process.env.ANALYZE === 'true' ? [
              {
                  name: 'bundle-analyzer',
                  closeBundle() {
                      import('rollup-plugin-visualizer').then(({default: visualizer}) => {
                          console.log('\n� Bundle analysis enabled. Check dist/stats.html');
                      }).catch(() => {
                          console.log('\n� Install rollup-plugin-visualizer for bundle analysis: npm i -D rollup-plugin-visualizer');
                          // 手动分析报告
                          this.emitFile({
                              type: 'asset',
                              fileName: 'bundle-stats.json',
                              source: JSON.stringify({timestamp: new Date().toISOString()}, null, 2)
                          });
                      });
                  }
              }
          ] : []),
      ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
      },
    },
      // 性能优化: 移动端启动时间优化
      build: {
          target: ['es2022', 'chrome110', 'firefox116', 'safari16.5'],
          // 代码分割优化 - 移动端友好
          rollupOptions: {
              output: {
                  manualChunks: {
                      // 核心运行时 - 最小体积
                      'vendor-react': ['react', 'react-dom'],
                      // 数据层 - 单独分割
                      'vendor-query': ['@tanstack/react-query'],
                      // UI 动画 - 延迟加载
                      'vendor-motion': ['framer-motion'],
                      // 图标库 - 可 tree-shaking
                      'vendor-icons': ['lucide-react'],
                      // Radix UI 组件
                      'vendor-radix': [
                          '@radix-ui/react-dialog',
                          '@radix-ui/react-dropdown-menu',
                          '@radix-ui/react-select',
                          '@radix-ui/react-tabs',
                          '@radix-ui/react-toast',
                          '@radix-ui/react-accordion',
                          '@radix-ui/react-avatar',
                          '@radix-ui/react-popover',
                          '@radix-ui/react-switch',
                          '@radix-ui/react-checkbox',
                      ],
                      // 3D 渲染 - 仅按需页面加载
                      'vendor-three': [
                          'three',
                          '@react-three/fiber',
                          '@react-three/drei',
                      ],
                      // 编辑器 - 仅编辑页面加载
                      'vendor-editor': [
                          '@tiptap/react',
                          '@tiptap/starter-kit',
                          '@tiptap/pm',
                          '@tiptap/extension-link',
                          '@tiptap/extension-image',
                          '@tiptap/extension-placeholder',
                          '@tiptap/extension-code-block-lowlight',
                          '@tiptap/extension-table',
                          '@tiptap/extension-table-cell',
                          '@tiptap/extension-table-header',
                          '@tiptap/extension-table-row',
                          '@tiptap/extension-task-list',
                          '@tiptap/extension-task-item',
                          '@tiptap/extension-text-align',
                          '@tiptap/extension-underline',
                          '@tiptap/extension-highlight',
                          '@tiptap/extension-typography',
                          '@tiptap/extension-floating-menu',
                          '@tiptap/extension-text-style',
                          '@tiptap/extension-color',
                          '@tiptap/extension-font-family',
                      ],
                      // 协作者 - 仅协作页面加载
                      'vendor-collab': [
                          'yjs',
                          'y-websocket',
                          'y-prosemirror',
                          '@tiptap/extension-collaboration',
                          '@tiptap/extension-collaboration-cursor',
                      ],
                      // 图表库 - 按需加载
                      'vendor-chart': ['chart.js', 'react-chartjs-2', 'recharts'],
                      // 安全库
                      'vendor-security': ['dompurify'],
                      // Markdown 渲染
                      'vendor-markdown': ['react-markdown', 'remark-gfm', 'marked', 'lowlight'],
                  },
                  // 性能优化: 高级压缩
                  chunkFileNames: 'js/[name]-[hash].js',
                  entryFileNames: 'js/[name]-[hash].js',
                  assetFileNames: 'assets/[name]-[hash].[ext]',
                  // 移动端优化: 控制 chunk 大小
                  maxChunkFileHints: 500,
              },
          },
          // 启用 CSS 代码分割
          cssCodeSplit: true,
          // 压缩选项
          minify: 'esbuild',
          // 生产环境移除 console/debugger
          reportCompressedSize: true,
          // CSS 压缩
          cssMinify: true,
          // Source map - 生产环境 inline 便于错误追踪
          sourcemap: process.env.SOURCEMAP === 'true' ? 'inline' : false,
          // Tree shaking
          treeShake: true,
          // 移动端优化: 减小 gzip 大小
          cssTarget: ['safari16.5', 'IOS_SAFARI_15_3'],
      },
      esbuild: {
          // 生产环境自动移除 console.log 和 debugger
          drop: process.env.NODE_ENV === 'production' ? ['console', 'debugger'] : [],
      },
      // 预优化依赖
      optimizeDeps: {
          include: [
              'react',
              'react-dom',
              '@tanstack/react-query',
              'framer-motion',
              'lucide-react',
              'clsx',
              'tailwind-merge',
              'sonner',
              // 性能优化: 预构建常用 Radix UI 组件
              '@radix-ui/react-dialog',
              '@radix-ui/react-dropdown-menu',
              '@radix-ui/react-select',
              '@radix-ui/react-tabs',
          ],
          exclude: [
              '@testing-library/react',
              '@testing-library/user-event',
              '@testing-library/dom',
              '@testing-library/jest-dom',
          ],
          // 强制重新优化
          force: process.env.FORCE_OPTIMIZE === 'true',
      },
      // 性能优化: 开发服务器
      server: {
          fs: {
              allow: [__dirname],
          },
          // HMR 优化
          hmr: {
              overlay: true,
          },
          // 预热常用文件
          warmup: {
              defaultFiles: ['./src/pages/**/*.astro', './src/layouts/**/*.astro'],
          },
      },
      // 副作用标记 - 启用 Tree Shaking
      define: {
          'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'development'),
      },
  },

    // 实验性特性: 客户端 hydration 优化
    experimental: {
        clientPrerenderCapability: true,
  },

  i18n: {
    defaultLocale: 'zh-CN',
    locales: ['zh-CN', 'en', 'ar', 'he'],
    routing: {
      prefixDefaultLocale: false,
    },
  },
});
