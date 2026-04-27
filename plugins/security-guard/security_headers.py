"""
安全头中间件
添加 HTTP 安全响应头
"""


class SecurityHeadersMiddleware:
    """安全头中间件"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # 默认安全头配置
        self.security_headers = {
            # 防止点击劫持
            'X-Frame-Options': 'DENY',
            
            # 防止 MIME 类型嗅探
            'X-Content-Type-Options': 'nosniff',
            
            # XSS 保护
            'X-XSS-Protection': '1; mode=block',
            
            # 引用策略
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            
            # 权限策略
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
        }
        
        # HSTS (仅在 HTTPS 环境下)
        self.hsts_enabled = False
        self.hsts_max_age = 31536000  # 1年
        self.hsts_include_subdomains = True
        self.hsts_preload = False
        
        # CSP (内容安全策略)
        self.csp_enabled = False
        self.csp_policy = {}
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # 添加基本安全头
        for header, value in self.security_headers.items():
            if header not in response:
                response[header] = value
        
        # 添加 HSTS
        if self.hsts_enabled and request.is_secure():
            hsts_value = f'max-age={self.hsts_max_age}'
            if self.hsts_include_subdomains:
                hsts_value += '; includeSubDomains'
            if self.hsts_preload:
                hsts_value += '; preload'
            response['Strict-Transport-Security'] = hsts_value
        
        # 添加 CSP
        if self.csp_enabled and self.csp_policy:
            csp_header = self._build_csp_header()
            response['Content-Security-Policy'] = csp_header
        
        return response
    
    def _build_csp_header(self) -> str:
        """
        构建 CSP 头
        
        Returns:
            CSP 策略字符串
        """
        parts = []
        
        for directive, values in self.csp_policy.items():
            if isinstance(values, list):
                value_str = ' '.join(values)
            else:
                value_str = values
            parts.append(f'{directive} {value_str}')
        
        return '; '.join(parts)
    
    @classmethod
    def get_presets(cls) -> dict:
        """
        获取预设的安全配置
        
        Returns:
            预设配置字典
        """
        return {
            'strict': {
                'X-Frame-Options': 'DENY',
                'X-Content-Type-Options': 'nosniff',
                'X-XSS-Protection': '1; mode=block',
                'Referrer-Policy': 'no-referrer',
                'Permissions-Policy': 'geolocation=(), microphone=(), camera=(), payment=()',
                'csp': {
                    'default-src': ["'self'"],
                    'script-src': ["'self'"],
                    'style-src': ["'self'"],
                    'img-src': ["'self'", 'data:'],
                    'font-src': ["'self'"],
                    'connect-src': ["'self'"],
                    'frame-ancestors': ["'none'"],
                }
            },
            'moderate': {
                'X-Frame-Options': 'SAMEORIGIN',
                'X-Content-Type-Options': 'nosniff',
                'X-XSS-Protection': '1; mode=block',
                'Referrer-Policy': 'strict-origin-when-cross-origin',
                'Permissions-Policy': 'geolocation=(), microphone=()',
                'csp': {
                    'default-src': ["'self'"],
                    'script-src': ["'self'", "'unsafe-inline'"],
                    'style-src': ["'self'", "'unsafe-inline'"],
                    'img-src': ["'self'", 'data:', 'https:'],
                    'font-src': ["'self'", 'https://fonts.gstatic.com'],
                    'connect-src': ["'self'"],
                }
            },
            'relaxed': {
                'X-Frame-Options': 'SAMEORIGIN',
                'X-Content-Type-Options': 'nosniff',
                'Referrer-Policy': 'no-referrer-when-downgrade',
                'csp': {
                    'default-src': ["'self'"],
                    'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
                    'style-src': ["'self'", "'unsafe-inline'"],
                    'img-src': ["*"],
                    'font-src': ["*"],
                }
            }
        }
    
    @classmethod
    def generate_csp_for_site(cls, allowed_domains: dict = None) -> str:
        """
        为网站生成推荐的 CSP 策略
        
        Args:
            allowed_domains: 允许的域名配置
            
        Returns:
            CSP 策略字符串
        """
        if not allowed_domains:
            allowed_domains = {
                'scripts': [],
                'styles': [],
                'images': [],
                'fonts': [],
                'connect': [],
            }
        
        csp = {
            'default-src': ["'self'"],
            'script-src': ["'self'"] + allowed_domains.get('scripts', []),
            'style-src': ["'self'"] + allowed_domains.get('styles', []),
            'img-src': ["'self'", 'data:'] + allowed_domains.get('images', []),
            'font-src': ["'self'"] + allowed_domains.get('fonts', []),
            'connect-src': ["'self'"] + allowed_domains.get('connect', []),
            'frame-ancestors': ["'none'"],
            'base-uri': ["'self'"],
            'form-action': ["'self'"],
        }
        
        parts = []
        for directive, values in csp.items():
            parts.append(f"{directive} {' '.join(values)}")
        
        return '; '.join(parts)
