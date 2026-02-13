# FastBlog 前端开发文档

基于 Next.js 14 的现代化前端应用，采用 App Router 架构和 TypeScript 开发。

## 🚀 快速开始

### 开发环境
```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev
# 访问 http://localhost:3000
```

### 生产构建
```bash
# 构建生产版本
npm run build

# 启动生产服务器
npm start
```

## 🏗️ 项目结构

```
frontend-next/
├── app/                    # App Router路由
│   ├── page.tsx           # 首页
│   ├── layout.tsx         # 根布局
│   ├── admin/             # 管理后台
│   └── api/               # API路由
├── components/            # 组件库
│   ├── ui/               # UI基础组件
│   ├── editor/           # 编辑器组件
│   └── layouts/          # 布局组件
├── hooks/                # 自定义Hooks
├── lib/                  # 工具库
├── types/                # TypeScript类型
├── styles/               # 样式文件
└── public/               # 静态资源
```

## 🎯 核心功能

### 技术栈
- **框架**：Next.js 14 (App Router)
- **语言**：TypeScript
- **样式**：TailwindCSS + shadcn/ui
- **状态管理**：React Context + SWR
- **表单**：React Hook Form + Zod

### 主要特性
- 响应式设计，支持移动端
- SSR/SSG混合渲染
- 组件化架构
- 类型安全
- 国际化支持
- 直接与更新服务器通信获取版本信息

## 🔧 开发指南

### 组件开发
```tsx
// 创建新组件
import { Button } from '@/components/ui/button'

interface Props {
  title: string
  onClick: () => void
}

export function MyComponent({ title, onClick }: Props) {
  return (
    <Button onClick={onClick}>
      {title}
    </Button>
  )
}
```

### API集成
```typescript
// lib/api/client.ts
import axios from 'axios'

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  timeout: 10000,
})

// 使用示例
const { data } = await apiClient.get('/articles')
```

### 状态管理
```typescript
// 使用SWR进行数据获取
import useSWR from 'swr'

function ArticleList() {
  const { data: articles, error } = useSWR('/api/articles', fetcher)
  
  if (error) return <div>加载失败</div>
  if (!data) return <div>加载中...</div>
  
  return (
    <div>
      {articles.map(article => (
        <ArticleCard key={article.id} article={article} />
      ))}
    </div>
  )
}
```

## 🎨 UI组件库

### 基础组件
- Button - 按钮组件
- Card - 卡片组件
- Input - 输入框组件
- Select - 选择器组件
- Dialog - 对话框组件

### 业务组件
- ArticleCard - 文章卡片
- Editor - Markdown编辑器
- ImageUploader - 图片上传器
- Pagination - 分页组件

## 📱 响应式设计

### 断点设置
```css
/* TailwindCSS断点 */
sm: 640px   /* 平板 */
md: 768px   /* 小桌面 */
lg: 1024px  /* 桌面 */
xl: 1280px  /* 大桌面 */
2xl: 1536px /* 超大屏 */
```

### 移动端适配
```tsx
// 使用useMediaQuery Hook
import { useMediaQuery } from '@/hooks/use-media-query'

function ResponsiveComponent() {
  const isMobile = useMediaQuery('(max-width: 768px)')
  
  return (
    <div>
      {isMobile ? <MobileView /> : <DesktopView />}
    </div>
  )
}
```

## 🔒 安全考虑

### 输入验证
```typescript
import { z } from 'zod'

const articleSchema = z.object({
  title: z.string().min(1).max(100),
  content: z.string().min(1),
  tags: z.array(z.string()).max(10)
})
```

### CSRF防护
```typescript
// 自动添加CSRF Token
apiClient.interceptors.request.use(config => {
  const token = getCsrfToken()
  if (token) {
    config.headers['X-CSRF-Token'] = token
  }
  return config
})
```

## 🚀 性能优化

### 代码分割
```tsx
// 动态导入组件
import dynamic from 'next/dynamic'

const HeavyComponent = dynamic(() => import('@/components/HeavyComponent'), {
  loading: () => <Skeleton />
})
```

### 图片优化
```tsx
// 使用Next.js Image组件
import Image from 'next/image'

<Image
  src="/images/photo.jpg"
  alt="描述"
  width={800}
  height={600}
  priority  // 关键图片优先加载
/>
```

## 🧪 测试

### 单元测试
```bash
# 运行测试
npm run test

# 监听模式
npm run test:watch
```

### E2E测试
```typescript
// 使用Playwright进行端到端测试
import { test, expect } from '@playwright/test'

test('should display articles', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('最新文章')).toBeVisible()
})
```

## 📚 学习资源

### 官方文档
- [Next.js文档](https://nextjs.org/docs)
- [React文档](https://react.dev)
- [TypeScript文档](https://www.typescriptlang.org/docs)
- [TailwindCSS文档](https://tailwindcss.com/docs)

### 推荐教程
- Next.js官方教程
- React Hooks深入理解
- TypeScript实战指南
- 现代CSS布局技巧

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 发起Pull Request

请确保代码符合项目规范并通过所有测试。

---
*文档版本：v1.0.0 | 最后更新：2026年2月*
