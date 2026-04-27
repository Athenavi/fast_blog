# FastBlog 快速入门指南

5分钟内部署和运行 FastBlog 系统。

## 🚀 Docker 部署（推荐）

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- Git

### 部署步骤

```bash
# 1. 克隆项目
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog

# 2. 配置环境变量（可选）
cp .env.docker.example .env

# 3. 启动服务
docker-compose up -d

# 4. 查看启动日志
docker-compose logs -f

# 5. 访问应用
# 前端：http://localhost:3000
# API：http://localhost:9421/docs
# Django Admin：http://localhost:9421/admin/
```

### 默认账号

- **Django Admin**: admin / admin123

### 常用管理命令

```bash
# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend   # 后端日志
docker-compose logs -f frontend  # 前端日志

# 进入容器
docker-compose exec backend bash
docker-compose exec frontend sh

# 更新服务
docker-compose pull
docker-compose up -d
```

## 💻 手动部署

### 前置要求

- Python 3.14+
- Node.js 18+
- PostgreSQL 17+
- Redis 7+
- Git

### 后端部署

#### 1. 准备环境

```bash
# 克隆项目
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/Mac
source venv/bin/activate
# Windows
venv\Scripts\activate

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

# 安全密钥
SECRET_KEY=your-secret-key-here

# CORS 配置
CORS_ORIGINS=http://localhost:3000,http://localhost:9421

# 后端模式
BACKEND_MODE=fastapi  # 或 django
```

**生成 SECRET_KEY**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

#### 3. 数据库初始化

```bash
# 创建数据库
psql -U postgres
CREATE DATABASE fast_blog;
\q

# 运行迁移
python django_blog/manage.py migrate

# 创建超级管理员（Django 模式）
python django_blog/manage.py createsuperuser
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

## 🎯 首次使用指南

### Django 模式

1. **访问管理后台**: http://localhost:9421/admin/
2. **登录**: 使用创建的管理员账号
3. **创建第一篇文章**:
   - 点击 "Articles" -> "Add Article"
   - 填写标题、内容（支持 Markdown）
   - 选择分类和标签
   - 点击 "Save"
4. **查看文章**: http://localhost:3000/blog/[article-slug]

### FastAPI 模式

1. **访问 API 文档**: http://localhost:9421/docs
2. **测试 API**:
   - 在 Swagger UI 中测试各个接口
   - 使用 Postman 或其他工具

### 基本配置

#### 1. 网站信息配置

```bash
# Django Admin -> Settings -> Site Settings
# 或使用 API
POST /api/v1/settings
{
  "site_name": "我的博客",
  "site_description": "一个现代化的博客系统",
  "site_url": "https://example.com"
}
```

#### 2. 主题配置

```bash
# Django Admin -> Themes
# 选择并激活主题
```

#### 3. 插件安装

```bash
# Django Admin -> Plugins
# 浏览可用插件
# 点击 "Install" 安装插件
# 点击 "Activate" 激活插件
```

## 🔧 常用命令速查

### 后端命令

```bash
# 路由代码生成
python scripts/generate_routes.py              # 生成所有路由
python scripts/generate_routes.py --watch      # 监听模式自动生成

# 数据库操作
python django_blog/manage.py migrate           # 运行迁移
python django_blog/manage.py makemigrations    # 创建迁移文件
python django_blog/manage.py createsuperuser   # 创建管理员
python django_blog/manage.py shell             # Django Shell
```

### 前端命令

```bash
cd frontend-next

# 开发
npm run dev              # 开发服务器
npm run build            # 生产构建
npm run start            # 启动生产服务器
npm run lint             # 代码检查
```

### Docker 命令

```bash
# 基础操作
docker-compose up -d              # 启动服务
docker-compose down               # 停止服务
docker-compose restart            # 重启服务
docker-compose ps                 # 查看状态

# 日志查看
docker-compose logs -f            # 所有日志
docker-compose logs -f backend    # 后端日志
docker-compose logs -f frontend   # 前端日志

# 维护操作
docker-compose exec backend bash  # 进入后端容器
docker-compose exec frontend sh   # 进入前端容器
docker-compose build --no-cache   # 重新构建镜像
docker-compose pull               # 拉取最新镜像

# 数据库备份
docker-compose exec postgres pg_dump -U postgres fast_blog > backup.sql

# 数据库恢复
docker-compose exec -T postgres psql -U postgres fast_blog < backup.sql
```

## 🆘 常见问题

### 1. 端口被占用

```bash
# 查看端口占用
lsof -i :3000  # 前端端口
lsof -i :9421  # 后端端口

# 修改端口
# 编辑 docker-compose.yml 或 .env 文件
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

### 4. 静态文件 404

```bash
# 收集静态文件（Django）
python django_blog/manage.py collectstatic

# 检查媒体文件权限
chmod -R 755 media/
chmod -R 755 static/
```

## 📚 下一步

- [📦 详细部署指南](DEPLOYMENT_GUIDE.md) - 生产环境部署
- [🔌 插件开发指南](PLUGIN_DEVELOPMENT_GUIDE.md) - 开发自定义插件
- [🎨 主题开发指南](THEME_DEVELOPMENT_GUIDE.md) - 创建自定义主题
- [📖 API 参考文档](API_REFERENCE.md) - 完整 API 文档
- [❓ 故障排查](TROUBLESHOOTING_FAQ.md) - 解决常见问题
- [🤝 贡献指南](CONTRIBUTING.md) - 参与项目开发

## 💬 获取帮助

- **GitHub Issues**: [提交问题](https://github.com/Athenavi/fast_blog/issues)
- **GitHub Discussions**: [社区讨论](https://github.com/Athenavi/fast_blog/discussions)
- **文档**: [完整文档](https://github.com/Athenavi/fast_blog/tree/main/docs)