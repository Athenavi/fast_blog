# FastBlog 快速入门指南

本文档提供 FastBlog 系统的详细部署和配置指南。

## 💻 手动部署

### 前置要求

- Python 3.14+
- Node.js 18+
- PostgreSQL 17+
- Redis 7+

### 后端部署

#### 1. 准备环境

```bash
# 克隆项目
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

#### 2. 配置环境

```bash
# 复制环境配置文件
cp .env_example .env

# 编辑 .env 文件，配置以下内容：
# - DATABASE_URL: PostgreSQL 连接字符串
# - REDIS_URL: Redis 连接字符串
# - SECRET_KEY: 随机生成的密钥
# - CORS_ORIGINS: 允许的前端域名
```

**.env 配置示例**:

```env
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/fast_blog

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# 安全密钥（生成命令：python -c "import secrets; print(secrets.token_urlsafe(50))"）
SECRET_KEY=your-secret-key-here

# CORS 配置
CORS_ORIGINS=http://localhost:3000,http://localhost:9421

# 后端模式
BACKEND_MODE=fastapi  # 或 django
```

#### 3. 数据库初始化

```bash
# 创建数据库
psql -U postgres
CREATE DATABASE fast_blog;
\q

# 运行迁移
# 应用启动后访问 /install 运行初始迁移
```

#### 4. 启动服务

```bash
# FastAPI 模式（推荐生产环境）
python main.py --backend fastapi

# Django 模式（适合开发和管理）
python main.py --backend django
```

### 前端部署

```bash
# 进入前端目录
cd frontend-next

# 安装依赖
npm install

# 配置环境变量
cp config.example.js config.js

# 开发模式
npm run dev

# 生产构建
npm run build
npm start
```

## 🔧 常用命令速查

### 前端命令

```bash
cd frontend-next

npm run dev              # 开发服务器
npm run build            # 生产构建
npm run start            # 启动生产服务器
npm run lint             # 代码检查
```

## 🆘 常见问题

### 1. 端口被占用

```bash
# 查看端口占用
lsof -i :3000  # 前端端口
lsof -i :9421  # 后端端口

# 修改 docker-compose.yml 中的端口映射
FRONTEND_PORT=3001
BACKEND_PORT=9422
```

### 2. 数据库连接失败

```bash
# 检查 PostgreSQL 是否运行
docker-compose ps postgres

# 查看数据库日志
docker-compose logs postgres

# 检查连接字符串
echo $DATABASE_URL
```

### 3. 前端无法连接后端

```bash
# 检查 CORS 配置
# 确保 .env 中包含前端域名
CORS_ORIGINS=http://localhost:3000

# 检查 API 地址配置
# frontend-next/config.js
export const API_URL = 'http://localhost:9421'
```

## 📚 下一步

- [📦 详细部署指南](DEPLOYMENT_GUIDE.md) - 生产环境部署
- [🔌 插件开发指南](PLUGIN_DEVELOPMENT_GUIDE.md) - 开发自定义插件
- [🎨 主题开发指南](THEME_DEVELOPMENT_GUIDE.md) - 创建自定义主题
- [📖 API 参考文档](API_REFERENCE.md) - 完整 API 文档
- [❓ 故障排查](TROUBLESHOOTING_FAQ.md) - 解决常见问题