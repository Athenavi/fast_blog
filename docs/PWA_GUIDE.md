# PWA (渐进式 Web 应用) 实现指南

## 📋 概述

FastBlog 已实现完整的 PWA 支持，提供原生应用般的用户体验。

**核心功能**:

- ✅ 可安装到主屏幕
- ✅ 离线访问支持
- ✅ 后台缓存同步
- ✅ 推送通知（预留接口）
- ✅ 应用快捷方式
- ✅ 智能安装提示

---

## 🏗️ 架构设计

### 文件结构

```
frontend-next/public/
├── manifest.json          # PWA 配置文件
├── sw.js                  # Service Worker
├── offline.html           # 离线页面
└── icons/                 # 应用图标
    ├── icon-72x72.png
    ├── icon-96x96.png
    ├── ...
    └── icon-512x512.png

frontend-next/components/
└── PWAInstallPrompt.tsx   # 安装提示组件
```

### 工作流程

```
用户首次访问
    ↓
注册 Service Worker
    ↓
预缓存静态资源
    ↓
监听 beforeinstallprompt
    ↓
显示安装提示（3秒后）
    ↓
用户选择安装/稍后
    ↓
添加到主屏幕
```

---

## 🚀 功能说明

### 1. Manifest 配置

**位置**: `frontend-next/public/manifest.json`

**关键配置**:

```json
{
  "name": "FastBlog",
  "short_name": "FastBlog",
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#3b82f6",
  "icons": [...],
  "shortcuts": [
    {
      "name": "Write Article",
      "url": "/admin/articles/new"
    }
  ]
}
```

**特性**:

- 自定义应用名称和图标
- 主题色和背景色
- 应用快捷方式（长按图标）
- 截图展示

### 2. Service Worker

**位置**: `frontend-next/public/sw.js`

**缓存策略**:

| 资源类型   | 策略                     | 说明          |
|--------|------------------------|-------------|
| API 请求 | Network First          | 优先网络，失败用缓存  |
| 静态资源   | Cache First            | 优先缓存，减少加载时间 |
| 页面     | Stale While Revalidate | 先返回缓存，同时更新  |

**生命周期事件**:

- `install`: 预缓存 App Shell
- `activate`: 清理旧缓存
- `fetch`: 拦截请求，应用缓存策略

### 3. 离线页面

**位置**: `frontend-next/public/offline.html`

**功能**:

- 友好的离线提示
- 自动检测网络恢复
- 重试按钮
- 使用建议

### 4. 安装提示

**组件**: `components/PWAInstallPrompt.tsx`

**特性**:

- 延迟 3 秒显示（避免打扰）
- 30 天内不再提示（如果用户选择"稍后"）
- 美观的 UI 设计
- 深色模式支持

---

## 💻 使用方法

### 桌面端安装

**Chrome/Edge**:

1. 访问网站
2. 地址栏右侧出现安装图标
3. 点击安装
4. 或等待安装提示弹出

**Firefox**:

1. 菜单 → 更多工具 → 将页面保存为应用

### 移动端安装

**iOS (Safari)**:

1. 点击分享按钮
2. 选择"添加到主屏幕"
3. 确认添加

**Android (Chrome)**:

1. 菜单 → 添加到主屏幕
2. 或等待安装提示

---

## 🔧 配置选项

### 修改应用信息

编辑 `manifest.json`:

```json
{
  "name": "你的应用名称",
  "short_name": "简称",
  "description": "应用描述",
  "theme_color": "#你的主题色"
}
```

### 调整缓存策略

编辑 `sw.js`:

```javascript
// 修改缓存名称（版本控制）
const CACHE_NAME = 'fastblog-v2';

// 添加需要预缓存的资源
const PRECACHE_URLS = [
  '/',
  '/new-page',
];
```

### 自定义安装提示

编辑 `components/PWAInstallPrompt.tsx`:

```typescript
// 修改延迟时间
setTimeout(() => {
  setShowPrompt(true);
}, 5000); // 改为 5 秒

// 修改不再提示的时间
const thirtyDays = 60 * 24 * 60 * 60 * 1000; // 改为 60 天
```

---

## 📊 测试方法

### 1. Lighthouse 测试

```bash
# Chrome DevTools → Lighthouse → 选择 PWA
# 目标分数: 90+
```

**检查项**:

- ✅ 提供有效的 manifest.json
- ✅ 注册 Service Worker
- ✅ 配置离线页面
- ✅ 支持 HTTPS

### 2. 离线测试

```bash
# Chrome DevTools → Application → Service Workers
# 勾选 "Offline"
# 刷新页面，应显示离线页面
```

### 3. 安装测试

```bash
# Chrome DevTools → Application → Manifest
# 查看 "Installability" 状态
# 应为 "Installable"
```

### 4. 缓存验证

```bash
# Chrome DevTools → Application → Cache Storage
# 查看缓存的内容
# 应包括静态资源和 API 响应
```

---

## 🎯 最佳实践

### 1. 图标准备

生成所有尺寸的图标：

```bash
# 推荐使用工具
https://realfavicongenerator.net/pwa/generator

# 或使用脚本
npm run generate-icons
```

**必需尺寸**:

- 192x192 (启动画面)
- 512x512 (启动画面高清)
- 其他尺寸用于不同设备

### 2. 缓存管理

```javascript
// 定期清理旧缓存
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name.startsWith('fastblog-') && name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
});
```

### 3. 更新策略

```javascript
// 检测 Service Worker 更新
navigator.serviceWorker.ready.then((registration) => {
  registration.addEventListener('updatefound', () => {
    const newWorker = registration.installing;
    
    newWorker.addEventListener('statechange', () => {
      if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
        // 有新版本可用，提示用户刷新
        showUpdatePrompt();
      }
    });
  });
});
```

### 4. 性能优化

- 只缓存必要的资源
- 设置合理的缓存过期时间
- 使用 Compression Brotli/Gzip
- 懒加载非关键资源

---

## ⚠️ 注意事项

### 1. HTTPS 要求

PWA **必须**在 HTTPS 环境下运行（localhost 除外）。

**生产环境**:

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
}
```

### 2. 跨域问题

Service Worker 只能控制同源请求。

**解决方案**:

- 使用 CORS 头
- 代理 API 请求
- 使用相同域名

### 3. iOS 限制

iOS Safari 对 PWA 有一些限制：

- 不支持后台同步
- 推送通知有限制
- Service Worker 有存储限制

### 4. 缓存大小

浏览器对缓存大小有限制：

- Chrome: 约 6% 的磁盘空间
- Firefox: 约 10% 的磁盘空间
- Safari: 约 50MB

**建议**:

- 定期清理旧缓存
- 压缩资源
- 使用 CDN

---

## 🔍 故障排除

### 问题 1: Service Worker 未注册

**检查**:

```javascript
console.log('serviceWorker' in navigator); // 应为 true
```

**解决**:

- 确保使用 HTTPS
- 检查浏览器兼容性
- 查看控制台错误

### 问题 2: 安装提示不显示

**原因**:

- 用户之前拒绝了安装
- 未达到 PWA 标准
- 已经安装

**解决**:

```javascript
// 清除 localStorage
localStorage.removeItem('pwa-install-dismissed');

// 检查 Lighthouse 分数
// 确保满足所有 PWA 要求
```

### 问题 3: 离线页面不工作

**检查**:

```javascript
// 查看缓存是否包含离线页面
caches.open('fastblog-static-v1').then(cache => {
  cache.keys().then(keys => console.log(keys));
});
```

**解决**:

- 确保 offline.html 在预缓存列表中
- 检查 Service Worker 是否正确激活

### 问题 4: 缓存未更新

**解决**:

```javascript
// 手动清除缓存
caches.keys().then(names => {
  names.forEach(name => caches.delete(name));
});

// 或使用 DevTools
// Application → Clear storage → Clear site data
```

---

## 📈 监控与分析

### 跟踪安装率

```javascript
// 在 PWAInstallPrompt 组件中
window.addEventListener('appinstalled', () => {
  // 发送到分析平台
  analytics.track('PWA Installed');
});
```

### 监控缓存命中率

```javascript
// 在 Service Worker 中
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then(response => {
      if (response) {
        // 缓存命中
        analytics.track('Cache Hit', { url: event.request.url });
        return response;
      } else {
        // 缓存未命中
        analytics.track('Cache Miss', { url: event.request.url });
        return fetch(event.request);
      }
    })
  );
});
```

---

## 🎨 自定义主题

### 修改主题色

1. 编辑 `manifest.json`:

```json
{
  "theme_color": "#你的颜色",
  "background_color": "#你的背景色"
}
```

2. 更新 `offline.html` 中的渐变:

```css
background: linear-gradient(135deg, #颜色1 0%, #颜色2 100%);
```

3. 修改 `PWAInstallPrompt.tsx` 中的颜色类

---

## 🚀 未来增强

### 计划功能

- [ ] 推送通知
- [ ] 后台同步
- [ ] 周期性后台同步
- [ ] 共享目标（Web Share Target）
- [ ] 文件处理（File Handling）
- [ ] 联系人选择器

### 高级缓存策略

- [ ] IndexedDB 存储
- [ ] 增量缓存
- [ ] 智能预取
- [ ] 基于网络的缓存策略

---

**维护者**: FastBlog Core Team  
**最后更新**: 2026-05-01  
**版本**: 1.0.0
