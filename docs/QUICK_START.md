# FastBlog 快速入门指南

**当前版本**: V0.6.26.0611

## 💻 手动部署

### 前置要求

- Python 3.14+
- Node.js 18+
- PostgreSQL 17+
- Redis 7+（可选，用于缓存）

### 后端部署

```bash
# 克隆项目
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog

# 创建虚拟环境并安装依赖
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 配置环境
cp .env_example .env
# 编辑 .env 中的数据库连接信息

# 初始化数据库
alembic upgrade head

# 启动后端（默认端口 9421）
python main.py
```

### 前端部署

```bash
cd frontend-astro
npm install
npm run dev     # 开发模式（自动扫描插件前端，默认端口 4321）
npm run build   # 生产构建（自动扫描插件前端）
npm run preview # 预览生产构建
```

> 插件前端：`npm run prescan` 会扫描 `plugins/*/frontend/manifest.json`，自动生成管理页面和侧边栏菜单。`dev` 和 `build` 命令已包含此步骤。

### Docker 部署

```bash
docker-compose up -d
```

---

## 🔧 常用命令

```bash
# CLI 工具
python scripts/cli.py create my-blog           # 初始化项目
python scripts/cli.py user create admin --admin # 创建管理员用户
python scripts/cli.py plugin list               # 列出插件
python scripts/cli.py cache clear               # 清除缓存

# 数据库迁移
alembic upgrade head             # 应用迁移
alembic revision --autogenerate -m "描述"  # 生成新迁移
alembic downgrade -1             # 回滚迁移
```

---

## 🆘 常见问题

### 端口被占用

```bash
# Windows
netstat -ano | findstr :4321
netstat -ano | findstr :9421
# Linux/Mac
lsof -i :4321
lsof -i :9421
```

### 前端无法连接后端

检查 `.env` 中的 CORS 配置，确保包含前端域名：
```env
CORS_ORIGINS=http://localhost:4321
```

### Redis 连接失败

Redis 为可选组件，不可用时自动降级为内存缓存。

---

## 📚 下一步

- [部署指南](DEPLOYMENT_GUIDE.md) — 生产环境部署
- [API 参考文档](API_REFERENCE.md) — 完整 API v2 文档
- [插件开发指南](PLUGIN_DEVELOPMENT_GUIDE.md) — 开发自定义插件
- [故障排查](TROUBLESHOOTING_FAQ.md) — 解决常见问题
