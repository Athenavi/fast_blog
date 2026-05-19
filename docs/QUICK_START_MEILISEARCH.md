# Meilisearch 快速开始指南

## 5分钟快速上手

### 步骤 1: 启动 Meilisearch (1分钟)

```bash
# Windows
start-meilisearch.bat

# Linux/macOS
chmod +x start-meilisearch.sh
./start-meilisearch.sh
```

等待看到 "✅ Meilisearch 已成功启动！" 消息。

### 步骤 2: 安装依赖 (30秒)

```bash
pip install meilisearch-python-sdk
```

### 步骤 3: 激活插件 (1分钟)

1. 登录 FastBlog 后台管理
2. 进入 **插件市场**
3. 找到 **"全文搜索引擎"** 插件
4. 点击 **"激活"**

### 步骤 4: 配置插件 (30秒)

在插件设置页面：

- ✅ 启用搜索引擎: **开启**
- 🌐 Meilisearch 服务器地址: `http://localhost:7700` (默认)
- 🔑 API 密钥: 留空（除非你设置了认证）
- 🔄 自动同步: **开启**
- 📝 发布时索引: **开启**

点击 **保存**。

### 步骤 5: 重建索引 (2分钟，可选)

如果你有现有文章，需要重建索引：

**方法1: 通过后台**

1. 进入插件设置页面
2. 点击 **"重建索引"** 按钮

**方法2: 通过 API**

```bash
curl -X POST http://localhost:8000/api/v1/search/rebuild-index \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### 步骤 6: 测试搜索 (30秒)

访问你的网站，在搜索框输入关键词进行测试。

或者使用 API 测试：

```bash
curl "http://localhost:8000/api/v1/search/articles?q=测试&page=1&per_page=10"
```

---

## 验证安装

运行测试脚本：

```bash
python test_meilisearch.py
```

如果看到 "✅ 所有测试通过！" 说明安装成功。

---

## 常见问题

### Q1: Meilisearch 无法启动？

**检查**:

```bash
# 查看日志
docker-compose -f docker-compose.meilisearch.yml logs

# 检查端口是否被占用
netstat -ano | findstr :7700  # Windows
lsof -i :7700                  # Linux/macOS
```

**解决**: 停止占用端口的程序或修改端口映射。

### Q2: 搜索无结果？

**检查**:

1. Meilisearch 是否正常运行: `http://localhost:7700/health`
2. 插件是否已激活
3. 是否已重建索引

**解决**: 执行索引重建。

### Q3: 新文章搜不到？

**检查**:

1. 文章状态是否为"已发布"
2. 自动同步是否开启
3. 查看插件日志

**手动同步**:

```bash
curl -X POST http://localhost:8000/api/v1/search/sync-article/文章ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 下一步

- 📖 阅读完整文档: `plugins/fulltext-search/README.md`
- 🔧 高级配置: 编辑 `plugins/fulltext-search/plugin.py`
- 📊 查看统计: `GET /api/v1/search/stats`

---

## 性能对比

| 功能   | SQL LIKE | Meilisearch |
|------|----------|-------------|
| 搜索速度 | ~500ms   | ~10-50ms    |
| 模糊匹配 | ❌        | ✅           |
| 结果高亮 | 手动实现     | 内置支持        |
| 拼音搜索 | ❌        | ✅ (可扩展)     |
| 并发支持 | 低        | 高           |
| 资源占用 | 低        | 中等          |

**提升 10-50 倍搜索性能！** 🚀
