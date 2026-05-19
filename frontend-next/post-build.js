#!/usr/bin/env node

/**
 * 构建后处理脚本
 * 将 .html 文件移动到对应的目录作为 index.html
 * 以支持无后缀 URL 访问
 */

const fs = require('fs');
const path = require('path');

const OUT_DIR = path.join(__dirname, 'out');
const DIST_DIR = path.join(__dirname, 'dist');

console.log('🔧 开始处理构建产物...\n');

// 复制 out 到 dist
if (fs.existsSync(DIST_DIR)) {
    fs.rmSync(DIST_DIR, {recursive: true});
}
fs.cpSync(OUT_DIR, DIST_DIR, {recursive: true});

console.log('✅ 已复制 out -> dist\n');

// 需要处理的路径模式
const dynamicRoutes = [
    {pattern: /\/blog\/detail\.html$/, dir: 'blog/detail'},
    {pattern: /\/articles\/detail\.html$/, dir: 'articles/detail'},
    {pattern: /\/category\/detail\.html$/, dir: 'category/detail'},
    {pattern: /\/user\/detail\.html$/, dir: 'user/detail'},
];

let processedCount = 0;

// 递归查找并处理文件
function processDirectory(dir) {
    const files = fs.readdirSync(dir);

    for (const file of files) {
        const filePath = path.join(dir, file);
        const stat = fs.statSync(filePath);

        if (stat.isDirectory()) {
            // 跳过 _next 等特殊目录
            if (file.startsWith('_')) continue;
            processDirectory(filePath);
        } else if (stat.isFile() && file.endsWith('.html')) {
            const relativePath = path.relative(DIST_DIR, filePath);

            // 检查是否需要处理
            for (const route of dynamicRoutes) {
                if (route.pattern.test('/' + relativePath.replace(/\\/g, '/'))) {
                    // 创建目标目录
                    const targetDir = path.join(DIST_DIR, route.dir);
                    if (!fs.existsSync(targetDir)) {
                        fs.mkdirSync(targetDir, {recursive: true});
                    }

                    // 移动文件为 index.html
                    const targetFile = path.join(targetDir, 'index.html');
                    fs.renameSync(filePath, targetFile);

                    console.log(`✅ 处理：${relativePath} -> ${route.dir}/index.html`);
                    processedCount++;
                    break;
                }
            }
        }
    }
}

processDirectory(DIST_DIR);

console.log(`\n✨ 完成！共处理 ${processedCount} 个动态路由文件`);
console.log('\n现在可以访问：');
console.log('  http://localhost:8080/blog/detail?slug=<article-slug>');
console.log('  http://localhost:8080/articles/detail?id=<article-id>');
console.log('\n无需 .html 后缀！🎉');
