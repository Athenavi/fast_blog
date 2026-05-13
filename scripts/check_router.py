#!/usr/bin/env python3
"""
检查所有路由模块是否有 router 属性
"""
import importlib
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置 Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_blog.settings')
import django

try:
    django.setup()
except:
    pass

# 从 app.py 导入路由注册表
from src.app import ROUTE_REGISTRY

print("检查所有路由模块的 router 属性...")
print("=" * 60)

failed_modules = []
success_modules = []

for module_path, prefix, tags, required in ROUTE_REGISTRY:
    try:
        mod = importlib.import_module(module_path)
        router = getattr(mod, "router", None)
        if router is None:
            status = "❌ FAIL"
            failed_modules.append((module_path, prefix, tags, required))
        else:
            status = "✅ OK"
            success_modules.append(module_path)
        print(f"{status} | {module_path:50s} | prefix: {prefix:30s} | required: {required}")
    except ImportError as e:
        status = "❌ IMPORT ERROR"
        failed_modules.append((module_path, prefix, tags, required))
        print(f"{status} | {module_path:50s} | {e}")
    except Exception as e:
        status = "❌ ERROR"
        failed_modules.append((module_path, prefix, tags, required))
        print(f"{status} | {module_path:50s} | {e}")

print("\n" + "=" * 60)
print(f"成功: {len(success_modules)}, 失败: {len(failed_modules)}")

if failed_modules:
    print("\n失败的模块:")
    for module_path, prefix, tags, required in failed_modules:
        print(f"  - {module_path} (required: {required})")
