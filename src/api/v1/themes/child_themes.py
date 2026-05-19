"""
子主题管理 API

提供子主题的创建、查询、验证等功能
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from shared.services.themes.child_theme_service import child_theme_service
from src.api.v1.core.responses import ApiResponse
from src.api.v1.users.user_management import jwt_required

router = APIRouter(prefix="/child-themes", tags=["Child Themes"])


# ==================== 请求模型 ====================

class CreateChildThemeRequest(BaseModel):
    """创建子主题请求"""
    parent_slug: str = Field(..., description="父主题 slug")
    child_name: str = Field(..., description="子主题名称")
    child_slug: Optional[str] = Field(None, description="子主题 slug（可选，自动生成）")
    description: Optional[str] = Field("", description="子主题描述")
    author: Optional[str] = Field("", description="作者信息")


# ==================== API 端点 ====================

@router.post("/create")
async def create_child_theme(request: CreateChildThemeRequest, current_user=Depends(jwt_required)):
    """
    创建子主题
    
    基于父主题创建一个新的子主题，包含完整的目录结构和配置文件
    """
    success, message, metadata = child_theme_service.create_child_theme(
        parent_slug=request.parent_slug,
        child_name=request.child_name,
        child_slug=request.child_slug,
        description=request.description,
        author=request.author
    )

    if not success:
        return ApiResponse(success=False, error=message)

    return ApiResponse(
        success=True,
        data={
            "metadata": metadata,
            "next_steps": [
                "在 style.css 中添加自定义样式",
                "创建模板文件覆盖父主题模板",
                "在 functions.php 中添加自定义功能",
                "上传 screenshot.png 作为主题预览图"
            ]
        },
        message=message
    )


@router.get("/list")
async def list_child_themes(
        parent_slug: Optional[str] = Query(None, description="父主题 slug（可选，过滤特定父主题的子主题）"),
        current_user=Depends(jwt_required)
):
    """
    列出所有子主题
    
    可以选择性地按父主题过滤
    """
    child_themes = child_theme_service.list_child_themes(parent_slug)

    return ApiResponse(
        success=True,
        data={
            "child_themes": child_themes,
            "total": len(child_themes)
        }
    )


@router.get("/{child_slug}/parent")
async def get_parent_theme_info(child_slug: str, current_user=Depends(jwt_required)):
    """
    获取子主题的父主题信息
    
    显示子主题继承自哪个父主题及其详细信息
    """
    parent_info = child_theme_service.get_parent_theme_info(child_slug)

    if parent_info is None:
        return ApiResponse(
            success=False,
            error=f"主题 '{child_slug}' 不是子主题或不存在"
        )

    return ApiResponse(
        success=True,
        data=parent_info
    )


@router.get("/{child_slug}/hierarchy")
async def get_theme_hierarchy(child_slug: str, current_user=Depends(jwt_required)):
    """
    获取主题继承层次结构
    
    显示从当前主题到根主题的完整继承链
    """
    hierarchy = child_theme_service.get_theme_hierarchy(child_slug)

    if not hierarchy:
        return ApiResponse(
            success=False,
            error=f"主题 '{child_slug}' 不存在"
        )

    return ApiResponse(
        success=True,
        data={
            "theme_slug": child_slug,
            "hierarchy": hierarchy,
            "depth": len(hierarchy)
        }
    )


@router.post("/{child_slug}/validate")
async def validate_child_theme(child_slug: str, current_user=Depends(jwt_required)):
    """
    验证子主题的完整性
    
    检查子主题是否具备所有必需的文件和配置
    """
    is_valid, errors = child_theme_service.validate_child_theme(child_slug)

    return ApiResponse(
        success=is_valid,
        data={
            "is_valid": is_valid,
            "errors": errors,
            "theme_slug": child_slug
        },
        message="验证通过" if is_valid else f"发现 {len(errors)} 个问题"
    )


@router.get("/{child_slug}/templates/{template_name}")
async def resolve_template(
        child_slug: str,
        template_name: str,
        current_user=Depends(jwt_required)
):
    """
    解析模板（支持继承）
    
    查找模板时先在子主题中查找，如果不存在则在父主题中查找
    """
    template_path = child_theme_service.resolve_template_with_inheritance(
        template_name=template_name,
        theme_slug=child_slug
    )

    if template_path is None:
        return ApiResponse(
            success=False,
            error=f"模板 '{template_name}' 在主题 '{child_slug}' 及其父主题中均未找到"
        )

    # 确定模板来源
    theme_path = child_theme_service.themes_dir / child_slug
    from_parent = not str(template_path).startswith(str(theme_path))

    return ApiResponse(
        success=True,
        data={
            "template_name": template_name,
            "template_path": str(template_path),
            "source": "parent" if from_parent else "child",
            "theme_slug": child_slug
        }
    )


@router.get("/guide")
async def get_child_theme_guide(current_user=Depends(jwt_required)):
    """
    获取子主题使用指南
    
    提供详细的子主题开发文档和最佳实践
    """
    guide = {
        "what_is_child_theme": {
            "title": "什么是子主题？",
            "description": "子主题是一种继承父主题所有功能和样式的主题。它允许您在不修改父主题的情况下进行自定义，确保父主题更新时不会丢失您的更改。"
        },
        "benefits": [
            "安全更新：父主题可以安全更新而不影响自定义内容",
            "易于维护：所有自定义集中在子主题中",
            "快速开发：基于成熟的父主题快速构建",
            "版本控制：可以轻松跟踪和管理自定义更改"
        ],
        "how_to_create": {
            "step_1": "选择要基于的父主题",
            "step_2": "调用 /create 接口创建子主题",
            "step_3": "在 style.css 中添加自定义样式",
            "step_4": "根据需要创建模板文件覆盖父主题",
            "step_5": "激活子主题并开始使用"
        },
        "file_structure": {
            "required_files": [
                {
                    "file": "metadata.json",
                    "description": "主题元数据，必须包含 'parent' 字段指向父主题"
                },
                {
                    "file": "style.css",
                    "description": "样式文件，子主题必须有这个文件"
                }
            ],
            "optional_files": [
                {
                    "file": "functions.php",
                    "description": "函数文件，在父主题之前加载"
                },
                {
                    "file": "*.html",
                    "description": "模板文件，会覆盖父主题的同名模板"
                },
                {
                    "file": "screenshot.png",
                    "description": "主题预览图（建议 800x600）"
                }
            ]
        },
        "template_override": {
            "description": "要覆盖父主题的模板，只需在子主题中创建同名文件",
            "examples": [
                {
                    "purpose": "覆盖首页",
                    "action": "创建 index.html"
                },
                {
                    "purpose": "覆盖文章页",
                    "action": "创建 article.html"
                },
                {
                    "purpose": "覆盖分类页",
                    "action": "创建 category.html"
                },
                {
                    "purpose": "覆盖单页",
                    "action": "创建 page.html"
                }
            ]
        },
        "css_customization": {
            "description": "在 style.css 中添加 CSS 规则来覆盖或扩展父主题样式",
            "example": """/* 
 * 覆盖父主题的主色调 
 */
:root {
    --primary-color: #ff6b6b;
}

/* 
 * 自定义标题样式 
 */
h1 {
    font-size: 2.5rem;
    color: #333;
}

/* 
 * 添加新的组件样式 
 */
.custom-component {
    background: linear-gradient(45deg, #ff6b6b, #feca57);
    padding: 20px;
    border-radius: 10px;
}""",
            "tips": [
                "使用浏览器开发者工具查看父主题的 CSS 类名",
                "使用更具体的选择器来确保覆盖生效",
                "避免删除父主题的重要样式，尽量追加或覆盖"
            ]
        },
        "best_practices": [
            "只在必要时覆盖模板文件",
            "保持子主题简洁，避免复制大量父主题代码",
            "记录所有自定义更改",
            "定期测试父主题更新后的兼容性",
            "使用 version control (Git) 管理子主题"
        ],
        "common_issues": {
            "styles_not_loading": {
                "problem": "子主题样式未加载",
                "solution": "确保 style.css 存在且格式正确，检查 functions.php 是否正确 enqueue 样式"
            },
            "template_not_found": {
                "problem": "模板未找到",
                "solution": "检查文件名是否正确，确认父主题中存在该模板"
            },
            "parent_theme_missing": {
                "problem": "父主题不存在",
                "solution": "确保父主题已安装且未被删除"
            }
        }
    }

    return ApiResponse(
        success=True,
        data=guide
    )


@router.get("/examples")
async def get_child_theme_examples(current_user=Depends(jwt_required)):
    """
    获取子主题示例
    
    提供常见的子主题定制示例代码
    """
    examples = {
        "style_customizations": [
            {
                "name": "修改主色调",
                "code": """:root {
    --primary-color: #your-color;
    --secondary-color: #your-color;
}""",
                "description": "通过 CSS 变量覆盖父主题的颜色方案"
            },
            {
                "name": "自定义字体",
                "code": """body {
    font-family: 'Your Custom Font', sans-serif;
}

h1, h2, h3 {
    font-family: 'Heading Font', serif;
}""",
                "description": "更改全站字体"
            },
            {
                "name": "调整布局间距",
                "code": """.container {
    max-width: 1200px;
    padding: 0 20px;
}

.article-content {
    margin: 40px 0;
}""",
                "description": "自定义页面布局和间距"
            }
        ],
        "template_overrides": [
            {
                "name": "自定义文章头部",
                "file": "article-header.html",
                "description": "覆盖文章页面的头部区域",
                "note": "复制父主题的 article-header.html 并修改"
            },
            {
                "name": "自定义页脚",
                "file": "footer.html",
                "description": "完全自定义网站页脚",
                "note": "可以添加额外的链接、社交媒体图标等"
            }
        ],
        "function_extensions": [
            {
                "name": "添加自定义菜单位置",
                "language": "php",
                "code": """<?php
// 注册新的菜单位置
function child_theme_register_menus() {
    register_nav_menu('custom-menu', __('Custom Menu', 'child-theme'));
}
add_action('init', 'child_theme_register_menus');
?>""",
                "description": "在子主题中添加新的导航菜单位置"
            },
            {
                "name": "添加自定义小工具区域",
                "language": "php",
                "code": """<?php
// 注册侧边栏
function child_theme_register_sidebars() {
    register_sidebar(array(
        'name' => __('Custom Sidebar', 'child-theme'),
        'id' => 'custom-sidebar',
        'description' => __('A custom sidebar area', 'child-theme'),
        'before_widget' => '<div class="widget">',
        'after_widget' => '</div>',
    ));
}
add_action('widgets_init', 'child_theme_register_sidebars');
?>""",
                "description": "创建新的小工具区域"
            }
        ]
    }

    return ApiResponse(
        success=True,
        data=examples
    )
