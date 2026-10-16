## 描述

简要说明这个 PR 做了什么，以及为什么。

Fixes #（issue 编号）

## 变更类型

- [ ] Bug 修复（不破坏现有行为）
- [ ] 新功能（不破坏现有行为）
- [ ] 破坏性变更（会让现有功能行为变化，请在下文说明迁移方式）
- [ ] 文档更新
- [ ] 性能优化
- [ ] 重构（无功能变化）
- [ ] 测试相关
- [ ] CI/CD 相关

## 如何验证

请描述验证方式，便于复现：

- [ ] 后端测试 `python -m pytest tests/ -q`
- [ ] 后端 lint `python -m ruff check --no-cache src/api/v3`
- [ ] 前端类型检查 `cd frontend/web && npm run type-check`
- [ ] i18n 校验 `cd frontend/web && npm run check:i18n`（改文案时必填）
- [ ] 前端构建 `cd frontend/web && npm run build`
- [ ] 端到端 `cd frontend/web && npm run test:e2e`
- [ ] 手动验证（说明步骤）

**验证环境**：

- OS: 例如 Ubuntu 22.04
- Python: 例如 3.14
- Node.js: 例如 22.x
- PostgreSQL: 例如 16

## 影响范围

- 涉及的 API（`/api/v3/<域>/<模块>`）或前端页面：
- 是否涉及数据库迁移 / `version.txt` 的 `[DATABASE] migration`：
- 是否涉及权限码（`src/api/v3/core/permission/codes.py`）与 `seed_rbac`：

## 检查清单

- [ ] 我遵循了项目现有风格与约定（见 [CONTRIBUTING.md](../CONTRIBUTING.md)）
- [ ] 我完成了自我审查，并已脱敏（无密钥、密码、真实用户数据）
- [ ] 新增/修改的行为已有测试覆盖
- [ ] 我更新了受影响的文档
- [ ] 我的改动不引入新的告警（ruff / mypy / vue-tsc 无新报错）
- [ ] 本地已通过上文勾选的检查项

## 截图（可选）

## 补充说明
