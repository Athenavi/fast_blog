import type {NextConfig} from "next";
import {version} from './package.json';

const nextConfig: NextConfig = {
    // 注入版本信息到环境变量
    env: {
        NEXT_PUBLIC_APP_VERSION: version,
        NEXT_PUBLIC_BUILD_TIME: new Date().toISOString(),
        NEXT_PUBLIC_NODE_ENV: process.env.NODE_ENV || 'development',
    },
    /* config options here */
    typedRoutes: true,
    images: {
        remotePatterns: [
            {
                protocol: 'http',
                hostname: 'localhost',
                port: '5000',
            },
            {
                protocol: 'http',
                hostname: '127.0.0.1',
                port: '5000',
            },
            {
                protocol: 'http',
                hostname: 'localhost',
                port: '8000',
            },
            {
                protocol: 'http',
                hostname: '127.0.0.1',
                port: '8000',
            },
        ],
    },
    async rewrites() {
        return [
            // 将所有以 /api/v1 开头的请求代理到后端服务器
            {
                source: '/api/v1/:path*',
                destination: `${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/api/v1/:path*`,
            },
        ]
    },
    // 配置代理头信息以传递认证凭据
    async headers() {
        return [
            {
                source: '/api/v1/:path*',
                headers: [
                    {
                        key: 'Access-Control-Allow-Credentials',
                        value: 'true',
                    },
                    {
                        key: 'Access-Control-Allow-Origin',
                        value: '*', // 在生产环境中应该指定具体的源
                    },
                    {
                        key: 'Access-Control-Allow-Methods',
                        value: 'GET,OPTIONS,PATCH,DELETE,POST,PUT',
                    },
                    {
                        key: 'Access-Control-Allow-Headers',
                        value: 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, Authorization, Access-Control-Allow-Headers, Cookie, Set-Cookie',
                    },
                    {
                        key: 'credentials',
                        value: 'include',
                    },
                ],
            },
        ]
    },
};

export default nextConfig;