"""
XML 站点地图生成器
支持标准 Sitemap 协议、多语言 hreflang 标签和多种站点地图类型
"""
from datetime import datetime
from typing import List, Optional, Dict
from xml.dom.minidom import parseString
from xml.etree.ElementTree import Element, SubElement, tostring


class SitemapUrl:
    """站点地图 URL 条目"""

    def __init__(
            self,
            loc: str,
            lastmod: Optional[datetime] = None,
            changefreq: str = 'weekly',
            priority: float = 0.5,
            alternate_links: Optional[List[Dict[str, str]]] = None,
    ):
        self.loc = loc
        self.lastmod = lastmod
        self.changefreq = changefreq
        self.priority = priority
        self.alternate_links = alternate_links or []


class SitemapGenerator:
    """XML 站点地图生成器"""

    def __init__(self):
        self.urls: List[SitemapUrl] = []

    def add_url(self, url: SitemapUrl):
        """添加 URL 条目"""
        self.urls.append(url)

    def generate_xml(self) -> str:
        """生成 XML 站点地图"""
        urlset = Element('urlset', {
            'xmlns': 'http://www.sitemaps.org/schemas/sitemap/0.9',
            'xmlns:xhtml': 'http://www.w3.org/1999/xhtml'  # 添加 xhtml 命名空间以支持 hreflang
        })

        for url in self.urls:
            url_elem = SubElement(urlset, 'url')
            SubElement(url_elem, 'loc').text = url.loc

            if url.lastmod:
                SubElement(url_elem, 'lastmod').text = url.lastmod.strftime('%Y-%m-%dT%H:%M:%S+00:00')

            if url.changefreq:
                SubElement(url_elem, 'changefreq').text = url.changefreq

            if url.priority is not None:
                SubElement(url_elem, 'priority').text = f"{url.priority:.1f}"

            # 添加多语言 hreflang 链接
            if url.alternate_links:
                for alt in url.alternate_links:
                    link_elem = SubElement(url_elem, '{http://www.w3.org/1999/xhtml}link')
                    link_elem.set('rel', 'alternate')
                    link_elem.set('hreflang', alt['hreflang'])
                    link_elem.set('href', alt['href'])

        return self._pretty_print(tostring(urlset, encoding='unicode'))

    @staticmethod
    def _pretty_print(xml_str: str) -> str:
        """美化 XML 输出"""
        dom = parseString(xml_str)
        return dom.toprettyxml(indent='  ', encoding=None)


class SitemapIndex:
    """站点地图索引（用于多个站点地图文件）"""

    def __init__(self):
        self.sitemaps: List[dict] = []

    def add_sitemap(self, loc: str, lastmod: Optional[datetime] = None):
        """添加站点地图引用"""
        self.sitemaps.append({
            'loc': loc,
            'lastmod': lastmod,
        })

    def generate_xml(self) -> str:
        """生成站点地图索引 XML"""
        sitemapindex = Element('sitemapindex', {
            'xmlns': 'http://www.sitemaps.org/schemas/sitemap/0.9'
        })

        for sm in self.sitemaps:
            sitemap_elem = SubElement(sitemapindex, 'sitemap')
            SubElement(sitemap_elem, 'loc').text = sm['loc']

            if sm['lastmod']:
                SubElement(sitemap_elem, 'lastmod').text = sm['lastmod'].strftime('%Y-%m-%dT%H:%M:%S+00:00')

        return self._pretty_print(tostring(sitemapindex, encoding='unicode'))

    @staticmethod
    def _pretty_print(xml_str: str) -> str:
        """美化 XML 输出"""
        dom = parseString(xml_str)
        return dom.toprettyxml(indent='  ', encoding=None)
