# FastBlog 快速入门指南

本指南将帮助您在5分钟内快速部署和运行FastBlog系统。

## 🚀 快速部署

### 方式一：Docker一键部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog

# 2. 启动完整环境
docker-compose up -d

# 3. 访问应用
# 前端界面: http://localhost:3000
# API文档: http://localhost:9421/docs
# 管理后台: http://localhost:3000/admin
```

### 方式二：手动部署

#### 后端部署
```bash
# 1. 准备环境
cd fast_blog
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境
cp .env_example .env
# 编辑 .env 文件配置数据库连接

# 4. 启动服务
python main.py
```

#### 前端部署
```bash
cd frontend-next
npm install
npm run dev
# 访问 http://localhost:3000
```

## 🔧 系统要求

### 最小配置
- **CPU**: 2核
- **内存**: 2GB
- **存储**: 10GB
- **数据库**: PostgreSQL 12+

### 推荐配置
- **CPU**: 4核
- **内存**: 4GB
- **存储**: 50GB SSD
- **数据库**: PostgreSQL 17+

## 🎯 首次使用

1. **访问管理后台**: `http://localhost:3000/admin`
2. **创建管理员账户**: 系统会引导创建首个管理员账户
3. **基础配置**: 设置网站信息、SMTP、评论系统等

## 🔍 验证部署

```bash
# 检查服务状态
curl http://localhost:9421/health
curl http://localhost:3000/api/health
```

## 🚀 下一步

- [技术架构](./TECHNICAL.md) - 了解系统技术细节
- [贡献指南](./CONTRIBUTING.md) - 参与项目开发

## 🆘 获取帮助

- [GitHub Issues](https://github.com/Athenavi/fast_blog/issues)
- [社区讨论](https://github.com/Athenavi/fast_blog/discussions)
- 技术支持: support@fastblog.example.com