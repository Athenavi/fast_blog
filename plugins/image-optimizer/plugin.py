"""
图片优化插件 (Image Optimizer)
提供自动压缩、WebP格式转换、懒加载和CDN集成功能
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

from shared.services.plugin_manager import BasePlugin, plugin_hooks


class ImageOptimizerPlugin(BasePlugin):
    """
    图片优化插件
    
    功能:
    1. 自动压缩上传的图片 - 减小文件大小
    2. WebP格式转换 - 现代图片格式
    3. 懒加载优化 - 提升页面加载速度
    4. CDN集成 - 加速图片分发
    """

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="图片优化",
            slug="image-optimizer",
            version="1.0.0"
        )

        # 默认设置
        self.settings = {
            'auto_compress': True,
            'compression_quality': 80,
            'convert_to_webp': True,
            'enable_lazy_load': True,
            'max_width': 1920,
            'max_height': 1080,
            'cdn_enabled': False,
            'cdn_url': '',
        }

        # 优化统计
        self.stats = {
            'total_images_optimized': 0,
            'total_size_before': 0,
            'total_size_after': 0,
            'webp_conversions': 0,
        }

        # 支持的图片格式
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']

    def register_hooks(self):
        """注册钩子"""
        # 图片上传时优化
        plugin_hooks.add_action(
            "image_uploaded",
            self.optimize_image,
            priority=10
        )

        # HTML输出时添加懒加载
        plugin_hooks.add_filter(
            "html_output",
            self.add_lazy_loading,
            priority=10
        )

        # 图片URL转换(CDN)
        plugin_hooks.add_filter(
            "image_url",
            self.convert_to_cdn_url,
            priority=10
        )

    def activate(self):
        """激活插件"""
        super().activate()
        print("[ImageOptimizer] Plugin activated")

    def deactivate(self):
        """停用插件"""
        super().deactivate()
        print("[ImageOptimizer] Plugin deactivated")

    def optimize_image(self, image_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        优化上传的图片
        
        Args:
            image_data: 图片数据 {file_path, original_size, mime_type}
            
        Returns:
            优化后的图片数据
        """
        if not self.settings.get('auto_compress'):
            return image_data

        try:
            file_path = image_data.get('file_path', '')
            if not file_path or not os.path.exists(file_path):
                return image_data

            original_size = os.path.getsize(file_path)
            image_data['original_size'] = original_size

            # 1. 调整尺寸
            resized_path = self._resize_image(file_path)

            # 2. 压缩图片
            compressed_path = self._compress_image(resized_path or file_path)

            # 3. 转换为WebP
            final_path = None
            if self.settings.get('convert_to_webp'):
                final_path = self._convert_to_webp(compressed_path)

            optimized_path = final_path or compressed_path or resized_path or file_path
            optimized_size = os.path.getsize(optimized_path) if os.path.exists(optimized_path) else original_size

            # 更新统计数据
            self.stats['total_images_optimized'] += 1
            self.stats['total_size_before'] += original_size
            self.stats['total_size_after'] += optimized_size

            if final_path:
                self.stats['webp_conversions'] += 1

            # 计算节省空间
            saved_bytes = original_size - optimized_size
            saved_percentage = round((saved_bytes / original_size * 100) if original_size > 0 else 0, 2)

            print(f"[ImageOptimizer] Optimized: {file_path}")
            print(f"  Original: {self._format_size(original_size)}")
            print(f"  Optimized: {self._format_size(optimized_size)}")
            print(f"  Saved: {saved_percentage}%")

            return {
                **image_data,
                'optimized_path': optimized_path,
                'optimized_size': optimized_size,
                'saved_bytes': saved_bytes,
                'saved_percentage': saved_percentage,
            }

        except Exception as e:
            print(f"[ImageOptimizer] Failed to optimize image: {str(e)}")
            return image_data

    def _resize_image(self, file_path: str) -> Optional[str]:
        """
        调整图片尺寸
        
        Args:
            file_path: 图片路径
            
        Returns:
            调整后的图片路径
        """
        try:
            from PIL import Image

            max_width = self.settings.get('max_width', 1920)
            max_height = self.settings.get('max_height', 1080)

            img = Image.open(file_path)
            original_width, original_height = img.size

            # 如果图片尺寸小于限制，不需要调整
            if original_width <= max_width and original_height <= max_height:
                return None

            # 计算新尺寸（保持宽高比）
            ratio = min(max_width / original_width, max_height / original_height)
            new_width = int(original_width * ratio)
            new_height = int(original_height * ratio)

            # 调整尺寸
            img_resized = img.resize((new_width, new_height), Image.LANCZOS)

            # 保存调整后的图片
            output_path = file_path.replace('.', '_resized.')
            img_resized.save(output_path, optimize=True)

            print(f"[ImageOptimizer] Resized: {original_width}x{original_height} -> {new_width}x{new_height}")
            return output_path

        except ImportError:
            print("[ImageOptimizer] PIL not installed, skipping resize")
            return None
        except Exception as e:
            print(f"[ImageOptimizer] Resize failed: {str(e)}")
            return None

    def _compress_image(self, file_path: str) -> Optional[str]:
        """
        压缩图片
        
        Args:
            file_path: 图片路径
            
        Returns:
            压缩后的图片路径
        """
        try:
            from PIL import Image

            quality = self.settings.get('compression_quality', 80)

            img = Image.open(file_path)

            # 保存压缩后的图片
            output_path = file_path.replace('.', '_compressed.')

            if file_path.lower().endswith('.png'):
                img.save(output_path, optimize=True, compress_level=9)
            else:
                img.save(output_path, optimize=True, quality=quality)

            return output_path

        except ImportError:
            print("[ImageOptimizer] PIL not installed, skipping compression")
            return None
        except Exception as e:
            print(f"[ImageOptimizer] Compression failed: {str(e)}")
            return None

    def _convert_to_webp(self, file_path: str) -> Optional[str]:
        """
        转换为WebP格式
        
        Args:
            file_path: 图片路径
            
        Returns:
            WebP图片路径
        """
        try:
            from PIL import Image

            img = Image.open(file_path)

            # 转换并保存为WebP
            webp_path = Path(file_path).with_suffix('.webp').__str__()
            img.save(webp_path, 'WEBP', quality=self.settings.get('compression_quality', 80))

            print(f"[ImageOptimizer] Converted to WebP: {webp_path}")
            return webp_path

        except ImportError:
            print("[ImageOptimizer] PIL not installed, skipping WebP conversion")
            return None
        except Exception as e:
            print(f"[ImageOptimizer] WebP conversion failed: {str(e)}")
            return None

    def add_lazy_loading(self, html_content: str) -> str:
        """
        在HTML中添加懒加载属性
        
        Args:
            html_content: HTML内容
            
        Returns:
            添加了懒加载的HTML
        """
        if not self.settings.get('enable_lazy_load'):
            return html_content

        try:
            # 为所有img标签添加loading="lazy"
            import re

            # 匹配img标签
            img_pattern = r'<img([^>]+)>'

            def add_lazy_attr(match):
                img_tag = match.group(0)
                # 如果已经有loading属性，跳过
                if 'loading=' in img_tag:
                    return img_tag

                # 添加loading="lazy"和decoding="async"
                return img_tag.replace('<img', '<img loading="lazy" decoding="async"')

            modified_html = re.sub(img_pattern, add_lazy_attr, html_content)
            return modified_html

        except Exception as e:
            print(f"[ImageOptimizer] Failed to add lazy loading: {str(e)}")
            return html_content

    def convert_to_cdn_url(self, image_url: str) -> str:
        """
        将图片URL转换为CDN URL
        
        Args:
            image_url: 原始图片URL
            
        Returns:
            CDN URL
        """
        if not self.settings.get('cdn_enabled'):
            return image_url

        cdn_url = self.settings.get('cdn_url', '')
        if not cdn_url:
            return image_url

        try:
            # 替换域名部分为CDN域名
            from urllib.parse import urlparse

            parsed = urlparse(image_url)
            cdn_parsed = urlparse(cdn_url)

            # 构建CDN URL
            cdn_image_url = f"{cdn_parsed.scheme}://{cdn_parsed.netloc}{parsed.path}"
            if parsed.query:
                cdn_image_url += f"?{parsed.query}"

            return cdn_image_url

        except Exception as e:
            print(f"[ImageOptimizer] CDN URL conversion failed: {str(e)}")
            return image_url

    def get_optimization_stats(self) -> Dict[str, Any]:
        """获取优化统计"""
        total_saved = self.stats['total_size_before'] - self.stats['total_size_after']
        avg_savings = round(
            (total_saved / self.stats['total_size_before'] * 100)
            if self.stats['total_size_before'] > 0 else 0, 2
        )

        return {
            'total_images_optimized': self.stats['total_images_optimized'],
            'total_size_before': self._format_size(self.stats['total_size_before']),
            'total_size_after': self._format_size(self.stats['total_size_after']),
            'total_saved': self._format_size(total_saved),
            'average_savings_percentage': avg_savings,
            'webp_conversions': self.stats['webp_conversions'],
        }

    def bulk_optimize(self, directory: str = 'media') -> Dict[str, Any]:
        """
        批量优化目录中的所有图片
        
        Args:
            directory: 图片目录
            
        Returns:
            优化结果统计
        """
        results = {
            'total': 0,
            'optimized': 0,
            'failed': 0,
            'errors': [],
        }

        media_dir = Path(directory)
        if not media_dir.exists():
            return {'error': f'Directory not found: {directory}'}

        # 查找所有图片文件
        image_files = []
        for ext in self.supported_formats:
            image_files.extend(media_dir.rglob(f'*{ext}'))

        results['total'] = len(image_files)

        # 逐个优化
        for image_file in image_files:
            try:
                image_data = {
                    'file_path': str(image_file),
                    'original_size': image_file.stat().st_size,
                }

                result = self.optimize_image(image_data)
                if result.get('optimized_path'):
                    results['optimized'] += 1
                else:
                    results['failed'] += 1

            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'file': str(image_file),
                    'error': str(e),
                })

        return results

    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    def get_settings_ui(self) -> Dict[str, Any]:
        """返回设置界面配置"""
        return {
            'fields': [
                {
                    'key': 'auto_compress',
                    'type': 'boolean',
                    'label': '自动压缩图片',
                },
                {
                    'key': 'compression_quality',
                    'type': 'number',
                    'label': '压缩质量(1-100)',
                    'min': 1,
                    'max': 100,
                },
                {
                    'key': 'convert_to_webp',
                    'type': 'boolean',
                    'label': '转换为WebP格式',
                },
                {
                    'key': 'enable_lazy_load',
                    'type': 'boolean',
                    'label': '启用懒加载',
                },
                {
                    'key': 'max_width',
                    'type': 'number',
                    'label': '最大宽度(px)',
                },
                {
                    'key': 'max_height',
                    'type': 'number',
                    'label': '最大高度(px)',
                },
                {
                    'key': 'cdn_enabled',
                    'type': 'boolean',
                    'label': '启用CDN',
                },
                {
                    'key': 'cdn_url',
                    'type': 'text',
                    'label': 'CDN URL',
                },
            ],
            'actions': [
                {
                    'type': 'button',
                    'label': '批量优化现有图片',
                    'action': 'bulk_optimize',
                    'variant': 'default',
                },
            ]
        }


# 插件实例
plugin_instance = ImageOptimizerPlugin()
