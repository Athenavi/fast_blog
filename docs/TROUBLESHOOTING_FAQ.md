# FastBlog 故障排查 FAQ

**适用版本**: FastBlog V0.3.26.0521+

---

## 📋 目录

1. [安装问题](#安装问题)
2. [配置问题](#配置问题)
3. [数据库问题](#数据库问题)
4. [前端问题](#前端问题)
5. [性能问题](#性能问题)
6. [常见问题](#常见问题)

---

## 安装问题

### Q1: pip install 失败，提示依赖冲突

**症状**:
```
ERROR: Cannot install fastblog and package-x because these package versions have conflicting dependencies.
```

**解决方案**:

```bash
# 1. 升级 pip
pip install --upgrade pip setuptools wheel

# 2. 使用虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 3. 清除缓存后重新安装
pip cache purge
pip install -r requirements.txt
```

### Q2: npm install 失败

**症状**:
```
npm ERR! ERESOLVE unable to resolve dependency tree
```

**解决方案**:

```bash
# 1. 清除 npm 缓存
npm cache clean --force

# 2. 删除 node_modules 和 lock 文件
rm -rf node_modules package-lock.json

# 3. 重新安装
npm install

# 4. 如果仍有问题，使用 legacy peer deps
npm install --legacy-peer-deps
```

### Q3: Docker 构建失败

**症状**:
```
ERROR: failed to solve: process "/bin/sh -c pip install -r requirements.txt" did not complete successfully
```

**解决方案**:

```bash
# 1. 清理 Docker 缓存
docker system prune -a

# 2. 不使用缓存重新构建
docker-compose build --no-cache

# 3. 检查网络连接
ping pypi.org
```

---

## 配置问题

### Q4: 启动时提示 SECRET_KEY 未设置

**症状**:
```
ValueError: SECRET_KEY must be set
```

**解决方案**:

```bash
# 1. 生成随机密钥
python -c "import secrets; print(secrets.token_urlsafe(50))"

# 2. 添加到 .env 文件
echo "SECRET_KEY=your-generated-key-here" >> .env

# 3. 重启服务
docker-compose restart
```

### Q5: CORS 错误

**症状**:
```
Access to fetch at 'http://localhost:9421/api/v2/articles' from origin 'http://localhost:4321' has been blocked by CORS policy
```

**解决方案**:

在 `.env` 中配置：

```env
CORS_ORIGINS=http://localhost:4321,http://localhost:9421,https://yourdomain.com
```

### Q6: 数据库连接超时

**症状**:
```
OperationalError: could not connect to server: Connection timed out
```

**解决方案**:

```bash
# 1. 检查数据库是否运行
sudo systemctl status postgresql

# 2. 检查防火墙
sudo ufw status
sudo ufw allow 5432/tcp

# 3. 检查 PostgreSQL 配置
sudo nano /etc/postgresql/16/main/postgresql.conf
# 确保
listen_addresses = '*'
```

---

## 数据库问题

### Q7: Alembic 迁移失败

**症状**:
```
sqlalchemy.exc.ProgrammingError: relation "xxx" does not exist
```

**解决方案**:

```bash
# 1. 检查当前迁移状态
alembic current

# 2. 查看迁移历史
alembic history

# 3. 如果需要重置，先备份数据库，然后：
alembic downgrade base
alembic upgrade head

# 4. 如果迁移文件损坏，从版本控制恢复
git checkout alembic_migrations/
alembic upgrade head
```

### Q8: 数据库性能慢

**解决方案**:

```sql
-- 1. 分析表
ANALYZE;

-- 2. 重建索引
REINDEX DATABASE fast_blog;

-- 3. 清理死元组
VACUUM FULL;

-- 4. 检查慢查询
SELECT *
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
```

---

## 前端问题

### Q9: 前端无法连接后端

**症状**:

- API 请求失败
- 控制台显示网络错误

**解决方案**:

```bash
# 1. 检查后端是否运行
curl http://localhost:9421/api/v2/health

# 2. 检查 CORS 配置
# 确保 .env 中包含前端域名
CORS_ORIGINS=http://localhost:4321

# 3. 检查 API 地址配置
# frontend-astro/.env
PUBLIC_API_BASE_URL=http://localhost:9421
```

### Q10: 静态文件 404

**症状**:

- CSS/JS 文件加载失败
- 图片显示 broken

**解决方案**:

```bash
# 1. 重新构建前端
cd frontend-astro
npm run build

# 2. 检查媒体文件权限
chmod -R 755 media/
chmod -R 755 static/

# 3. 检查 Nginx 配置
sudo nginx -t
sudo systemctl restart nginx

# 4. 确认静态资源路径
# 本地存储: /assets/storage/
# 主题文件: /assets/themes/
# 标准静态: /static/
```

### Q11: Astro 构建失败

**症状**:

```
Error: Build failed with errors
```

**解决方案**:

```bash
# 1. 清除缓存
rm -rf .astro dist node_modules/.cache

# 2. 重新安装依赖
npm install

# 3. 重新构建
npm run build
```

---

## 性能问题

### Q12: 响应速度慢

**解决方案**:

1. **启用缓存**

```env
REDIS_URL=redis://localhost:6379/0
CACHE_BACKEND=redis
```

2. **优化数据库查询**

- 添加适当的索引
- 使用 `selectinload` 和 `joinedload` 避免 N+1 查询
- 使用异步会话 (`AsyncSession`) 提高并发性能

3. **启用 CDN**

```env
CDN_ENABLED=true
CDN_URL=https://cdn.yourdomain.com
```

4. **压缩资源**

```nginx
gzip on;
gzip_types text/plain text/css application/json application/javascript;
```

### Q13: 内存占用高

**解决方案**:

1. **调整 Uvicorn workers**
```bash
# 减少 worker 数量
python main.py --port 9421
# 默认单 worker，如需多 worker 通过 Docker Compose 扩展
```

2. **优化数据库连接池**

```env
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
```

3. **清理缓存**
```bash
# Redis
redis-cli FLUSHDB
```

---

## 常见问题

### Q14: 如何重置管理员密码？

```bash
# 通过 API 重置（需要数据库直接访问）
# 1. 连接数据库
docker-compose exec postgres psql -U postgres fast_blog

# 2. 生成新的密码哈希
python -c "from src.extensions import _get_pwd_context; print(_get_pwd_context().hash('new_password'))"

# 3. 更新数据库中的密码
UPDATE users SET hashed_password = '新哈希值' WHERE username = 'admin';
```

### Q15: 如何查看日志？

```bash
# Docker 环境
docker-compose logs -f backend
docker-compose logs -f frontend

# 本地环境
tail -f logs/app.log

# 查看 Nginx 日志
docker-compose logs -f nginx
```

### Q16: 端口被占用

```bash
# 查看端口占用
lsof -i :4321  # 前端端口 (Astro)
lsof -i :9421  # 后端端口 (FastAPI)

# 修改端口
# 编辑 docker-compose.yml 或 .env 文件
FRONTEND_PORT=4322
BACKEND_PORT=9422
```

### Q17: 如何备份数据？

```bash
# 数据库备份
docker-compose exec postgres pg_dump -U postgres fast_blog > backup.sql

# 媒体文件备份
tar -czf media_backup.tar.gz media/

# 完整备份
docker-compose down
tar -czf full_backup.tar.gz .

# 使用内置备份 API
curl -X POST http://localhost:9421/api/v2/system/backup/create
```

### Q18: 如何更新系统？

```bash
# Docker 环境
git pull
docker-compose build --no-cache
docker-compose up -d

# 本地环境
git pull
pip install -r requirements.txt
cd frontend-astro && npm install && npm run build
alembic upgrade head
```

---

## 获取帮助

如果以上方法无法解决您的问题：

1. **查看完整日志**

```bash
docker-compose logs -f
# 或
tail -f logs/*.log
```

2. **搜索 Issues**
   访问 [GitHub Issues](https://github.com/Athenavi/fast_blog/issues) 搜索类似问题

3. **提交新 Issue**
   提供以下信息：

- 问题描述
- 重现步骤
- 错误日志
- 环境信息（操作系统、Python 版本、Docker 版本等）

4. **社区讨论**
   访问 [GitHub Discussions](https://github.com/Athenavi/fast_blog/discussions) 寻求帮助

---

## 总结

- ✅ 遇到问题先查看日志
- ✅ 确保配置文件正确
- ✅ 检查依赖版本兼容性
- ✅ 定期备份数据
- ✅ 保持系统和依赖更新

更多详细信息请参考其他文档。
