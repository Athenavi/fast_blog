#!/usr/bin/env python3
"""
扫描所有 API 模块，找出有 router 属性的模块
"""
import importlib
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置 Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_blog.settings')
import django

try:
    django.setup()
except:
    pass

api_v1_path = Path("src/api/v1")
modules_with_router = []

print("扫描 src/api/v1 目录下的所有模块...")
print("=" * 80)

# 遍历所有子目录
for item in api_v1_path.iterdir():
    if item.is_dir() and not item.name.startswith('_'):
        # 检查目录下是否有 __init__.py 或 .py 文件
        init_file = item / "__init__.py"

        # 尝试导入目录（如果有 __init__.py）
        if init_file.exists():
            module_name = f"src.api.v1.{item.name}"
            try:
                mod = importlib.import_module(module_name)
                router = getattr(mod, "router", None)
                if router:
                    modules_with_router.append((module_name, item.name))
                    print(f"✅ {module_name:50s} - 找到 router")
            except Exception as e:
                print(f"❌ {module_name:50s} - 导入失败: {e}")

        # 检查目录下的 .py 文件
        for py_file in item.glob("*.py"):
            if py_file.name.startswith('_'):
                continue

            module_name = f"src.api.v1.{item.name}.{py_file.stem}"
            try:
                mod = importlib.import_module(module_name)
                router = getattr(mod, "router", None)
                if router:
                    modules_with_router.append((module_name, f"{item.name}/{py_file.name}"))
                    print(f"✅ {module_name:50s} - 找到 router")
            except Exception as e:
                # 忽略导入错误，只报告成功找到的
                pass

print("\n" + "=" * 80)
print(f"共找到 {len(modules_with_router)} 个带有 router 的模块\n")

print("可用的模块列表（可用于 ROUTE_REGISTRY）:")
print("-" * 80)
for module_name, file_path in sorted(modules_with_router):
    print(f'    ("{module_name}", "/api/v1", ["{module_name.split(".")[-1]}"], False),')
