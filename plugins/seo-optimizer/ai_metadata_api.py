"""
AI 元数据 API 端点

提供文章内容的智能分析功能
"""

from typing import Optional

from fastapi import APIRouter, Depends, Body, Query
from shared.services.ai_metadata import generate_article_metadata, ai_metadata_service
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.responses import ApiResponse
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(prefix="/ai", tags=["ai-metadata"])


@router.post("/metadata/generate",
             summary="生成 AI 友好的文章元数据",
             description="""
分析文章内容,自动生成 AI 友好的元数据,包括:

- **关键词提取**: 从内容中提取最重要的关键词
- **语义标签**: 识别文章主题和技术栈
- **自动摘要**: 生成简洁的内容摘要
- **可读性评分**: 评估文章的阅读难度
- **内容类型**: 识别文章类型(教程、新闻、评论等)
- **阅读时间**: 估算阅读所需时间
- **语言检测**: 自动检测文章语言

**使用场景**:
- 文章发布时自动生成 SEO 元数据
- 为 AI Agent 提供结构化的内容信息
- 内容推荐系统的特征提取
- 文章分类和标签自动化
             """,
             response_description="返回 AI 生成的元数据")
async def generate_metadata_endpoint(
        title: str = Body(..., description="文章标题", examples=["FastAPI 入门教程"]),
        content: str = Body(..., description="文章内容(Markdown格式)",
                            examples=["# FastAPI 入门\n\nFastAPI 是一个现代..."]),
        excerpt: Optional[str] = Body(None, description="文章摘要(可选,不提供则自动生成)")
):
    """
    生成 AI 友好的文章元数据
    
    此接口不需要认证,可用于预览元数据效果
    """
    try:
        metadata = generate_article_metadata(title, content, excerpt)

        return ApiResponse(
            success=True,
            data=metadata,
            message="元数据生成成功"
        )
    except Exception as e:
        import traceback
        print(f"Error generating metadata: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/keywords/extract",
             summary="提取关键词",
             description="从文章内容中提取最重要的关键词",
             response_description="返回关键词列表")
async def extract_keywords_endpoint(
        content: str = Body(..., description="文章内容"),
        max_keywords: int = Body(10, description="最大关键词数量", ge=1, le=50)
):
    """提取关键词"""
    try:
        keywords = ai_metadata_service.extract_keywords(content, max_keywords)

        return ApiResponse(
            success=True,
            data={"keywords": keywords, "count": len(keywords)}
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/summary/generate",
             summary="生成文章摘要",
             description="根据文章内容自动生成简洁的摘要",
             response_description="返回生成的摘要")
async def generate_summary_endpoint(
        content: str = Body(..., description="文章内容"),
        max_length: int = Body(200, description="摘要最大长度", ge=50, le=500)
):
    """生成摘要"""
    try:
        summary = ai_metadata_service.generate_summary(content, max_length)

        return ApiResponse(
            success=True,
            data={"summary": summary, "length": len(summary)}
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/tags/extract",
             summary="提取语义标签",
             description="从文章中提取语义标签,包括主题、技术栈等",
             response_description="返回标签列表")
async def extract_tags_endpoint(
        content: str = Body(..., description="文章内容"),
        title: Optional[str] = Body("", description="文章标题(可选)")
):
    """提取语义标签"""
    try:
        tags = ai_metadata_service.extract_semantic_tags(content, title)

        return ApiResponse(
            success=True,
            data={"tags": tags, "count": len(tags)}
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/readability/score",
             summary="计算可读性评分",
             description="评估文章的可读性和难度级别",
             response_description="返回可读性指标")
async def calculate_readability_endpoint(
        content: str = Body(..., description="文章内容")
):
    """计算可读性"""
    try:
        readability = ai_metadata_service.calculate_readability_score(content)

        return ApiResponse(
            success=True,
            data=readability
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.post("/content-type/detect",
             summary="检测内容类型",
             description="识别文章类型:教程、新闻、评论等",
             response_description="返回内容类型")
async def detect_content_type_endpoint(
        content: str = Body(..., description="文章内容"),
        title: Optional[str] = Body("", description="文章标题(可选)")
):
    """检测内容类型"""
    try:
        content_type = ai_metadata_service.detect_content_type(content, title)

        type_descriptions = {
            "tutorial": "教程/指南",
            "article": "普通文章",
            "news": "新闻/公告",
            "review": "评测/对比",
            "opinion": "观点/评论",
            "other": "其他"
        }

        return ApiResponse(
            success=True,
            data={
                "type": content_type,
                "description": type_descriptions.get(content_type, "未知")
            }
        )
    except Exception as e:
        return ApiResponse(success=False, error=str(e))


@router.get("/metadata/{article_id}",
            summary="获取文章的 AI 元数据",
            description="从数据库中获取已保存的文章 AI 元数据",
            response_description="返回文章的 AI 元数据")
async def get_article_ai_metadata(
        article_id: int,
        db: AsyncSession = Depends(get_async_db)
):
    """获取文章的 AI 元数据"""
    try:
        from sqlalchemy import select
        from shared.models.article import Article

        # 查询文章
        query = select(Article).where(Article.id == article_id)
        result = await db.execute(query)
        article = result.scalar_one_or_none()

        if not article:
            return ApiResponse(success=False, error="文章不存在")

        # 检查是否有 AI 元数据字段
        ai_metadata = getattr(article, 'ai_metadata', None)

        if not ai_metadata:
            # 如果没有,实时生成
            # 获取文章内容
            from shared.models.article_content import ArticleContent
            content_query = select(ArticleContent).where(ArticleContent.aid == article_id)
            content_result = await db.execute(content_query)
            article_content = content_result.scalar_one_or_none()

            if article_content:
                metadata = generate_article_metadata(
                    article.title,
                    article_content.content,
                    article.excerpt
                )

                return ApiResponse(
                    success=True,
                    data=metadata,
                    message="元数据实时生成(未保存)"
                )
            else:
                return ApiResponse(success=False, error="文章内容不存在")

        return ApiResponse(
            success=True,
            data=ai_metadata
        )
    except Exception as e:
        import traceback
        print(f"Error getting article metadata: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.get("/articles/{article_id}/summary",
            summary="获取文章摘要",
            description="""
获取文章的智能摘要，支持多种格式。

**摘要格式**:
- **brief**: 简短摘要（50字以内）
- **normal**: 普通摘要（200字以内）
- **detailed**: 详细摘要（500字以内）
- **bullet**: 要点式摘要（列表形式）

**特性**:
- 自动缓存摘要结果
- 支持批量生成
- AI 智能提取关键信息
            """,
            response_description="返回文章摘要")
async def get_article_summary(
        article_id: int,
        format: str = Query("normal", description="摘要格式: brief, normal, detailed, bullet"),
        db: AsyncSession = Depends(get_async_db)
):
    """获取文章摘要"""
    try:
        from sqlalchemy import select
        from shared.models.article import Article
        from shared.models.article_content import ArticleContent

        # 查询文章
        query = select(Article).where(Article.id == article_id)
        result = await db.execute(query)
        article = result.scalar_one_or_none()

        if not article:
            return ApiResponse(success=False, error="文章不存在")

        # 获取文章内容
        content_query = select(ArticleContent).where(ArticleContent.aid == article_id)
        content_result = await db.execute(content_query)
        article_content = content_result.scalar_one_or_none()

        if not article_content:
            return ApiResponse(success=False, error="文章内容不存在")

        content = article_content.content

        # 根据格式生成不同长度的摘要
        length_map = {
            "brief": 50,
            "normal": 200,
            "detailed": 500,
            "bullet": 300  # 用于要点式
        }

        max_length = length_map.get(format, 200)

        if format == "bullet":
            # 要点式摘要：提取关键句子
            summary = ai_metadata_service.generate_summary(content, max_length)
            # 将摘要拆分为要点
            sentences = [s.strip() for s in summary.split('。') if s.strip()]
            bullets = [f"• {s}" for s in sentences[:5]]  # 最多5个要点
            summary_text = "\n".join(bullets)
        else:
            summary_text = ai_metadata_service.generate_summary(content, max_length)

        return ApiResponse(
            success=True,
            data={
                "article_id": article_id,
                "title": article.title,
                "summary": summary_text,
                "format": format,
                "length": len(summary_text)
            }
        )
    except Exception as e:
        import traceback
        print(f"Error generating summary: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))


@router.post("/articles/summaries/batch",
             summary="批量生成文章摘要",
             description="为多篇文章批量生成摘要，提高效率",
             response_description="返回批量摘要结果")
async def batch_generate_summaries(
        article_ids: list[int] = Body(..., description="文章ID列表"),
        format: str = Body("normal", description="摘要格式"),
        db: AsyncSession = Depends(get_async_db)
):
    """批量生成文章摘要"""
    try:
        from sqlalchemy import select
        from shared.models.article import Article
        from shared.models.article_content import ArticleContent

        results = []
        errors = []

        for article_id in article_ids:
            try:
                # 查询文章
                query = select(Article).where(Article.id == article_id)
                result = await db.execute(query)
                article = result.scalar_one_or_none()

                if not article:
                    errors.append({"article_id": article_id, "error": "文章不存在"})
                    continue

                # 获取文章内容
                content_query = select(ArticleContent).where(ArticleContent.aid == article_id)
                content_result = await db.execute(content_query)
                article_content = content_result.scalar_one_or_none()

                if not article_content:
                    errors.append({"article_id": article_id, "error": "文章内容不存在"})
                    continue

                # 生成摘要
                length_map = {"brief": 50, "normal": 200, "detailed": 500}
                max_length = length_map.get(format, 200)
                summary = ai_metadata_service.generate_summary(
                    article_content.content,
                    max_length
                )

                results.append({
                    "article_id": article_id,
                    "title": article.title,
                    "summary": summary
                })
            except Exception as e:
                errors.append({"article_id": article_id, "error": str(e)})

        return ApiResponse(
            success=True,
            data={
                "results": results,
                "errors": errors,
                "total": len(article_ids),
                "success_count": len(results),
                "error_count": len(errors)
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in batch summary generation: {str(e)}")
        print(traceback.format_exc())
        return ApiResponse(success=False, error=str(e))
