# FastBlog 开发指南

## 📋 文档信息

**版本**：v2.1.0  
**更新时间**：2026年2月

## 🛠️ 开发环境搭建

### 系统要求
- **Python**: 3.14+
- **Node.js**: 18+
- **数据库**: PostgreSQL 17+
- **IDE**: VS Code 或 PyCharm

### 后端环境
```bash
# 1. 克隆项目
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境
cp .env_example .env
# 编辑数据库连接等配置

# 5. 启动开发服务器
python main.py --env dev
# 或监督器模式: python main.py --mode supervisor --env dev
```

### 前端环境
```bash
cd frontend-next
npm install
cp .env.local.example .env.local
npm run dev
# 访问 http://localhost:3000
```

## 📁 项目结构

### 后端结构
```
src/
├── api/v1/           # API接口
├── models/           # 数据模型
├── services/         # 业务逻辑
├── utils/            # 工具函数
└── app.py            # 应用入口
```

### 前端结构
```
frontend-next/
├── app/              # 页面路由
├── components/       # UI组件
├── hooks/            # 自定义Hooks
├── lib/              # 工具库
└── types/            # 类型定义
```

## 🎯 核心开发

### API开发示例
```python
# src/api/v1/articles.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/articles", tags=["文章"])

class ArticleCreate(BaseModel):
    title: str
    content: str

@router.post("/")
async def create_article(article: ArticleCreate):
    return {"message": f"文章 '{article.title}' 创建成功"}
```

### 组件开发示例
```tsx
// components/ArticleCard.tsx
import { Card } from "@/components/ui/card"

interface Props {
  title: string
  excerpt: string
}

export function ArticleCard({ title, excerpt }: Props) {
  return (
    <Card className="p-4 hover:shadow-lg transition-shadow">
      <h3 className="font-bold">{title}</h3>
      <p className="text-gray-600">{excerpt}</p>
    </Card>
  )
}
```

## 🔧 开发工具

### 代码规范
```bash
# 后端
flake8 src/
black src/

# 前端
npm run lint
npm run format
```

### 测试
```bash
# 后端测试
pytest tests/

# 前端测试
npm run test
```

## 🚀 启动模式

| 模式 | 命令 | 用途 |
|------|------|------|
| App模式 | `python main.py` | 开发调试 |
| Supervisor模式 | `python main.py --mode supervisor` | 生产环境 |

## 📚 学习资源

- [FastAPI文档](https://fastapi.tiangolo.com/)
- [Next.js文档](https://nextjs.org/docs)
- [贡献指南](./CONTRIBUTING.md)

---
*文档版本：v2.1.0 | 更新时间：2026年2月*