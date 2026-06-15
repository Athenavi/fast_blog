"""
AI 智能标签推荐 API
"""
import asyncio
from functools import wraps
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

from shared.services.advanced_features.ai_tag_recommendation import ai_tag_service
from shared.services.advanced_features.ai_writing_assistant import ai_writing_assistant
from shared.services.security.content_moderation import content_moderation_service
from src.api.v2._helpers import ok, fail, _catch
from src.auth import jwt_required_dependency as jwt_required

router = APIRouter(tags=["ai"])


class TagRecommendationRequest(BaseModel):
    """标签推荐请求"""
    title: str
    content: str
    max_tags: int = 5
    existing_tags: Optional[List[str]] = None


class TextRequest(BaseModel):
    """文本请求模型"""
    text: str
    max_length: int = 200
    target_style: str = 'formal'


class TextPolishRequest(BaseModel):
    """文本润色请求"""
    text: str


class TextGrammarRequest(BaseModel):
    """语法检查请求"""
    text: str


@router.post("/recommend-tags")
@_catch
async def recommend_tags(request: TagRecommendationRequest):
    """基于文章内容推荐标签"""
    if not request.title or not request.content:
        raise HTTPException(status_code=400, detail="标题和内容不能为空")

    recommended_tags = ai_tag_service.recommend_tags(
        title=request.title, content=request.content,
        max_tags=request.max_tags, existing_tags=request.existing_tags
    )
    return ok(data={'tags': recommended_tags, 'count': len(recommended_tags)})


@router.get("/extract-summary")
@_catch
async def extract_summary(
        content: str = Query(..., min_length=10, description="文章内容"),
        max_length: int = Query(200, ge=50, le=500, description="摘要最大长度"),
        method: str = Query('smart', enum=['simple', 'smart'], description="提取方法")
):
    """从文章内容中提取摘要"""
    summary = ai_tag_service.extract_summary(
        content=content, max_length=max_length, method=method
    )
    return ok(data={'summary': summary, 'length': len(summary), 'method': method})


@router.get("/analyze-sentiment")
@_catch
async def analyze_sentiment(
        text: str = Query(..., min_length=1, description="要分析的文本")
):
    """简单的情感分析"""
    sentiment = ai_tag_service.analyze_sentiment(text=text)
    return ok(data=sentiment)


@router.post("/moderate-content")
@_catch
async def moderate_content(
        content: str = Body(..., description="文章内容"),
        title: Optional[str] = Body(None, description="文章标题（可选）"),
        check_type: str = Body('all', enum=['sensitive', 'spam', 'ads', 'all'], description="检查类型")
):
    """内容审核"""
    result = await asyncio.get_event_loop().run_in_executor(
        None, content_moderation_service.moderate_content, content, title, check_type
    )
    return ok(data=result)


@router.post("/writing/continue")
@_catch
async def smart_continue(request: TextRequest, current_user=Depends(jwt_required)):
    """智能续写"""
    continuation = await asyncio.get_event_loop().run_in_executor(
        None, ai_writing_assistant.smart_continue, request.text, request.max_length
    )
    return ok(data={'continuation': continuation, 'length': len(continuation)})


@router.post("/writing/transform-style")
@_catch
async def transform_style(request: TextRequest, current_user=Depends(jwt_required)):
    """风格转换"""
    transformed = await asyncio.get_event_loop().run_in_executor(
        None, ai_writing_assistant.transform_style, request.text, request.target_style
    )
    return ok(data={'original': request.text, 'transformed': transformed, 'style': request.target_style})


@router.post("/writing/check-grammar")
@_catch
async def check_grammar(request: TextGrammarRequest, current_user=Depends(jwt_required)):
    """语法检查"""
    issues = await asyncio.get_event_loop().run_in_executor(
        None, ai_writing_assistant.check_grammar, request.text
    )
    return ok(data={'issues': issues, 'count': len(issues)})


@router.post("/writing/polish")
@_catch
async def polish_text(request: TextPolishRequest, current_user=Depends(jwt_required)):
    """文本润色"""
    result = await asyncio.get_event_loop().run_in_executor(
        None, ai_writing_assistant.polish_text, request.text
    )
    return ok(data=result)


@router.post("/writing/generate-titles")
@_catch
async def generate_titles(current_user=Depends(jwt_required), 
        content: str = Body(..., description="文章内容"),
        count: int = Body(5, ge=1, le=10, description="生成数量"),
        style: str = Body('normal', enum=['normal', 'question', 'list', 'howto'], description="标题风格")
):
    """生成标题建议"""
    titles = await asyncio.get_event_loop().run_in_executor(
        None, ai_writing_assistant.generate_titles, content, count, style
    )
    return ok(data={'titles': titles, 'count': len(titles), 'style': style})
