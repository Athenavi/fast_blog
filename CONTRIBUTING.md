# 贡献指南

感谢您对 FastBlog 的关注！以下是参与贡献的指引。

## 开发环境

- Python 3.11+ / 3.14+
- Node.js 20+
- PostgreSQL 16+
- Redis 7+

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog

# 后端
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
python main.py

# 前端
cd frontend-astro
npm install
npm run dev
```

## 运行测试

```bash
# 后端测试
python -m pytest tests/ -v

# 前端测试
cd frontend-astro
npm run test

# TypeScript 检查
npx tsc --noEmit
```

## 数据库迁移

```bash
# 生成新的迁移
alembic revision --autogenerate -m "描述变更"

# 应用迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

## 代码规范

- Python: 遵循 PEP 8，使用 Black 格式化
- TypeScript: 严格模式（`strict: true`）
- API 路径: 使用 `src/lib/api/api-paths.ts` 中的常量
- API 版本: 新功能在 V2 中开发，V1 不再注册新路由

## 提交信息

建议使用以下格式：
```
<类型>: <简短描述>

<详细描述>
```

类型: `feat` / `fix` / `test` / `refactor` / `docs` / `ci` / `chore`
