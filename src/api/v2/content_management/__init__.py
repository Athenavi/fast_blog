"""
内容管理API聚合路由器 - V2统一入口
整合V1的content_management相关模块
"""
from fastapi import APIRouter

from src.api.v1.content_management.block_editor import router as block_editor_router
# 导入V1的content_management子模块
from src.api.v1.content_management.category_management import router as category_management_router
from src.api.v1.content_management.custom_block_patterns import router as custom_block_patterns_router
from src.api.v1.content_management.custom_post_types import router as custom_post_types_router
from src.api.v1.content_management.feed import router as feed_router
from src.api.v1.content_management.form_builder import router as form_builder_router
from src.api.v1.content_management.menu_management import router as menu_management_router
from src.api.v1.content_management.shortcode import router as shortcode_router
from src.api.v1.content_management.widgets import router as widgets_router

# 创建聚合路由器
router = APIRouter(tags=["content-management"])

# 按顺序包含子路由
router.include_router(category_management_router, prefix="/categories")  # /categories/*
router.include_router(form_builder_router, prefix="/admin/form")  # /admin/form/*
router.include_router(menu_management_router, prefix="/admin/menu")  # /admin/menu/*
router.include_router(custom_block_patterns_router, prefix="/pattern")  # /pattern/*
router.include_router(block_editor_router, prefix="")  # 块编辑器
router.include_router(custom_post_types_router, prefix="")  # 自定义文章类型
router.include_router(feed_router, prefix="")  # Feed
router.include_router(shortcode_router, prefix="")  # Shortcode
router.include_router(widgets_router, prefix="")  # Widgets
