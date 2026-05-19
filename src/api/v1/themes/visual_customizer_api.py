"""
可视化主题定制器 API

提供实时预览、配置管理、CSS变量生成等功能
"""

from typing import Dict, Any

from fastapi import APIRouter, Depends, Query, Body

from shared.services.themes.visual_customizer import visual_customizer
from src.api.v1.core.responses import ApiResponse
from src.api.v1.users.user_management import jwt_required

router = APIRouter(prefix="/visual-customizer", tags=["Visual Theme Customizer"])


@router.post("/preview")
async def generate_preview(
        theme_slug: str = Body(..., description="主题标识"),
        config: Dict[str, Any] = Body(..., description="主题配置"),
        preview_type: str = Body("article", description="预览类型 (article/homepage/category)"),
        current_user=Depends(jwt_required)
):
    """
    生成主题预览
    
    根据配置生成实时预览HTML，支持文章页、首页等不同页面类型
    """
    html = visual_customizer.generate_preview_html(
        theme_slug=theme_slug,
        config=config,
        preview_type=preview_type
    )

    return ApiResponse(
        success=True,
        data={
            "html": html,
            "preview_type": preview_type
        }
    )


@router.post("/css-variables")
async def generate_css_variables(
        config: Dict[str, Any] = Body(..., description="主题配置"),
        current_user=Depends(jwt_required)
):
    """
    生成CSS变量
    
    根据配置自动生成CSS自定义属性（变量）
    """
    css = visual_customizer.generate_css_variables(config)

    return ApiResponse(
        success=True,
        data={
            "css": css
        }
    )


@router.get("/color-presets")
async def get_color_presets(current_user=Depends(jwt_required)):
    """
    获取颜色预设方案
    
    返回多种预设的颜色搭配方案
    """
    presets = visual_customizer.get_color_presets()

    return ApiResponse(
        success=True,
        data={
            "presets": presets,
            "total": len(presets)
        }
    )


@router.get("/font-options")
async def get_font_options(current_user=Depends(jwt_required)):
    """
    获取字体选项
    
    返回可用的字体列表，包括Google Fonts
    """
    fonts = visual_customizer.get_font_options()

    return ApiResponse(
        success=True,
        data={
            "fonts": fonts,
            "total": len(fonts)
        }
    )


@router.get("/layout-options")
async def get_layout_options(current_user=Depends(jwt_required)):
    """
    获取布局选项
    
    返回侧边栏位置、内容宽度等布局配置选项
    """
    options = visual_customizer.get_layout_options()

    return ApiResponse(
        success=True,
        data=options
    )


@router.post("/save-version")
async def save_config_version(
        theme_slug: str = Body(..., description="主题标识"),
        config: Dict[str, Any] = Body(..., description="主题配置"),
        note: str = Body("", description="版本说明"),
        current_user=Depends(jwt_required)
):
    """
    保存配置版本
    
    将当前配置保存为历史版本，方便后续恢复
    """
    success = visual_customizer.save_config_version(
        theme_slug=theme_slug,
        config=config,
        note=note
    )

    if success:
        return ApiResponse(
            success=True,
            message="配置版本已保存"
        )
    else:
        return ApiResponse(
            success=False,
            error="保存失败"
        )


@router.get("/history/{theme_slug}")
async def get_config_history(
        theme_slug: str,
        limit: int = Query(20, ge=1, le=100, description="返回数量"),
        current_user=Depends(jwt_required)
):
    """
    获取配置历史
    
    查看指定主题的配置版本历史记录
    """
    history = visual_customizer.get_config_history(
        theme_slug=theme_slug,
        limit=limit
    )

    return ApiResponse(
        success=True,
        data={
            "history": history,
            "total": len(history)
        }
    )


@router.post("/restore-version/{filename}")
async def restore_config_version(
        filename: str,
        current_user=Depends(jwt_required)
):
    """
    恢复配置版本
    
    从历史版本中恢复配置
    """
    config = visual_customizer.restore_config_version(filename)

    if config is None:
        return ApiResponse(
            success=False,
            error="版本文件不存在或已损坏"
        )

    return ApiResponse(
        success=True,
        data={
            "config": config,
            "message": "配置已恢复"
        }
    )


@router.post("/export")
async def export_config(
        config: Dict[str, Any] = Body(..., description="主题配置"),
        current_user=Depends(jwt_required)
):
    """
    导出配置
    
    将配置导出为JSON格式，便于备份或分享
    """
    json_str = visual_customizer.export_config(config)

    return ApiResponse(
        success=True,
        data={
            "json": json_str,
            "size": len(json_str)
        }
    )


@router.post("/import")
async def import_config(
        json_str: str = Body(..., description="JSON配置字符串"),
        current_user=Depends(jwt_required)
):
    """
    导入配置
    
    从JSON字符串导入配置
    """
    config = visual_customizer.import_config(json_str)

    if config is None:
        return ApiResponse(
            success=False,
            error="配置格式无效"
        )

    return ApiResponse(
        success=True,
        data={
            "config": config,
            "message": "配置导入成功"
        }
    )


@router.get("/device-previews")
async def get_device_preview_sizes(current_user=Depends(jwt_required)):
    """
    获取设备预览尺寸
    
    返回不同设备的屏幕尺寸配置
    """
    devices = [
        {
            "name": "桌面显示器",
            "id": "desktop",
            "width": 1920,
            "height": 1080,
            "icon": "monitor"
        },
        {
            "name": "笔记本",
            "id": "laptop",
            "width": 1366,
            "height": 768,
            "icon": "laptop"
        },
        {
            "name": "平板横屏",
            "id": "tablet-landscape",
            "width": 1024,
            "height": 768,
            "icon": "tablet"
        },
        {
            "name": "平板竖屏",
            "id": "tablet-portrait",
            "width": 768,
            "height": 1024,
            "icon": "tablet"
        },
        {
            "name": "手机",
            "id": "mobile",
            "width": 375,
            "height": 667,
            "icon": "smartphone"
        }
    ]

    return ApiResponse(
        success=True,
        data={
            "devices": devices
        }
    )


@router.get("/animation-options")
async def get_animation_options(current_user=Depends(jwt_required)):
    """
    获取动画效果选项
    
    返回可用的CSS动画和过渡效果
    """
    animations = {
        "transitions": [
            {"value": "none", "label": "无"},
            {"value": "fast", "label": "快速 (150ms)"},
            {"value": "normal", "label": "正常 (250ms)"},
            {"value": "slow", "label": "慢速 (350ms)"},
        ],
        "hover_effects": [
            {"value": "none", "label": "无"},
            {"value": "scale", "label": "缩放"},
            {"value": "lift", "label": "上浮"},
            {"value": "glow", "label": "发光"},
        ],
        "page_transitions": [
            {"value": "fade", "label": "淡入淡出"},
            {"value": "slide", "label": "滑动"},
            {"value": "zoom", "label": "缩放"},
        ]
    }

    return ApiResponse(
        success=True,
        data=animations
    )


@router.post("/apply-preset/{preset_id}")
async def apply_color_preset(
        preset_id: str,
        current_theme_config: Dict[str, Any] = Body({}, description="当前主题配置"),
        current_user=Depends(jwt_required)
):
    """
    应用颜色预设
    
    将预设的颜色方案应用到当前配置
    """
    presets = visual_customizer.get_color_presets()
    preset = next((p for p in presets if p["id"] == preset_id), None)

    if not preset:
        return ApiResponse(
            success=False,
            error=f"未找到预设: {preset_id}"
        )

    # 合并配置
    merged_config = current_theme_config.copy()
    if "colors" not in merged_config:
        merged_config["colors"] = {}

    merged_config["colors"].update(preset["colors"])

    return ApiResponse(
        success=True,
        data={
            "config": merged_config,
            "preset_name": preset["name"]
        }
    )


@router.get("/guide")
async def get_customizer_guide(current_user=Depends(jwt_required)):
    """
    获取定制器使用指南
    """
    guide = {
        "overview": {
            "title": "可视化主题定制器",
            "description": "通过直观的界面自定义网站外观，无需编写代码。"
        },
        "features": [
            "实时预览 - 所见即所得的编辑体验",
            "颜色方案 - 选择预设配色或自定义颜色",
            "字体排版 - 丰富的字体库和字号调整",
            "布局定制 - 灵活调整页面结构和组件位置",
            "动画效果 - 添加平滑的过渡和交互动画",
            "深色模式 - 自动适配系统深色模式偏好",
            "版本历史 - 保存和恢复配置版本",
            "导入导出 - 备份配置或在站点间迁移"
        ],
        "workflow": [
            {
                "step": 1,
                "title": "选择基础主题",
                "description": "从已安装的主题中选择一个作为起点"
            },
            {
                "step": 2,
                "title": "调整颜色方案",
                "description": "选择预设配色或自定义主色、辅色、强调色"
            },
            {
                "step": 3,
                "title": "设置字体排版",
                "description": "选择正文字体、标题字体，调整字号和行高"
            },
            {
                "step": 4,
                "title": "配置布局",
                "description": "设置侧边栏位置、内容宽度、页眉页脚样式"
            },
            {
                "step": 5,
                "title": "预览效果",
                "description": "在不同设备上预览效果，确保响应式设计"
            },
            {
                "step": 6,
                "title": "保存配置",
                "description": "保存配置并添加版本说明，方便后续修改"
            }
        ],
        "tips": [
            "定期保存版本，避免意外丢失配置",
            "在多个浏览器中测试以确保兼容性",
            "使用预设配色可以快速获得专业的外观",
            "注意颜色对比度，确保可读性",
            "移动端预览很重要，大部分流量来自手机"
        ]
    }

    return ApiResponse(
        success=True,
        data=guide
    )
