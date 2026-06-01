# FastBlog 主题开发指南

> **版本**: V0.3.26.0521+ | **前端框架**: Astro 5.x + React 19 + TailwindCSS

---

## 📋 目录

1. [概述](#概述)
2. [快速开始](#快速开始)
3. [主题结构](#主题结构)
4. [配置文件详解](#配置文件详解)
5. [样式定制](#样式定制)
6. [最佳实践](#最佳实践)

---

## 概述

FastBlog 的主题系统基于 **Astro SSG + TailwindCSS** 构建，允许开发者自定义博客的外观和布局。通过主题，您可以：

- ✅ 完全控制网站的视觉设计
- ✅ 自定义布局和组件样式
- ✅ 支持深色模式
- ✅ 提供用户可配置的选项
- ✅ 利用 TailwindCSS 的原子化样式系统

### 主题系统架构

```
┌─────────────────────────────────────┐
│         FastBlog Core               │
│      (Astro + React Islands)        │
└──────────┬──────────────────────────┘
           │
           │  Theme Config (theme.json + theme.config.js)
           │
    ┌──────┴──────┬──────────┬───────┐
    │             │          │       │
┌───▼───┐   ┌────▼────┐  ┌──▼───┐  ┌▼──────┐
│default│   │magazine │  │modern│  │  ...  │
│       │   │         │  │minimal│ │       │
└───────┘   └─────────┘  └──────┘  └───────┘
```

### 内置主题

| 主题               | Slug             | 说明          |
|------------------|------------------|-------------|
| FastBlog Default | `default`        | 简洁、现代、响应式设计 |
| Magazine         | `magazine`       | 杂志风格布局      |
| Modern Minimal   | `modern-minimal` | 极简主义设计      |

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
    "author_url": "https://example.com",
    "theme_url": "https://example.com/themes/my-theme",
    "screenshot": "screenshot.png",
    "tags": [
        "responsive",
        "modern",
        "clean"
    ],
    "requires": {
        "fastblog": ">=1.0.0"
    },
    "supports": [
        "custom-logo",
        "custom-header",
        "featured-image",
        "post-thumbnails",
        "comments",
        "widgets"
    ]
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
        "accent": "#f59e0b",
      "background": "#ffffff",
        "foreground": "#1f2937",
        "muted": "#f3f4f6",
        "border": "#e5e7eb"
    },
    "layout": {
      "sidebarPosition": "right",
      "contentWidth": "max-w-4xl",
        "showSidebar": true,
        "showHeader": true,
        "showFooter": true
    },
      "typography": {
          "fontFamily": "Inter, system-ui, sans-serif",
          "fontSize": "16px",
          "lineHeight": 1.6,
          "headingFontWeight": 700
      },
      "components": {
          "borderRadius": "0.5rem",
          "shadowStyle": "medium",
          "buttonStyle": "default"
    }
  },
    "supports": [
        "custom-logo",
        "custom-header",
        "featured-image",
        "post-thumbnails",
        "comments",
        "widgets"
    ]
}
```

### 4. 创建 JavaScript 配置

创建 `theme.config.js`（用于前端组件读取配置）：

```javascript
/**
 * 我的主题 - 前端配置文件
 */

export const themeConfig = {
        // 颜色方案
        colors: {
            primary: '#3b82f6',
            secondary: '#64748b',
            accent: '#f59e0b',
            background: '#ffffff',
            foreground: '#1f2937',
            muted: '#f3f4f6',
            border: '#e5e7eb',
        },

        // 布局配置
        layout: {
            sidebarPosition: 'right',   // 'left' | 'right' | 'none'
            contentWidth: 'max-w-4xl',
            showSidebar: true,
            showHeader: true,
            showFooter: true,
        },

        // 排版配置
        typography: {
            fontFamily: 'Inter, system-ui, sans-serif',
            fontSize: '16px',
            lineHeight: 1.6,
            headingFontWeight: 700,
        },

        // 组件样式
        components: {
            borderRadius: '0.5rem',
            shadowStyle: 'medium',      // 'none' | 'small' | 'medium' | 'large'
            buttonStyle: 'default',     // 'default' | 'rounded' | 'pill'
        },

        // 功能开关
        features: {
            showComments: true,
            showShareButtons: true,
            showRelatedPosts: true,
            showTableOfContents: true,
            enableDarkMode: true,
        },
    };
```

### 5. 添加样式文件

创建 `styles.css`：

```css
:root {
    --color-primary: #3b82f6;
    --color-secondary: #64748b;
    --color-accent: #f59e0b;
    --color-background: #ffffff;
    --color-foreground: #1f2937;
    --color-muted: #f3f4f6;
    --color-border: #e5e7eb;
    --font-family: 'Inter', system-ui, sans-serif;
}

[data-theme='dark'] {
    --color-background: #111827;
    --color-foreground: #f9fafb;
    --color-muted: #1f2937;
    --color-border: #374151;
}

body {
    font-family: var(--font-family);
    background-color: var(--color-background);
    color: var(--color-foreground);
}
```

### 6. 激活主题

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
├── theme.config.js        # 前端 JavaScript 配置（必需）
├── styles.css             # 样式文件（必需）
├── screenshot.png         # 主题截图（推荐）
├── screenshot.svg         # 主题截图 SVG（可选）
├── README.md              # 使用说明（推荐）
└── templates/             # 模板文件（可选）
```

### metadata.json 字段说明

| 字段                | 类型       | 必需 | 说明                                |
|-------------------|----------|----|-----------------------------------|
| `name`            | string   | ✅  | 主题显示名称                            |
| `slug`            | string   | ✅  | 主题唯一标识（小写，用连字符）                   |
| `version`         | string   | ✅  | 版本号（语义化版本）                        |
| `description`     | string   | ✅  | 主题描述                              |
| `author`          | string   | ✅  | 作者名称                              |
| `author_url`      | string   | ❌  | 作者网站                              |
| `theme_url`       | string   | ❌  | 主题主页                              |
| `screenshot`      | string   | ❌  | 截图文件名                             |
| `tags`            | string[] | ❌  | 标签列表                              |
| `requires`        | object   | ❌  | 版本要求（如 `{"fastblog": ">=1.0.0"}`） |
| `supports`        | string[] | ❌  | 支持的功能列表                           |
| `settings_schema` | object   | ❌  | 设置界面字段定义                          |

---

## 配置文件详解

### theme.json 配置

#### 颜色设置

```json
"colors": {
"primary": "#3b82f6", // 主色调
"secondary": "#64748b", // 次要色
"accent": "#f59e0b", // 强调色
"background": "#ffffff", // 背景色
"foreground": "#1f2937",    // 前景色（文字）
"muted": "#f3f4f6", // 弱化色
"border": "#e5e7eb"         // 边框色
}
```

#### 布局设置

```json
"layout": {
"sidebarPosition": "right", // 侧边栏位置: left/right/none
"contentWidth": "max-w-4xl", // 内容宽度（TailwindCSS 类名）
"showSidebar": true, // 是否显示侧边栏
"showHeader": true, // 是否显示头部
"showFooter": true           // 是否显示底部
}
```

#### 排版设置

```json
"typography": {
"fontFamily": "Inter, system-ui, sans-serif", // 正文字体
"fontSize": "16px", // 基础字号
"lineHeight": 1.6, // 行高
"headingFontWeight": 700       // 标题字重
}
```

#### 组件设置

```json
"components": {
"borderRadius": "0.5rem", // 圆角大小
"shadowStyle": "medium", // 阴影风格: none/small/medium/large
"buttonStyle": "default"       // 按钮风格: default/rounded/pill
}
```

### theme.config.js 配置

`theme.config.js` 是前端组件（React Islands）读取主题配置的入口文件。它导出一个 `themeConfig` 对象，结构与 `theme.json` 的
`settings` 部分一致，并增加了 `features` 功能开关。

---

## 样式定制

### CSS 变量

使用 CSS 变量实现主题定制，变量名与 `theme.json` 的颜色配置对应：

```css
:root {
    --color-primary: #3b82f6;
    --color-secondary: #64748b;
    --color-accent: #f59e0b;
    --color-background: #ffffff;
    --color-foreground: #1f2937;
    --font-family: 'Inter', system-ui, sans-serif;
}

[data-theme='dark'] {
    --color-background: #111827;
    --color-foreground: #f9fafb;
}
```

### TailwindCSS 集成

FastBlog 前端使用 TailwindCSS，主题可以通过以下方式集成：

```html
<!-- 使用主题颜色的 TailwindCSS 类 -->
<div class="bg-[var(--color-background)] text-[var(--color-foreground)]">
    <h1 class="text-[var(--color-primary)]">标题</h1>
</div>

<!-- 使用 TailwindCSS 响应式布局 -->
<div class="container mx-auto px-4">
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <!-- 内容 -->
    </div>
</div>
```

### 深色模式

支持系统自动检测和手动切换：

```css
/* 系统自动检测 */
@media (prefers-color-scheme: dark) {
    :root {
        --color-background: #111827;
        --color-foreground: #f9fafb;
    }
}

/* 手动切换（通过 data-theme 属性） */
[data-theme='dark'] {
    --color-background: #111827;
    --color-foreground: #f9fafb;
}
```

```javascript
// JavaScript 切换深色模式
document.documentElement.setAttribute('data-theme', 'dark');
```

---

## 最佳实践

### 1. 性能优化

- 使用 CSS 变量减少重复代码
- 利用 TailwindCSS 的 JIT 模式按需生成样式
- 压缩 CSS 和 JavaScript 文件
- 懒加载图片和资源
- 使用现代图片格式（WebP、AVIF）

### 2. 可访问性

- 确保足够的颜色对比度（WCAG AA 标准）
- 提供键盘导航支持
- 使用语义化 HTML
- 添加 ARIA 标签

### 3. 响应式设计

- 使用 TailwindCSS 断点：`sm`、`md`、`lg`、`xl`
- 移动端优先设计
- 测试主流设备尺寸

### 4. 兼容性

- 测试主流浏览器（Chrome、Firefox、Safari、Edge）
- 支持移动端和桌面端
- 优雅降级处理旧浏览器

### 5. 文档

- 编写清晰的 README
- 提供配置选项说明
- 包含截图预览

---

## 常见问题

### Q: 如何自定义首页布局？

A: 在 `templates/` 目录中创建自定义 Astro 组件，并通过 `theme.json` 配置控制显示。

### Q: 如何添加自定义字体？

A: 在 CSS 中使用 `@font-face` 引入字体文件，或通过 Google Fonts CDN 加载：

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

:root {
    --font-family: 'Inter', system-ui, sans-serif;
}
```

### Q: 如何实现主题切换？

A: 使用 JavaScript 切换 `data-theme` 属性：

```javascript
document.documentElement.setAttribute('data-theme', 'dark');
// 保存用户偏好
localStorage.setItem('theme', 'dark');
```

### Q: theme.json 和 theme.config.js 有什么区别？

A:

- `theme.json`：服务端配置，定义主题的元数据和默认设置
- `theme.config.js`：前端配置，供 React Islands 组件读取，包含功能开关

### Q: 主题必须包含 templates/ 目录吗？

A: 不是必需的。`templates/` 目录是可选的，用于自定义页面模板。默认情况下，Astro 使用 `frontend-astro/src/pages/` 中的页面路由。

---

## 总结

- ✅ 创建 `metadata.json`（元数据）、`theme.json`（配置）、`theme.config.js`（前端配置）
- ✅ 使用 CSS 变量 + TailwindCSS 实现灵活的样式定制
- ✅ 支持响应式设计和深色模式
- ✅ 遵循最佳实践确保性能和可访问性
- ✅ 参考内置主题（default、magazine、modern-minimal）进行开发

更多详细信息请参考 [`themes/`](../themes/) 目录中的内置主题源码。
