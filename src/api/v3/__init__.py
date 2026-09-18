"""FastBlog API v3 —— 唯一权威 API 层

结构对齐 FastApiAdmin：

  - ``DOMAIN_MODULES`` 是路由的**唯一事实来源**（对应官方 ``app/api/v1/routers.py`` 的
    ``DOMAIN_CONTROLLERS``）
  - 业务模块放在 ``modules/<domain>/<module>/``，五件套分层
    （``controller.py`` / ``schema.py`` / ``crud.py`` / ``service.py`` / ``model.py``）
  - 路由前缀 ``/api/v3/<domain>/<module>``
  - **导入失败与路由冲突/遮蔽都会中止启动**（对应官方 ``app/core/discover.py`` 的两条原则）

迁移状态（Phase 5 完成后的现状）：

  - 旧 ``src/api/v3/admin/**``（18 个模块，从未加载成功）与 ``src/api/v3/mobile/**``
    （6 个扁平前缀模块）已删除，能力分别由 ``system`` 与 ``mobile`` 域取代；
    过渡期使用的 ``LEGACY_V3_REGISTRY`` 机制随之移除
  - ``src/api/v2`` 仍是冻结的兼容层，v3 逐步取代其全部端点
  - 响应格式统一为 ``{code, msg, data, pagination}``
"""

from fastapi import APIRouter

from src.api.v3.core.discover import (
    RouteRegistrationError,
    assert_no_route_conflicts,
    assert_no_shadowed_routes,
    check_controller_prefix,
    controller_module_path,
    import_controller,
    scan_unregistered_modules,
)
from src.api.v3.core.exceptions import register_v3_exception_handlers
from src.api.v3.core.logger import get_logger

logger = get_logger("registry")

API_PREFIX = "/api/v3"
MODULES_PACKAGE = "src.api.v3.modules"

#: 域 → 已登记模块（唯一路由事实来源；新模块必须登记到这里）
DOMAIN_MODULES: dict[str, tuple[str, ...]] = {
    "/system": (
        "admin_menu",
        "auth",
        "group",
        "health",
        "log",
        "menu",
        "permission",
        "role",
        "setting",
        "user",
    ),
    "/content": ("article", "category", "comment", "media", "page", "tag"),
    "/analytics": ("dashboard", "search", "seo"),
    "/ops": ("backup", "notification", "webhook"),
    "/extension": ("plugin", "theme", "widget"),
    "/mobile": ("article", "auth", "category", "comment", "media", "user"),
}


def register_v3_routes(app, *, fail_fast: bool = True) -> dict:
    """注册 v3 路由并返回注册摘要

    :param fail_fast: 模块导入失败时是否直接抛错（默认 True，任何环境都建议开启）
    :raises RouteRegistrationError: 模块导入失败、存在路由冲突或被遮蔽
    """
    root = APIRouter(prefix=API_PREFIX)
    summary: dict = {"domains": {}, "routes": 0, "unregistered": []}

    for domain, modules in DOMAIN_MODULES.items():
        domain_router = APIRouter(prefix=domain)
        loaded: list[str] = []
        for name in modules:
            module_path = controller_module_path(domain, name, MODULES_PACKAGE)
            try:
                router = import_controller(module_path)
            except RouteRegistrationError as exc:
                if fail_fast:
                    logger.error("API v3 模块加载失败，中止启动：%s", exc)
                    raise
                logger.error("API v3 跳过模块 %s：%s", module_path, exc)
                continue
            check_controller_prefix(module_path, router, f"/{name}")
            domain_router.include_router(router)
            loaded.append(name)
        root.include_router(domain_router)
        summary["domains"][domain] = loaded

        unregistered = scan_unregistered_modules(domain, modules, package=MODULES_PACKAGE)
        if unregistered:
            summary["unregistered"].extend(f"{domain}/{name}" for name in unregistered)
            logger.warning(
                "API v3 域 %s 下存在未登记模块 %s（不会被注册，请加入 DOMAIN_MODULES）",
                domain,
                unregistered,
            )

    # 启动期冲突检测：只针对 v3 骨架，避免被 v2 的历史冲突牵连
    assert_no_route_conflicts(root, source="API v3")
    # 遮蔽检测：静态路径不得注册在能匹配它的参数路径之后
    assert_no_shadowed_routes(root, source="API v3")
    app.include_router(root)
    summary["routes"] = len(root.routes)

    # 统一异常响应（仅作用于 /api/v3/**），随路由注册一起挂载
    register_v3_exception_handlers(app)

    logger.info(
        "API v3 路由注册完成 (域: %s, 路由: %d)",
        ", ".join(f"{domain}({len(names)})" for domain, names in summary["domains"].items()),
        summary["routes"],
    )
    return summary


__all__ = [
    "API_PREFIX",
    "DOMAIN_MODULES",
    "MODULES_PACKAGE",
    "RouteRegistrationError",
    "register_v3_routes",
]
