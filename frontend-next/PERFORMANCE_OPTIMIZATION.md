# 前端性能优化指南

本文档介绍 FastBlog 前端项目的性能优化配置和使用方法。

## 🚀 已实现的优化

### 1. 图像优化 (next/image)

**配置位置**: `next.config.ts`

**特性**:

- ✅ 自动 WebP/AVIF 格式转换
- ✅ 响应式图像（根据设备尺寸）
- ✅ 懒加载（lazy loading）
- ✅ 模糊占位符支持
- ✅ 图像质量优化（默认 85%）

**使用方法**:

```tsx
import Image from 'next/image'

// 基本用法
<Image
  src="/path/to/image.jpg"
  alt="Description"
  width={800}
  height={600}
  priority  // 首屏图片使用 priority
/>

// 响应式图像
<Image
  src="/path/to/image.jpg"
  alt="Description"
  width={1200}
  height={800}
  sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
  style={{ objectFit: 'cover' }}
/>

// 远程图像
<Image
  src="https://example.com/image.jpg"
  alt="Remote image"
  width={800}
  height={600}
/>
```

**配置说明**:

```typescript
images: {
    unoptimized: false,  // 启用优化
    formats: ['image/webp', 'image/avif'],  // 优先使用现代格式
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    quality: 85,  // 图像质量
}
```

---

### 2. 代码分割优化

**配置位置**: `next.config.ts` - webpack.splitChunks

**优化策略**:

- React 核心库单独打包
- UI 组件库单独打包
- 图表库单独打包
- 其他 vendor 库统一打包

**动态导入示例**:

```tsx
import dynamic from 'next/dynamic'

// 动态导入重型组件
const ArticleEditor = dynamic(() => import('@/components/editor/ArticleEditor'), {
  loading: () => <Skeleton className="h-96" />,
  ssr: false,  // 如果不需要 SSR
})

// 动态导入图表组件
const AnalyticsChart = dynamic(() => import('@/components/charts/AnalyticsChart'), {
  loading: () => <div>Loading chart...</div>,
  ssr: false,
})

export default function Page() {
  return (
    <div>
      <ArticleEditor />
      <AnalyticsChart />
    </div>
  )
}
```

---

### 3. Bundle 分析

**安装依赖**:

```bash
cd frontend-next
npm install
```

**使用方法**:

```bash
# 分析整体 bundle 大小
npm run analyze

# 只分析服务端 bundle
npm run analyze:server

# 只分析浏览器端 bundle
npm run analyze:browser
```

**输出**:

- 分析完成后会自动打开浏览器显示可视化报告
- 可以看到每个模块的大小和占比
- 识别可以优化的大体积依赖

---

### 4. 字体优化

**最佳实践**:

```tsx
// 使用系统字体栈（无需加载外部字体）
const systemFonts = `
  -apple-system,
  BlinkMacSystemFont,
  "Segoe UI",
  Roboto,
  "Helvetica Neue",
  Arial,
  sans-serif
`

// 在 Tailwind 中配置
// tailwind.config.js
module.exports = {
  theme: {
    fontFamily: {
      sans: ['var(--font-sans)', ...systemFonts.split(',')],
    },
  },
}
```

**如果使用自定义字体**:

```tsx
import { Inter } from 'next/font/google'

// Next.js 自动优化字体加载
const inter = Inter({
  subsets: ['latin'],
  display: 'swap',  // 避免 FOIT
  preload: true,
})

export default function RootLayout({ children }) {
  return (
    <html className={inter.className}>
      <body>{children}</body>
    </html>
  )
}
```

---

### 5. 包导入优化

**配置位置**: `next.config.ts` - experimental.optimizePackageImports

**已优化的包**:

- `@radix-ui/react-icons` - 按需导入图标
- `lucide-react` - 按需导入图标

**使用示例**:

```tsx
// ❌ 不好的做法 - 导入整个库
import * as Icons from '@radix-ui/react-icons'

// ✅ 好的做法 - 按需导入
import { CheckIcon, CrossIcon } from '@radix-ui/react-icons'

// ✅ 更好的做法 - 使用 tree-shaking
import { Check, X } from 'lucide-react'
```

---

## 📊 性能监控

### Lighthouse 评分目标

- **Performance**: 95+
- **Accessibility**: 95+
- **Best Practices**: 95+
- **SEO**: 100

### 关键指标

| 指标                             | 目标值     | 说明     |
|--------------------------------|---------|--------|
| FCP (First Contentful Paint)   | < 1.5s  | 首次内容绘制 |
| LCP (Largest Contentful Paint) | < 2.5s  | 最大内容绘制 |
| TBT (Total Blocking Time)      | < 200ms | 总阻塞时间  |
| CLS (Cumulative Layout Shift)  | < 0.1   | 累积布局偏移 |
| Speed Index                    | < 3.5s  | 速度指数   |

---

## 🔧 优化建议

### 1. 组件级别优化

```tsx
// 使用 React.memo 避免不必要的重渲染
export const ExpensiveComponent = React.memo(({ data }) => {
  return <div>{/* 复杂渲染 */}</div>
})

// 使用 useMemo 缓存计算结果
const sortedData = useMemo(() => {
  return data.sort((a, b) => a.value - b.value)
}, [data])

// 使用 useCallback 缓存函数
const handleClick = useCallback(() => {
  doSomething(id)
}, [id])
```

### 2. 路由级别优化

```tsx
// 使用 next/link 进行客户端导航
import Link from 'next/link'

<Link href="/articles/123" prefetch>
  <a>文章标题</a>
</Link>

// prefetch 会在空闲时预加载页面
```

### 3. 数据获取优化

```tsx
// 使用 SWR 或 React Query 进行数据缓存
import useSWR from 'swr'

function ArticleList() {
  const { data, error } = useSWR('/api/articles', fetcher, {
    revalidateOnFocus: false,
    dedupingInterval: 5000,  // 5秒内重复请求去重
  })
  
  if (error) return <div>Failed to load</div>
  if (!data) return <div>Loading...</div>
  
  return <div>{/* render articles */}</div>
}
```

---

## 🎯 最佳实践清单

- [ ] 所有图片使用 `<Image>` 组件
- [ ] 首屏图片添加 `priority` 属性
- [ ] 大型组件使用动态导入
- [ ] 避免在客户端组件中使用大量静态数据
- [ ] 使用 `React.memo` 优化重渲染
- [ ] 定期运行 bundle 分析
- [ ] 保持第三方依赖最小化
- [ ] 使用系统字体或优化字体加载
- [ ] 实现适当的缓存策略
- [ ] 监控 Core Web Vitals

---

## 📚 相关资源

- [Next.js Image Optimization](https://nextjs.org/docs/app/building-your-application/optimizing/images)
- [Next.js Code Splitting](https://nextjs.org/docs/app/building-your-application/optimizing/lazy-loading)
- [Web Vitals](https://web.dev/vitals/)
- [Bundle Analyzer](https://github.com/vercel/next.js/tree/canary/packages/next-bundle-analyzer)
