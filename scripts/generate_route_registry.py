#!/usr/bin/env python3
"""
生成正确的 ROUTE_REGISTRY 配置
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

# 遍历所有子目录
for item in api_v1_path.iterdir():
    if item.is_dir() and not item.name.startswith('_'):
        # 检查目录下是否有 __init__.py
        init_file = item / "__init__.py"

        if init_file.exists():
            module_name = f"src.api.v1.{item.name}"
            try:
                mod = importlib.import_module(module_name)
                router = getattr(mod, "router", None)
                if router:
                    modules_with_router.append((module_name, item.name))
            except Exception:
                pass

        # 检查目录下的 .py 文件
        for py_file in sorted(item.glob("*.py")):
            if py_file.name.startswith('_'):
                continue

            module_name = f"src.api.v1.{item.name}.{py_file.stem}"
            try:
                mod = importlib.import_module(module_name)
                router = getattr(mod, "router", None)
                if router:
                    modules_with_router.append((module_name, f"{item.name}/{py_file.name}"))
            except Exception:
                pass

# 核心模块（必需）
core_modules = [
    "src.api.v1.users.users",
    "src.api.v1.__init__",
    "src.api.v1.content_management.category_management",
    "src.api.v1.dashboard.dashboard",
    "src.api.v1.core.home",
]

# 生成配置
print("# ---------- 路由自动发现 ----------")
print("# 配置表：(模块路径, 前缀, 标签列表, 是否必需)")
print("ROUTE_REGISTRY = [")
print("    # 核心模块（必需）")

for module_name, _ in modules_with_router:
    if module_name in core_modules:
        prefix_map = {
            "src.api.v1.users.users": ("/api/v1/users", ["users"]),
            "src.api.v1.__init__": ("", []),
            "src.api.v1.content_management.category_management": ("/api/v1/categories", ["categories"]),
            "src.api.v1.dashboard.dashboard": ("/api/v1/dashboard", ["dashboard"]),
            "src.api.v1.core.home": ("/api/v1", ["home"]),
        }
        prefix, tags = prefix_map.get(module_name, ("/api/v1", [module_name.split(".")[-1]]))
        print(f'    ("{module_name}", "{prefix}", {tags}, True),')

print("    # 功能模块（可选加载，失败仅警告）")

# 添加其他模块
for module_name, file_path in sorted(modules_with_router):
    if module_name not in core_modules:
        # 简化标签名
        tag = module_name.split(".")[-1].replace("_", "-")
        print(f'    ("{module_name}", "/api/v1", ["{tag}"], False),')

print("]")
