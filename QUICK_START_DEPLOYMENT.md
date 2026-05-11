# FastBlog 快速开始指南

## 🚀 一键部署（推荐）

### Linux/macOS

```bash
# 下载FastBlog
git clone https://github.com/yourusername/fast_blog.git
cd fast_blog

# 运行安装脚本
chmod +x install.sh
./install.sh
```

### Windows

```powershell
# 克隆仓库
git clone https://github.com/yourusername/fast_blog.git
cd fast_blog

# 运行安装脚本
.\install.bat
```

安装完成后，访问 http://localhost:9421

---

## 📋 手动部署

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB RAM
- 至少 10GB 磁盘空间

### 步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/yourusername/fast_blog.git
   cd fast_blog
   ```

2. **配置环境变量**
   ```bash
   cp .env_example .env
   # 编辑 .env 文件，修改必要配置
   ```

3. **启动服务**
   ```bash
   docker-compose up -d
   ```

4. **等待服务就绪**
   ```bash
   # 查看日志
   docker-compose logs -f app
   
   # 检查健康状态
   curl http://localhost:9421/api/v1/health
   ```

5. **访问应用**
    - 浏览器打开: http://localhost:9421
    - API文档: http://localhost:9421/docs

---

## 🔧 配置说明

### 环境变量 (.env)

```bash
# 数据库配置
DB_NAME=fastblog
DB_USER=postgres
DB_PASSWORD=your_secure_password
DB_PORT=5432

# Redis配置
REDIS_PORT=6379
REDIS_MAX_MEMORY=256mb

# 应用配置
APP_PORT=9421
DEBUG=false
SECRET_KEY=change-this-to-random-key

# Meilisearch (可选)
MEILI_MASTER_KEY=your_master_key
MEILI_PORT=7700

# Nginx (可选)
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443
```

### 数据持久化

所有数据都存储在Docker卷中：

- `postgres_data` - PostgreSQL数据库
- `redis_data` - Redis缓存
- `meilisearch_data` - 搜索引擎索引
- `nginx_cache` - Nginx缓存

本地目录映射：

- `./media` - 媒体文件
- `./static` - 静态文件
- `./themes` - 主题文件
- `./plugins` - 插件文件
- `./backups` - 备份文件
- `./logs` - 日志文件

---

## 🛠️ 常用命令

### 服务管理

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f app

# 查看特定服务日志
docker-compose logs -f postgres
docker-compose logs -f redis
```

### 数据库管理

```bash
# 进入数据库容器
docker-compose exec postgres psql -U postgres -d fastblog

# 备份数据库
docker-compose exec postgres pg_dump -U postgres fastblog > backup.sql

# 恢复数据库
cat backup.sql | docker-compose exec -T postgres psql -U postgres fastblog
```

### 应用管理

```bash
# 进入应用容器
docker-compose exec app bash

# 运行CLI命令
docker-compose exec app python scripts/cli.py --help

# 创建管理员
docker-compose exec app python scripts/cli.py create-admin --username admin --email admin@example.com

# 备份数据
docker-compose exec app python scripts/cli.py backup
```

### 更新升级

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build

# 清理旧镜像
docker image prune -f
```

---

## 🔐 SSL/HTTPS配置

### 使用Let's Encrypt

1. **安装certbot**
   ```bash
   sudo apt-get install certbot
   ```

2. **获取证书**
   ```bash
   sudo certbot certonly --standalone -d your-domain.com
   ```

3. **配置Nginx**
   ```bash
   # 复制证书到ssl目录
   sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./ssl/cert.pem
   sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./ssl/key.pem
   
   # 编辑nginx配置，启用HTTPS部分
   ```

4. **重启Nginx**
   ```bash
   docker-compose restart nginx
   ```

### 自动续期

```bash
# 添加cron任务
0 0 1 * * certbot renew && docker-compose restart nginx
```

---

## 📊 监控和维护

### 健康检查

```bash
# 检查所有服务状态
docker-compose ps

# 检查应用健康
curl http://localhost:9421/api/v1/health

# 查看资源使用
docker stats
```

### 日志管理

```bash
# 查看实时日志
docker-compose logs -f

# 查看最近100行
docker-compose logs --tail=100 app

# 导出日志
docker-compose logs app > app.log
```

### 备份策略

```bash
# 手动备份
docker-compose exec app python scripts/cli.py backup

# 自动备份（已配置backup-scheduler）
# 默认每天凌晨2点备份，保留30天
```

### 清理空间

```bash
# 清理未使用的镜像
docker image prune -a

# 清理未使用的卷
docker volume prune

# 清理所有未使用资源
docker system prune -a --volumes
```

---

## ❓ 常见问题

### 1. 端口冲突

**问题**: 端口已被其他服务占用

**解决**: 修改 `.env` 文件中的端口配置

```bash
APP_PORT=9422  # 改为其他端口
DB_PORT=5433
REDIS_PORT=6380
```

### 2. 内存不足

**问题**: 容器因内存不足被杀死

**解决**: 调整 `docker-compose.yml` 中的资源限制

```yaml
deploy:
  resources:
    limits:
      memory: 2G  # 降低内存限制
```

### 3. 数据库连接失败

**问题**: 应用无法连接数据库

**解决**:

```bash
# 检查数据库是否启动
docker-compose ps postgres

# 查看数据库日志
docker-compose logs postgres

# 重启数据库
docker-compose restart postgres
```

### 4. 权限问题

**问题**: 文件写入权限错误

**解决**:

```bash
# 修复文件权限
sudo chown -R $USER:$USER .
sudo chmod -R 755 media static uploads
```

### 5. 服务启动慢

**问题**: 首次启动需要下载镜像

**解决**: 这是正常现象，后续启动会很快。可以预先拉取镜像：

```bash
docker-compose pull
```

---

## 📞 获取帮助

- 📖 [完整文档](./docs/)
- 💬 [GitHub Discussions](https://github.com/yourusername/fast_blog/discussions)
- 🐛 [Issue Tracker](https://github.com/yourusername/fast_blog/issues)
- 📧 Email: support@fastblog.com

---

## 🎯 下一步

1. **创建管理员账户**
   ```bash
   docker-compose exec app python scripts/cli.py create-admin
   ```

2. **配置域名和SSL**
    - 参考上面的SSL配置章节

3. **安装插件和主题**
    - 访问管理后台 → 插件/主题市场

4. **导入现有数据**
   ```bash
   docker-compose exec app python scripts/cli.py import --file data.json
   ```

5. **配置备份策略**
    - 备份已自动配置，检查 `./backups` 目录

祝您使用愉快！🎉
