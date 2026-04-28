"""
Block 编辑器 API 端点
提供块的 CRUD 操作和渲染功能
"""

import json
from typing import List, Optional, Dict

from fastapi import APIRouter, Body, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_super_user
from shared.models.block_pattern import BlockPattern
from shared.services.editor.block_editor import block_registry
from src.utils.database.main import get_async_session

router = APIRouter(prefix="/blocks", tags=["block-editor"])


@router.get("/registry")
async def get_block_registry():
    """
    获取所有注册的块类型
    
    Returns:
        所有块的配置信息
    """
    try:
        blocks = block_registry.get_all_blocks()
        
        # 移除不可序列化的 render_callback
        serializable_blocks = {}
        for block_type, config in blocks.items():
            serializable_config = {k: v for k, v in config.items() if k != 'render_callback'}
            serializable_blocks[block_type] = serializable_config
        
        return {
            'success': True,
            'data': {
                'blocks': serializable_blocks,
                'total': len(serializable_blocks)
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@router.get("/patterns")
async def get_block_patterns(
    category: str = None, 
    search: str = None,
    include_custom: bool = True,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_super_user)
):
    """
    获取所有块模式（包括预定义和自定义）
    
    Args:
        category: 按分类过滤
        search: 搜索关键词
        include_custom: 是否包含自定义模式
    
    Returns:
        块模式列表
    """
    try:
        # 获取预定义模式（暂时返回空列表，因为 block_pattern_registry 不存在）
        patterns = []
        result_patterns = [pattern.to_dict() if hasattr(pattern, 'to_dict') else pattern for pattern in patterns]
        
        # 如果需要，添加自定义模式
        if include_custom and current_user:
            query = select(BlockPattern).where(BlockPattern.user_id == current_user.id)
            
            if category:
                query = query.where(BlockPattern.category == category)
            
            query = query.order_by(BlockPattern.created_at.desc())
            
            db_result = await db.execute(query)
            custom_patterns = db_result.scalars().all()
            
            for pattern in custom_patterns:
                result_patterns.append(pattern.to_pattern_dict())
        
        return {
            'success': True,
            'data': {
                'patterns': result_patterns,
                'total': len(result_patterns)
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@router.get("/patterns/{pattern_name}")
async def get_block_pattern(
    pattern_name: str,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_super_user)
):
    """
    获取指定名称的块模式
    
    Args:
        pattern_name: 模式名称
    
    Returns:
        块模式详情
    """
    try:
        # 从数据库查找自定义模式
        result = await db.execute(
            select(BlockPattern).where(BlockPattern.name == pattern_name)
        )
        pattern = result.scalar_one_or_none()
        
        if not pattern:
            return {
                'success': False,
                'error': f'Pattern "{pattern_name}" not found'
            }
        
        return {
            'success': True,
            'data': pattern.to_pattern_dict()
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@router.get("/registry/{block_type}")
async def get_block_config(block_type: str):
    """
    获取指定块的配置
    
    Args:
        block_type: 块类型标识
        
    Returns:
        块的配置信息
    """
    try:
        config = block_registry.get_block_config(block_type)
        
        if not config:
            return {
                'success': False,
                'error': f'块类型 "{block_type}" 未注册'
            }
        
        # 移除不可序列化的字段
        serializable_config = {k: v for k, v in config.items() if k != 'render_callback'}
        
        return {
            'success': True,
            'data': serializable_config
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@router.post("/validate")
async def validate_block(
    block_data: dict = Body(...)
):
    """
    验证块数据是否符合 schema
    
    Args:
        block_data: 块数据字典
        
    Returns:
        验证结果
    """
    try:
        block_type = block_data.get('block_type')
        attributes = block_data.get('attributes', {})
        
        if not block_type:
            return {
                'success': False,
                'error': '缺少 block_type 字段'
            }
        
        config = block_registry.get_block_config(block_type)
        
        if not config:
            return {
                'success': False,
                'error': f'块类型 "{block_type}" 未注册'
            }
        
        schema = config.get('attributes_schema', {})
        errors = []
        
        # 验证属性
        for attr_name, attr_schema in schema.items():
            value = attributes.get(attr_name)
            attr_type = attr_schema.get('type')
            
            # 检查必填字段（有默认值的不是必填）
            if value is None and 'default' not in attr_schema:
                errors.append(f'缺少必需属性: {attr_name}')
                continue
            
            # 类型检查
            if value is not None:
                if attr_type == 'string' and not isinstance(value, str):
                    errors.append(f'属性 "{attr_name}" 必须是字符串')
                elif attr_type == 'integer' and not isinstance(value, int):
                    errors.append(f'属性 "{attr_name}" 必须是整数')
                elif attr_type == 'boolean' and not isinstance(value, bool):
                    errors.append(f'属性 "{attr_name}" 必须是布尔值')
                elif attr_type == 'array' and not isinstance(value, list):
                    errors.append(f'属性 "{attr_name}" 必须是数组')
                
                # 枚举检查
                if 'enum' in attr_schema and value not in attr_schema['enum']:
                    errors.append(f'属性 "{attr_name}" 的值必须是 {attr_schema["enum"]} 之一')
                
                # 数值范围检查
                if attr_type == 'integer':
                    if 'min' in attr_schema and value < attr_schema['min']:
                        errors.append(f'属性 "{attr_name}" 不能小于 {attr_schema["min"]}')
                    if 'max' in attr_schema and value > attr_schema['max']:
                        errors.append(f'属性 "{attr_name}" 不能大于 {attr_schema["max"]}')
        
        return {
            'success': len(errors) == 0,
            'data': {
                'valid': len(errors) == 0,
                'errors': errors
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@router.post("/render")
async def render_block(
    block_data: dict = Body(...)
):
    """
    渲染块为 HTML
    
    Args:
        block_data: 块数据字典
        
    Returns:
        渲染后的 HTML
    """
    try:
        block_type = block_data.get('block_type')
        attributes = block_data.get('attributes', {})
        inner_html = block_data.get('inner_html', '')
        
        if not block_type:
            return {
                'success': False,
                'error': '缺少 block_type 字段'
            }
        
        config = block_registry.get_block_config(block_type)
        
        if not config:
            return {
                'success': False,
                'error': f'块类型 "{block_type}" 未注册'
            }
        
        # 如果有自定义渲染回调，使用它
        render_callback = config.get('render_callback')
        if render_callback:
            html = render_callback(attributes, inner_html)
        else:
            # 使用默认渲染
            html = render_block_default(block_type, attributes, inner_html)
        
        return {
            'success': True,
            'data': {
                'html': html,
                'block_type': block_type
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def render_block_default(block_type: str, attributes: dict, inner_html: str) -> str:
    """
    默认的块渲染逻辑
    
    Args:
        block_type: 块类型
        attributes: 属性
        inner_html: 内部 HTML
        
    Returns:
        渲染后的 HTML
    """
    if block_type == 'paragraph':
        align = attributes.get('align', '')
        align_class = f' text-{align}' if align else ''
        content = attributes.get('content', inner_html)
        return f'<p class="paragraph{align_class}">{content}</p>'
    
    elif block_type == 'heading':
        level = attributes.get('level', 2)
        align = attributes.get('align', '')
        align_class = f' text-{align}' if align else ''
        content = attributes.get('content', inner_html)
        return f'<h{level} class="heading{align_class}">{content}</h{level}>'
    
    elif block_type == 'image':
        url = attributes.get('url', '')
        alt = attributes.get('alt', '')
        caption = attributes.get('caption', '')
        width = attributes.get('width', '')
        height = attributes.get('height', '')
        align = attributes.get('align', '')
        
        style = ''
        if width:
            style += f'width: {width}px; '
        if height:
            style += f'height: {height}px; '
        
        align_class = f' align-{align}' if align else ''
        
        img_html = f'<img src="{url}" alt="{alt}" style="{style}" />'
        
        if caption:
            return f'<figure class="image-block{align_class}">{img_html}<figcaption>{caption}</figcaption></figure>'
        else:
            return f'<div class="image-block{align_class}">{img_html}</div>'
    
    elif block_type == 'quote':
        content = attributes.get('content', inner_html)
        citation = attributes.get('citation', '')
        style = attributes.get('style', 'default')
        
        html = f'<blockquote class="quote quote-{style}"><p>{content}</p>'
        if citation:
            html += f'<cite>{citation}</cite>'
        html += '</blockquote>'
        return html
    
    elif block_type == 'button':
        text = attributes.get('text', '点击我')
        url = attributes.get('url', '#')
        style = attributes.get('style', 'primary')
        size = attributes.get('size', 'medium')
        open_new = attributes.get('open_in_new_tab', False)
        
        target = ' target="_blank" rel="noopener noreferrer"' if open_new else ''
        
        return f'<a href="{url}" class="btn btn-{style} btn-{size}"{target}>{text}</a>'
    
    elif block_type == 'list':
        items = attributes.get('items', [])
        ordered = attributes.get('ordered', False)
        
        if not items:
            return inner_html
        
        tag = 'ol' if ordered else 'ul'
        items_html = ''.join([f'<li>{item}</li>' for item in items])
        return f'<{tag} class="list-block">{items_html}</{tag}>'
    
    elif block_type == 'code':
        language = attributes.get('language', 'javascript')
        content = attributes.get('content', inner_html)
        show_lines = attributes.get('show_line_numbers', True)
        
        line_numbers_class = ' line-numbers' if show_lines else ''
        
        return f'<pre class="code-block{line_numbers_class}"><code class="language-{language}">{content}</code></pre>'
    
    elif block_type == 'separator':
        style = attributes.get('style', 'solid')
        return f'<hr class="separator separator-{style}" />'
    
    elif block_type == 'columns':
        column_count = attributes.get('column_count', 2)
        gap = attributes.get('gap', 'medium')
        
        return f'<div class="columns columns-{column_count} gap-{gap}">{inner_html}</div>'
    
    else:
        # 未知块类型，返回原始 HTML
        return inner_html or f'<!-- Unknown block: {block_type} -->'


@router.post("/convert/from-html")
async def convert_html_to_blocks(
    html: str = Body(..., embed=True)
):
    """
    将 HTML 转换为块数组（简化版）
    
    Args:
        html: HTML 字符串
        
    Returns:
        块数组
    """
    try:
        # 实现完整的 HTML 到 Blocks 转换
        from bs4 import BeautifulSoup
        
        blocks = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # 遍历所有顶层元素
        for element in soup.children:
            if not element.name:  # 跳过文本节点
                continue
            
            block = _convert_element_to_block(element)
            if block:
                blocks.append(block)
        
        return {
            'success': True,
            'data': {
                'blocks': blocks,
                'total': len(blocks)
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }


def _convert_element_to_block(element) -> Optional[Dict]:
    """
    将HTML元素转换为Block
    
    Args:
        element: BeautifulSoup元素
        
    Returns:
        Block字典或None
    """
    from bs4 import Tag
    
    if not isinstance(element, Tag):
        return None
    
    tag_name = element.name.lower()
    
    # 段落
    if tag_name == 'p':
        return {
            'block_type': 'paragraph',
            'attributes': {'content': str(element)},
            'inner_blocks': [],
            'inner_html': ''
        }
    
    # 标题
    elif tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        level = int(tag_name[1])
        return {
            'block_type': 'heading',
            'attributes': {
                'level': level,
                'content': element.get_text()
            },
            'inner_blocks': [],
            'inner_html': ''
        }
    
    # 图片
    elif tag_name == 'img':
        return {
            'block_type': 'image',
            'attributes': {
                'url': element.get('src', ''),
                'alt': element.get('alt', ''),
                'caption': element.get('title', '')
            },
            'inner_blocks': [],
            'inner_html': ''
        }
    
    # 链接
    elif tag_name == 'a':
        return {
            'block_type': 'link',
            'attributes': {
                'url': element.get('href', ''),
                'text': element.get_text(),
                'target': element.get('target', '_self')
            },
            'inner_blocks': [],
            'inner_html': ''
        }
    
    # 列表
    elif tag_name in ['ul', 'ol']:
        items = []
        for li in element.find_all('li', recursive=False):
            items.append(str(li))
        
        return {
            'block_type': 'list',
            'attributes': {
                'ordered': tag_name == 'ol',
                'items': items
            },
            'inner_blocks': [],
            'inner_html': ''
        }
    
    # 引用块
    elif tag_name == 'blockquote':
        return {
            'block_type': 'quote',
            'attributes': {'content': element.get_text()},
            'inner_blocks': [],
            'inner_html': ''
        }
    
    # 代码块
    elif tag_name == 'pre':
        code_elem = element.find('code')
        code_content = code_elem.get_text() if code_elem else element.get_text()
        return {
            'block_type': 'code',
            'attributes': {
                'language': code_elem.get('class', [''])[0].replace('language-', '') if code_elem and code_elem.get('class') else '',
                'content': code_content
            },
            'inner_blocks': [],
            'inner_html': ''
        }
    
    # 分隔线
    elif tag_name == 'hr':
        return {
            'block_type': 'separator',
            'attributes': {},
            'inner_blocks': [],
            'inner_html': ''
        }
    
    # 视频
    elif tag_name == 'video':
        source = element.find('source')
        return {
            'block_type': 'video',
            'attributes': {
                'url': source.get('src', '') if source else element.get('src', ''),
                'poster': element.get('poster', '')
            },
            'inner_blocks': [],
            'inner_html': ''
        }
    
    # 表格
    elif tag_name == 'table':
        return {
            'block_type': 'table',
            'attributes': {'html': str(element)},
            'inner_blocks': [],
            'inner_html': ''
        }
    
    # 其他元素作为HTML块
    else:
        return {
            'block_type': 'html',
            'attributes': {'content': str(element)},
            'inner_blocks': [],
            'inner_html': ''
        }


@router.post("/convert/to-html")
async def convert_blocks_to_html(
    blocks: List[dict] = Body(...)
):
    """
    将块数组转换为 HTML
    
    Args:
        blocks: 块数组
        
    Returns:
        HTML 字符串
    """
    try:
        html_parts = []
        
        for block_data in blocks:
            result = await render_block(block_data)
            if result['success']:
                html_parts.append(result['data']['html'])
        
        html = '\n'.join(html_parts)
        
        return {
            'success': True,
            'data': {
                'html': html
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


# ============================================================================
# 自定义块模式管理 API
# ============================================================================

@router.post("/patterns/custom")
async def save_custom_pattern(
    pattern_data: dict = Body(...),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_super_user)
):
    """
    保存自定义块模式
    
    Args:
        pattern_data: 模式数据，包含 name, title, description, category, blocks, keywords, thumbnail, is_public
    
    Returns:
        保存的模式信息
    """
    try:
        # 验证必填字段
        required_fields = ['name', 'title', 'blocks']
        for field in required_fields:
            if field not in pattern_data or not pattern_data[field]:
                return {
                    'success': False,
                    'error': f'缺少必填字段: {field}'
                }
        
        # 检查名称是否已存在
        result = await db.execute(
            select(BlockPattern).where(BlockPattern.name == pattern_data['name'])
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            return {
                'success': False,
                'error': f'模式名称 "{pattern_data["name"]}" 已存在'
            }
        
        # 序列化 blocks 和 keywords
        blocks_json = json.dumps(pattern_data['blocks'], ensure_ascii=False) if isinstance(pattern_data['blocks'], (list, dict)) else pattern_data['blocks']
        
        keywords_value = None
        if 'keywords' in pattern_data and pattern_data['keywords']:
            if isinstance(pattern_data['keywords'], list):
                keywords_value = ','.join(pattern_data['keywords'])
            elif isinstance(pattern_data['keywords'], str):
                keywords_value = pattern_data['keywords']
        
        # 创建新模式
        new_pattern = BlockPattern(
            name=pattern_data['name'],
            title=pattern_data['title'],
            description=pattern_data.get('description'),
            category=pattern_data.get('category', 'custom'),
            blocks=blocks_json,
            keywords=keywords_value,
            thumbnail=pattern_data.get('thumbnail'),
            is_public=pattern_data.get('is_public', False),
            user_id=current_user.id,
            viewport_width=pattern_data.get('viewport_width', 800)
        )
        
        db.add(new_pattern)
        await db.commit()
        await db.refresh(new_pattern)
        
        return {
            'success': True,
            'data': new_pattern.to_dict(),
            'message': '模式保存成功'
        }
    except Exception as e:
        await db.rollback()
        return {
            'success': False,
            'error': f'保存失败: {str(e)}'
        }


@router.get("/patterns/custom")
async def get_custom_patterns(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_super_user)
):
    """
    获取当前用户的自定义模式
    
    Args:
        category: 按分类过滤（可选）
    
    Returns:
        自定义模式列表
    """
    try:
        query = select(BlockPattern).where(BlockPattern.user_id == current_user.id)
        
        if category:
            query = query.where(BlockPattern.category == category)
        
        query = query.order_by(BlockPattern.created_at.desc())
        
        result = await db.execute(query)
        patterns = result.scalars().all()
        
        return {
            'success': True,
            'data': {
                'patterns': [pattern.to_pattern_dict() for pattern in patterns],
                'total': len(patterns)
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'获取失败: {str(e)}'
        }


@router.put("/patterns/custom/{pattern_id}")
async def update_custom_pattern(
    pattern_id: int,
    pattern_data: dict = Body(...),
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_super_user)
):
    """
    更新自定义模式
    
    Args:
        pattern_id: 模式 ID
        pattern_data: 要更新的字段
    
    Returns:
        更新后的模式信息
    """
    try:
        # 查询模式
        result = await db.execute(
            select(BlockPattern).where(BlockPattern.id == pattern_id)
        )
        pattern = result.scalar_one_or_none()
        
        if not pattern:
            return {
                'success': False,
                'error': '模式不存在'
            }
        
        # 检查权限
        if pattern.user_id != current_user.id and not current_user.is_superuser:
            return {
                'success': False,
                'error': '无权修改此模式'
            }
        
        # 更新字段
        updatable_fields = ['title', 'description', 'category', 'blocks', 'keywords', 'thumbnail', 'is_public', 'viewport_width']
        
        for field in updatable_fields:
            if field in pattern_data:
                value = pattern_data[field]
                
                # 特殊处理 blocks 和 keywords
                if field == 'blocks' and isinstance(value, (list, dict)):
                    value = json.dumps(value, ensure_ascii=False)
                elif field == 'keywords' and isinstance(value, list):
                    value = ','.join(value)
                
                setattr(pattern, field, value)
        
        await db.commit()
        await db.refresh(pattern)
        
        return {
            'success': True,
            'data': pattern.to_pattern_dict(),
            'message': '模式更新成功'
        }
    except Exception as e:
        await db.rollback()
        return {
            'success': False,
            'error': f'更新失败: {str(e)}'
        }


@router.delete("/patterns/custom/{pattern_id}")
async def delete_custom_pattern(
    pattern_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_super_user)
):
    """
    删除自定义模式
    
    Args:
        pattern_id: 模式 ID
    
    Returns:
        删除结果
    """
    try:
        # 查询模式
        result = await db.execute(
            select(BlockPattern).where(BlockPattern.id == pattern_id)
        )
        pattern = result.scalar_one_or_none()
        
        if not pattern:
            return {
                'success': False,
                'error': '模式不存在'
            }
        
        # 检查权限
        if pattern.user_id != current_user.id and not current_user.is_superuser:
            return {
                'success': False,
                'error': '无权删除此模式'
            }
        
        await db.delete(pattern)
        await db.commit()
        
        return {
            'success': True,
            'message': '模式删除成功'
        }
    except Exception as e:
        await db.rollback()
        return {
            'success': False,
            'error': f'删除失败: {str(e)}'
        }
