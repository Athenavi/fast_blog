"""
批量 SEO 管理 API
提供批量更新文章SEO元数据的功能
"""
from datetime import datetime
from functools import wraps
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User
from shared.models.article import Article, ArticleSEO
from src.api.v2._helpers import ok, fail, _catch
from src.auth import jwt_required_dependency as jwt_required
from src.extensions import get_async_db_session as get_async_db

router = APIRouter(tags=["batch-seo"])


class BatchSEOUpdateRequest(BaseModel):
    """批量SEO更新请求"""
    article_ids: List[int]
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    seo_keywords: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    canonical_url: Optional[str] = None
    robots_meta: Optional[str] = None
    schema_org_enabled: Optional[bool] = None
    schema_org_type: Optional[str] = None


class BatchSEOExportRequest(BaseModel):
    """批量SEO导出请求"""
    article_ids: Optional[List[int]] = None
    category_id: Optional[int] = None
    status: Optional[str] = None


@router.post("/update", summary="批量更新文章SEO")
@_catch
async def batch_update_seo(
        request: BatchSEOUpdateRequest,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(jwt_required)
):
    """批量更新多个文章的SEO元数据"""
    if not request.article_ids:
        raise HTTPException(status_code=400, detail="文章ID列表不能为空")

    stmt = select(Article).where(Article.id.in_(request.article_ids))
    result = await db.execute(stmt)
    articles = result.scalars().all()

    if len(articles) != len(request.article_ids):
        raise HTTPException(
            status_code=404,
            detail=f"部分文章不存在，找到{len(articles)}个，请求{len(request.article_ids)}个"
        )

    updated_count = 0
    now = datetime.now()

    for article in articles:
        stmt = select(ArticleSEO).where(ArticleSEO.article_id == article.id)
        result = await db.execute(stmt)
        seo = result.scalar_one_or_none()

        if seo:
            if request.seo_title is not None:
                seo.seo_title = request.seo_title
            if request.seo_description is not None:
                seo.seo_description = request.seo_description
            if request.seo_keywords is not None:
                seo.seo_keywords = request.seo_keywords
            if request.og_title is not None:
                seo.og_title = request.og_title
            if request.og_description is not None:
                seo.og_description = request.og_description
            if request.og_image is not None:
                seo.og_image = request.og_image
            if request.canonical_url is not None:
                seo.canonical_url = request.canonical_url
            if request.robots_meta is not None:
                seo.robots_meta = request.robots_meta
            if request.schema_org_enabled is not None:
                seo.schema_org_enabled = request.schema_org_enabled
            if request.schema_org_type is not None:
                seo.schema_org_type = request.schema_org_type
            seo.updated_at = now
        else:
            seo = ArticleSEO(
                article_id=article.id,
                seo_title=request.seo_title,
                seo_description=request.seo_description,
                seo_keywords=request.seo_keywords,
                og_title=request.og_title,
                og_description=request.og_description,
                og_image=request.og_image,
                canonical_url=request.canonical_url,
                robots_meta=request.robots_meta or "index,follow",
                schema_org_enabled=request.schema_org_enabled if request.schema_org_enabled is not None else True,
                schema_org_type=request.schema_org_type or "BlogPosting",
                created_at=now,
                updated_at=now,
            )
            db.add(seo)
        updated_count += 1

    await db.commit()
    return ok(data={"updated_count": updated_count, "total_requested": len(request.article_ids)},
              message=f"成功更新{updated_count}个文章的SEO元数据")


@router.post("/export", summary="批量导出SEO数据")
@_catch
async def batch_export_seo(
        request: BatchSEOExportRequest,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(jwt_required)
):
    """批量导出文章SEO数据为CSV格式"""
    stmt = select(Article, ArticleSEO).outerjoin(
        ArticleSEO, Article.id == ArticleSEO.article_id
    )

    if request.article_ids:
        stmt = stmt.where(Article.id.in_(request.article_ids))
    if request.category_id:
        stmt = stmt.where(Article.category == request.category_id)
    if request.status:
        status_map = {'published': 1, 'draft': 0, 'deleted': -1}
        if request.status in status_map:
            stmt = stmt.where(Article.status == status_map[request.status])

    result = await db.execute(stmt)
    rows = result.all()

    csv_lines = [
        "article_id,title,slug,seo_title,seo_description,seo_keywords,og_title,og_description,og_image,canonical_url,robots_meta,status,created_at"
    ]

    for article, seo in rows:
        def escape_csv(value):
            if value is None:
                return ""
            value = str(value).replace('"', '""')
            return f'"{value}"'

        line = ",".join([
            escape_csv(article.id), escape_csv(article.title), escape_csv(article.slug),
            escape_csv(seo.seo_title if seo else None),
            escape_csv(seo.seo_description if seo else None),
            escape_csv(seo.seo_keywords if seo else None),
            escape_csv(seo.og_title if seo else None),
            escape_csv(seo.og_description if seo else None),
            escape_csv(seo.og_image if seo else None),
            escape_csv(seo.canonical_url if seo else None),
            escape_csv(seo.robots_meta if seo else "index,follow"),
            escape_csv(article.status),
            escape_csv(article.created_at.isoformat() if article.created_at else None),
        ])
        csv_lines.append(line)

    csv_content = "\n".join(csv_lines)
    return ok(data={
        "count": len(rows),
        "csv_content": csv_content,
        "filename": f"seo_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    }, message=f"成功导出{len(rows)}个文章的SEO数据")


@router.post("/import", summary="批量导入SEO数据")
@_catch
async def batch_import_seo(
        csv_content: str,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(jwt_required)
):
    """从CSV内容批量导入SEO数据"""
    lines = csv_content.strip().split('\n')
    if len(lines) < 2:
        raise HTTPException(status_code=400, detail="CSV内容为空或格式不正确")

    headers = [h.strip().strip('"').lower() for h in lines[0].split(',')]
    if 'article_id' not in headers:
        raise HTTPException(status_code=400, detail="CSV必须包含article_id列")

    imported_count = 0
    error_count = 0
    errors = []
    now = datetime.now()

    for i, line in enumerate(lines[1:], start=2):
        try:
            values = [v.strip().strip('"') for v in line.split(',')]
            if len(values) != len(headers):
                errors.append(f"第{i}行：列数不匹配")
                error_count += 1
                continue

            row_dict = dict(zip(headers, values))
            article_id = int(row_dict.get('article_id', 0))
            if not article_id:
                errors.append(f"第{i}行：article_id无效")
                error_count += 1
                continue

            stmt = select(Article).where(Article.id == article_id)
            result = await db.execute(stmt)
            article = result.scalar_one_or_none()
            if not article:
                errors.append(f"第{i}行：文章ID {article_id} 不存在")
                error_count += 1
                continue

            stmt = select(ArticleSEO).where(ArticleSEO.article_id == article_id)
            result = await db.execute(stmt)
            seo = result.scalar_one_or_none()

            if seo:
                if 'seo_title' in row_dict and row_dict['seo_title']:
                    seo.seo_title = row_dict['seo_title']
                if 'seo_description' in row_dict and row_dict['seo_description']:
                    seo.seo_description = row_dict['seo_description']
                if 'seo_keywords' in row_dict and row_dict['seo_keywords']:
                    seo.seo_keywords = row_dict['seo_keywords']
                if 'og_title' in row_dict and row_dict['og_title']:
                    seo.og_title = row_dict['og_title']
                if 'og_description' in row_dict and row_dict['og_description']:
                    seo.og_description = row_dict['og_description']
                if 'og_image' in row_dict and row_dict['og_image']:
                    seo.og_image = row_dict['og_image']
                if 'canonical_url' in row_dict and row_dict['canonical_url']:
                    seo.canonical_url = row_dict['canonical_url']
                if 'robots_meta' in row_dict and row_dict['robots_meta']:
                    seo.robots_meta = row_dict['robots_meta']
                seo.updated_at = now
            else:
                seo = ArticleSEO(
                    article_id=article_id,
                    seo_title=row_dict.get('seo_title'),
                    seo_description=row_dict.get('seo_description'),
                    seo_keywords=row_dict.get('seo_keywords'),
                    og_title=row_dict.get('og_title'),
                    og_description=row_dict.get('og_description'),
                    og_image=row_dict.get('og_image'),
                    canonical_url=row_dict.get('canonical_url'),
                    robots_meta=row_dict.get('robots_meta', 'index,follow'),
                    created_at=now, updated_at=now,
                )
                db.add(seo)
            imported_count += 1
        except Exception as e:
            errors.append(f"第{i}行：{str(e)}")
            error_count += 1

    await db.commit()
    return ok(data={
        "imported_count": imported_count,
        "error_count": error_count,
        "errors": errors[:10]
    }, message=f"导入完成：成功{imported_count}个，失败{error_count}个")


@router.get("/stats", summary="获取SEO统计信息")
@_catch
async def get_seo_stats(
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(jwt_required)
):
    """获取SEO数据统计信息"""
    stmt = select(func.count(Article.id))
    result = await db.execute(stmt)
    total_articles = result.scalar() or 0

    stmt = select(func.count(ArticleSEO.id))
    result = await db.execute(stmt)
    articles_with_seo = result.scalar() or 0

    stmt = select(func.count(ArticleSEO.id)).where(
        (ArticleSEO.seo_title.is_(None)) | (ArticleSEO.seo_title == '')
    )
    result = await db.execute(stmt)
    missing_title = result.scalar() or 0

    stmt = select(func.count(ArticleSEO.id)).where(
        (ArticleSEO.seo_description.is_(None)) | (ArticleSEO.seo_description == '')
    )
    result = await db.execute(stmt)
    missing_description = result.scalar() or 0

    coverage_rate = (articles_with_seo / total_articles * 100) if total_articles > 0 else 0

    return ok(data={
        "total_articles": total_articles,
        "articles_with_seo": articles_with_seo,
        "coverage_rate": round(coverage_rate, 2),
        "missing_title": missing_title,
        "missing_description": missing_description,
        "optimization_score": round(
            ((articles_with_seo - missing_title - missing_description) / total_articles * 100)
            if total_articles > 0 else 0, 2
        )
    })
