# FastBlog 技术架构文档

## 🏗️ 系统架构

FastBlog采用**进程监督器模式**和**前后端分离架构**，确保系统的高可靠性和可扩展性。

### 进程监督器架构

```
┌─────────────────────────────────────────┐
│           SupervisedLauncher            │ ◄─ 主监督器
└─────────────────┬───────────────────────┘
                  │
                  ▼
        ┌─────────────────┐
        │ ProcessSupervisor │ ◄─ 进程监督核心
        └────────┬────────┘
                 │
        ┌────────┴────────┬───────────────┬───────────────┐
        ▼                 ▼               ▼               ▼
┌─────────────┐   ┌──────────────┐  ┌──────────┐  ┌──────────┐
│ IPC Server  │   │ UpdateChecker│  │ Main App │  │ Updater  │
│ (端口:12345)│   │ (端口:8001)  │  │(端口:9421)│  │ (按需)   │
└─────────────┘   └──────────────┘  └──────────┘  └──────────┘
```

**核心优势**：
- 高可靠性：自动故障检测和恢复
- 进程隔离：组件独立运行
- 统一管理：集中生命周期控制
- 安全更新：独立的文件更新机制

### 启动模式对比

| 模式 | 命令 | 适用场景 | 特点 |
|------|------|----------|------|
| App模式 | `python main.py` | 开发调试 | 直接启动，轻量级 |
| Supervisor模式 | `python main.py --mode supervisor` | 生产环境 | 进程监督，自动重启 |

## 📐 系统架构图

### 前后端分离架构
```
用户端 ↔ 负载均衡(Nginx) ↔ 前端(Next.js:3000) ↔ 后端(FastAPI:9421) ↔ 数据库(PostgreSQL)
                                      ↓
                                  缓存(Redis)
```

### 后端服务架构
```
src/
├── api/v1/           # REST API接口
├── models/           # 数据模型
├── services/         # 业务逻辑
├── utils/            # 工具函数
└── middleware/       # 中间件
```

### 前端架构
```
frontend-next/
├── app/              # 路由页面
├── components/       # UI组件
├── hooks/            # 自定义Hooks
└── lib/              # 工具库
```

## 🔧 核心组件

### 1. 进程管理组件
- **SupervisedLauncher**: 主启动器和监督器
- **ProcessSupervisor**: 进程生命周期管理
- **IPC Server**: 进程间通信服务
- **UpdateChecker**: 版本检查服务

### 2. 业务组件
- **Main App**: 核心业务逻辑 (FastAPI)
- **Frontend**: 用户界面 (Next.js)
- **Database**: 数据存储 (PostgreSQL)
- **Cache**: 缓存服务 (Redis)

## 🛡️ 安全架构

### 多层安全防护
- **认证授权**: JWT Token + RBAC权限控制
- **输入验证**: 参数校验和SQL注入防护
- **传输安全**: HTTPS/TLS 1.3加密
- **访问控制**: 细粒度权限管理

## 🛠️ 技术栈

### 前端
- **框架**: Next.js 16 (App Router)
- **语言**: TypeScript
- **样式**: TailwindCSS + shadcn/ui
- **状态**: React Context + SWR

### 后端
- **框架**: FastAPI
- **语言**: Python 3.14+
- **数据库**: PostgreSQL 17+
- **缓存**: Redis

### 基础设施
- **容器化**: Docker + Docker Compose
- **部署**: Nginx + Gunicorn
- **监控**: Prometheus + Grafana

## 🎯 开发环境搭建

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

## 📚 学习资源

- [FastAPI文档](https://fastapi.tiangolo.com/)
- [Next.js文档](https://nextjs.org/docs)
- [贡献指南](./CONTRIBUTING.md)