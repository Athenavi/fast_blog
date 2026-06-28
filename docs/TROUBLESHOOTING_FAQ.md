# FastBlog 故障排查 FAQ

**适用版本**: FastBlog V0.3.26.0521+

---

## 安装问题

### pip install 失败

```bash
pip install --upgrade pip setuptools wheel
pip cache purge
pip install -r requirements.txt
```

### npm install 失败

```bash
npm cache clean --force
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps
```

### Docker 构建失败

```bash
docker system prune -a
docker-compose build --no-cache
```

---

## 配置问题

### SECRET_KEY 未设置

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
# 将输出添加到 .env 的 SECRET_KEY
```

### CORS 错误

在 `.env` 中配置：
```env
CORS_ORIGINS=http://localhost:4321,http://localhost:9421,https://yourdomain.com
```

---

## 数据库问题

### Alembic 迁移失败

```bash
alembic current          # 检查当前状态
alembic history          # 查看迁移历史
alembic downgrade base   # 回滚到初始
alembic upgrade head     # 重新应用
```

### Alembic 报 "No 'script_location' key"

`alembic.ini` 文件缺失（被 `.gitignore` 忽略）。

```bash
# 强制添加并提交
git add -f alembic.ini
git commit -m "chore: force add alembic.ini"
git push

# 或在服务器上手动创建
cat > alembic.ini << 'EOF'
[alembic]
script_location = alembic_migrations
prepend_sys_path = .
path_separator = os
EOF
```

### Alembic 报 "permission denied for schema public"

数据库用户 `fastblog` 没有 `public` schema 的权限。需要用 `postgres` 超级用户授权：

```bash
psql -h localhost -U postgres -d fb260628 -c "
GRANT ALL PRIVILEGES ON DATABASE fb260628 TO fastblog;
GRANT ALL PRIVILEGES ON SCHEMA public TO fastblog;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO fastblog;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO fastblog;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO fastblog;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO fastblog;
"
```

### Alembic 报 "permission denied for table alembic_version"

`fastblog` 用户无权创建表。同样需要用 `postgres` 超级用户执行上述授权命令。

### 登录报 "Failed to record audit log: 'details' is an invalid keyword argument for AuditLog"

后端代码 `shared/services/security/audit_log_service.py` 使用了 `details=` 参数，
但 SQLAlchemy 模型 `AuditLog` 没有 `details` 字段（正确的字段名是 `request_data`）。

```bash
# 拉取修复后重启后端
git pull origin alpha
pkill -f "python main.py"
cd /www/wwwroot/fast_blog
nohup python3 main.py --port 9421 > logs/app.log 2>&1 &
```

### 数据库性能慢

```sql
ANALYZE;
REINDEX DATABASE fast_blog;
VACUUM FULL;
```

---

## 前端问题

### 前端无法连接后端

```bash
curl http://localhost:9421/api/v2/health  # 检查后端是否运行
# 确认 CORS 配置
# 确认 frontend-astro/.env 中的 PUBLIC_API_BASE_URL
```

### Astro 构建失败

```bash
rm -rf .astro dist node_modules/.cache
npm install
npm run build
```

### 构建报错 "Unterminated string literal"

`import` 语句被放在了 frontmatter 中的动态代码之后（如 `try/catch` 之后）。ESM `import` 是静态声明，Rollup 要求它们在模块顶部。

**修复**：将 `import` 移到 frontmatter 最顶部：

```astro
---
import '@/styles/globals.css';  // ✅ 正确：放在最前面
import Layout from '@/layouts/Layout.astro';
// ... 动态代码 ...
---
```

### 页面请求 localhost:9421

浏览器端仍在请求开发地址。检查 `dist/client/config.js`：

```js
// ✅ 正确：生产环境应为空字符串
API_BASE_URL: ''
// ❌ 错误：这是开发地址
API_BASE_URL: 'http://localhost:9421'
```

> 同域名部署时，`API_BASE_URL` 设为 `''`，浏览器使用相对路径，由 Nginx 代理转发。

### 前端 502 Bad Gateway

可能原因：

```bash
# 1. 后端未运行
ss -tlnp | grep 9421

# 2. SSR 未运行
pm2 list
ss -tlnp | grep 4321

# 3. Nginx 配置错误（IPv4/IPv6 不匹配）
# SSR 默认监听 [::1]:4321（IPv6），Nginx 需用 proxy_pass http://[::1]:4321
# 如用 127.0.0.1:4321 会 502

# 4. uwsgi vs HTTP（重要）
# 如果后端用 uwsgi，Nginx 需用 uwsgi_pass 而非 proxy_pass
# 改用 python main.py（uvicorn）后使用标准 HTTP

---

## 常见问题

### 如何重置管理员密码？

```bash
# 连接数据库并更新密码哈希
docker-compose exec postgres psql -U postgres fast_blog
python -c "from src.extensions import _get_pwd_context; print(_get_pwd_context().hash('new_password'))"
UPDATE users SET hashed_password = '新哈希值' WHERE username = 'admin';
```

### 如何备份数据？

```bash
docker-compose exec postgres pg_dump -U postgres fast_blog > backup.sql
tar -czf media_backup.tar.gz media/
```

---

## 获取帮助

- [GitHub Issues](https://github.com/Athenavi/fast_blog/issues)
- [GitHub Discussions](https://github.com/Athenavi/fast_blog/discussions)
