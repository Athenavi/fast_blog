# FastBlog 安全扫描工具使用说明

## 概述

`security_scan.py` 是一个自动化的依赖安全扫描工具，用于检查 Python 和 Node.js 依赖的安全漏洞。

## 功能特性

- 🔍 **Python 依赖扫描**: 使用 Safety 工具检查 pip 包的安全漏洞
- 📦 **Node.js 依赖扫描**: 使用 npm audit 检查 npm 包的安全漏洞
- 📊 **详细报告**: 按严重程度分类显示漏洞信息
- 🔧 **修复建议**: 提供具体的修复命令和建议

## 使用方法

### 基本用法

```bash
# 在项目根目录运行
python scripts/security_scan.py
```

### 输出示例

```
================================================================================
Python 依赖安全扫描
================================================================================

🔍 正在扫描 Python 依赖漏洞...

✅ Python 依赖安全检查通过！

================================================================================
Node.js 依赖安全扫描
================================================================================

🔍 正在扫描 Node.js 依赖漏洞...

⚠️  发现 3 个安全漏洞

  - moderate: 2
  - high: 1

建议运行以下命令修复:
  npm audit fix          # 自动修复兼容的漏洞
  npm audit fix --force  # 强制修复（可能引入 breaking changes）

================================================================================
安全扫描总结
================================================================================

Python 依赖: ✅ 通过
Node.js 依赖: ⚠️  发现问题

⚠️  建议尽快修复发现的安全漏洞

后续步骤:
1. 查看上述详细报告
2. 更新有漏洞的依赖包
3. 重新运行此脚本验证修复
4. 将此脚本添加到 CI/CD 流程中
```

## 集成到 CI/CD

### GitHub Actions 示例

```yaml
name: Security Scan

on:
  schedule:
    - cron: '0 0 * * 1'  # 每周一运行
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  security-scan:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install safety

      - name: Run security scan
        run: python scripts/security_scan.py
```

### GitLab CI 示例

```yaml
security_scan:
  stage: test
  script:
    - pip install -r requirements.txt
    - pip install safety
    - python scripts/security_scan.py
  only:
    - schedules
    - main
```

## 定期执行

建议将安全扫描设置为定期任务：

```bash
# 添加到 crontab，每周日凌晨 2 点执行
0 2 * * 0 cd /path/to/fast_blog && python scripts/security_scan.py >> logs/security_scan.log 2>&1
```

## 注意事项

1. **首次运行**: 脚本会自动安装 Safety 工具
2. **网络要求**: 需要访问 PyPI 和 npm registry
3. **退出码**:
    - 0: 所有检查通过
    - 1: 发现安全漏洞
4. **误报处理**: 某些漏洞可能有误报，请根据实际情况评估

## 相关资源

- [Safety 官方文档](https://pyup.io/safety/)
- [npm audit 文档](https://docs.npmjs.com/cli/v9/commands/npm-audit)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)

## 维护者

FastBlog Core Team

最后更新: 2026-05-01
