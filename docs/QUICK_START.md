# FastBlog 快速入门指南

本文档提供 FastBlog 系统的详细部署和配置指南。

**当前版本**: V0.3.26.0521

## 💻 手动部署

### 前置要求

- Python 3.14+
- Node.js 18+
- PostgreSQL 17+
- Redis 7+（可选，用于缓存）

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
CORS_ORIGINS=http://localhost:4321,http://localhost:9421
```

#### 3. 数据库初始化

```bash
# 创建数据库
psql -U postgres
CREATE DATABASE fast_blog;
\q

# 运行迁移
alembic upgrade head

# 或者应用启动后访问 /install 运行初始迁移
```

#### 4. 启动服务

```bash
# 启动 FastAPI 后端（默认端口 9421）
python main.py

# 指定端口和环境
python main.py --port 9421 --env prod

# 使用监督器模式启动（自动重启崩溃的进程）
python main.py --mode supervisor
```

### 前端部署（Astro）

```bash
# 进入前端目录
cd frontend-astro

# 安装依赖
npm install

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置 API_BASE_URL

# 开发模式（默认端口 4321）
npm run dev

# 生产构建
npm run build
npm run preview
```

### Docker 部署（推荐）

```bash
# 一键启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 🔧 常用命令速查

### CLI 工具

```bash
# 项目管理
python scripts/cli.py create my-blog       # 初始化项目
python scripts/cli.py dev --port 9421      # 启动开发服务器
python scripts/cli.py doctor               # 系统健康检查

# 用户管理
python scripts/cli.py user create admin --admin  # 创建管理员用户

# 插件管理
python scripts/cli.py plugin list          # 列出插件
python scripts/cli.py plugin enable <slug> # 启用插件

# 主题管理
python scripts/cli.py theme activate modern-minimal  # 切换主题

# 数据库
python scripts/cli.py db backup            # 备份数据库

# 缓存
python scripts/cli.py cache clear          # 清除缓存
```

### 前端命令（Astro）

```bash
cd frontend-astro

npm run dev              # 开发服务器 (http://localhost:4321)
npm run build            # 生产构建
npm run preview          # 预览生产构建
npm run lint             # 代码检查
```

### 数据库迁移

```bash
# 生成新迁移
alembic revision --autogenerate -m "描述信息"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1

# 查看当前版本
alembic current
```

## 🆘 常见问题

### 1. 端口被占用

```bash
# 查看端口占用（Linux/Mac）
lsof -i :4321  # 前端端口
lsof -i :9421  # 后端端口

# Windows
netstat -ano | findstr :4321
netstat -ano | findstr :9421

# 修改端口
# 后端：python main.py --port 9422
# 前端：修改 frontend-astro/astro.config.mjs 中的 server.port
```

### 2. 数据库连接失败

```bash
# 检查 PostgreSQL 是否运行
# Linux
sudo systemctl status postgresql
# Docker
docker-compose ps postgres

# 检查连接字符串
echo $DATABASE_URL

# 测试连接
psql -U user -d fast_blog -h localhost
```

### 3. 前端无法连接后端

```bash
# 检查 CORS 配置
# 确保 .env 中包含前端域名
CORS_ORIGINS=http://localhost:4321

# 检查 API 地址配置
# frontend-astro/.env
PUBLIC_API_BASE_URL=http://localhost:9421
```

### 4. Redis 连接失败

Redis 是可选的缓存组件。如果 Redis 不可用，系统会自动降级为内存缓存。

```bash
# 检查 Redis 是否运行
redis-cli ping

# 启动 Redis
# Linux
sudo systemctl start redis
# Docker
docker-compose up -d redis
```

## 📚 下一步

- [📦 详细部署指南](DEPLOYMENT_GUIDE.md) - 生产环境部署
- [🔌 插件开发指南](PLUGIN_DEVELOPMENT_GUIDE.md) - 开发自定义插件
- [🎨 主题开发指南](THEME_DEVELOPMENT_GUIDE.md) - 创建自定义主题
- [📖 API 参考文档](API_REFERENCE.md) - 完整 API v2 文档
- [❓ 故障排查](TROUBLESHOOTING_FAQ.md) - 解决常见问题
- [🤖 AI 交互指南](AI_INTERACTION_GUIDE.md) - MCP Server 集成
