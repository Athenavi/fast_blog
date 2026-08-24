# FastBlog Test Suite

**适用版本**: FastBlog V0.5.26.0612+

## Quick Start

```bash
python -m pytest tests/                          # 运行全部测试
python -m pytest tests/ --cov=src --cov-report=html  # 覆盖率报告
python -m pytest tests/ -m unit                  # 仅单元测试
python -m pytest tests/test_api.py -v            # 指定文件
```

## Structure

```
tests/
├── conftest.py           # 共享 fixtures
├── test_health.py        # 健康检查
├── test_models.py        # 模型单元测试
├── test_api.py           # API 端点测试
└── README.md             # 本文件
```

## Conventions

- 文件: `test_<module>.py`
- 类: `Test<Feature>`
- 函数: `test_<behavior>`
- 标记: `@pytest.mark.unit` / `@pytest.mark.integration` / `@pytest.mark.slow`

测试在每次 push 和 PR 时通过 GitHub Actions 自动运行。
