"""
企业管理API聚合路由器 - V2统一入口
整合许可证管理、技术支持工单、部署脚本和监控告警
"""
from fastapi import APIRouter

# 导入V1的企业模块（基础功能）
from src.api.v1.enterprise.enterprise_api import router as base_enterprise_router
# 导入V2的管理增强端点
from src.api.v2.enterprise.admin_endpoints import router as admin_enterprise_router

# 创建聚合路由器
router = APIRouter(tags=["enterprise-v2"])

# 包含V1基础路由（许可证验证、创建工单、回复等用户端功能）
router.include_router(base_enterprise_router, prefix="")
# 包含V2管理增强路由（管理员列表/详情/更新/删除等CRUD）
router.include_router(admin_enterprise_router, prefix="/admin")
