import type {NextConfig} from "next";
// next-intl 插件已禁用，使用客户端国际化方案
// import createNextIntlPlugin from 'next-intl/plugin';
// const withNextIntl = createNextIntlPlugin('./i18n/request.ts');

// Bundle Analyzer (仅在分析时启用)
const withBundleAnalyzer = require('@next/bundle-analyzer')({
    enabled: process.env.ANALYZE === 'true',
});

const nextConfig: NextConfig = {
    // 禁用 React Strict Mode，避免 @hello-pangea/dnd 在开发环境报错
    reactStrictMode: false,
    
    // 启用静态导出（生成 out 目录）
    output: 'export',

    // 图像优化配置
    images: {
        // 启用图像优化
        unoptimized: false,
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
        // 图像格式优化
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
        optimizePackageImports: ['@radix-ui/react-icons', 'lucide-react'],
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
                    maxInitialRequests: 25,
                    minSize: 20000,
                    cacheGroups: {
                        // 分离 React 核心库
                        react: {
                            test: /[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/,
                            name: 'react-vendor',
                            priority: 20,
                        },
                        // 分离 UI 组件库
                        ui: {
                            test: /[\\/]node_modules[\\/](@radix-ui|shadcn)[\\/]/,
                            name: 'ui-vendor',
                            priority: 15,
                        },
                        // 分离图表库
                        charts: {
                            test: /[\\/]node_modules[\\/](recharts|chart.js)[\\/]/,
                            name: 'charts-vendor',
                            priority: 10,
                        },
                        // 其他 vendor 库
                        vendor: {
                            test: /[\\/]node_modules[\\/]/,
                            name: 'vendors',
                            chunks: 'all',
                            priority: 5,
                        },
                    },
                },
            };
        }
        return config;
    },
};

// 导出时包装 Bundle Analyzer
export default withBundleAnalyzer(nextConfig);
