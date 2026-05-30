"""
系统管理API聚合路由器 - V2统一入口
整合V1的system相关模块
"""
from fastapi import APIRouter

# 导入V1的system子模块
from src.api.v1.system.admin_settings import router as admin_settings_router
from src.api.v1.system.batch_operations import router as batch_operations_router
from src.api.v1.system.data_export import router as data_export_router
from src.api.v1.system.database_migration import router as database_migration_router
from src.api.v1.system.incremental_backup import router as incremental_backup_router
from src.api.v1.system.installation import router as installation_router
from src.api.v1.system.maintenance import router as maintenance_router
from src.api.v1.system.migrations import router as migrations_router
from src.api.v1.system.multisite import router as multisite_router
from src.api.v1.system.report_management import router as report_management_router
from src.api.v1.system.resource_transfer import router as resource_transfer_router
from src.api.v1.system.screen_options import router as screen_options_router
from src.api.v1.system.webhook_management import router as webhook_management_router
from src.api.v1.system.workflow import router as workflow_router

# 创建聚合路由器
router = APIRouter(tags=["system"])

# 按顺序包含子路由
router.include_router(admin_settings_router, prefix="/settings")  # /admin-settings/*
router.include_router(database_migration_router,
                      prefix="/db/database-migration")  # /db/database-migration/*
router.include_router(report_management_router, prefix="/report")  # /report/*
router.include_router(webhook_management_router, prefix="/webhook")  # /webhook/*
router.include_router(incremental_backup_router, prefix="/backup-plus")  # /backup-plus/*
router.include_router(batch_operations_router, prefix="/batch")  # /batch/* - 批量操作
router.include_router(data_export_router, prefix="/export")  # /export/* - 数据导出
router.include_router(installation_router, prefix="/install")  # /install/* - 安装
router.include_router(maintenance_router, prefix="/maintenance")  # /maintenance/* - 维护
router.include_router(migrations_router, prefix="/migrations")  # /migrations/* - 迁移
router.include_router(multisite_router, prefix="/multisite")  # /multisite/* - 多站点
router.include_router(resource_transfer_router, prefix="/transfer")  # /transfer/* - 资源转移
router.include_router(screen_options_router, prefix="/screen-options")  # /screen-options/* - 屏幕选项
router.include_router(workflow_router, prefix="/workflow")  # /workflow/* - 工作流
