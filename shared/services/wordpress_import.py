"""
WordPress XML 导入服务
支持从 WordPress 导出的 WXR (WordPress eXtended RSS) 文件导入文章、分类、标签等内容
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Any, Optional


class WordPressImportService:
    """
    WordPress XML 导入服务
    
    功能:
    1. 解析 WordPress WXR 文件
    2. 导入文章(包括内容、标题、摘要等)
    3. 导入分类和标签
    4. 导入媒体文件引用
    5. 导入评论
    6. 处理作者映射
    """

    def __init__(self):
        self.namespaces = {
            'content': 'http://purl.org/rss/1.0/modules/content/',
            'wfw': 'http://wellformedweb.org/CommentAPI/',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'wp': 'http://wordpress.org/export/1.2/',
            'excerpt': 'http://wordpress.org/export/1.2/excerpt/',
        }

    def parse_wxr_file(self, file_path: str) -> Dict[str, Any]:
        """
        解析 WordPress WXR 文件
        
        Args:
            file_path: WXR 文件路径
            
        Returns:
            包含所有解析数据的字典
        """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # 提取频道信息
            channel = root.find('channel')
            if channel is None:
                raise ValueError("无效的 WXR 文件格式")

            data = {
                'site_info': self._parse_site_info(channel),
                'authors': self._parse_authors(channel),
                'categories': self._parse_categories(channel),
                'tags': self._parse_tags(channel),
                'articles': self._parse_articles(channel),
                'media': self._parse_media(channel),
            }

            return {
                'success': True,
                'data': data,
                'stats': self._calculate_stats(data)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _parse_site_info(self, channel) -> Dict[str, str]:
        """解析站点基本信息"""
        return {
            'title': self._get_text(channel, 'title'),
            'link': self._get_text(channel, 'link'),
            'description': self._get_text(channel, 'description'),
            'pubDate': self._get_text(channel, 'pubDate'),
            'language': self._get_text(channel, 'language', 'zh-CN'),
        }

    def _parse_authors(self, channel) -> List[Dict[str, str]]:
        """解析作者信息"""
        authors = []
        for author in channel.findall('wp:author', self.namespaces):
            authors.append({
                'author_id': self._get_text(author, 'wp:author_id'),
                'login': self._get_text(author, 'wp:author_login'),
                'email': self._get_text(author, 'wp:author_email'),
                'display_name': self._get_text(author, 'wp:author_display_name'),
                'first_name': self._get_text(author, 'wp:author_first_name'),
                'last_name': self._get_text(author, 'wp:author_last_name'),
            })
        return authors

    def _parse_categories(self, channel) -> List[Dict[str, Any]]:
        """解析分类"""
        categories = []
        for category in channel.findall('wp:category', self.namespaces):
            cat_name = category.find('wp:cat_name', self.namespaces)
            cat_nicename = category.find('wp:category_nicename', self.namespaces)
            cat_parent = category.find('wp:category_parent', self.namespaces)

            categories.append({
                'name': cat_name.text if cat_name is not None else '',
                'slug': cat_nicename.text if cat_nicename is not None else '',
                'parent': cat_parent.text if cat_parent is not None else '',
                'description': '',
            })
        return categories

    def _parse_tags(self, channel) -> List[Dict[str, str]]:
        """解析标签"""
        tags = []
        for tag in channel.findall('wp:tag', self.namespaces):
            tag_name = tag.find('wp:tag_name', self.namespaces)
            tag_slug = tag.find('wp:tag_slug', self.namespaces)

            tags.append({
                'name': tag_name.text if tag_name is not None else '',
                'slug': tag_slug.text if tag_slug is not None else '',
            })
        return tags

    def _parse_articles(self, channel) -> List[Dict[str, Any]]:
        """解析文章"""
        articles = []
        for item in channel.findall('item'):
            post_type = self._get_text(item, 'wp:post_type')

            # 只处理文章类型
            if post_type != 'post' and post_type != 'page':
                continue

            article = {
                'type': post_type,
                'title': self._get_text(item, 'title'),
                'link': self._get_text(item, 'link'),
                'pubDate': self._get_text(item, 'pubDate'),
                'author': self._get_text(item, 'dc:creator', self.namespaces),
                'content': self._get_text(item, 'content:encoded', self.namespaces),
                'excerpt': self._get_text(item, 'excerpt:encoded', self.namespaces),
                'status': self._get_text(item, 'wp:status'),
                'slug': self._get_text(item, 'wp:post_name'),
                'created_at': self._parse_date(self._get_text(item, 'wp:post_date')),
                'modified_at': self._parse_date(self._get_text(item, 'wp:post_modified')),
                'categories': [],
                'tags': [],
                'comments': [],
                'featured_image': None,
            }

            # 解析分类
            for category in item.findall('category'):
                domain = category.get('domain', '')
                nicename = category.get('nicename', '')

                if domain == 'category':
                    article['categories'].append({
                        'name': category.text,
                        'slug': nicename,
                    })
                elif domain == 'post_tag':
                    article['tags'].append({
                        'name': category.text,
                        'slug': nicename,
                    })

            # 解析评论
            for comment in item.findall('wp:comment', self.namespaces):
                article['comments'].append(self._parse_comment(comment))

            # 解析特色图片
            attachment_id = self._get_text(item, 'wp:postmeta/wp:meta_key[text()="_thumbnail_id"]/../wp:meta_value',
                                           self.namespaces)
            if attachment_id:
                article['featured_image'] = attachment_id

            articles.append(article)

        return articles

    def _parse_comment(self, comment_elem) -> Dict[str, Any]:
        """解析评论"""
        return {
            'id': self._get_text(comment_elem, 'wp:comment_id'),
            'author': self._get_text(comment_elem, 'wp:comment_author'),
            'email': self._get_text(comment_elem, 'wp:comment_author_email'),
            'url': self._get_text(comment_elem, 'wp:comment_author_url'),
            'ip': self._get_text(comment_elem, 'wp:comment_author_IP'),
            'date': self._parse_date(self._get_text(comment_elem, 'wp:comment_date')),
            'content': self._get_text(comment_elem, 'wp:comment_content'),
            'approved': self._get_text(comment_elem, 'wp:comment_approved') == '1',
            'parent': self._get_text(comment_elem, 'wp:comment_parent'),
        }

    def _parse_media(self, channel) -> List[Dict[str, Any]]:
        """解析媒体文件"""
        media = []
        for item in channel.findall('item'):
            post_type = self._get_text(item, 'wp:post_type')

            if post_type != 'attachment':
                continue

            media_item = {
                'id': self._get_text(item, 'wp:post_id'),
                'title': self._get_text(item, 'title'),
                'url': self._get_text(item, 'wp:attachment_url'),
                'mime_type': self._get_text(item, 'wp:post_mime_type'),
                'created_at': self._parse_date(self._get_text(item, 'wp:post_date')),
            }
            media.append(media_item)

        return media

    def _get_text(self, parent, path, namespaces=None, default=''):
        """安全获取文本内容"""
        try:
            if namespaces:
                elem = parent.find(path, namespaces)
            else:
                elem = parent.find(path)
            return elem.text.strip() if elem is not None and elem.text else default
        except:
            return default

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """解析日期字符串"""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except:
            try:
                return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%SZ')
            except:
                return None

    def _calculate_stats(self, data: Dict[str, Any]) -> Dict[str, int]:
        """计算导入统计信息"""
        return {
            'total_articles': len(data['articles']),
            'total_pages': sum(1 for a in data['articles'] if a['type'] == 'page'),
            'total_posts': sum(1 for a in data['articles'] if a['type'] == 'post'),
            'total_categories': len(data['categories']),
            'total_tags': len(data['tags']),
            'total_comments': sum(len(a['comments']) for a in data['articles']),
            'total_media': len(data['media']),
            'total_authors': len(data['authors']),
        }

    async def import_to_database(self, parsed_data: Dict[str, Any], db_session, user_mapping: Dict[str, int] = None) -> \
    Dict[str, Any]:
        """
        将解析的数据导入数据库
        
        Args:
            parsed_data: parse_wxr_file 返回的解析数据
            db_session: 数据库会话
            user_mapping: 作者ID映射 {wordpress_author_id: system_user_id}
            
        Returns:
            导入结果统计
        """
        from shared.models.category import Category
        from shared.models.blog import Article, ArticleContent
        from sqlalchemy import select

        results = {
            'imported_categories': 0,
            'imported_tags': 0,
            'imported_articles': 0,
            'imported_comments': 0,
            'errors': [],
        }

        try:
            # 1. 导入分类
            for cat_data in parsed_data['categories']:
                try:
                    # 检查分类是否已存在
                    stmt = select(Category).where(Category.slug == cat_data['slug'])
                    result = await db_session.execute(stmt)
                    existing = result.scalar_one_or_none()

                    if not existing:
                        category = Category(
                            name=cat_data['name'],
                            slug=cat_data['slug'],
                            description=cat_data.get('description', ''),
                        )
                        db_session.add(category)
                        results['imported_categories'] += 1
                except Exception as e:
                    results['errors'].append(f"分类导入失败: {cat_data['name']} - {str(e)}")

            await db_session.commit()

            # 2. 导入文章
            for article_data in parsed_data['articles']:
                try:
                    # 确定用户ID
                    user_id = 1  # 默认用户
                    if user_mapping and article_data['author'] in user_mapping:
                        user_id = user_mapping[article_data['author']]

                    # 创建文章
                    article = Article(
                        title=article_data['title'],
                        slug=article_data['slug'],
                        excerpt=article_data['excerpt'][:200] if article_data['excerpt'] else '',
                        status=self._map_status(article_data['status']),
                        user=user_id,
                        created_at=article_data['created_at'] or datetime.now(),
                        updated_at=article_data['modified_at'] or datetime.now(),
                    )
                    db_session.add(article)
                    await db_session.flush()  # 获取文章ID

                    # 创建文章内容
                    now = datetime.now()
                    content = ArticleContent(
                        article=article.id,
                        content=article_data['content'],
                        created_at=now,
                        updated_at=now,
                    )
                    db_session.add(content)

                    results['imported_articles'] += 1

                except Exception as e:
                    results['errors'].append(f"文章导入失败: {article_data['title']} - {str(e)}")
                    await db_session.rollback()

            await db_session.commit()

            return {
                'success': True,
                'results': results,
            }

        except Exception as e:
            await db_session.rollback()
            return {
                'success': False,
                'error': str(e),
                'results': results,
            }

    def _map_status(self, wp_status: str) -> str:
        """映射 WordPress 状态到系统状态"""
        status_map = {
            'publish': 'published',
            'draft': 'draft',
            'pending': 'pending',
            'private': 'private',
            'trash': 'deleted',
        }
        return status_map.get(wp_status, 'draft')
