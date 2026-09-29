"""system/edge：边缘函数（Cloudflare Workers / Vercel Edge）注册 / 校验 / 部署

定义落 ``system_settings``（键 ``edge.functions``），部署记录落 ``edge.deployments``；
校验与产物摘要为纯函数；**不执行**用户代码，无凭据时部署如实降级。
"""

from src.api.v3.modules.system.edge.service import edge_function_service

__all__ = ["edge_function_service"]
