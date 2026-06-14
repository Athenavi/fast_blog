"""
封面图片处理API - 支持外链图片转本地存储
"""
import hashlib
from functools import wraps

import aiohttp
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from shared.services.articles.cover_image_service import CoverImageService
from src.api.v2._helpers import ok, fail

router = APIRouter(tags=["cover-image"])


def _catch(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            import traceback
            print(f"Error in {func.__name__}: {e}")
            print(traceback.format_exc())
            return fail(str(e))
    return wrapper


class ExternalImageUrlRequest(BaseModel):
    """外链图片URL请求模型"""
    url: str


class ExternalImageUrlResponse(BaseModel):
    """外链图片转换响应模型"""
    cover_url: str
    message: str


@router.post("/from-url", summary="从外链URL生成封面")
@_catch
async def generate_cover_from_external_url(request_data: ExternalImageUrlRequest):
    """
    从外链图片URL下载并生成本地封面
    
    Args:
        request_data: 包含外链图片URL的请求数据
        
    Returns:
        本地封面URL
    """
    external_url = request_data.url.strip()

    if not external_url:
        raise HTTPException(status_code=400, detail="图片URL不能为空")

    # 验证URL格式
    if not external_url.startswith(('http://', 'https://')):
        raise HTTPException(status_code=400, detail="URL必须以http://或https://开头")

    # SSRF 防护：阻止访问内网/私有地址
    from urllib.parse import urlparse
    parsed = urlparse(external_url)
    import ipaddress
    try:
        host = parsed.hostname
        # 检查是否为 IP 地址
        addr = ipaddress.ip_address(host)
        if addr.is_private or addr.is_loopback or addr.is_link_local:
            raise HTTPException(status_code=400, detail="不允许访问内网地址")
    except ValueError:
        # 域名：检查是否解析到内网
        pass

    # 下载图片
    async with aiohttp.ClientSession() as session:
        async with session.get(external_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"无法下载图片，HTTP状态码: {response.status}"
                )

            # 检查Content-Type是否为图片
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                raise HTTPException(
                    status_code=400,
                    detail=f"URL不是有效的图片地址，Content-Type: {content_type}"
                )

            # 读取图片数据
            image_data = await response.read()

            if not image_data:
                raise HTTPException(status_code=400, detail="下载的图片数据为空")

            # 限制图片大小（最大10MB）
            max_size = 10 * 1024 * 1024  # 10MB
            if len(image_data) > max_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"图片过大（{len(image_data) / 1024 / 1024:.2f}MB），最大支持10MB"
                )

    # 计算文件哈希
    file_hash = hashlib.sha256(image_data).hexdigest()

    # 确定文件扩展名
    # 从URL或Content-Type推断扩展名
    ext = '.jpg'  # 默认扩展名
    if 'png' in content_type:
        ext = '.png'
    elif 'gif' in content_type:
        ext = '.gif'
    elif 'webp' in content_type:
        ext = '.webp'
    elif external_url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
        ext = '.' + external_url.split('.')[-1].split('?')[0]

    # 使用虚拟的media_id（因为是外链图片，没有媒体库ID）
    # 使用URL的哈希作为标识
    url_hash = hashlib.md5(external_url.encode()).hexdigest()[:8]
    media_id = f"ext_{url_hash}"

    # 优化并保存封面
    cover_service = CoverImageService()
    cover_filename = cover_service.optimize_and_save_cover(
        media_id=media_id,  # 使用字符串ID
        image_data=image_data,
        file_hash=file_hash,
        filename=f"{media_id}{ext}"
    )

    cover_url = f"{cover_filename}"

    return ok(data={
        "cover_url": cover_url,
        "message": "封面图片已成功生成"
    })
