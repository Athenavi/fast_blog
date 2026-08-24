# FastBlog 快速开始

> 适用版本：V0.6.26+ | 前置要求：Python 3.14+ / Node.js 18+ / PostgreSQL 16+ / Redis 7+（可选）

## 方式一：Docker（推荐）

```bash
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog
cp .env.example .env
# 编辑 .env：必须设置 SECRET_KEY / JWT_SECRET_KEY（>=32 位随机）与数据库密码
docker compose up -d
```

生产环境请使用：

```bash
docker compose -f docker-compose.prod.yml up -d
```

> 生产 compose 强制要求显式密钥（缺失即报错），并自动启用多 worker + Redis。

## 方式二：手动部署

### 后端

```bash
cd fast_blog
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# 编辑 .env：设置 SECRET_KEY / JWT_SECRET_KEY（>=32 位随机）与数据库连接信息

alembic upgrade head       # 初始化数据库
python main.py             # 启动后端（默认端口 9421）
```

### 前端

```bash
cd frontend-astro
npm install
npm run dev        # 开发模式（自动扫描插件前端，默认端口 4321）
npm run build      # 生产构建（自动扫描插件前端）
npm run preview    # 预览生产构建
```

> `npm run prescan` 会扫描 `plugins/*/frontend/manifest.json` 自动生成管理页面与侧边栏菜单；`dev`/`build` 已内置该步骤。

## 常用命令

```bash
# CLI 工具
python -m cli user create --username admin --password 你的密码 --superuser  # 创建管理员
python -m cli plugin list     # 列出插件
python -m cli cache clear     # 清除缓存

# 数据库迁移
alembic upgrade head                    # 应用迁移
alembic revision --autogenerate -m "描述"  # 生成新迁移
alembic downgrade -1                    # 回滚迁移

# 性能压测（k6）
k6 run --vus 20 --duration 60s tests/load/k6/benchmark.js
```

## 常见问题

- **端口被占用**：`netstat -ano | findstr :4321`（Windows）或 `lsof -i :4321`（Linux/Mac）
- **前端无法连接后端**：检查 `.env` 的 `CORS_ORIGINS`，确保包含前端域名，如 `CORS_ORIGINS=http://localhost:4321`
- **Redis 连接失败**：Redis 为可选组件，不可用时自动降级为内存缓存

## 下一步

- [部署指南](deployment.md) — 生产环境部署与安全
- [开发指南](development.md) — 架构 / 插件 / 主题 / API
- [运维手册](operations.md) — 故障排查 / AI / 移动端
