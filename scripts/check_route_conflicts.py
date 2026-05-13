"""
路由冲突检测与修复工具

功能：
1. 检测 v1 和 v2 路由中的路径冲突
2. 识别重复注册的端点
3. 生成修复建议报告
4. 自动修复部分常见冲突
"""
import importlib
from collections import defaultdict
from typing import Dict, List, Tuple, Set


def extract_routes_from_registry(registry: list) -> List[Dict]:
    """
    从路由注册表中提取所有路由信息
    
    Args:
        registry: 路由注册表列表
        
    Returns:
        路由信息列表
    """
    routes = []

    for module_path, prefix, tags, required in registry:
        try:
            mod = importlib.import_module(module_path)
            router = getattr(mod, "router", None)

            if router is None:
                continue

            # 遍历路由器中的所有路由
            if hasattr(router, 'routes'):
                for route in router.routes:
                    if hasattr(route, 'path') and hasattr(route, 'methods'):
                        full_path = f"{prefix}{route.path}" if prefix else route.path

                        # 规范化路径（移除尾部斜杠）
                        normalized_path = full_path.rstrip('/')
                        if not normalized_path:
                            normalized_path = '/'

                        for method in route.methods:
                            routes.append({
                                'method': method,
                                'path': normalized_path,
                                'full_path': full_path,
                                'module': module_path,
                                'tags': tags,
                                'handler': getattr(route, 'endpoint', None).__name__ if hasattr(route,
                                                                                                'endpoint') else 'unknown'
                            })

        except Exception as e:
            print(f"Warning: Failed to load {module_path}: {e}")

    return routes


def detect_route_conflicts(routes: List[Dict]) -> Dict[str, List[Dict]]:
    """
    检测路由冲突
    
    Args:
        routes: 路由信息列表
        
    Returns:
        冲突字典，key 为冲突路径，value 为冲突的路由列表
    """
    # 按 (method, path) 分组
    route_map = defaultdict(list)

    for route in routes:
        key = (route['method'], route['path'])
        route_map[key].append(route)

    # 找出冲突（多个模块注册了相同的路径）
    conflicts = {}
    for key, route_list in route_map.items():
        if len(route_list) > 1:
            # 检查是否来自不同模块
            modules = set(r['module'] for r in route_list)
            if len(modules) > 1:
                conflicts[f"{key[0]} {key[1]}"] = route_list

    return conflicts


def detect_dynamic_path_conflicts(routes: List[Dict]) -> List[Dict]:
    """
    检测动态路径冲突（如 /api/v1/{id} 可能覆盖其他路径）
    
    Args:
        routes: 路由信息列表
        
    Returns:
        潜在冲突列表
    """
    dynamic_routes = []
    static_routes = []

    # 分离动态和静态路由
    for route in routes:
        path = route['path']
        if '{' in path:
            dynamic_routes.append(route)
        else:
            static_routes.append(route)

    conflicts = []

    # 检查动态路由是否在根级别（危险）
    for route in dynamic_routes:
        parts = route['path'].split('/')
        # 如果动态参数在较浅层级，可能覆盖其他路由
        for i, part in enumerate(parts):
            if part.startswith('{') and i < len(parts) - 1:
                conflicts.append({
                    'type': 'root_level_dynamic',
                    'route': route,
                    'issue': f"动态参数 '{part}' 位于路径层级 {i}，可能覆盖后续路径",
                    'severity': 'high'
                })

    return conflicts


def analyze_generic_paths(routes: List[Dict]) -> Dict[str, List[Dict]]:
    """
    分析通用路径使用情况（如 /stats、/config）
    
    Args:
        routes: 路由信息列表
        
    Returns:
        通用路径使用统计
    """
    generic_keywords = ['stats', 'config', 'delete', 'export', 'generate', 'sync']
    generic_usage = defaultdict(list)

    for route in routes:
        path_parts = route['path'].split('/')
        last_part = path_parts[-1] if path_parts else ''

        if last_part in generic_keywords:
            generic_usage[last_part].append(route)

    return dict(generic_usage)


def generate_conflict_report(
        v1_routes: List[Dict],
        v2_routes: List[Dict],
        output_file: str = None
) -> str:
    """
    生成完整的冲突检测报告
    
    Args:
        v1_routes: v1 路由列表
        v2_routes: v2 路由列表
        output_file: 输出文件路径（可选）
        
    Returns:
        报告文本
    """
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("FastBlog API 路由冲突检测报告")
    report_lines.append("=" * 80)
    report_lines.append("")

    # 1. V1 路由冲突
    report_lines.append("## 1. V1 路由内部冲突")
    report_lines.append("-" * 80)
    v1_conflicts = detect_route_conflicts(v1_routes)

    if v1_conflicts:
        report_lines.append(f"发现 {len(v1_conflicts)} 个冲突:\n")
        for conflict_path, conflicting_routes in v1_conflicts.items():
            report_lines.append(f"### 冲突: {conflict_path}")
            for route in conflicting_routes:
                report_lines.append(
                    f"  - 模块: {route['module']}\n"
                    f"    Handler: {route['handler']}\n"
                    f"    Tags: {route['tags']}"
                )
            report_lines.append("")
    else:
        report_lines.append("✅ 未发现 V1 路由冲突\n")

    # 2. V2 路由冲突
    report_lines.append("\n## 2. V2 路由内部冲突")
    report_lines.append("-" * 80)
    v2_conflicts = detect_route_conflicts(v2_routes)

    if v2_conflicts:
        report_lines.append(f"发现 {len(v2_conflicts)} 个冲突:\n")
        for conflict_path, conflicting_routes in v2_conflicts.items():
            report_lines.append(f"### 冲突: {conflict_path}")
            for route in conflicting_routes:
                report_lines.append(
                    f"  - 模块: {route['module']}\n"
                    f"    Handler: {route['handler']}\n"
                    f"    Tags: {route['tags']}"
                )
            report_lines.append("")
    else:
        report_lines.append("✅ 未发现 V2 路由冲突\n")

    # 3. 动态路径冲突
    report_lines.append("\n## 3. 动态路径风险分析")
    report_lines.append("-" * 80)
    v1_dynamic_conflicts = detect_dynamic_path_conflicts(v1_routes)
    v2_dynamic_conflicts = detect_dynamic_path_conflicts(v2_routes)

    all_dynamic_conflicts = v1_dynamic_conflicts + v2_dynamic_conflicts

    if all_dynamic_conflicts:
        report_lines.append(f"发现 {len(all_dynamic_conflicts)} 个潜在风险:\n")
        for conflict in all_dynamic_conflicts:
            report_lines.append(
                f"### 风险 [{conflict['severity'].upper()}]"
            )
            report_lines.append(
                f"  - 路径: {conflict['route']['path']}\n"
                f"    模块: {conflict['route']['module']}\n"
                f"    问题: {conflict['issue']}"
            )
            report_lines.append("")
    else:
        report_lines.append("✅ 未发现动态路径风险\n")

    # 4. 通用路径使用统计
    report_lines.append("\n## 4. 通用路径使用统计")
    report_lines.append("-" * 80)
    v1_generic = analyze_generic_paths(v1_routes)
    v2_generic = analyze_generic_paths(v2_routes)

    all_generic = {}
    for keyword in set(list(v1_generic.keys()) + list(v2_generic.keys())):
        all_generic[keyword] = {
            'v1': v1_generic.get(keyword, []),
            'v2': v2_generic.get(keyword, [])
        }

    for keyword, usage in all_generic.items():
        v1_count = len(usage['v1'])
        v2_count = len(usage['v2'])
        report_lines.append(f"\n### /{keyword}")
        report_lines.append(f"  V1 使用次数: {v1_count}")
        report_lines.append(f"  V2 使用次数: {v2_count}")

        if v1_count > 1:
            report_lines.append(f"  ⚠️  V1 中存在 {v1_count} 个 /{keyword} 路径，建议迁移到 V2")
        if v2_count > 1:
            report_lines.append(f"  ⚠️  V2 中仍存在 {v2_count} 个 /{keyword} 路径，需要进一步区分")

    # 5. 统计摘要
    report_lines.append("\n\n## 5. 统计摘要")
    report_lines.append("-" * 80)
    report_lines.append(f"V1 路由总数: {len(v1_routes)}")
    report_lines.append(f"V2 路由总数: {len(v2_routes)}")
    report_lines.append(f"V1 冲突数量: {len(v1_conflicts)}")
    report_lines.append(f"V2 冲突数量: {len(v2_conflicts)}")
    report_lines.append(f"动态路径风险: {len(all_dynamic_conflicts)}")
    report_lines.append("")

    report_text = "\n".join(report_lines)

    # 输出到文件
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        print(f"报告已保存到: {output_file}")

    return report_text


def main():
    """主函数：执行完整的路由冲突检测"""
    import sys
    import os

    # 添加项目根目录到 Python 路径
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # 设置输出编码为 UTF-8
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("开始加载路由配置...")
    print(f"项目根目录: {project_root}")

    # 加载 v1 路由
    try:
        from src.app import ROUTE_REGISTRY
        print(f"[OK] 加载 V1 路由配置 ({len(ROUTE_REGISTRY)} 个模块)")
        v1_routes = extract_routes_from_registry(ROUTE_REGISTRY)
        print(f"[OK] 提取 V1 路由 ({len(v1_routes)} 条)")
    except Exception as e:
        print(f"[ERROR] 加载 V1 路由失败: {e}")
        v1_routes = []

    # 加载 v2 路由
    try:
        from src.api.v2 import ROUTE_REGISTRY_V2
        print(f"[OK] 加载 V2 路由配置 ({len(ROUTE_REGISTRY_V2)} 个模块)")
        v2_routes = extract_routes_from_registry(ROUTE_REGISTRY_V2)
        print(f"[OK] 提取 V2 路由 ({len(v2_routes)} 条)")
    except Exception as e:
        print(f"[ERROR] 加载 V2 路由失败: {e}")
        v2_routes = []

    # 生成报告
    print("\n生成冲突检测报告...")
    report = generate_conflict_report(
        v1_routes,
        v2_routes,
        output_file="X:\\project\\fast_blog\\debug\\route_conflict_report.md"
    )

    print("\n" + report)
    print("\n✅ 检测完成！")


if __name__ == "__main__":
    main()
