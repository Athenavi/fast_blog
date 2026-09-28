"""AI Agent 技能框架：可注册、可发现、按权限执行

对齐 v2 的 ``shared/services/ai/skills_framework.py``（SkillMetadata / BaseSkill /
SkillRegistry / SkillSandbox）与 ``core_skills.py``（content_creator / seo_optimizer / …）。
v3 的做法有三点不同，都是有意的：

1. **技能是代码注册表，不是数据库记录** —— 技能就是代码，存表只会带来"表里有、代码没有"的漂移；
2. **权限真实校验**：技能声明 ``required_permission``（复用 v3 权限码），执行前用
   ``load_codes`` 读当前用户真实拥有的权限码，不满足就 403；
3. **技能都做真事**：每个技能都调用 v3 已有的真实服务（LLM / SEO / 迁移解析 / 真表聚合），
   没有"返回固定 JSON"的空壳技能。

v2 的 ``SkillSandbox`` 只是进程内 try/except 包装（隔离能力有限）；v3 保留"单个技能失败不影响
框架"的语义，但**不假装**成安全沙箱 —— 技能与框架同进程，这里如实说明。
"""

import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.core.permission.loader import load_codes

logger = get_logger("ai.skill")

#: 技能分类（对齐 v2 的 SkillCategory，只保留 v3 实际落地的几类）
SKILL_CATEGORIES: Dict[str, str] = {
    "content_creation": "内容创作",
    "seo_optimization": "SEO 优化",
    "data_analysis": "数据分析",
    "data_migration": "数据迁移",
    "system_ops": "系统运维",
}


@dataclass
class SkillContext:
    """技能执行上下文：数据库会话 + 参数 + 当前用户"""

    db: AsyncSession
    params: Dict[str, Any] = field(default_factory=dict)
    user: Any = None
    request: Any = None
    #: 需要调用 LLM 的技能用它选配置（留空则由技能自行取第一条配置）
    config_id: Optional[int] = None

    def param(self, name: str, default: Any = None) -> Any:
        value = self.params.get(name)
        return default if value in (None, "") else value

    def require(self, name: str, *, label: Optional[str] = None) -> Any:
        value = self.params.get(name)
        if value in (None, "", [], {}):
            raise BadRequestError(f"缺少必填参数：{label or name}")
        return value

    def int_param(self, name: str, *, default: Optional[int] = None) -> Optional[int]:
        value = self.params.get(name)
        if value in (None, ""):
            return default
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise BadRequestError(f"参数 {name} 必须是整数") from exc


@dataclass(frozen=True)
class SkillSpec:
    """技能定义（不可变）"""

    name: str
    label: str
    description: str
    category: str
    #: 执行该技能所需的 v3 权限码；None 表示登录即可
    required_permission: Optional[str]
    params: Tuple[Dict[str, Any], ...]
    handler: Callable[[SkillContext], Awaitable[Dict[str, Any]]]


class SkillRegistry:
    """技能注册表"""

    def __init__(self) -> None:
        self._skills: Dict[str, SkillSpec] = {}

    def register(self, spec: SkillSpec) -> SkillSpec:
        if spec.name in self._skills:
            raise ValueError(f"技能已注册：{spec.name}")
        if spec.category not in SKILL_CATEGORIES:
            raise ValueError(f"未知技能分类：{spec.category}（可选：{sorted(SKILL_CATEGORIES)}）")
        self._skills[spec.name] = spec
        return spec

    def get(self, name: str) -> SkillSpec:
        spec = self._skills.get(name)
        if spec is None:
            raise NotFoundError(f"技能不存在：{name}（可用：{', '.join(sorted(self._skills))}）")
        return spec

    def describe(self, name: str) -> Dict[str, Any]:
        """技能详情（含参数说明，供前端渲染表单）"""
        return self._out(self.get(name))

    def names(self) -> List[str]:
        return sorted(self._skills)

    def list_skills(
        self, *, category: Optional[str] = None, keyword: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        items = sorted(self._skills.values(), key=lambda spec: (spec.category, spec.name))
        if category:
            items = [spec for spec in items if spec.category == category]
        if keyword:
            needle = keyword.strip().lower()
            items = [
                spec
                for spec in items
                if needle in spec.name.lower()
                   or needle in spec.label.lower()
                   or needle in spec.description.lower()
            ]
        return [self._out(spec) for spec in items]

    async def execute(self, ctx: SkillContext, name: str) -> Dict[str, Any]:
        """执行技能：先校验权限，再跑处理器，最后带上耗时"""
        spec = self.get(name)
        await self._assert_permission(ctx, spec)

        started = time.perf_counter()
        try:
            result = await spec.handler(ctx)
        except (BadRequestError, ForbiddenError, NotFoundError):
            raise
        except Exception as exc:  # noqa: BLE001 - 技能内部异常要转成可读的 400，并留下堆栈
            logger.exception("技能 %s 执行失败", name)
            raise BadRequestError(f"技能「{spec.label}」执行失败：{type(exc).__name__}: {exc}") from exc

        return {
            "skill": spec.name,
            "label": spec.label,
            "category": spec.category,
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "result": result,
        }

    async def _assert_permission(self, ctx: SkillContext, spec: SkillSpec) -> None:
        if not spec.required_permission:
            return
        user_id = getattr(ctx.user, "id", None)
        if user_id is None:
            raise ForbiddenError("执行技能需要登录")
        owned = await load_codes(ctx.db, int(user_id), request=ctx.request)
        if spec.required_permission not in owned:
            raise ForbiddenError(
                f"执行技能「{spec.label}」需要权限 {spec.required_permission}"
            )

    @staticmethod
    def _out(spec: SkillSpec) -> Dict[str, Any]:
        return {
            "name": spec.name,
            "label": spec.label,
            "description": spec.description,
            "category": spec.category,
            "category_label": SKILL_CATEGORIES.get(spec.category, spec.category),
            "required_permission": spec.required_permission,
            "params": [dict(item) for item in spec.params],
        }


registry = SkillRegistry()


def skill(
    name: str,
    *,
    label: str,
    description: str,
    category: str,
    required_permission: Optional[str] = None,
    params: Tuple[Dict[str, Any], ...] = (),
):
    """装饰器：把 ``async def handler(ctx) -> dict`` 注册成技能"""

    def wrapper(func: Callable[[SkillContext], Awaitable[Dict[str, Any]]]):
        registry.register(
            SkillSpec(
                name=name,
                label=label,
                description=description,
                category=category,
                required_permission=required_permission,
                params=tuple(params),
                handler=func,
            )
        )
        return func

    return wrapper
