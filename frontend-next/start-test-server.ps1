#!/usr/bin/env pwsh
# 前端本地测试服务器启动脚本（带 URL 重写支持）

Write-Host "🚀 启动前端本地测试服务器..." -ForegroundColor Green

$DIST_PATH = Join-Path $PSScriptRoot "dist"

if (-not (Test-Path $DIST_PATH)) {
    Write-Host "❌ dist 目录不存在！请先运行构建。" -ForegroundColor Red
    Write-Host "提示：在 frontend-next 目录运行：npm run build:dist" -ForegroundColor Yellow
    exit 1
}

Write-Host "📁 服务目录：$DIST_PATH" -ForegroundColor Cyan
Write-Host "🔗 端口：8080" -ForegroundColor Cyan
Write-Host "`n💡 提示：访问时请使用 .html 后缀，例如：" -ForegroundColor Yellow
Write-Host "   http://localhost:8080/blog/detail.html?slug=xxx" -ForegroundColor Cyan
Write-Host "   http://localhost:8080/articles/detail.html?id=xxx" -ForegroundColor Cyan
Write-Host "`n按 Ctrl+C 停止服务器" -ForegroundColor Gray
Write-Host "----------------------------------------" -ForegroundColor Gray

# 尝试使用 Node.js 自定义服务器（支持 URL 重写）
try {
    $nodeCmd = Get-Command node -ErrorAction Stop
    Write-Host "📦 使用 Node.js 自定义服务器（支持 URL 重写）..." -ForegroundColor Green
    Set-Location $PSScriptRoot
    node test-server.js
    exit 0
} catch {
    Write-Host "⚠️  未找到 Node.js，尝试其他方法..." -ForegroundColor Yellow
}

# 尝试使用 Python
try {
    $pythonCmd = Get-Command python -ErrorAction Stop
    Write-Host "🐍 使用 Python HTTP Server (不支持 URL 重写)..." -ForegroundColor Green
    Set-Location $DIST_PATH
    python -m http.server 8080
    exit 0
} catch {
    Write-Host "⚠️  未找到 Python" -ForegroundColor Yellow
}

Write-Host "`n❌ 未找到可用的 HTTP 服务器" -ForegroundColor Red
Write-Host "`n请安装以下任一工具：" -ForegroundColor White
Write-Host "  1. Python 3 (推荐): https://www.python.org/" -ForegroundColor Cyan
Write-Host "  2. Node.js + http-server: npm install -g http-server" -ForegroundColor Cyan
Write-Host "`n或者使用 VS Code Live Server 扩展" -ForegroundColor Cyan
