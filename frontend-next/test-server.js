#!/usr/bin/env node

/**
 * 本地测试服务器（支持 URL 重写）
 * 用于测试静态导出的 Next.js 应用
 */

const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = 8080;
const DIST_PATH = path.join(__dirname, 'dist');

console.log('🚀 启动前端本地测试服务器...');
console.log('📁 服务目录：', DIST_PATH);

// 静态文件服务
app.use(express.static(DIST_PATH));

// URL 重写中间件：处理 /blog/detail -> /blog/detail.html
app.use((req, res, next) => {
    // 检查是否为动态路由路径
    const url = req.url;
    const parsedUrl = new URL(url, `http://${req.headers.host}`);
    const pathname = parsedUrl.pathname;

    // 检查是否存在对应的 .html 文件
    const htmlPath = path.join(DIST_PATH, pathname + '.html');

    if (fs.existsSync(htmlPath)) {
        // 存在 .html 文件，重定向到该文件
        const queryString = parsedUrl.search;
        const newUrl = pathname + '.html' + queryString;
        console.log('🔄 URL 重写:', url, '->', newUrl);
        return res.sendFile(path.join(DIST_PATH, newUrl));
    }

    // 检查目录下是否有 index.html
    const indexPath = path.join(DIST_PATH, pathname, 'index.html');
    if (fs.existsSync(indexPath)) {
        console.log('🔄 目录重定向:', url, '->', pathname + '/index.html');
        return res.sendFile(indexPath);
    }

    next();
});

app.listen(PORT, () => {
    console.log('🔗 服务器地址：http://localhost:' + PORT);
    console.log('');
    console.log('💡 提示：现在可以访问以下 URL：');
    console.log('   http://localhost:8080/blog/detail?slug=<article-slug> (自动重写到 .html)');
    console.log('   http://localhost:8080/articles/detail?id=<article-id> (自动重写到 .html)');
    console.log('');
    console.log('按 Ctrl+C 停止服务器');
    console.log('----------------------------------------');
});
