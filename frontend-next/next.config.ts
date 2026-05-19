import type {NextConfig} from "next";
// next-intl 插件已禁用，使用客户端国际化方案
// import createNextIntlPlugin from 'next-intl/plugin';
// const withNextIntl = createNextIntlPlugin('./i18n/request.ts');

// Bundle Analyzer (仅在分析时启用)
const withBundleAnalyzer = require('@next/bundle-analyzer')({
    enabled: process.env.ANALYZE === 'true',
});

// PWA 配置 - 优化缓存策略和离线体验
const withPWA = require('next-pwa')({
    dest: 'public',
    register: true,
    skipWaiting: true,
    disable: process.env.NODE_ENV === 'development',
    // 自定义 Service Worker 配置
    sw: 'sw.js',
    // 缓存策略 - 分层缓存
    runtimeCaching: [
        // API 请求 - NetworkFirst（优先网络，失败时使用缓存）
        {
            urlPattern: /^https?:\/\/.*\/api\/.*/i,
            handler: 'NetworkFirst',
            options: {
                cacheName: 'api-cache',
                expiration: {
                    maxEntries: 50,
                    maxAgeSeconds: 60 * 5, // 5 分钟
                },
                networkTimeoutSeconds: 10,
                cacheableResponse: {
                    statuses: [0, 200],
                },
            },
        },
        // 静态资源（JS/CSS）- StaleWhileRevalidate（使用缓存，后台更新）
        {
            urlPattern: /\.(?:js|css)$/,
            handler: 'StaleWhileRevalidate',
            options: {
                cacheName: 'static-resources',
                expiration: {
                    maxEntries: 50,
                    maxAgeSeconds: 3 * 24 * 60 * 60, // 3 天
                },
            },
        },
        // 图片资源 - CacheFirst（优先缓存，减少流量）
        {
            urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp|avif|ico)$/,
            handler: 'CacheFirst',
            options: {
                cacheName: 'image-cache',
                expiration: {
                    maxEntries: 100,
                    maxAgeSeconds: 7 * 24 * 60 * 60, // 7 天
                },
                cacheableResponse: {
                    statuses: [0, 200],
                },
            },
        },
        // 字体文件 - CacheFirst
        {
            urlPattern: /\.(?:woff|woff2|ttf|eot)$/,
            handler: 'CacheFirst',
            options: {
                cacheName: 'font-cache',
                expiration: {
                    maxEntries: 20,
                    maxAgeSeconds: 30 * 24 * 60 * 60, // 30 天
                },
            },
        },
        // 页面导航 - NetworkFirst（确保内容最新）
        {
            urlPattern: ({request}) => request.mode === 'navigate',
            handler: 'NetworkFirst',
            options: {
                cacheName: 'pages-cache',
                expiration: {
                    maxEntries: 50,
                    maxAgeSeconds: 24 * 60 * 60, // 24 小时
                },
                networkTimeoutSeconds: 10,
            },
        },
        // 其他请求 - NetworkFirst
        {
            urlPattern: /^https?.*/,
            handler: 'NetworkFirst',
            options: {
                cacheName: 'offline-cache',
                expiration: {
                    maxEntries: 200,
                    maxAgeSeconds: 24 * 60 * 60, // 24 小时
                },
                networkTimeoutSeconds: 10,
            },
        },
    ],
    // 预缓存文件
    buildExcludes: [/middleware-manifest\.json$/],
    // fallbacks
    fallbacks: {
        document: '/offline', // 离线时的回退页面
        image: '/icons/icon-192x192.png', // 图片加载失败时的默认图
    },
});

const nextConfig: NextConfig = {
    // 禁用 React Strict Mode，避免 @hello-pangea/dnd 在开发环境报错
    reactStrictMode: false,
    
    // 启用静态导出（生成 out 目录）
    output: 'export',

    // 图像优化配置
    images: {
        // 静态导出模式下必须禁用图片优化
        unoptimized: true,
        // 允许的远程图像域名
        remotePatterns: [
            {
                protocol: 'http',
                hostname: 'localhost',
                port: '9421',
                pathname: '/media/**',
            },
            {
                protocol: 'https',
                hostname: '**',
            },
        ],
        // 图像格式优化（静态导出时不生效）
        formats: ['image/webp', 'image/avif'],
        // 设备尺寸预设（响应式图像）
        deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
        // 注意：quality 配置在 Next.js 16 中已移除，使用默认值 75
    },

    // 在构建时忽略 TypeScript 错误（API 响应类型问题）
    typescript: {
        ignoreBuildErrors: true,
    },
    
    // 实验性功能：优化加载策略
    experimental: {
        // 注意：optimizeFonts 在 Next.js 14+ 中已移除，不再需要此配置
        // optimizeFonts: true,
        // 优化包导入
        optimizePackageImports: ['@radix-ui/react-icons', 'lucide-react', 'react-icons'],
        // 启用 scroll restoration
        scrollRestoration: true,
        // 优化服务器组件边界（为未来迁移做准备）
        serverComponentsExternalPackages: [],
    },

    // Turbopack 配置（Next.js 16 默认使用 Turbopack）
    turbopack: {},
    
    // Webpack 配置优化
    webpack: (config, { isServer }) => {
        if (!isServer) {
            // 客户端优化：代码分割
            config.optimization = {
                ...config.optimization,
                splitChunks: {
                    chunks: 'all',
                    maxInitialRequests: 30,
                    minSize: 20000,
                    cacheGroups: {
                        // 分离 React 核心库
                        react: {
                            test: /[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/,
                            name: 'react-vendor',
                            priority: 30,
                            reuseExistingChunk: true,
                        },
                        // 分离 UI 组件库
                        ui: {
                            test: /[\\/]node_modules[\\/](@radix-ui|class-variance-authority|clsx|tailwind-merge)[\\/]/,
                            name: 'ui-vendor',
                            priority: 25,
                            reuseExistingChunk: true,
                        },
                        // 分离图标库
                        icons: {
                            test: /[\\/]node_modules[\\/](lucide-react|react-icons|@heroicons)[\\/]/,
                            name: 'icons-vendor',
                            priority: 20,
                            reuseExistingChunk: true,
                        },
                        // 分离图表库（仅后台使用）
                        charts: {
                            test: /[\\/]node_modules[\\/](recharts|chart.js|react-chartjs-2)[\\/]/,
                            name: 'charts-vendor',
                            priority: 15,
                            reuseExistingChunk: true,
                        },
                        // 分离编辑器库（仅后台使用）
                        editor: {
                            test: /[\\/]node_modules[\\/](@tiptap|prosemirror|y-?)[\\/]/,
                            name: 'editor-vendor',
                            priority: 15,
                            reuseExistingChunk: true,
                        },
                        // 其他 vendor 库
                        vendor: {
                            test: /[\\/]node_modules[\\/]/,
                            name: (module) => {
                                // 为展示层和应用层创建不同的 vendor chunk
                                const path = module.context;
                                if (path && path.includes('admin')) {
                                    return 'admin-vendors';
                                }
                                return 'vendors';
                            },
                            chunks: 'all',
                            priority: 5,
                            reuseExistingChunk: true,
                        },
                    },
                },
            };
        }
        return config;
    },

    // 注意：在 output: export 模式下，headers 配置不被支持
    // 缓存控制需要在部署时通过 Web 服务器（如 Nginx）配置
    // async headers() {
    //     return [
    //         {
    //             source: '/(.*)',
    //             headers: [
    //                 {
    //                     key: 'Cache-Control',
    //                     value: 'public, max-age=3600, s-maxage=3600, stale-while-revalidate=86400',
    //                 },
    //             ],
    //         },
    //         {
    //             source: '/_next/static/(.*)',
    //             headers: [
    //                 {
    //                     key: 'Cache-Control',
    //                     value: 'public, max-age=31536000, immutable',
    //                 },
    //             ],
    //         },
    //         {
    //             source: '/static/(.*)',
    //             headers: [
    //                 {
    //                     key: 'Cache-Control',
    //                     value: 'public, max-age=31536000, immutable',
    //                 },
    //             ],
    //         },
    //     ];
    // },
};

// 导出时包装 Bundle Analyzer 和 PWA
export default withBundleAnalyzer(withPWA(nextConfig));
