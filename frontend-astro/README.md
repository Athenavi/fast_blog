# FastBlog Astro Frontend

FastBlog 的 Astro 前端，提供极致的性能和零 JavaScript 默认策略。

## Quick Start

```bash
npm install
npm run dev     # 开发模式，默认端口 4321
npm run build   # 生产构建，输出到 dist/
npm run preview # 预览生产构建
```

## Project Structure

```
frontend-astro/
├── src/
│   ├── components/     # React 组件（Islands）
│   ├── layouts/        # Astro 布局组件
│   ├── pages/          # 页面路由（SSR + SSG 混合）
│   ├── lib/
│   │   ├── api/         # API service 文件
│   │   ├── hooks/       # 自定义 hooks
│   │   └── schemas/     # Zod 验证 schema
│   └── styles/         # 全局样式
├── public/             # 静态资源
├── astro.config.mjs    # Astro 配置
└── package.json
```

## Tech Stack

- **Framework**: Astro 5.x (SSR + SSG hybrid)
- **UI**: React 19 (Islands)
- **Styling**: TailwindCSS 4.x
- **State**: TanStack React Query
- **Components**: Radix UI / shadcn/ui
- **Editor**: TipTap 3.x (ProseMirror)

## Environment Variables

Create `.env`:

```env
PUBLIC_API_BASE_URL=http://localhost:9421
SITE_URL=https://yourdomain.com
```
