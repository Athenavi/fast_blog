# FastBlog 部署指南

本文档提供FastBlog的完整部署说明，包括Docker Compose、Kubernetes Helm Chart和手动部署方式。

## 📋 目录

- [快速开始](#快速开始)
- [Docker Compose部署](#docker-compose部署)
- [Kubernetes Helm部署](#kubernetes-helm部署)
- [手动部署](#手动部署)
- [配置说明](#配置说明)
- [备份和恢复](#备份和恢复)
- [监控和维护](#监控和维护)
- [故障排查](#故障排查)

---

## 快速开始

### 一键部署（推荐）

**Linux/macOS:**

```bash
git clone https://github.com/yourusername/fast_blog.git
cd fast_blog
chmod +x install.sh
./install.sh
```

**Windows:**

```cmd
git clone https://github.com/yourusername/fast_blog.git
cd fast_blog
install.bat
```

访问 http://localhost:9421 即可使用。

---

## Docker Compose部署

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少4GB RAM
- 至少10GB磁盘空间

### 部署步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/yourusername/fast_blog.git
   cd fast_blog
   ```

2. **配置环境变量**
   ```bash
   cp .env_example .env
   # 编辑.env文件，修改必要配置
   ```

3. **启动服务**
   ```bash
   docker-compose up -d
   ```

4. **查看日志**
   ```bash
   docker-compose logs -f app
   ```

5. **访问应用**
    - 浏览器: http://localhost:9421
    - API文档: http://localhost:9421/docs

### 服务组成

- **app** - FastBlog主应用 (端口: 9421)
- **postgres** - PostgreSQL数据库 (端口: 5432)
- **redis** - Redis缓存 (端口: 6379)
- **meilisearch** - Meilisearch搜索引擎 (端口: 7700, 可选)
- **nginx** - Nginx反向代理 (端口: 80/443, 可选)

### 常用命令

```bash
# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看状态
docker-compose ps

# 查看资源使用
docker stats

# 进入应用容器
docker-compose exec app bash

# 备份数据
docker-compose exec app python scripts/cli.py backup
```

---

## Kubernetes Helm部署

### 前置要求

- Kubernetes 1.19+
- Helm 3.2.0+
- PV provisioner支持

### 部署步骤

1. **安装Chart**
   ```bash
   helm install fastblog ./k8s/helm
   ```

2. **自定义配置**
   ```bash
   helm install fastblog ./k8s/helm -f production-values.yaml
   ```

3. **查看状态**
   ```bash
   kubectl get pods -l app.kubernetes.io/instance=fastblog
   ```

4. **端口转发（本地访问）**
   ```bash
   kubectl port-forward svc/fastblog 9421:9421
   ```

### 生产环境配置示例

创建 `production-values.yaml`:

```yaml
replicaCount: 3

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10

ingress:
  enabled: true
  className: "nginx"
  hosts:
    - host: blog.example.com
  tls:
    - secretName: fastblog-tls
      hosts:
        - blog.example.com

postgresql:
  primary:
    persistence:
      size: 50Gi

config:
  secretKey: "your-secure-secret-key"
  debug: false
```

```bash
helm install fastblog ./k8s/helm -f production-values.yaml
```

### 升级和回滚

```bash
# 升级
helm upgrade fastblog ./k8s/helm -f production-values.yaml

# 查看历史
helm history fastblog

# 回滚
helm rollback fastblog 1
```

---

## 手动部署

### 前置要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- FFmpeg (视频处理)

### 部署步骤

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **配置环境变量**
   ```bash
   cp .env_example .env
   # 编辑.env文件
   ```

3. **初始化数据库**
   ```bash
   python scripts/cli.py db-upgrade
   ```

4. **启动应用**
   ```bash
   python main.py
   ```

详细的手动部署说明请参考 [QUICK_START_DEPLOYMENT.md](./QUICK_START_DEPLOYMENT.md)

---

## 配置说明

### 环境变量 (.env)

```bash
# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fastblog
DB_USER=postgres
DB_PASSWORD=your_password

# Redis配置
REDIS_URL=redis://localhost:6379/0

# 应用配置
HOST=0.0.0.0
PORT=9421
DEBUG=false
SECRET_KEY=change-this-to-random-key

# Meilisearch配置
MEILISEARCH_URL=http://localhost:7700
MEILISEARCH_KEY=your_master_key

# OAuth配置（可选）
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GITHUB_OAUTH_CLIENT_ID=
GITHUB_OAUTH_CLIENT_SECRET=

# LDAP配置（可选）
LDAP_SERVER=
LDAP_PORT=389
LDAP_BASE_DN=
LDAP_BIND_DN=
LDAP_BIND_PASSWORD=
```

### 重要配置项

| 配置项                     | 说明                | 默认值       |
|-------------------------|-------------------|-----------|
| `SECRET_KEY`            | 应用密钥（必须修改）        | -         |
| `DB_PASSWORD`           | 数据库密码             | -         |
| `DEBUG`                 | 调试模式（生产环境设为false） | false     |
| `BACKUP_DIR`            | 备份目录              | ./backups |
| `BACKUP_RETENTION_DAYS` | 备份保留天数            | 30        |

---

## 备份和恢复

### 自动备份

Docker Compose已配置定时备份服务（backup-scheduler），默认每天凌晨2点备份。

### 手动备份

```bash
# 使用CLI工具备份
docker-compose exec app python scripts/cli.py backup

# 或使用备份脚本
docker-compose exec backup-scheduler /backup.sh
```

### 备份位置

- 数据库备份: `./backups/database/`
- 文件备份: `./backups/files/`
- 完整备份: `./backups/full/`

### 恢复备份

```bash
# 通过API恢复
curl -X POST http://localhost:9421/api/v1/backup/restore/database \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"backup_path": "/app/backups/database/db_backup_20260511.sql.gz", "confirm": true}'
```

详细备份说明请参考 [备份管理API文档](./docs/API_REFERENCE.md)

---

## 监控和维护

### 健康检查

```bash
# 检查应用健康状态
curl http://localhost:9421/api/v1/health

# Docker Compose
docker-compose ps

# Kubernetes
kubectl get pods -l app.kubernetes.io/instance=fastblog
```

### 日志查看

```bash
# Docker Compose
docker-compose logs -f app
docker-compose logs -f postgres

# Kubernetes
kubectl logs -l app.kubernetes.io/instance=fastblog -f
```

### 资源监控

```bash
# Docker
docker stats

# Kubernetes
kubectl top pods -l app.kubernetes.io/instance=fastblog
```

### 数据库维护

```bash
# 进入数据库
docker-compose exec postgres psql -U postgres -d fastblog

# 查看表大小
\dt+

# 清理过期数据
VACUUM ANALYZE;
```

---

## 故障排查

### 常见问题

#### 1. 端口冲突

**症状**: 服务启动失败，提示端口已被占用

**解决**: 修改 `.env` 文件中的端口配置

```bash
APP_PORT=9422
DB_PORT=5433
REDIS_PORT=6380
```

#### 2. 内存不足

**症状**: 容器被杀死或OOM

**解决**:

- Docker: 调整 `docker-compose.yml` 中的资源限制
- Kubernetes: 调整 `values.yaml` 中的resources配置

#### 3. 数据库连接失败

**症状**: 应用无法连接数据库

**解决**:

```bash
# 检查数据库状态
docker-compose ps postgres
docker-compose logs postgres

# 重启数据库
docker-compose restart postgres
```

#### 4. 权限问题

**症状**: 文件写入失败

**解决**:

```bash
sudo chown -R $USER:$USER .
sudo chmod -R 755 media static uploads
```

#### 5. 备份失败

**症状**: 备份脚本执行失败

**解决**:

```bash
# 检查备份目录权限
ls -la backups/

# 手动执行备份
docker-compose exec backup-scheduler /backup.sh

# 查看备份日志
docker-compose logs backup-scheduler
```

### 获取帮助

- 📖 [完整文档](./docs/)
- 💬 [GitHub Discussions](https://github.com/yourusername/fast_blog/discussions)
- 🐛 [Issue Tracker](https://github.com/yourusername/fast_blog/issues)

---

## 安全建议

1. **修改默认密码**
    - 数据库密码
    - SECRET_KEY
    - Meilisearch Master Key

2. **启用HTTPS**
    - 使用Let's Encrypt免费证书
    - 配置Nginx SSL

3. **配置防火墙**
    - 只开放必要端口（80, 443）
    - 限制数据库和Redis的外部访问

4. **定期更新**
    - 及时应用安全补丁
    - 更新依赖包

5. **备份策略**
    - 定期备份数据
    - 测试恢复流程
    - 异地备份

---

## 性能优化

### 应用优化

- 启用Redis缓存
- 配置CDN加速静态资源
- 启用Gzip压缩

### 数据库优化

- 添加适当的索引
- 定期执行VACUUM
- 配置连接池

### Nginx优化

- 启用静态文件缓存
- 配置负载均衡
- 启用HTTP/2

---

祝您部署顺利！🎉
