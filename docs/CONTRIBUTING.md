# FastBlog 贡献指南

欢迎为 FastBlog 做出贡献！

## 贡献方式

- **代码贡献**: 修复 bug、添加功能、优化性能
- **文档贡献**: 完善文档、翻译、编写教程
- **社区贡献**: 回答问题、提交 issue、参与讨论

## 贡献流程

```bash
# 1. Fork 并克隆
git clone https://github.com/Athenavi/fast_blog.git

# 2. 创建分支
git checkout -b feature/your-feature

# 3. 提交更改
git commit -m "feat: 添加新功能"
git push origin feature/your-feature

# 4. 创建 Pull Request
```

## 提交规范

使用约定式提交（Conventional Commits）：

```
<type>(<scope>): <subject>

feat(auth): 添加 OAuth 登录
fix(api): 修复用户查询 bug
docs(readme): 更新安装说明
```

**类型**: `feat` | `fix` | `docs` | `style` | `refactor` | `test` | `chore`

## 开发规范

```bash
# 后端
black src/ && flake8 src/

# 前端
cd frontend-astro && npm run lint
```

## 报告 Issue

请在 [GitHub Issues](https://github.com/Athenavi/fast_blog/issues) 提交，并提供：
- 问题描述和重现步骤
- 期望行为和实际行为
- 环境信息（OS、Python 版本等）
