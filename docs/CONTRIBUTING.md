# FastBlog 贡献指南

欢迎为 FastBlog 做出贡献！本指南将帮助您开始。

## 🎯 如何贡献

### 代码贡献
- 修复 bug / 添加功能 / 优化性能

### 文档贡献
- 完善文档 / 翻译 / 编写教程

### 社区贡献
- 回答问题 / 提交 issue / 参与讨论

## 🚀 贡献流程

```bash
# 1. Fork 并克隆
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog

# 2. 创建分支
git checkout -b feature/your-feature

# 3. 开发测试
pip install -r requirements.txt
cd frontend-next && npm install

# 4. 提交
git add .
git commit -m "feat: 添加新功能"
git push origin feature/your-feature
```

## 📝 提交规范

使用约定式提交：

```
<type>(<scope>): <subject>

示例：
feat(auth): 添加 OAuth 登录
fix(api): 修复用户查询 bug
docs(readme): 更新安装说明
```

**类型**: feat | fix | docs | style | refactor | test

## 🔧 开发规范

```bash
# 后端检查
black src/
flake8 src/

# 前端检查
npm run lint
```

## 🐛 报告 Issue

**模板**:

```
**描述 bug**
简要描述现象

**重现步骤**
1. 访问 '...'
2. 点击 '....'
3. 看到错误

**期望行为**
应该发生什么

**环境**
- 操作系统：Windows/Linux/macOS
- 浏览器：Chrome/Firefox
- 版本：具体版本号
```

## 🙏 感谢！

您的每一份贡献都让 FastBlog 变得更好！
