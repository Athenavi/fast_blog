"""
Hreflang 标签 API 端点
"""
import json
from functools import wraps

from fastapi import APIRouter, Depends, HTTPException, Query

from shared.services.seo.hreflang_generator import hreflang_generator
from src.api.v2._helpers import ok, fail, _catch
from src.auth import jwt_required_dependency as jwt_required

router = APIRouter(tags=["hreflang"])


@router.get("/generate")
@_catch
async def generate_hreflang(
    current_url: str = Query(..., description="当前页面URL"),
    translations: str = Query(..., description="翻译JSON字符串 {lang: url}"),
    default_language: str = Query("en", description="默认语言"),
    include_x_default: bool = Query(True, description="是否包含x-default"),
    current_user=Depends(jwt_required)
):
    """生成 hreflang 标签"""
    trans_dict = json.loads(translations)

    tags = hreflang_generator.generate_hreflang_tags(
        current_url=current_url,
        translations=trans_dict,
        default_language=default_language,
        include_x_default=include_x_default
    )

    html = hreflang_generator.render_html_tags(tags)

    return ok(data={
        "tags": tags,
        "html": html,
        "count": len(tags)
    })


@router.get("/validate")
@_catch
async def validate_hreflang(
    url1: str = Query(..., description="第一个URL"),
    lang1: str = Query(..., description="第一个语言代码"),
    url2: str = Query(..., description="第二个URL"),
    lang2: str = Query(..., description="第二个语言代码"),
    current_user=Depends(jwt_required)
):
    """验证 hreflang 双向链接"""
    result = hreflang_generator.validate_hreflang_pair(url1, lang1, url2, lang2)
    if result["valid"]:
        return ok(data=result)
    return fail(result.get("error", "验证失败"))


@router.get("/sitemap-entry")
@_catch
async def generate_sitemap_entry(
    url: str = Query(..., description="主URL"),
    translations: str = Query(..., description="翻译JSON字符串"),
    lastmod: str = Query(None, description="最后修改时间"),
    changefreq: str = Query("weekly", description="更新频率"),
    priority: float = Query(0.8, description="优先级"),
    current_user=Depends(jwt_required)
):
    """生成 sitemap 条目（含多语言）"""
    trans_dict = json.loads(translations)

    entry = hreflang_generator.generate_sitemap_entry(
        url=url,
        translations=trans_dict,
        lastmod=lastmod,
        changefreq=changefreq,
        priority=priority
    )
    return ok(data={"entry": entry})


@router.get("/languages")
@_catch
async def list_supported_languages():
    """获取支持的语言列表"""
    languages = hreflang_generator.get_recommended_languages()
    return ok(data={"languages": languages})
