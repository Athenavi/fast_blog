"""
AI 智能标签推荐 API
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from shared.services.ai_tag_recommendation import ai_tag_service
from shared.services.content_moderation import content_moderation_service
from shared.services.ai_writing_assistant import ai_writing_assistant

router = APIRouter(prefix="/ai", tags=["ai"])


class TagRecommendationRequest(BaseModel):
    """标签推荐请求"""
    title: str
    content: str
    max_tags: int = 5
    existing_tags: Optional[List[str]] = None


class TagRecommendationResponse(BaseModel):
    """标签推荐响应"""
    success: bool
    data: dict


@router.post("/recommend-tags", response_model=TagRecommendationResponse)
async def recommend_tags(request: TagRecommendationRequest):
    """
    基于文章内容推荐标签
    
    Args:
        title: 文章标题
        content: 文章内容
        max_tags: 最大推荐标签数（默认 5）
        existing_tags: 已有标签（用于去重）
        
    Returns:
        推荐的标签列表
    """
    try:
        # 验证输入
        if not request.title or not request.content:
            raise HTTPException(
                status_code=400,
                detail="标题和内容不能为空"
            )

        # 推荐标签
        recommended_tags = ai_tag_service.recommend_tags(
            title=request.title,
            content=request.content,
            max_tags=request.max_tags,
            existing_tags=request.existing_tags
        )

        return TagRecommendationResponse(
            success=True,
            data={
                'tags': recommended_tags,
                'count': len(recommended_tags),
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/extract-summary")
async def extract_summary(
        content: str = Query(..., min_length=10, description="文章内容"),
        max_length: int = Query(200, ge=50, le=500, description="摘要最大长度"),
        method: str = Query('smart', enum=['simple', 'smart'], description="提取方法")
):
    """
    从文章内容中提取摘要
    
    Args:
        content: 文章内容
        max_length: 摘要最大长度
        method: 提取方法 ('simple' 或 'smart')
        
    Returns:
        提取的摘要
    """
    try:
        summary = ai_tag_service.extract_summary(
            content=content,
            max_length=max_length,
            method=method
        )

        return {
            'success': True,
            'data': {
                'summary': summary,
                'length': len(summary),
                'method': method,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze-sentiment")
async def analyze_sentiment(
        text: str = Query(..., min_length=1, description="要分析的文本")
):
    """
    简单的情感分析
    
    Args:
        text: 要分析的文本
        
    Returns:
        情感分析结果（正面、负面、中性分数）
    """
    try:
        sentiment = ai_tag_service.analyze_sentiment(text=text)

        return {
            'success': True,
            'data': sentiment
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/moderate-content")
async def moderate_content(
        content: str,
        title: Optional[str] = None,
        check_type: str = Query('all', enum=['sensitive', 'spam', 'ads', 'all'], description="检查类型")
):
    """
    内容审核
    
    Args:
        content: 文章内容
        title: 文章标题（可选）
        check_type: 检查类型 ('sensitive', 'spam', 'ads', 'all')
        
    Returns:
        审核结果
    """
    try:
        result = content_moderation_service.moderate_content(
            content=content,
            title=title,
            check_type=check_type
        )

        return {
            'success': True,
            'data': result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/writing/continue")
async def smart_continue(
        text: str,
        max_length: int = Query(200, ge=50, le=500, description="最大续写长度")
):
    """
    智能续写
    
    Args:
        text: 已有文本
        max_length: 最大续写长度
        
    Returns:
        续写的内容
    """
    try:
        continuation = ai_writing_assistant.smart_continue(
            text=text,
            max_length=max_length
        )

        return {
            'success': True,
            'data': {
                'continuation': continuation,
                'length': len(continuation),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/writing/transform-style")
async def transform_style(
        text: str,
        target_style: str = Query('formal', enum=['formal', 'casual', 'concise', 'detailed'], description="目标风格")
):
    """
    风格转换
    
    Args:
        text: 原文本
        target_style: 目标风格
        
    Returns:
        转换后的文本
    """
    try:
        transformed = ai_writing_assistant.transform_style(
            text=text,
            target_style=target_style
        )

        return {
            'success': True,
            'data': {
                'original': text,
                'transformed': transformed,
                'style': target_style,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/writing/check-grammar")
async def check_grammar(text: str):
    """
    语法检查
    
    Args:
        text: 要检查的文本
        
    Returns:
        发现的问题列表
    """
    try:
        issues = ai_writing_assistant.check_grammar(text=text)

        return {
            'success': True,
            'data': {
                'issues': issues,
                'count': len(issues),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/writing/polish")
async def polish_text(text: str):
    """
    文本润色
    
    Args:
        text: 原文本
        
    Returns:
        润色结果和建议
    """
    try:
        result = ai_writing_assistant.polish_text(text=text)

        return {
            'success': True,
            'data': result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/writing/generate-titles")
async def generate_titles(
        content: str,
        count: int = Query(5, ge=1, le=10, description="生成数量"),
        style: str = Query('normal', enum=['normal', 'question', 'list', 'howto'], description="标题风格")
):
    """
    生成标题建议
    
    Args:
        content: 文章内容
        count: 生成数量
        style: 标题风格
        
    Returns:
        标题列表
    """
    try:
        titles = ai_writing_assistant.generate_titles(
            content=content,
            count=count,
            style=style
        )

        return {
            'success': True,
            'data': {
                'titles': titles,
                'count': len(titles),
                'style': style,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
