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
