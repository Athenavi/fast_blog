"""
内容质量检测 API 端点
"""
from functools import wraps

from fastapi import APIRouter, Depends, HTTPException, Request

from shared.services.seo.content_quality import content_quality_service
from src.api.v2._helpers import ok, fail, _catch
from src.auth import jwt_required_dependency as jwt_required

router = APIRouter(tags=["content-quality"])


@router.post("/analyze")
@_catch
async def analyze_content_quality(
        request: Request,
        current_user=Depends(jwt_required)
):
    """分析文章内容质量"""
    body = await request.json()
    content = body.get('content', '')
    title = body.get('title', '')
    excerpt = body.get('excerpt', '')

    if not content:
        return fail("文章内容不能为空")

    result = content_quality_service.analyze_content_quality(content, title, excerpt)
    return ok(data=result)


@router.post("/check-grammar")
@_catch
async def check_grammar(
        request: Request,
        current_user=Depends(jwt_required)
):
    """检查语法错误"""
    body = await request.json()
    content = body.get('content', '')
    if not content:
        return fail("文章内容不能为空")

    issues = content_quality_service._check_grammar(content)
    return ok(data={'issues': issues, 'total_issues': len(issues)})


@router.post("/analyze-readability")
@_catch
async def analyze_readability(
        request: Request,
        current_user=Depends(jwt_required)
):
    """分析可读性"""
    body = await request.json()
    content = body.get('content', '')
    if not content:
        return fail("文章内容不能为空")

    result = content_quality_service._analyze_readability(content)
    return ok(data=result)


@router.post("/analyze-tone")
@_catch
async def analyze_tone(
        request: Request,
        current_user=Depends(jwt_required)
):
    """分析语气风格"""
    body = await request.json()
    content = body.get('content', '')
    if not content:
        return fail("文章内容不能为空")

    result = content_quality_service._analyze_tone(content)
    return ok(data=result)
