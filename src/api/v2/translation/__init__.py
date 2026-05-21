"""
翻译API聚合路由器 - V2统一入口
整合V1的translation相关模块（都使用/i18n前缀）
"""
from fastapi import APIRouter

# 导入V1的translation子模块
from src.api.v1.translation.i18n import router as i18n_router
from src.api.v1.translation.translation_io import router as translation_io_router
from src.api.v1.translation.translation_progress import router as translation_progress_router
from src.api.v1.translation.translation_service import router as translation_service_router
from src.api.v1.translation.translations import router as translations_router

# 创建聚合路由器
router = APIRouter(tags=["i18n"])

# 所有子模块都使用相同的/i18n前缀，按顺序包含
router.include_router(i18n_router, prefix="")
router.include_router(translation_io_router, prefix="")
router.include_router(translation_progress_router, prefix="")
router.include_router(translation_service_router, prefix="")
router.include_router(translations_router, prefix="")
