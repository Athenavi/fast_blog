"""
页面模板服务 - 管理页面模板系统
"""
from pathlib import Path
from typing import List, Dict, Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.pages import Pages


class PageTemplateService:
    """页面模板服务"""
    
    def __init__(self):
        self.themes_dir = Path("themes")
    
    async def get_available_templates(
        self, 
        db: AsyncSession,
        theme_slug: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        获取可用的页面模板列表
        
        Args:
            db: 数据库会话
            theme_slug: 主题slug，默认为当前激活主题
            
        Returns:
            模板列表，每个元素包含 name, slug, description
        """
        templates = [
            {
                "name": "默认模板",
                "slug": "default",
                "description": "使用主题的默认页面布局"
            },
            {
                "name": "全宽无侧边栏",
                "slug": "full-width",
                "description": "全宽度布局，不显示侧边栏"
            },
            {
                "name": "联系页面",
                "slug": "contact",
                "description": "带有联系表单的页面模板"
            },
            {
                "name": "落地页",
                "slug": "landing",
                "description": "营销落地页模板，突出CTA按钮"
            }
        ]
        
        # 从主题目录扫描自定义模板
        if theme_slug:
            theme_path = self.themes_dir / theme_slug / "templates" / "pages"
            if theme_path.exists():
                for template_file in theme_path.glob("*.html"):
                    if template_file.stem not in ['default', 'full-width', 'contact', 'landing']:
                        templates.append({
                            "name": template_file.stem.replace('-', ' ').title(),
                            "slug": template_file.stem,
                            "description": f"来自主题的自定义模板: {template_file.stem}"
                        })
        
        return templates
    
    async def get_page_template(
        self, 
        db: AsyncSession,
        page_id: int
    ) -> Optional[str]:
        """
        获取页面的模板
        
        Args:
            db: 数据库会话
            page_id: 页面ID
            
        Returns:
            模板slug，None表示使用默认模板
        """
        page_query = select(Pages).where(Pages.id == page_id)
        page_result = await db.execute(page_query)
        page = page_result.scalar_one_or_none()
        
        if not page:
            return None
        
        return page.template
    
    async def set_page_template(
        self,
        db: AsyncSession,
        page_id: int,
        template: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        设置页面模板
        
        Args:
            db: 数据库会话
            page_id: 页面ID
            template: 模板slug，None表示使用默认模板
            
        Returns:
            操作结果
        """
        page_query = select(Pages).where(Pages.id == page_id)
        page_result = await db.execute(page_query)
        page = page_result.scalar_one_or_none()
        
        if not page:
            return {
                "success": False,
                "error": "Page not found"
            }
        
        page.template = template
        await db.commit()
        await db.refresh(page)
        
        return {
            "success": True,
            "page_id": page.id,
            "template": page.template
        }
    
    async def get_template_preview(
        self,
        theme_slug: str,
        template_slug: str
    ) -> Optional[str]:
        """
        获取模板预览图路径
        
        Args:
            theme_slug: 主题slug
            template_slug: 模板slug
            
        Returns:
            预览图路径，不存在返回None
        """
        preview_path = self.themes_dir / theme_slug / "templates" / "pages" / f"{template_slug}-preview.jpg"
        
        if preview_path.exists():
            return str(preview_path)
        
        # 尝试png格式
        preview_path = preview_path.with_suffix('.png')
        if preview_path.exists():
            return str(preview_path)
        
        return None


# 全局实例
page_template_service = PageTemplateService()
