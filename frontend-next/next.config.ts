import type {NextConfig} from "next";
// next-intl 插件已禁用，使用客户端国际化方案
// import createNextIntlPlugin from 'next-intl/plugin';
// const withNextIntl = createNextIntlPlugin('./i18n/request.ts');

const nextConfig: NextConfig = {
    // 启用静态导出（生成 out 目录）
    output: 'export',
    
    // 禁用图像优化（OSS 不支持，使用普通 img 标签）
    images: {
        unoptimized: true,
    },

    // 在构建时忽略 TypeScript 错误（API 响应类型问题）
    typescript: {
        ignoreBuildErrors: true,
    },
    
    // 实验性功能：优化加载策略
    experimental: {
        // 注意：optimizeFonts 在 Next.js 14+ 中已移除，不再需要此配置
        // optimizeFonts: true,
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
                    cacheGroups: {
                        // 分离 vendor 库
                        vendor: {
                            test: /[\\/]node_modules[\\/]/,
                            name: 'vendors',
                            chunks: 'all',
                        },
                    },
                },
            };
        }
        return config;
    },
};

export default nextConfig;
