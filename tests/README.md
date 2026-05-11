# FastBlog 测试套件

本目录包含 FastBlog 项目的单元测试和集成测试。

## 📋 目录结构

```
tests/
├── __init__.py              # 测试包初始化
├── test_plugin_manager.py   # 插件管理器测试
├── test_seo_service.py      # SEO 服务测试
├── test_cache_service.py    # 缓存服务测试
└── conftest.py              # pytest 共享配置（待添加）
```

## 🚀 运行测试

### 运行所有测试

```bash
pytest tests/ -v
```

### 运行特定测试文件

```bash
pytest tests/test_plugin_manager.py -v
```

### 运行特定测试类

```bash
pytest tests/test_plugin_manager.py::TestPluginHooks -v
```

### 运行特定测试方法

```bash
pytest tests/test_plugin_manager.py::TestPluginHooks::test_add_action -v
```

### 运行带标记的测试

```bash
# 运行单元测试
pytest -m unit

# 跳过慢速测试
pytest -m "not slow"
```

### 生成覆盖率报告

```bash
# 安装 coverage
pip install pytest-cov

# 运行并生成报告
pytest tests/ --cov=shared/services --cov-report=html

# 查看 HTML 报告
open htmlcov/index.html
```

## 📊 测试覆盖目标

- **核心服务**: 80%+ 覆盖率
- **API 端点**: 70%+ 覆盖率
- **工具函数**: 90%+ 覆盖率

## 🔧 编写新测试

### 测试文件命名

- 文件名必须以 `test_` 开头
- 例如: `test_my_module.py`

### 测试类命名

- 类名必须以 `Test` 开头
- 例如: `TestMyService`

### 测试函数命名

- 函数名必须以 `test_` 开头
- 描述性命名，说明测试内容
- 例如: `test_user_login_with_valid_credentials`

### 测试示例

```python
import pytest
from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.services.my_service import MyService


class TestMyService:
    """我的服务测试"""

    def setup_method(self):
        """每个测试前的设置"""
        self.service = MyService()

    def test_basic_functionality(self):
        """测试基本功能"""
        result = self.service.do_something("input")
        assert result == "expected_output"

    def test_edge_case(self):
        """测试边界情况"""
        with pytest.raises(ValueError):
            self.service.do_something("")
```

## 🎯 测试最佳实践

1. **独立性**: 每个测试应该独立运行，不依赖其他测试
2. **可重复性**: 测试结果应该一致，不受外部因素影响
3. **清晰性**: 测试名称和断言应该清晰表达意图
4. **完整性**: 测试正常情况和异常情况
5. **隔离性**: 使用 mock 隔离外部依赖

## 📝 待完成的测试模块

- [ ] API 端点测试
- [ ] 数据库模型测试
- [ ] 用户认证测试
- [ ] 文章管理测试
- [ ] 媒体管理测试
- [ ] 评论系统测试
- [ ] Widget 管理测试
- [ ] 主题管理测试
- [ ] 权限系统测试
- [ ] 通知系统测试

## 🔍 调试测试

```bash
# 显示详细输出
pytest tests/ -vv

# 停止在第一个失败
pytest tests/ -x

# 显示本地变量
pytest tests/ --showlocals

# PDB 调试
pytest tests/ --pdb
```

## 📚 参考资料

- [pytest 官方文档](https://docs.pytest.org/)
- [测试最佳实践](https://docs.pytest.org/en/stable/goodpractices.html)
- [Mock 对象](https://docs.python.org/3/library/unittest.mock.html)
