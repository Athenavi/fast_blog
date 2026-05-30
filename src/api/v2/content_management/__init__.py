"""
内容管理API聚合路由器 - V2统一入口
整合V1的content_management相关模块
"""
from fastapi import APIRouter

from src.api.v1.content_management.block_editor import router as block_editor_router
# 导入V1的content_management子模块
from src.api.v1.content_management.block_patterns import router as block_patterns_router
from src.api.v1.content_management.category_management import router as category_management_router
from src.api.v1.content_management.custom_block_patterns import router as custom_block_patterns_router
from src.api.v1.content_management.custom_post_types import router as custom_post_types_router
from src.api.v1.content_management.feed import router as feed_router
from src.api.v1.content_management.form_builder import router as form_builder_router
from src.api.v1.content_management.global_styles import router as global_styles_router
from src.api.v1.content_management.menu_management import router as menu_management_router
from src.api.v1.content_management.page_builder_routes import router as page_builder_router
from src.api.v1.content_management.shortcode import router as shortcode_router
from src.api.v1.content_management.widgets import router as widgets_router

# 创建聚合路由器
router = APIRouter(tags=["content-management"])

# 按顺序包含子路由
router.include_router(category_management_router, prefix="/categories")  # /categories/*
router.include_router(form_builder_router, prefix="/admin/form")  # /admin/form/*
router.include_router(menu_management_router, prefix="/admin/menu")  # /admin/menu/*
router.include_router(custom_block_patterns_router, prefix="/pattern")  # /pattern/*
router.include_router(block_patterns_router, prefix="/block-patterns")  # /block-patterns/* - 块模式库
router.include_router(global_styles_router, prefix="/global-styles")  # /global-styles/* - 全局样式
router.include_router(block_editor_router, prefix="/editor")  # /editor/* - 块编辑器
router.include_router(custom_post_types_router, prefix="/post-types")  # /post-types/* - 自定义文章类型
router.include_router(feed_router, prefix="")  # RSS/Atom Feed
router.include_router(shortcode_router, prefix="/shortcodes")  # /shortcodes/* - 短代码
router.include_router(widgets_router, prefix="/widgets")  # /widgets/* - 小部件
router.include_router(page_builder_router, prefix="")  # /page-builder/* - 页面构建器
