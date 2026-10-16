# 贡献指南

欢迎提交代码、文档、翻译与问题反馈。参与前请先读本页与 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)（架构与硬约定）。

## 1. 环境准备

```bash
git clone https://github.com/Athenavi/fast_blog.git
cd fast_blog

# 后端
python -m venv .venv
.venv/Scripts/activate                 # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

# 依赖服务（PostgreSQL + Redis）
docker compose -f docker-compose.dev.yml up -d

# 前端
cd frontend/web && npm ci && cd ../..
```

配置：`cp .env.example .env`，填写 `SECRET_KEY`（≥32 位随机）与 `DB_PASSWORD`；然后 `python -m alembic upgrade head` 建表、
`python -m scripts.seed_rbac` 同步权限、`python -m scripts.seed_admin_menus --apply --grant-system-roles` 写入后台菜单。

## 2. 开发约定

**后端**

- API 只在 `src/api/v3/` 下新增，模块用「五件套」结构（`controller.py` / `schema.py` / `crud.py` / `service.py` / 可选
  `model.py`），并在 `src/api/v3/__init__.py::DOMAIN_MODULES` 登记。
- 响应统一 `{code, msg, data, pagination}`（`src/api/v3/common/response.py`）；写操作路由启用 `OperationLogRoute`；权限码加进
  `src/api/v3/core/permission/codes.py` 并跑 `python -m scripts.seed_rbac`。
- 数据模型以 `config/models.yaml` 为唯一权威，改动走生成器与 Alembic 迁移。
- 风格：ruff（行宽 120）与 black/isort 一致；类型标注尽量补全。

**前端**（`frontend/web`）

- 前台只用 Tailwind + `components/ui`，后台只用 Element Plus；颜色走 `styles/index.css` 的语义令牌。
- 新接口封装进 `api/modules/*.ts` 并在 `api/index.ts` 导出；新页面按需在 `nuxt.config.ts::routeRules` 关闭 SSR。
- 改文案必须跑 `npm run check:i18n`（两份 locale 必须对称）。

**提交信息**：沿用 Conventional Commits + 中文描述，例如

```
feat(content): 添加多平台发布适配器
fix(seeds): 修复管理员菜单种子脚本的路径解析问题
docs: 重构部署与开发文档
```

## 3. 提交前必须通过

```bash
python -m pytest tests/ -q
python -m ruff check --no-cache src/api/v3
cd frontend/web && npm run type-check && npm run check:i18n
```

推荐安装 pre-commit（`.pre-commit-config.yaml` 已配置 ruff、ruff-format、mypy、tsc、detect-secrets 等）：

```bash
pip install pre-commit && pre-commit install && pre-commit install --hook-type pre-push
```

## 4. Pull Request

1. 从 `main` 切分支（`feat/…`、`fix/…`、`docs/…`）。
2. 使用仓库的 [PR 模板](.github/PULL_REQUEST_TEMPLATE.md)，说明改动与验证方式。
3. 覆盖新行为：新增功能请补测试（`tests/test_v3_*.py` 或前端 `e2e/*.spec.ts`）。
4. 确保 CI 全绿（`.github/workflows/ci.yml`：lint → 快速用例 / 前端构建与类型检查 → 后端全量测试 + 迁移往返 → 镜像构建）。
5. 保持改动聚焦，一个 PR 解决一件事。

## 5. 其他

- **行为准则**：[CODE_OF_CONDUCT.md](.github/CODE_OF_CONDUCT.md)
- **安全漏洞**：不要开公开 issue，请按 [SECURITY.md](SECURITY.md) 私下报告
- **问题反馈**：用 [Issue 模板](.github/ISSUE_TEMPLATE/) 提交，附版本（`version.txt`）、部署方式、日志
- **许可**：主仓库 Apache-2.0；`plugins/` 下的作品为 MIT
