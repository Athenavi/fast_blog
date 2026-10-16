"""V3 模块发现、路由装载与冲突检查

结构对齐 FastApiAdmin `app/core/discover.py`，保留其中两条工程原则：

1. **导入失败必须中止启动**。原文理由："半成品 router 会让进程带着缺失的接口正常提供服务，
   故障被推迟成『某个模块突然 404』，比启动即失败难定位得多"。这直接对立于旧 v3 的
   ``required=False`` 静默跳过 —— 实测旧 v3 的 18 个 admin 模块全部因
   ``No module named 'extensions'`` 加载失败而无人察觉。

2. **启动期检测路由冲突**。FastAPI 按注册顺序首次匹配，冲突不报错、只让部分接口永远不可达。
   实测旧 v3 已有两处：``mobile/articles.py`` 的 ``/search`` 被 ``/{article_id}`` 吞掉、
   ``admin/notifications.py`` 的 ``/clean`` 被 ``/{notification_id}`` 吞掉。

目录约定（与 `src/api/v3/modules/<domain>/<module>/controller.py` 对应）::

    modules/
      system/                  <- 域，映射前缀 /system
        health/controller.py   <- 模块，controller 内声明 APIRouter(prefix="/health")
"""

import importlib
import re
from pathlib import Path
from typing import Iterable

from fastapi import APIRouter, FastAPI

from src.api.v3.core.logger import get_logger

logger = get_logger("discover")

# 路径参数只参与匹配、不参与语义：比对重复路由时先抹掉参数名
_PATH_PARAM_RE = re.compile(r"\{[^}]*\}")


class RouteRegistrationError(RuntimeError):
    """模块导入失败或未暴露 router 时抛出（fail-fast）"""


def controller_module_path(domain: str, module: str, package: str) -> str:
    """由域与模块名拼出 controller 的点号路径"""
    return f"{package}.{domain.strip('/')}.{module}.controller"


def import_controller(module_path: str) -> APIRouter:
    """导入 controller 模块并取回其顶层 APIRouter

    任何失败都抛 ``RouteRegistrationError``（附排查提示），由调用方决定是否 fail-fast。
    """
    try:
        module = importlib.import_module(module_path)
    except Exception as exc:  # noqa: BLE001 - 需要把任何导入期异常都转成可读提示
        raise RouteRegistrationError(f"{module_path} 导入失败：{_import_failure_hint(exc)}") from exc

    routers = [
        value
        for name, value in vars(module).items()
        if not name.startswith("_") and isinstance(value, APIRouter)
    ]
    if not routers:
        raise RouteRegistrationError(
            f"{module_path} 中未找到顶层 APIRouter 实例（约定变量名 router）"
        )
    if len(routers) > 1:
        logger.warning("%s 中存在 %d 个顶层 APIRouter，将按定义顺序全部挂载", module_path, len(routers))
    return routers[0] if len(routers) == 1 else _merge(routers)


def _merge(routers: Iterable[APIRouter]) -> APIRouter:
    merged = APIRouter()
    for router in routers:
        merged.include_router(router)
    return merged


def check_controller_prefix(module_path: str, router: APIRouter, expected_prefix: str) -> None:
    """校验 controller 的 prefix 与目录名一致（不一致只告警，避免过度约束）"""
    if router.prefix != expected_prefix:
        logger.warning(
            "%s 的 APIRouter.prefix=%r 与目录名约定的 %r 不一致，最终路径以 prefix 为准",
            module_path,
            router.prefix,
            expected_prefix,
        )


def scan_unregistered_modules(
    domain: str,
    registered: Iterable[str],
    *,
    package: str,
) -> list[str]:
    """找出磁盘上存在 controller.py 但未登记进路由表的模块（返回模块名列表）"""
    base = importlib.import_module(package)
    domain_dir = Path(next(iter(base.__path__))) / domain.strip("/")
    if not domain_dir.is_dir():
        return []
    found = sorted(
        child.name
        for child in domain_dir.iterdir()
        if child.is_dir() and not child.name.startswith("_") and (child / "controller.py").is_file()
    )
    return [name for name in found if name not in set(registered)]


# ------------------------------------------------------------------ 冲突检测
def find_route_conflicts(routes: Iterable) -> list[str]:
    """返回冲突描述列表；空列表表示无冲突

    参数名不参与匹配语义，``/user/{id}`` 与 ``/user/{uid}`` 视为冲突。
    """
    seen: dict[tuple[str, str], str] = {}
    conflicts: list[str] = []
    for route in routes:
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", None)
        if not methods or not path:
            continue
        normalized = _PATH_PARAM_RE.sub("{}", path)
        endpoint = getattr(route, "name", None) or str(path)
        for method in sorted(methods):
            key = (method, normalized)
            if key in seen:
                conflicts.append(f"{method} {path}（{endpoint}）已被 {seen[key]} 占用")
            else:
                seen[key] = endpoint
    return conflicts


def _compile_path_pattern(pattern: str) -> "re.Pattern[str]":
    """把 ``/user/{id}`` 编译为正则，用于判断某静态路径是否会被它匹配"""
    segments = []
    for segment in pattern.split("/"):
        if not segment:
            continue
        if segment.startswith("{") and segment.endswith("}"):
            segments.append("[^/]+")
        else:
            segments.append(re.escape(segment))
    return re.compile("^/" + "/".join(segments) + "$")


def find_shadowed_routes(routes: Iterable) -> list[str]:
    """返回「静态路径被更早注册的参数路径遮蔽」的描述列表

    这是本项目真实踩过的坑：旧 v3 的 ``GET /articles/{article_id}`` 注册在
    ``GET /articles/search`` 之前，导致 ``/articles/search`` 永远 422。
    纯 REST 路径（``/user``、``/user/{id}``）本身不会触发，但**兼容别名**
    （``/user/list``、``/user/detail/{id}``）会，因此必须守护。
    """
    indexed: list[tuple[int, str, set[str]]] = []
    for position, route in enumerate(routes):
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", None)
        if not methods or not path:
            continue
        indexed.append((position, path, set(methods)))

    shadows: list[str] = []
    for position, path, methods in indexed:
        if "{" in path:
            continue
        for prev_position, prev_path, prev_methods in indexed:
            if prev_position >= position:
                break
            if "{" not in prev_path or not (methods & prev_methods):
                continue
            if _compile_path_pattern(prev_path).match(path):
                shadows.append(
                    f"{path}（第 {position} 条）被更早注册的 {prev_path}（第 {prev_position} 条）遮蔽"
                )
    return shadows


def assert_no_shadowed_routes(target: FastAPI | APIRouter, *, source: str = "API v3") -> None:
    """存在被遮蔽的静态路径时抛 ``RouteRegistrationError``，中止启动"""
    shadows = find_shadowed_routes(target.routes)
    if shadows:
        raise RouteRegistrationError(
            f"{source} 检测到 {len(shadows)} 处路由遮蔽，已中止启动（被遮蔽者永远不可达）：\n   "
            + "\n   ".join(shadows)
        )


def assert_no_route_conflicts(target: FastAPI | APIRouter, *, source: str = "API v3") -> None:
    """存在路由冲突时抛 ``RouteRegistrationError``，中止启动"""
    conflicts = find_route_conflicts(target.routes)
    if conflicts:
        raise RouteRegistrationError(
            f"{source} 检测到 {len(conflicts)} 处路由冲突，已中止启动（后注册者将永远不可达）：\n   "
            + "\n   ".join(conflicts)
        )


def _import_failure_hint(exc: BaseException) -> str:
    """按异常类型给出简短排查提示（照搬 FastApiAdmin 的提示策略）"""
    if isinstance(exc, ModuleNotFoundError):
        missing = getattr(exc, "name", None) or str(exc)
        return (
            f"无法解析模块（ModuleNotFoundError: {missing}）。常见原因："
            "① controller 所在每级目录缺少 __init__.py；"
            "② 目录名不是合法 Python 标识符；"
            "③ 导入路径写错（v3 内部一律用 src.api.v3.* 绝对导入）。"
        )
    if isinstance(exc, ImportError):
        return "导入失败（ImportError），常见原因：循环导入、依赖未安装、相对导入路径错误。"
    if isinstance(exc, SyntaxError):
        return f"controller.py 存在语法错误：{exc.msg}（约第 {exc.lineno} 行）。"
    return f"未分类异常（{type(exc).__name__}）：{exc}"


__all__ = [
    "RouteRegistrationError",
    "assert_no_route_conflicts",
    "assert_no_shadowed_routes",
    "check_controller_prefix",
    "controller_module_path",
    "find_route_conflicts",
    "find_shadowed_routes",
    "import_controller",
    "scan_unregistered_modules",
]
