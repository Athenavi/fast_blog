"""
Shortcode短代码系统
提供类似WordPress的短代码解析功能
"""

import re
from html import escape
from typing import Dict, Callable


class ShortcodeService:
    """
    Shortcode短代码服务
    
    功能:
    1. Shortcode解析器
    2. 内置Shortcode(code/gist/youtube/bilibili/note/tabs)
    3. 插件扩展支持
    4. Shortcode钩子
    """

    def __init__(self):
        # 注册的shortcodes
        self.shortcodes: Dict[str, Callable] = {}
        
        # 注册内置shortcodes
        self._register_builtin_shortcodes()

    def _register_builtin_shortcodes(self):
        """注册内置短代码"""
        self.register('code', self._code_shortcode)
        self.register('gist', self._gist_shortcode)
        self.register('youtube', self._youtube_shortcode)
        self.register('bilibili', self._bilibili_shortcode)
        self.register('note', self._note_shortcode)
        self.register('tabs', self._tabs_shortcode)

    def register(self, name: str, handler: Callable):
        """
        注册shortcode
        
        Args:
            name: shortcode名称
            handler: 处理函数,接收 (attrs, content) 参数
        """
        self.shortcodes[name.lower()] = handler

    def unregister(self, name: str):
        """
        注销shortcode
        
        Args:
            name: shortcode名称
        """
        if name.lower() in self.shortcodes:
            del self.shortcodes[name.lower()]

    def parse(self, content: str) -> str:
        """
        解析内容中的shortcodes
        
        Args:
            content: 包含shortcodes的内容
            
        Returns:
            解析后的内容
        """
        if not content:
            return content
        
        # 匹配shortcode模式: [name attr="value"]content[/name]
        pattern = r'\[(\w+)([^\]]*)\](.*?)\[\/\1\]'
        
        def replace_shortcode(match):
            name = match.group(1).lower()
            attrs_str = match.group(2)
            content = match.group(3)
            
            # 解析属性
            attrs = self._parse_attrs(attrs_str)
            
            # 查找处理器
            if name in self.shortcodes:
                try:
                    return self.shortcodes[name](attrs, content)
                except Exception as e:
                    return f'<!-- Shortcode error: {str(e)} -->'
            else:
                # 未注册的shortcode,保留原文
                return match.group(0)
        
        # 替换所有shortcodes
        result = re.sub(pattern, replace_shortcode, content, flags=re.DOTALL)
        
        return result

    def _parse_attrs(self, attrs_str: str) -> Dict[str, str]:
        """
        解析shortcode属性字符串
        
        Args:
            attrs_str: 属性字符串,如 'id="123" class="test"'
            
        Returns:
            属性字典
        """
        attrs = {}
        
        if not attrs_str or not attrs_str.strip():
            return attrs
        
        # 匹配 key="value" / key='value' / key=value
        pattern = r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s"\']+))'
        matches = re.findall(pattern, attrs_str)
        
        for match in matches:
            key = match[0]
            value = match[1] or match[2] or match[3]  # 取双引号、单引号或无引号的值
            attrs[key] = value
        
        return attrs

    # ========== 内置Shortcode处理器 ==========

    def _code_shortcode(self, attrs: Dict[str, str], content: str) -> str:
        """代码块短代码: [code language="python"]print("hello")[/code]"""
        language = escape(attrs.get('language', 'text'))
        escaped_content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        return f'''
<div class="shortcode-code relative my-4 rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700">
    <div class="flex items-center justify-between px-4 py-2 bg-gray-100 dark:bg-gray-800 text-xs text-gray-500 border-b border-gray-200 dark:border-gray-700">
        <span>{language}</span>
        <button onclick="navigator.clipboard.writeText(this.parentElement.nextElementSibling.textContent)" class="hover:text-blue-600 transition-colors">复制</button>
    </div>
    <pre class="p-4 overflow-x-auto text-sm bg-gray-50 dark:bg-gray-900"><code class="language-{language}">{escaped_content}</code></pre>
</div>
'''

    def _gist_shortcode(self, attrs: Dict[str, str], content: str) -> str:
        """GitHub Gist 短代码: [gist id="abc123"]"""
        gist_id = attrs.get('id', '').strip()
        # 仅允许字母数字和斜线
        gist_id = re.sub(r'[^a-zA-Z0-9/]', '', gist_id)

        if not gist_id:
            return '<!-- Gist: No id specified -->'

        return f'''
<div class="shortcode-gist my-4">
    <script src="https://gist.github.com/{gist_id}.js"></script>
</div>
'''

    def _youtube_shortcode(self, attrs: Dict[str, str], content: str) -> str:
        """YouTube 视频短代码: [youtube id="dQw4w9WgXcQ"]"""
        video_id = attrs.get('id', '').strip()
        # 仅允许字母数字、下划线和连字符
        video_id = re.sub(r'[^a-zA-Z0-9_-]', '', video_id)
        
        if not video_id:
            return '<!-- YouTube: No id specified -->'
        
        return f'''
<div class="shortcode-youtube my-4 aspect-video rounded-xl overflow-hidden shadow-lg">
    <iframe 
        src="https://www.youtube.com/embed/{video_id}" 
        frameborder="0" 
        allowfullscreen
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        class="w-full h-full"
    ></iframe>
</div>
'''

    def _bilibili_shortcode(self, attrs: Dict[str, str], content: str) -> str:
        """Bilibili 视频短代码: [bilibili id="BV1xx411c7mD"]"""
        video_id = attrs.get('id', '').strip()
        # 仅允许字母数字
        video_id = re.sub(r'[^a-zA-Z0-9]', '', video_id)
        
        if not video_id:
            return '<!-- Bilibili: No id specified -->'
        
        return f'''
<div class="shortcode-bilibili my-4 aspect-video rounded-xl overflow-hidden shadow-lg">
    <iframe 
        src="//player.bilibili.com/player.html?bvid={video_id}&autoplay=0"
        frameborder="0" 
        allowfullscreen
        class="w-full h-full"
    ></iframe>
</div>
'''

    def _note_shortcode(self, attrs: Dict[str, str], content: str) -> str:
        """提示框短代码: [note type="info|warning|tip"]内容[/note]"""
        note_type = attrs.get('type', 'info')
        
        type_styles = {
            'info': {
                'bg': 'bg-blue-50 dark:bg-blue-900/20',
                'border': 'border-blue-200 dark:border-blue-800',
                'icon': '💡',
                'text': 'text-blue-800 dark:text-blue-200'
            },
            'warning': {
                'bg': 'bg-yellow-50 dark:bg-yellow-900/20',
                'border': 'border-yellow-200 dark:border-yellow-800',
                'icon': '⚠️',
                'text': 'text-yellow-800 dark:text-yellow-200'
            },
            'tip': {
                'bg': 'bg-green-50 dark:bg-green-900/20',
                'border': 'border-green-200 dark:border-green-800',
                'icon': '✅',
                'text': 'text-green-800 dark:text-green-200'
            }
        }
        
        style = type_styles.get(note_type, type_styles['info'])
        
        return f'''
<div class="shortcode-note {style['bg']} {style['border']} {style['text']} border-l-4 rounded-r-xl p-4 my-4">
    <div class="flex items-start gap-2">
        <span class="text-lg">{style['icon']}</span>
        <div class="text-sm">{escape(content)}</div>
    </div>
</div>
'''

    def _tabs_shortcode(self, attrs: Dict[str, str], content: str) -> str:
        """标签切换短代码: [tabs][tab name="A"]A[/tab][tab name="B"]B[/tabs]"""
        # 解析子 tab 标签
        tab_pattern = r'\[tab\s+name="([^"]*)"\](.*?)\[\/tab\]'
        tabs = re.findall(tab_pattern, content, re.DOTALL)
        
        if not tabs:
            return f'<div class="shortcode-tabs my-4 p-4 border rounded-xl">{escape(content)}</div>'
        
        tab_id = f'tabs-{hash(content) % 10000}'
        
        # 构建标签头
        headers_html = ''
        panels_html = ''
        for i, (name, tab_content) in enumerate(tabs):
            active = 'active' if i == 0 else ''
            selected = 'true' if i == 0 else 'false'
            safe_name = escape(name)
            safe_content = escape(tab_content)
            headers_html += f'''
            <button class="tab-header {active} px-4 py-2 text-sm font-medium rounded-t-lg transition-colors" role="tab" aria-selected="{selected}" data-tab-target="{tab_id}-panel-{i}">{safe_name}</button>'''
            panels_html += f'''
            <div class="tab-panel {active} p-4 text-sm" id="{tab_id}-panel-{i}" role="tabpanel" data-tab-group="{tab_id}">{safe_content}</div>'''
        
        return f'''
<div class="shortcode-tabs my-4 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
    <div class="tab-headers flex border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800" role="tablist">
        {headers_html}
    </div>
    <div class="tab-panels bg-white dark:bg-gray-900">
        {panels_html}
    </div>
    <script>
        (function() {{
            document.querySelectorAll('[data-tab-group="{tab_id}"]').forEach(panel => {{
                if (panel.id === "{tab_id}-panel-0") panel.style.display = "block";
                else panel.style.display = "none";
            }});
            document.querySelectorAll('[data-tab-target^="{tab_id}"]').forEach(btn => {{
                btn.addEventListener('click', function() {{
                    document.querySelectorAll('[data-tab-group="{tab_id}"]').forEach(p => p.style.display = "none");
                    document.querySelectorAll('[data-tab-target^="{tab_id}"]').forEach(b => {{
                        b.classList.remove('active', 'bg-white', 'dark:bg-gray-900', 'border-l', 'border-r', 'border-t');
                        b.ariaSelected = "false";
                    }});
                    var target = document.getElementById(this.dataset.tabTarget);
                    if (target) target.style.display = "block";
                    this.classList.add('active', 'bg-white', 'dark:bg-gray-900', 'border-l', 'border-r', 'border-t');
                    this.ariaSelected = "true";
                }});
            }});
        }})();
    </script>
</div>
'''


# 全局实例
shortcode_service = ShortcodeService()
