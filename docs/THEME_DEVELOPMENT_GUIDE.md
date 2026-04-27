# FastBlog 主题开发指南

**适用版本**: FastBlog 0.0.2.0+

---

## 📋 目录

1. [概述](#概述)
2. [快速开始](#快速开始)
3. [主题结构](#主题结构)
4. [配置文件](#配置文件)
5. [样式定制](#样式定制)
6. [最佳实践](#最佳实践)

---

## 概述

FastBlog 的主题系统允许开发者自定义博客的外观和布局，而无需修改核心代码。通过主题，您可以：

- ✅ 完全控制网站的视觉设计
- ✅ 自定义布局和组件样式
- ✅ 支持深色模式
- ✅ 提供用户可配置的选项

### 主题系统架构

```
┌─────────────────────────────────────┐
│         FastBlog Core               │
└──────────┬──────────────────────────┘
           │
           │  Theme Engine
           │
    ┌──────┴──────┬──────────┬───────┐
    │             │          │       │
┌───▼───┐   ┌────▼────┐  ┌──▼───┐  ┌▼──────┐
│Theme 1│   │Theme 2  │  │ ...  │  │Theme N│
└───────┘   └─────────┘  └──────┘  └───────┘
```

---

## 快速开始

### 1. 创建主题目录

```bash
mkdir themes/my-theme
cd themes/my-theme
```

### 2. 创建元数据文件

创建 `metadata.json`：

```json
{
  "name": "我的主题",
  "slug": "my-theme",
  "version": "1.0.0",
  "description": "一个现代化、响应式的博客主题",
  "author": "您的名字",
  "min_fastblog_version": "0.0.2.0"
}
```

### 3. 创建主题配置文件

创建 `theme.json`：

```json
{
  "version": "1.0",
  
  "metadata": {
    "name": "我的主题",
    "slug": "my-theme",
    "version": "1.0.0",
    "description": "一个现代化、响应式的博客主题",
    "author": "您的名字"
  },
  
  "settings": {
    "colors": {
      "primary": "#3b82f6",
      "secondary": "#64748b",
      "background": "#ffffff",
      "foreground": "#1f2937"
    },
    
    "typography": {
      "fontFamily": "Inter, system-ui, sans-serif",
      "fontSize": "16px",
      "lineHeight": 1.6
    },
    
    "layout": {
      "sidebarPosition": "right",
      "contentWidth": "max-w-4xl",
      "showSidebar": true
    },
    
    "features": {
      "showComments": true,
      "showShareButtons": true,
      "enableDarkMode": true
    }
  }
}
```

### 4. 添加样式文件

创建 `styles.css`：

```css
:root {
    --color-primary: #3b82f6;
    --color-background: #ffffff;
    --color-foreground: #1f2937;
}

[data-theme='dark'] {
    --color-background: #111827;
    --color-foreground: #f9fafb;
}

body {
    font-family: var(--font-family, 'Inter', system-ui, sans-serif);
    background-color: var(--color-background);
    color: var(--color-foreground);
}
```

### 5. 激活主题

1. 重启 FastBlog 服务
2. 进入管理后台 → 外观 → 主题
3. 找到"我的主题"
4. 点击"启用"

---

## 主题结构

### 标准目录结构

```
my-theme/
├── metadata.json          # 主题元数据（必需）
├── theme.json             # 主题配置（必需）
├── styles.css             # 样式文件（必需）
├── script.js              # 脚本文件（可选）
├── screenshot.png         # 主题截图（推荐）
├── README.md              # 使用说明（推荐）
└── assets/                # 静态资源（可选）
    ├── images/
    └── fonts/
```

### metadata.json 字段说明

| 字段                     | 类型     | 必需 | 说明               |
|------------------------|--------|----|------------------|
| `name`                 | string | ✅  | 主题显示名称           |
| `slug`                 | string | ✅  | 主题唯一标识（小写，用连字符）  |
| `version`              | string | ✅  | 版本号              |
| `description`          | string | ❌  | 主题描述             |
| `author`               | string | ❌  | 作者名称             |
| `min_fastblog_version` | string | ❌  | 最低 FastBlog 版本要求 |

---

## 配置文件

### theme.json 配置详解

#### 颜色设置

```json
"colors": {
"primary": "#3b82f6", // 主色调
"secondary": "#64748b", // 次要色
"accent": "#f59e0b", // 强调色
"background": "#ffffff", // 背景色
"foreground": "#1f2937",   // 前景色（文字）
"muted": "#f3f4f6", // 弱化色
"border": "#e5e7eb"        // 边框色
}
```

#### 字体设置

```json
"typography": {
"fontFamily": "Inter, system-ui, sans-serif", // 正文体
"headingFont": "Inter, system-ui, sans-serif", // 标题字体
"fontSize": "16px", // 基础字号
"lineHeight": 1.6, // 行高
"headingWeight": 700    // 标题字重
}
```

#### 布局设置

```json
"layout": {
"sidebarPosition": "right", // 侧边栏位置: left/right/none
"contentWidth": "max-w-4xl", // 内容宽度
"showSidebar": true, // 是否显示侧边栏
"gridColumns": 3              // 网格列数
}
```

#### 功能设置

```json
"features": {
"showComments": true, // 显示评论
"showShareButtons": true, // 显示分享按钮
"showRelatedPosts": true, // 显示相关文章
"enableDarkMode": true        // 启用深色模式
}
```

---

## 样式定制

### CSS 变量

使用 CSS 变量实现主题定制：

```css
:root {
    --color-primary: #3b82f6;
    --color-background: #ffffff;
    --color-foreground: #1f2937;
    --font-family: 'Inter', system-ui, sans-serif;
}

[data-theme='dark'] {
    --color-background: #111827;
    --color-foreground: #f9fafb;
}

body {
    font-family: var(--font-family);
    background-color: var(--color-background);
    color: var(--color-foreground);
}
```

### 响应式设计

使用 TailwindCSS 类实现响应式：

```html
<div class="container mx-auto px-4">
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    <!-- 内容 -->
  </div>
</div>
```

### 深色模式

自动适配系统深色模式：

```css
@media (prefers-color-scheme: dark) {
  :root {
    --color-background: #111827;
    --color-foreground: #f9fafb;
  }
}
```

---

## 最佳实践

### 1. 性能优化

- 使用 CSS 变量减少重复代码
- 压缩 CSS 和 JavaScript 文件
- 懒加载图片和资源
- 使用现代图片格式（WebP）

### 2. 可访问性

- 确保足够的颜色对比度
- 提供键盘导航支持
- 使用语义化 HTML
- 添加 ARIA 标签

### 3. 兼容性

- 测试主流浏览器（Chrome, Firefox, Safari, Edge）
- 支持移动端和桌面端
- 优雅降级处理旧浏览器

### 4. 文档

- 编写清晰的 README
- 提供配置选项说明
- 包含截图预览

### 5. 代码规范

- 使用一致的命名约定
- 添加必要的注释
- 遵循 CSS 最佳实践

---

## 常见问题

### Q: 如何自定义首页布局？

A: 在主题中创建自定义模板文件，并通过 theme.json 配置。

### Q: 如何添加自定义字体？

A: 在 `assets/fonts/` 中添加字体文件，并在 CSS 中引用：

```css
@font-face {
  font-family: 'MyFont';
  src: url('assets/fonts/myfont.woff2') format('woff2');
}
```

### Q: 如何实现主题切换？

A: 使用 JavaScript 切换 `data-theme` 属性：

```javascript
document.documentElement.setAttribute('data-theme', 'dark');
```

---

## 总结

- ✅ 创建 `metadata.json` 和 `theme.json` 配置文件
- ✅ 使用 CSS 变量实现灵活的样式定制
- ✅ 支持响应式设计和深色模式
- ✅ 遵循最佳实践确保性能和可访问性
- ✅ 编写清晰的文档

更多详细信息请参考源码和示例主题。
