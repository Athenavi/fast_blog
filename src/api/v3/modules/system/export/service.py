"""数据导出（v3）：真表取数 → CSV 文件 / 预览 JSON

v2 的 ``shared/services/system/data_export_service.py`` 只做「把调用方**已经查好**的
``list[dict]`` 转成 CSV/Excel」——它自己不查库、不做字段映射、不管权限。更关键的是它的
``export_user_list`` / ``export_articles`` / ``export_comments`` 里写死的字段名与**真实表列
大量不符**：

  - ``users`` 表没有 ``last_login`` / ``article_count`` / ``follower_count``
    （真列是 ``last_login_at`` / ``date_joined``）
  - ``articles`` 表没有 ``author_id`` / ``category_id`` / ``view_count`` / ``like_count`` /
    ``comment_count`` / ``updated_at`` 之外的想象列（真列是 ``user`` / ``category`` /
    ``views`` / ``likes``）
  - ``page_views`` 的用户外键列是 ``user``，不是 ``user_id``

照搬 v2 会在真实数据上导出整列空值或直接 ``KeyError``。因此 v3 把「登记表 → 真表查询 →
CSV 生成」三段做全，字段名一律取**真实列名**：

  - :data:`EXPORT_RESOURCES` 是**唯一登记表**：resource → 中文名 / 模型 / 所需权限码 /
    排序 / 时间列 / 搜索列 / 字段（真实列名 + 中文表头）
  - :meth:`ExportService.rows` 用 SQLAlchemy ``select`` 直接从真表取数（支持关键词模糊与
    时间范围），不把全表拉到应用层
  - :func:`to_csv` 是**纯函数**（标准库 ``csv`` + ``io.StringIO``），带 UTF-8 BOM，字段顺序
    与中文表头一一对应
  - :meth:`ExportService.templates` 暴露字段清单，供前端渲染资源 / 字段选择器
  - :meth:`ExportService.preview` 返回前 N 行 JSON，供前端预览

**Excel 导出未实现**：本项目未安装 ``openpyxl``，且约定不为此引入新依赖，故只提供 CSV。
"""

import csv
import io
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional, Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.analytics.page_view import PageView
from shared.models.article.article import Article
from shared.models.category.category import Category
from shared.models.comment.comment import Comment
from shared.models.user import User
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.core.permission import codes

logger = get_logger("system.export")

#: 单次导出上限（防止把整张大表一次性拉进内存）
MAX_EXPORT_ROWS = 10000

#: 预览默认行数
DEFAULT_PREVIEW_ROWS = 20

#: 导出资源登记表（**唯一事实来源**）
#:
#: 每个条目的 ``fields`` 是 ``(真实列名, 中文表头)`` 的元组列表；``columns`` 由它派生，
#: 查询时只 ``select`` 这些真实列。``permission`` 是该资源细粒度查看权限码
#: （导出端点除统一入口权限外，还会按此码再校验一次）。
EXPORT_RESOURCES: dict[str, dict[str, Any]] = {
    "users": {
        "label": "用户",
        "model": User,
        "permission": codes.USER_VIEW,
        "order_by": "id",
        "time_field": "date_joined",
        "search_fields": ("username", "email"),
        "fields": (
            {"key": "id", "label": "ID"},
            {"key": "username", "label": "用户名"},
            {"key": "email", "label": "邮箱"},
            {"key": "is_active", "label": "是否激活"},
            {"key": "is_staff", "label": "是否员工"},
            {"key": "is_superuser", "label": "是否超管"},
            {"key": "vip_level", "label": "VIP 等级"},
            {"key": "date_joined", "label": "注册时间"},
            {"key": "last_login_at", "label": "上次登录时间"},
            {"key": "last_login_ip", "label": "上次登录 IP"},
            {"key": "locale", "label": "语言"},
            {"key": "is_2fa_enabled", "label": "启用双因素"},
        ),
    },
    "articles": {
        "label": "文章",
        "model": Article,
        "permission": codes.ARTICLE_VIEW,
        "order_by": "id",
        "time_field": "created_at",
        "search_fields": ("title", "slug"),
        "fields": (
            {"key": "id", "label": "ID"},
            {"key": "title", "label": "标题"},
            {"key": "slug", "label": "Slug"},
            {"key": "excerpt", "label": "摘要"},
            {"key": "user", "label": "作者 ID"},
            {"key": "category", "label": "分类 ID"},
            {"key": "status", "label": "状态"},
            {"key": "post_type", "label": "内容类型"},
            {"key": "views", "label": "浏览量"},
            {"key": "likes", "label": "点赞数"},
            {"key": "is_featured", "label": "是否推荐"},
            {"key": "is_sticky", "label": "是否置顶"},
            {"key": "hidden", "label": "是否隐藏"},
            {"key": "published_at", "label": "发布时间"},
            {"key": "created_at", "label": "创建时间"},
            {"key": "updated_at", "label": "更新时间"},
        ),
    },
    "comments": {
        "label": "评论",
        "model": Comment,
        "permission": codes.COMMENT_VIEW,
        "order_by": "id",
        "time_field": "created_at",
        "search_fields": ("content", "author_name"),
        "fields": (
            {"key": "id", "label": "ID"},
            {"key": "article_id", "label": "文章 ID"},
            {"key": "user_id", "label": "用户 ID"},
            {"key": "parent_id", "label": "父评论 ID"},
            {"key": "content", "label": "内容"},
            {"key": "author_name", "label": "访客昵称"},
            {"key": "author_email", "label": "访客邮箱"},
            {"key": "author_ip", "label": "访客 IP"},
            {"key": "is_approved", "label": "是否通过"},
            {"key": "likes", "label": "点赞数"},
            {"key": "spam_score", "label": "垃圾评分"},
            {"key": "created_at", "label": "创建时间"},
        ),
    },
    "categories": {
        "label": "分类",
        "model": Category,
        "permission": codes.CATEGORY_VIEW,
        "order_by": "id",
        "time_field": "created_at",
        "search_fields": ("name", "slug"),
        "fields": (
            {"key": "id", "label": "ID"},
            {"key": "name", "label": "分类名"},
            {"key": "slug", "label": "Slug"},
            {"key": "description", "label": "描述"},
            {"key": "parent_id", "label": "父分类 ID"},
            {"key": "sort_order", "label": "排序"},
            {"key": "is_visible", "label": "是否可见"},
            {"key": "articles_count", "label": "文章数"},
            {"key": "created_at", "label": "创建时间"},
            {"key": "updated_at", "label": "更新时间"},
        ),
    },
    "page_views": {
        "label": "页面浏览",
        "model": PageView,
        "permission": codes.REPORT_VIEW,
        "order_by": "id",
        "time_field": "created_at",
        "search_fields": ("page_url", "page_title"),
        "fields": (
            {"key": "id", "label": "ID"},
            {"key": "user", "label": "用户 ID"},
            {"key": "session_id", "label": "会话 ID"},
            {"key": "page_url", "label": "页面 URL"},
            {"key": "page_title", "label": "页面标题"},
            {"key": "referrer", "label": "来源页面"},
            {"key": "ip_address", "label": "IP 地址"},
            {"key": "device_type", "label": "设备类型"},
            {"key": "browser", "label": "浏览器"},
            {"key": "platform", "label": "操作系统"},
            {"key": "country", "label": "国家"},
            {"key": "city", "label": "城市"},
            {"key": "created_at", "label": "访问时间"},
        ),
    },
}


def _resolve_limit(limit: Optional[int]) -> int:
    """校验并归一化导出 / 预览行数上限"""
    if limit is None:
        return MAX_EXPORT_ROWS
    if limit < 1:
        raise BadRequestError("limit 必须 ≥ 1")
    if limit > MAX_EXPORT_ROWS:
        raise BadRequestError(f"单次导出最多 {MAX_EXPORT_ROWS} 行")
    return limit


def _cell(value: Any) -> str:
    """把一个字段值转成 CSV 单元格文本（None→空、bool→是/否、时间→ISO、复合→JSON）"""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def to_csv(
    rows: Sequence[dict[str, Any]],
    fields: Sequence[dict[str, str]],
    *,
    with_bom: bool = True,
) -> bytes:
    """把行数据渲染成 CSV 字节流（**纯函数**，无副作用，便于测试）

    :param rows: 行数据（键为真实列名）
    :param fields: 字段定义，每项 ``{"key": 真实列名, "label": 中文表头}``；**顺序即列顺序**
    :param with_bom: 是否加 UTF-8 BOM（``\\ufeff``）——Excel 靠它正确识别中文
    """
    keys = [field["key"] for field in fields]
    labels = [field["label"] for field in fields]

    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(labels)
    for row in rows:
        writer.writerow([_cell(row.get(key)) for key in keys])

    text = buffer.getvalue()
    if with_bom:
        text = "\ufeff" + text
    return text.encode("utf-8")


class ExportService:
    """数据导出服务：真表取数 + CSV 生成 + 模板 / 预览"""

    def spec(self, resource: str) -> dict[str, Any]:
        """取资源登记，未知资源抛 ``NotFoundError``"""
        spec = EXPORT_RESOURCES.get(resource)
        if spec is None:
            raise NotFoundError(f"未知导出资源：{resource}")
        return spec

    def templates(self) -> dict[str, Any]:
        """每种资源的字段清单（供前端渲染资源 / 字段选择器）"""
        resources = [
            {
                "resource": name,
                "label": spec["label"],
                "permission": spec["permission"],
                "fields": [dict(field) for field in spec["fields"]],
            }
            for name, spec in EXPORT_RESOURCES.items()
        ]
        return {"resources": resources, "count": len(resources)}

    def _apply_filters(self, stmt: Any, spec: dict[str, Any], filters: dict[str, Any]) -> Any:
        """把关键词 / 时间范围过滤施加到 ``select`` 上（只命中真实列）"""
        model = spec["model"]
        keyword = filters.get("keyword")
        if keyword:
            search_fields = spec.get("search_fields") or ()
            pattern = f"%{keyword}%"
            conditions = [getattr(model, column).ilike(pattern) for column in search_fields]
            if conditions:
                stmt = stmt.where(or_(*conditions))

        time_field = spec.get("time_field")
        if time_field:
            column = getattr(model, time_field)
            start = filters.get("start")
            end = filters.get("end")
            if start is not None:
                stmt = stmt.where(column >= start)
            if end is not None:
                stmt = stmt.where(column <= end)
        return stmt

    async def rows(
        self,
        db: AsyncSession,
        resource: str,
        *,
        limit: int = MAX_EXPORT_ROWS,
        offset: int = 0,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """从**真表**取数，返回 ``list[dict]``（键为真实列名）"""
        limit = _resolve_limit(limit)
        if offset < 0:
            raise BadRequestError("offset 不能为负")

        spec = self.spec(resource)
        model = spec["model"]
        columns = [field["key"] for field in spec["fields"]]

        stmt = select(*[getattr(model, column) for column in columns])
        stmt = self._apply_filters(stmt, spec, filters or {})
        stmt = stmt.order_by(getattr(model, spec["order_by"]).desc())
        stmt = stmt.limit(limit).offset(offset)

        result = await db.execute(stmt)
        return [dict(zip(columns, row)) for row in result.all()]

    async def export_csv(
        self,
        db: AsyncSession,
        resource: str,
        *,
        limit: int = MAX_EXPORT_ROWS,
        filters: Optional[dict[str, Any]] = None,
    ) -> tuple[bytes, int]:
        """取数并渲染 CSV，返回 ``(csv_bytes, 行数)``"""
        spec = self.spec(resource)
        data = await self.rows(db, resource, limit=limit, offset=0, filters=filters)
        return to_csv(data, spec["fields"]), len(data)

    async def preview(
        self,
        db: AsyncSession,
        resource: str,
        *,
        limit: int = DEFAULT_PREVIEW_ROWS,
        filters: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """返回前 N 行 JSON（含列定义），供前端预览"""
        spec = self.spec(resource)
        data = await self.rows(db, resource, limit=limit, offset=0, filters=filters)
        return {
            "resource": resource,
            "label": spec["label"],
            "columns": [dict(field) for field in spec["fields"]],
            "rows": data,
            "count": len(data),
        }


# 全局单例
export_service = ExportService()
