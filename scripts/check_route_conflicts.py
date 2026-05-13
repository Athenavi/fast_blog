#!/usr/bin/env python3
"""
路由自动检测脚本
用于检测路由冲突、重复和冗余问题
"""
import sys
from collections import defaultdict
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.app import create_app
    from src.setting import ProductionConfig

    # 创建应用实例
    app = create_app(ProductionConfig())

    if app is None:
        print("Error: app is None. The application failed to initialize.")
        sys.exit(1)
except Exception as e:
    print(f"Error importing or creating app: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)


def check_duplicate_routes():
    """检测完全相同的 (method, path) 对"""
    print("\n" + "=" * 80)
    print("检查重复路由...")
    print("=" * 80)

    routes_map = defaultdict(list)
    duplicates_found = False

    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            for method in route.methods:
                if method in ['HEAD', 'OPTIONS']:
                    continue
                key = (method, route.path)
                endpoint_name = route.endpoint.__name__ if hasattr(route.endpoint, '__name__') else str(route.endpoint)
                routes_map[key].append(endpoint_name)

    for (method, path), endpoints in routes_map.items():
        if len(endpoints) > 1:
            duplicates_found = True
            print(f"\n❌ 发现重复路由: {method} {path}")
            for endpoint in endpoints:
                print(f"   - {endpoint}")

    if not duplicates_found:
        print("\n✅ 未发现重复路由")

    return not duplicates_found


def check_path_conflicts():
    """检测路径参数与具体路径的冲突"""
    print("\n" + "=" * 80)
    print("检查路径冲突...")
    print("=" * 80)

    # 收集所有路由路径
    static_paths = []
    dynamic_paths = []

    for route in app.routes:
        if hasattr(route, 'path'):
            path = route.path
            if '{' in path:
                dynamic_paths.append((path, route))
            else:
                static_paths.append((path, route))

    conflicts_found = False

    # 检查静态路径是否是动态路径的前缀
    for static_path, static_route in static_paths:
        for dynamic_path, dynamic_route in dynamic_paths:
            # 将动态路径转换为正则模式
            pattern = dynamic_path.replace('{', '<').replace('}', '>')
            parts_dynamic = pattern.split('/')
            parts_static = static_path.split('/')

            # 检查是否可能冲突
            if len(parts_static) == len(parts_dynamic):
                match = True
                for s_part, d_part in zip(parts_static, parts_dynamic):
                    if d_part.startswith('<') and d_part.endswith('>'):
                        continue  # 动态参数，匹配任何值
                    elif s_part != d_part:
                        match = False
                        break

                if match:
                    conflicts_found = True
                    static_endpoint = static_route.endpoint.__name__ if hasattr(static_route.endpoint,
                                                                                '__name__') else str(
                        static_route.endpoint)
                    dynamic_endpoint = dynamic_route.endpoint.__name__ if hasattr(dynamic_route.endpoint,
                                                                                  '__name__') else str(
                        dynamic_route.endpoint)
                    print(f"\n⚠️  潜在路径冲突:")
                    print(f"   静态路径: {static_path} -> {static_endpoint}")
                    print(f"   动态路径: {dynamic_path} -> {dynamic_endpoint}")
                    print(f"   建议: 确保静态路径在动态路径之前注册")

    if not conflicts_found:
        print("\n✅ 未发现路径冲突")

    return not conflicts_found


def check_path_redundancy():
    """检测路径冗余（如重复的单词）"""
    print("\n" + "=" * 80)
    print("检查路径冗余...")
    print("=" * 80)

    redundancy_found = False

    for route in app.routes:
        if hasattr(route, 'path'):
            path = route.path
            parts = path.split('/')

            # 检查是否有连续的重复部分
            for i in range(len(parts) - 1):
                if parts[i] and parts[i] == parts[i + 1]:
                    redundancy_found = True
                    endpoint_name = route.endpoint.__name__ if hasattr(route.endpoint, '__name__') else str(
                        route.endpoint)
                    print(f"\n❌ 发现路径冗余: {path}")
                    print(f"   重复部分: '{parts[i]}'")
                    print(f"   端点: {endpoint_name}")
                    break

    if not redundancy_found:
        print("\n✅ 未发现路径冗余")

    return not redundancy_found


def check_naming_consistency():
    """检查路由命名一致性"""
    print("\n" + "=" * 80)
    print("检查路由命名一致性...")
    print("=" * 80)

    issues_found = False

    for route in app.routes:
        if hasattr(route, 'path'):
            path = route.path

            # 检查是否使用了下划线而不是连字符
            if '_' in path and '/api/' in path:
                issues_found = True
                endpoint_name = route.endpoint.__name__ if hasattr(route.endpoint, '__name__') else str(route.endpoint)
                suggested = path.replace('_', '-')
                print(f"\n⚠️  命名不一致: {path}")
                print(f"   建议使用连字符: {suggested}")
                print(f"   端点: {endpoint_name}")

    if not issues_found:
        print("\n✅ 路由命名一致性好")

    return not issues_found


def generate_report():
    """生成完整的检测报告"""
    print("\n" + "=" * 80)
    print("路由自动检测报告")
    print("=" * 80)
    print(f"检测时间: {Path(__file__).stat().st_mtime}")
    print(f"应用路由总数: {len(app.routes)}")

    results = {
        'duplicate_routes': check_duplicate_routes(),
        'path_conflicts': check_path_conflicts(),
        'path_redundancy': check_path_redundancy(),
        'naming_consistency': check_naming_consistency(),
    }

    print("\n" + "=" * 80)
    print("检测总结")
    print("=" * 80)

    all_passed = all(results.values())

    for check_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{check_name}: {status}")

    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 所有检查通过！路由配置良好。")
    else:
        print("⚠️  发现一些问题，请查看上述详情进行修复。")
    print("=" * 80)

    return all_passed


if __name__ == "__main__":
    success = generate_report()
    sys.exit(0 if success else 1)
