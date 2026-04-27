"""
主题系统核心架构
提供类似WordPress的主题管理功能
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# 常量定义
DEFAULT_THEME = 'default'
SCREENSHOT_SIZE = (800, 600)
SCREENSHOT_BG_COLOR = (240, 240, 240)
SCREENSHOT_TEXT_COLOR = (100, 100, 100)


class ThemeManager:
    """
    主题管理器
    负责主题的发现、安装、激活和管理
    """

    def __init__(self, themes_dir: str = "themes", uploads_dir: str = "storage/objects"):
        self.themes_dir = Path(themes_dir)
        self.uploads_dir = Path(uploads_dir)

        # 确保目录存在
        self.themes_dir.mkdir(parents=True, exist_ok=True)

    def discover_themes(self) -> List[dict]:
        """
        扫描主题目录，发现所有可用主题
        
        Returns:
            主题信息列表
        """
        discovered = []

        if not self.themes_dir.exists():
            return discovered

        for theme_dir in self.themes_dir.iterdir():
            if not theme_dir.is_dir():
                continue

            metadata_file = theme_dir / "metadata.json"
            if not metadata_file.exists():
                continue

            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    metadata['path'] = str(theme_dir)
                    metadata['slug'] = theme_dir.name

                    # 检查截图
                    screenshot_path = theme_dir / "screenshot.png"
                    if screenshot_path.exists():
                        metadata['has_screenshot'] = True
                        metadata['screenshot_url'] = f"/themes/{theme_dir.name}/screenshot.png"
                    else:
                        metadata['has_screenshot'] = False

                    discovered.append(metadata)
            except Exception as e:
                print(f"读取主题元数据失败 {theme_dir.name}: {e}")

        return discovered

    def get_active_theme(self) -> str:
        """
        获取当前激活的主题slug
        
        Returns:
            激活的主题slug，默认返回'default'
        """
        from shared.models.theme import Theme
        from sqlalchemy import select
        import asyncio

        async def _get_active():
            # 使用标准的异步数据库会话
            from src.utils.database.unified_manager import db_manager
            async with db_manager.get_session() as db:
                query = select(Theme).where(Theme.is_active == True)
                result = await db.execute(query)
                theme = result.scalar_one_or_none()
                return theme.slug if theme else DEFAULT_THEME

        try:
            # 尝试获取当前事件循环
            loop = asyncio.get_running_loop()
            # 如果已经有运行中的循环，创建新任务
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _get_active())
                return future.result(timeout=5)
        except RuntimeError:
            # 没有运行中的循环，直接运行
            return asyncio.run(_get_active())
        except Exception as e:
            print(f"[ThemeManager] 获取激活主题失败: {e}")
            import traceback
            traceback.print_exc()
            return DEFAULT_THEME

    async def activate_theme(self, theme_slug: str, db) -> bool:
        """
        激活主题
        
        Args:
            theme_slug: 主题slug
            db: 数据库会话
            
        Returns:
            是否成功
        """
        from shared.models.theme import Theme
        from sqlalchemy import select
        
        try:
            # 批量停用所有主题
            all_query = select(Theme)
            all_result = await db.execute(all_query)
            all_themes = all_result.scalars().all()

            print(f"[ThemeManager] 开始激活主题: {theme_slug}")
            print(f"[ThemeManager] 找到 {len(all_themes)} 个主题")

            for theme in all_themes:
                theme.is_active = False
                print(f"[ThemeManager] 停用主题: {theme.slug} (ID={theme.id})")

            # 激活指定主题
            theme_query = select(Theme).where(Theme.slug == theme_slug)
            theme_result = await db.execute(theme_query)
            theme = theme_result.scalar_one_or_none()

            if not theme:
                print(f"[ThemeManager] 错误: 主题 '{theme_slug}' 不存在")
                return False

            theme.is_active = True
            theme.updated_at = datetime.now()
            print(f"[ThemeManager] 激活主题: {theme.slug} (ID={theme.id})")
            
            await db.commit()
            print(f"[ThemeManager] 主题激活成功并已提交到数据库")
            return True

        except Exception as e:
            await db.rollback()
            print(f"[ThemeManager] 激活主题失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def get_theme_settings(self, theme_slug: str, db) -> Dict[str, Any]:
        """
        获取主题设置
        
        Args:
            theme_slug: 主题slug
            db: 数据库会话
            
        Returns:
            主题设置字典
        """
        from shared.models.theme import Theme
        from sqlalchemy import select
        
        try:
            query = select(Theme).where(Theme.slug == theme_slug)
            result = await db.execute(query)
            theme = result.scalar_one_or_none()

            return json.loads(theme.settings) if theme and theme.settings else {}
        except Exception as e:
            print(f"获取主题设置失败: {e}")
            return {}

    async def update_theme_settings(self, theme_slug: str, settings: Dict[str, Any], db) -> bool:
        """
        更新主题设置
        
        Args:
            theme_slug: 主题slug
            settings: 新设置
            db: 数据库会话
            
        Returns:
            是否成功
        """
        from shared.models.theme import Theme
        from sqlalchemy import select
        
        try:
            query = select(Theme).where(Theme.slug == theme_slug)
            result = await db.execute(query)
            theme = result.scalar_one_or_none()

            if not theme:
                return False

            theme.settings = json.dumps(settings, ensure_ascii=False)
            theme.updated_at = datetime.now()
            await db.commit()
            return True

        except Exception as e:
            await db.rollback()
            print(f"更新主题设置失败: {e}")
            return False

    def preview_theme(self, theme_slug: str) -> Optional[str]:
        """
        预览主题（返回预览URL）
        
        Args:
            theme_slug: 主题slug
            
        Returns:
            预览URL
        """
        theme_path = self.themes_dir / theme_slug

        if not theme_path.exists():
            return None

        # 返回预览URL（前端处理）
        return f"/preview?theme={theme_slug}"
    
    def generate_screenshot(self, theme_slug: str) -> bool:
        """
        为主题生成截图
        
        Args:
            theme_slug: 主题slug
            
        Returns:
            是否成功
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            theme_path = self.themes_dir / theme_slug
            if not theme_path.exists():
                return False

            # 创建默认截图
            image = Image.new('RGB', SCREENSHOT_SIZE, color=SCREENSHOT_BG_COLOR)
            draw = ImageDraw.Draw(image)
            
            # 绘制主题名称
            theme_name = theme_slug.replace('-', ' ').title()
            try:
                font = ImageFont.truetype("arial.ttf", 48)
            except:
                font = ImageFont.load_default()
            
            # 计算文字位置（居中）
            bbox = draw.textbbox((0, 0), theme_name, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (SCREENSHOT_SIZE[0] - text_width) // 2
            y = (SCREENSHOT_SIZE[1] - text_height) // 2

            # 绘制文字并保存
            draw.text((x, y), theme_name, fill=SCREENSHOT_TEXT_COLOR, font=font)
            screenshot_path = theme_path / "screenshot.png"
            image.save(str(screenshot_path), 'PNG')
            
            return True
            
        except ImportError:
            print("PIL/Pillow 未安装，无法生成截图")
            return False
        except Exception as e:
            print(f"生成截图失败: {e}")
            return False

    def export_theme(self, theme_slug: str, output_path: str) -> bool:
        """
        导出主题为ZIP文件
        
        Args:
            theme_slug: 主题slug
            output_path: 输出路径
            
        Returns:
            是否成功
        """
        try:
            theme_path = self.themes_dir / theme_slug

            if not theme_path.exists():
                return False

            # 使用shutil打包
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)

            shutil.make_archive(
                str(Path(output_path).with_suffix('')),
                'zip',
                theme_path
            )

            return True

        except Exception as e:
            print(f"导出主题失败: {e}")
            return False


# 全局主题管理器实例
theme_manager = ThemeManager()
