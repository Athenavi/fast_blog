# FastBlog 测试套件

后端测试基于 **pytest**。当前 `tests/` 下共 **58 个 `test_*.py`**，其中 **41 个是 v3 域模块测试**（`test_v3_*.py`）。

## 运行环境

- Python 依赖：`pip install -r requirements.txt`（含 `pytest`、`pytest-asyncio`；CI 里另外显式装了这两个）
- 外部服务：**PostgreSQL 16** 与 **Redis 7**（部分用例需要；本地可 `docker compose -f docker-compose.dev.yml up -d`）
- 环境变量：`tests/conftest.py` 已为所有用例注入默认值，无需手工配置

  | 变量 | conftest 默认值 |
    |---|---|
  | `ENVIRONMENT` | `testing` |
  | `SECRET_KEY` | `test-secret-key-for-testing-only`（仅本地测试用） |
  | `JWT_SECRET_KEY` | `test-jwt-secret-key` |
  | `DB_NAME` | `fast_blog_test` |

  `test_config` fixture 提供 `database_url`（`DATABASE_URL`，默认
  `postgresql+asyncpg://postgres:postgres@localhost:5432/fast_blog_test`）与 `redis_url`（`REDIS_URL`，默认
  `redis://localhost:6379/1`）。

## 运行

```bash
python -m pytest tests/ -q                       # 全量
python -m pytest tests/test_v3_content.py -q     # 单个文件
python -m pytest tests/ -m unit                  # 仅单元测试
python -m pytest tests/ -m "not slow"            # 跳过慢用例
python -m pytest tests/ --cov=src --cov-report=html
```

标记（`pytest.ini` 与 `conftest.py` 均已注册）：`unit`、`integration`、`slow`、`asyncio`。

## 文件组织

| 分组         | 文件                                                                                        | 覆盖内容                                                                                                                                                                                                      |
|------------|-------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 基础         | `test_health.py`、`test_api.py`、`test_crud_api.py`、`test_models.py`                        | 健康检查、API 端点、CRUD 骨架、模型                                                                                                                                                                                    |
| 认证与安全      | `test_auth.py`、`test_security.py`、`test_permission_control.py`、`test_permission_cache.py` | JWT、安全中间件、权限判定与缓存                                                                                                                                                                                         |
| 查询行为       | `test_filters.py`、`test_field_filter.py`、`test_pagination.py`                             | 过滤、字段裁剪、分页                                                                                                                                                                                                |
| SEO / 内容辅助 | `test_seo.py`、`test_seo_helpers.py`                                                       | sitemap、元数据等                                                                                                                                                                                              |
| 插件与 MCP    | `test_plugins.py`、`test_mcp_agent_engine.py`、`test_mcp_tool_handlers.py`                  | 插件系统、MCP 引擎与工具                                                                                                                                                                                            |
| v3 域模块（41） | `test_v3_*.py`                                                                            | 按域覆盖：`system` / `content` / `analytics` / `ops` / `extension` / `marketing` / `mobile` / `ai` / `chat` / `commerce` / `gamification`，以及基础 CRUD 骨架（`test_v3_base_crud.py`）、数据范围（`test_v3_group_scope.py`）等 |
| 工具链        | `test_generate_routes_model.py`、`test_version_manager_format.py`                          | 模型生成器、`version.txt` 格式                                                                                                                                                                                    |
| 共享 fixture | `conftest.py`                                                                             | 事件循环、`test_config`、环境变量默认值                                                                                                                                                                                |

## 约定

- 文件 `test_<module>.py`、类 `Test<Feature>`、函数 `test_<behavior>`（`pytest.ini` 的 `python_files` / `python_classes` /
  `python_functions`）。
- 新增 v3 模块时，多个测试里硬编码了"模块集合期望常量"（`test_v3_system.py`、`test_v3_mobile.py`、`test_v3_group_scope.py`、
  `test_v3_analytics_ops.py`、`test_v3_gamification.py`），改 `DOMAIN_MODULES` 后必须同步。
- 需要真实外部工具的能力（备份类依赖 `pg_dump` / `pg_restore` / `psql`）在工具或权限缺失时 `pytest.skip`，不会伪装通过。

## 注意事项

- 本机 **Redis 不可用会让登录相关用例超时**（限流/防爆破中间件同步等待缓存），表现为大面积挂起而不是 401/500。
- 迁移相关用例通过 `DATABASE_URL` + `alembic upgrade head` 建表；`alembic_migrations/env.py` 会以 `config/.env` 覆盖环境变量。
- CI 的 `test-backend` job 会跑 `tests/` 全量，并额外做 `alembic upgrade head → downgrade -1 → upgrade head` 往返（
  `.github/workflows/ci.yml`）。
