// 运行时 API 配置
// 将此文件复制到 frontend-next/out/config.js 并修改配置
// 这样可以不重新构建就修改 API 地址

window.runtimeConfig = {
    API_BASE_URL: 'http://localhost:9421',  // Django 服务器地址
    API_PREFIX: '/api/v1'                   // API 前缀
};
