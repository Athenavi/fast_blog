"""
图片懒加载插件
优化图片加载性能，实现懒加载和占位符显示
"""

import re
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup

from shared.services.plugin_manager import BasePlugin, plugin_hooks


class ImageLazyLoadPlugin(BasePlugin):
    """
    图片懒加载插件
    
    功能:
    1. 图片懒加载实现
    2. 占位符显示
    3. 渐进式加载
    4. 视口检测
    5. 预加载策略
    6. 性能监控
    """

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="图片懒加载",
            slug="image-lazy-load",
            version="1.0.0"
        )

        # 默认设置
        self.settings = {
            'enable_lazy_load': True,
            'placeholder_type': 'blur',  # blur, color, skeleton, none
            'placeholder_color': '#f0f0f0',  # 占位符颜色
            'blur_hash_enabled': True,  # 启用BlurHash
            'threshold': 200,  # 提前加载距离(像素)
            'effect': 'fade-in',  # 加载效果: fade-in, slide-up, none
            'exclude_classes': ['no-lazy', 'critical-image'],  # 排除的CSS类
            'exclude_selectors': ['.hero-image', '.above-fold'],  # 排除的选择器
            'max_concurrent_loads': 4,  # 最大并发加载数
            'enable_preload': True,  # 启用预加载
            'preload_count': 2,  # 预加载下一张图片数量
        }

        # 性能统计
        self.stats = {
            'total_images': 0,
            'lazy_loaded': 0,
            'preloaded': 0,
            'errors': 0,
            'avg_load_time': 0,
        }

    def register_hooks(self):
        """注册钩子"""
        # 处理文章内容中的图片
        plugin_hooks.add_filter(
            "article_content",
            self.process_article_images,
            priority=10
        )

        # 处理页面内容
        plugin_hooks.add_filter(
            "page_content",
            self.process_page_images,
            priority=10
        )

        # 注入懒加载脚本
        plugin_hooks.add_action(
            "before_body_close",
            self.inject_lazy_load_script,
            priority=10
        )

    def activate(self):
        """激活插件"""
        super().activate()
        print("[ImageLazyLoad] Plugin activated - Lazy loading enabled")

    def deactivate(self):
        """停用插件"""
        super().deactivate()
        print("[ImageLazyLoad] Plugin deactivated")

    def process_article_images(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理文章中的图片
        
        Args:
            content_data: 内容数据 {html, article_id}
            
        Returns:
            处理后的内容数据
        """
        if not self.settings.get('enable_lazy_load'):
            return content_data

        html = content_data.get('html', '')
        if not html:
            return content_data

        try:
            soup = BeautifulSoup(html, 'html.parser')
            images = soup.find_all('img')

            processed_count = 0
            for img in images:
                if self._should_lazy_load(img):
                    self._convert_to_lazy_load(img)
                    processed_count += 1

            content_data['html'] = str(soup)
            content_data['processed_images'] = processed_count
            
            self.stats['total_images'] += processed_count
            print(f"[ImageLazyLoad] Processed {processed_count} images in article")

        except Exception as e:
            print(f"[ImageLazyLoad] Failed to process images: {e}")

        return content_data

    def process_page_images(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理页面中的图片
        
        Args:
            content_data: 内容数据 {html}
            
        Returns:
            处理后的内容数据
        """
        if not self.settings.get('enable_lazy_load'):
            return content_data

        html = content_data.get('html', '')
        if not html:
            return content_data

        try:
            soup = BeautifulSoup(html, 'html.parser')
            images = soup.find_all('img')

            processed_count = 0
            for img in images:
                if self._should_lazy_load(img):
                    self._convert_to_lazy_load(img)
                    processed_count += 1

            content_data['html'] = str(soup)
            content_data['processed_images'] = processed_count

        except Exception as e:
            print(f"[ImageLazyLoad] Failed to process page images: {e}")

        return content_data

    def inject_lazy_load_script(self, context: Dict[str, Any]):
        """
        注入懒加载JavaScript脚本
        
        Args:
            context: 上下文数据
        """
        if not self.settings.get('enable_lazy_load'):
            return

        script = self._generate_lazy_load_script()
        
        # 返回需要注入的脚本
        if 'scripts' not in context:
            context['scripts'] = []
        
        context['scripts'].append({
            'type': 'inline',
            'content': script,
            'position': 'before_body_close',
        })

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        获取性能统计
        
        Returns:
            统计数据
        """
        return {
            'enabled': self.settings.get('enable_lazy_load'),
            'total_images_processed': self.stats['total_images'],
            'lazy_loaded_count': self.stats['lazy_loaded'],
            'preloaded_count': self.stats['preloaded'],
            'error_count': self.stats['errors'],
            'average_load_time_ms': self.stats['avg_load_time'],
            'settings': self.settings,
        }

    def _should_lazy_load(self, img_tag) -> bool:
        """
        判断图片是否应该懒加载
        
        Args:
            img_tag: BeautifulSoup的img标签
            
        Returns:
            是否应该懒加载
        """
        # 检查是否有data-no-lazy属性
        if img_tag.get('data-no-lazy'):
            return False

        # 检查CSS类
        css_classes = img_tag.get('class', [])
        exclude_classes = self.settings.get('exclude_classes', [])
        if any(cls in exclude_classes for cls in css_classes):
            return False

        # 检查是否是内联小图片（base64）
        src = img_tag.get('src', '')
        if src.startswith('data:'):
            return False

        # 检查是否在首屏（简化判断：没有特定类名）
        # 实际项目中可以通过更复杂的逻辑判断
        if img_tag.get('data-above-fold'):
            return False

        return True

    def _convert_to_lazy_load(self, img_tag):
        """
        将普通图片转换为懒加载图片
        
        Args:
            img_tag: BeautifulSoup的img标签
        """
        original_src = img_tag.get('src', '')
        if not original_src:
            return

        # 保存原始src
        img_tag['data-src'] = original_src
        
        # 设置占位符
        placeholder = self._get_placeholder(img_tag)
        img_tag['src'] = placeholder

        # 添加懒加载类
        existing_classes = img_tag.get('class', [])
        if isinstance(existing_classes, str):
            existing_classes = existing_classes.split()
        
        if 'lazy-image' not in existing_classes:
            existing_classes.append('lazy-image')
        img_tag['class'] = existing_classes

        # 添加加载效果类
        effect = self.settings.get('effect', 'fade-in')
        if effect and effect != 'none':
            img_tag['data-effect'] = effect

        # 添加alt文本（如果没有）
        if not img_tag.get('alt'):
            img_tag['alt'] = 'Loading...'

        # 添加loading属性（浏览器原生懒加载作为fallback）
        img_tag['loading'] = 'lazy'

    def _get_placeholder(self, img_tag) -> str:
        """
        获取占位符
        
        Args:
            img_tag: BeautifulSoup的img标签
            
        Returns:
            占位符URL或data URI
        """
        placeholder_type = self.settings.get('placeholder_type', 'blur')

        if placeholder_type == 'color':
            # 纯色占位符
            color = self.settings.get('placeholder_color', '#f0f0f0')
            return self._generate_color_placeholder(color)
        
        elif placeholder_type == 'blur':
            # 模糊占位符（使用BlurHash或低质量图片）
            if self.settings.get('blur_hash_enabled'):
                blur_hash = img_tag.get('data-blurhash')
                if blur_hash:
                    return self._decode_blur_hash(blur_hash)
            
            # 降级为灰色占位符
            return self._generate_color_placeholder('#e0e0e0')
        
        elif placeholder_type == 'skeleton':
            # 骨架屏占位符（通过CSS实现）
            return 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'
        
        else:
            # 透明占位符
            return 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'

    def _generate_color_placeholder(self, color: str) -> str:
        """
        生成纯色占位符
        
        Args:
            color: 颜色值
            
        Returns:
            data URI
        """
        # 创建一个1x1的彩色PNG
        from base64 import b64encode
        
        # 简化的1x1 PNG生成
        # 实际项目中可以使用PIL库生成真正的彩色图片
        return f'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"%3E%3Crect fill="{color}" width="1" height="1"/%3E%3C/svg%3E'

    def _decode_blur_hash(self, blur_hash: str) -> str:
        """
        解码BlurHash为占位符图片
        
        Args:
            blur_hash: BlurHash字符串
            
        Returns:
            data URI
        """
        # 这里需要集成blurhash库
        # 简化实现：返回默认占位符
        return 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'

    def _generate_lazy_load_script(self) -> str:
        """
        生成懒加载JavaScript脚本
        
        Returns:
            JavaScript代码
        """
        threshold = self.settings.get('threshold', 200)
        max_concurrent = self.settings.get('max_concurrent_loads', 4)
        enable_preload = self.settings.get('enable_preload', True)
        preload_count = self.settings.get('preload_count', 2)

        script = f'''
<script>
(function() {{
    'use strict';
    
    // 配置
    const config = {{
        threshold: {threshold},
        maxConcurrentLoads: {max_concurrent},
        enablePreload: {str(enable_preload).lower()},
        preloadCount: {preload_count},
    }};
    
    // 跟踪加载状态
    let activeLoads = 0;
    const loadedImages = new Set();
    
    /**
     * 懒加载观察器
     */
    const observer = new IntersectionObserver((entries) => {{
        entries.forEach(entry => {{
            if (entry.isIntersecting) {{
                const img = entry.target;
                
                // 如果已经加载过，跳过
                if (loadedImages.has(img)) {{
                    return;
                }}
                
                // 检查并发加载限制
                if (activeLoads < config.maxConcurrentLoads) {{
                    loadImage(img);
                }} else {{
                    // 等待其他图片加载完成
                    setTimeout(() => observer.observe(img), 100);
                }}
            }}
        }});
    }}, {{
        rootMargin: `${{config.threshold}}px`,
        threshold: 0
    }});
    
    /**
     * 加载图片
     */
    function loadImage(img) {{
        const src = img.getAttribute('data-src');
        if (!src) return;
        
        activeLoads++;
        
        const image = new Image();
        
        image.onload = () => {{
            // 应用淡入效果
            const effect = img.getAttribute('data-effect') || 'fade-in';
            applyEffect(img, effect);
            
            img.src = src;
            img.removeAttribute('data-src');
            img.classList.add('lazy-loaded');
            img.classList.remove('lazy-image');
            
            loadedImages.add(img);
            activeLoads--;
            
            // 触发预加载
            if (config.enablePreload) {{
                preloadNextImages();
            }}
        }};
        
        image.onerror = () => {{
            console.error('[ImageLazyLoad] Failed to load:', src);
            img.classList.add('lazy-error');
            activeLoads--;
        }};
        
        image.src = src;
    }}
    
    /**
     * 应用加载效果
     */
    function applyEffect(img, effect) {{
        switch(effect) {{
            case 'fade-in':
                img.style.opacity = '0';
                img.style.transition = 'opacity 0.3s ease-in';
                setTimeout(() => {{
                    img.style.opacity = '1';
                }}, 50);
                break;
                
            case 'slide-up':
                img.style.transform = 'translateY(20px)';
                img.style.opacity = '0';
                img.style.transition = 'all 0.3s ease-out';
                setTimeout(() => {{
                    img.style.transform = 'translateY(0)';
                    img.style.opacity = '1';
                }}, 50);
                break;
                
            default:
                // 无效果
                break;
        }}
    }}
    
    /**
     * 预加载下一批图片
     */
    function preloadNextImages() {{
        if (!config.enablePreload) return;
        
        const lazyImages = document.querySelectorAll('.lazy-image:not([data-preloading])');
        let preloaded = 0;
        
        lazyImages.forEach(img => {{
            if (preloaded >= config.preloadCount) return;
            
            const rect = img.getBoundingClientRect();
            const viewportHeight = window.innerHeight;
            
            // 预加载即将进入视口的图片
            if (rect.top > viewportHeight && rect.top < viewportHeight + 1000) {{
                img.setAttribute('data-preloading', 'true');
                const src = img.getAttribute('data-src');
                if (src) {{
                    const preloadImg = new Image();
                    preloadImg.src = src;
                    preloaded++;
                }}
            }}
        }});
    }}
    
    /**
     * 初始化懒加载
     */
    function initLazyLoad() {{
        const lazyImages = document.querySelectorAll('img.lazy-image');
        
        lazyImages.forEach(img => {{
            observer.observe(img);
        }});
        
        console.log(`[ImageLazyLoad] Initialized with ${{lazyImages.length}} images`);
    }}
    
    // DOM加载完成后初始化
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', initLazyLoad);
    }} else {{
        initLazyLoad();
    }}
    
    // 暴露API
    window.ImageLazyLoad = {{
        refresh: () => {{
            observer.disconnect();
            initLazyLoad();
        }},
        getStats: () => {{
            return {{
                totalImages: document.querySelectorAll('img.lazy-image').length,
                loadedImages: loadedImages.size,
                activeLoads: activeLoads,
            }};
        }}
    }};
}})();
</script>
        '''
        
        return script

    def get_settings_ui(self) -> Dict[str, Any]:
        """返回设置界面配置"""
        return {
            'fields': [
                {
                    'key': 'enable_lazy_load',
                    'type': 'boolean',
                    'label': '启用图片懒加载',
                },
                {
                    'key': 'placeholder_type',
                    'type': 'select',
                    'label': '占位符类型',
                    'options': [
                        {'value': 'blur', 'label': '模糊效果'},
                        {'value': 'color', 'label': '纯色'},
                        {'value': 'skeleton', 'label': '骨架屏'},
                        {'value': 'none', 'label': '无'},
                    ],
                },
                {
                    'key': 'placeholder_color',
                    'type': 'color',
                    'label': '占位符颜色',
                    'show_if': {'placeholder_type': 'color'},
                },
                {
                    'key': 'threshold',
                    'type': 'number',
                    'label': '提前加载距离（像素）',
                    'min': 0,
                    'max': 1000,
                    'help': '图片距离视口多远时开始加载',
                },
                {
                    'key': 'effect',
                    'type': 'select',
                    'label': '加载效果',
                    'options': [
                        {'value': 'fade-in', 'label': '淡入'},
                        {'value': 'slide-up', 'label': '上滑'},
                        {'value': 'none', 'label': '无'},
                    ],
                },
                {
                    'key': 'max_concurrent_loads',
                    'type': 'number',
                    'label': '最大并发加载数',
                    'min': 1,
                    'max': 10,
                    'help': '同时加载的图片数量',
                },
                {
                    'key': 'enable_preload',
                    'type': 'boolean',
                    'label': '启用预加载',
                    'help': '提前加载即将进入视口的图片',
                },
                {
                    'key': 'preload_count',
                    'type': 'number',
                    'label': '预加载数量',
                    'min': 1,
                    'max': 5,
                    'show_if': {'enable_preload': True},
                },
                {
                    'key': 'exclude_classes',
                    'type': 'text',
                    'label': '排除的CSS类（逗号分隔）',
                    'help': '这些类的图片不会懒加载',
                },
            ],
            'actions': [
                {
                    'type': 'button',
                    'label': '查看性能统计',
                    'action': 'view_stats',
                    'variant': 'outline',
                },
            ]
        }


# 插件实例
plugin_instance = ImageLazyLoadPlugin()
