/**
 * 运行时配置文件 - 示例
 *
 * 部署到 OSS 后，复制此文件为 config.js 并修改 API_BASE_URL
 *
 * 使用方法：
 * 1. 复制此文件为 public/config.js
 * 2. 修改 API_BASE_URL 为你的后端服务器地址
 * 3. 刷新页面即可生效（无需重新构建！）
 */

export const runtimeConfig = {
    // 后端 API 基础地址
    // 开发环境：http://localhost:8000
    // 生产环境（OSS 部署）：修改为实际的后端服务器地址
    // 例如：https://api.yourdomain.com 或 http://your-server-ip:8000
    API_BASE_URL: 'http://localhost:8000',

    // API 版本前缀（通常不需要修改）
    API_PREFIX: '/api/v1'
};
