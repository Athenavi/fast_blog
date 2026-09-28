"""ai/skill：AI Agent 技能框架

技能是代码注册表（``registry.py`` 的 ``@skill`` 装饰器），内置技能在 ``builtin.py``；
执行前按技能声明的 ``required_permission`` 做真实权限校验。
"""

from src.api.v3.modules.ai.skill import builtin  # noqa: F401 - 导入即完成技能注册
from src.api.v3.modules.ai.skill.registry import SKILL_CATEGORIES, registry, skill

__all__ = ["SKILL_CATEGORIES", "registry", "skill"]
