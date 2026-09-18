"""V3 通用 CRUD 基类

结构对齐 FastApiAdmin `app/core/base_crud.py`：把「按主键取 / 条件查 / 存在性 / 计数 / 分页列表 /
建 / 改 / 删」收敛到一个泛型基类，让每个模块的 ``crud.py`` 只声明模型与少量元信息。

实现层适配 fast_blog（与 FastApiAdmin 的差异）：
  - 会话是 ``AsyncSession``（来自 ``src/utils/database/unified_manager.get_db_session``），
    因此所有方法都是 ``async``，且不持有会话
  - 模型基类是 ``shared.models.Base``（``shared/models/__init__.py:12``）
  - 软删除、关键词搜索字段由子类按模型实际情况声明，默认关闭
"""

from typing import Any, Generic, Iterable, Mapping, Optional, Sequence, TypeVar

from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """通用 CRUD 基类

    子类只需声明::

        class ArticleCRUD(CRUDBase[Article, ArticleCreate, ArticleUpdate]):
            model = Article
            keyword_fields = ("title", "summary")
            default_order_by = "created_at"
            soft_delete_field = "is_deleted"   # 该模型确实有软删除字段时才声明
    """

    #: 绑定的 SQLAlchemy 模型
    model: type[ModelType]
    #: 关键词模糊搜索覆盖的字段（为空时 keyword 参数不生效）
    keyword_fields: tuple[str, ...] = ()
    #: 默认排序字段（不存在时回退主键）
    default_order_by: str = "id"
    #: 软删除字段名；None 表示不做软删除过滤（物理删除）
    soft_delete_field: Optional[str] = None
    #: 软删除字段取何值代表「已删除」
    soft_delete_value: Any = True

    def __init__(self, model: Optional[type[ModelType]] = None) -> None:
        if model is not None:
            self.model = model

    # ------------------------------------------------------------------ 元信息
    @property
    def columns(self) -> set[str]:
        """模型列名集合（用于过滤查询与排序字段，防止注入非法列名）"""
        return {col.key for col in self.model.__table__.columns}

    @property
    def primary_key(self) -> str:
        return next(iter(self.model.__table__.primary_key.columns.keys()))

    @property
    def soft_delete_enabled(self) -> bool:
        return bool(self.soft_delete_field) and self.soft_delete_field in self.columns

    # ------------------------------------------------------------------ 内部构造
    def _apply_soft_delete(self, stmt: Select) -> Select:
        if self.soft_delete_enabled:
            column = getattr(self.model, self.soft_delete_field)
            return stmt.where(column != self.soft_delete_value)
        return stmt

    def _apply_filters(self, stmt: Select, filters: Optional[Mapping[str, Any]]) -> Select:
        """按「列名 -> 值」过滤；值为 None 的条件忽略，非法列名直接忽略（不抛错、不注入）"""
        if not filters:
            return stmt
        valid = self.columns
        for key, value in filters.items():
            if value is None or key not in valid:
                continue
            if isinstance(value, (list, tuple, set)):
                stmt = stmt.where(getattr(self.model, key).in_(list(value)))
            else:
                stmt = stmt.where(getattr(self.model, key) == value)
        return stmt

    def _apply_keyword(self, stmt: Select, keyword: Optional[str]) -> Select:
        if not keyword or not self.keyword_fields:
            return stmt
        valid = self.columns
        clauses = [
            getattr(self.model, field).ilike(f"%{keyword}%")
            for field in self.keyword_fields
            if field in valid
        ]
        if not clauses:
            return stmt
        from sqlalchemy import or_

        return stmt.where(or_(*clauses))

    def _apply_order(self, stmt: Select, order_by: Optional[str], order: str) -> Select:
        """排序字段白名单：只允许模型真实列名，非法值回退默认字段"""
        valid = self.columns
        field = order_by if order_by in valid else None
        if field is None:
            field = self.default_order_by if self.default_order_by in valid else self.primary_key
        column = getattr(self.model, field)
        return stmt.order_by(column.asc() if order == "asc" else column.desc())

    def _build_query(
        self,
        filters: Optional[Mapping[str, Any]] = None,
        keyword: Optional[str] = None,
    ) -> Select:
        stmt = select(self.model)
        stmt = self._apply_soft_delete(stmt)
        stmt = self._apply_filters(stmt, filters)
        stmt = self._apply_keyword(stmt, keyword)
        return stmt

    # ------------------------------------------------------------------ 读
    async def get(self, db: AsyncSession, pk: Any) -> Optional[ModelType]:
        """按主键取单条（软删除记录视为不存在）"""
        stmt = self._apply_soft_delete(select(self.model).where(getattr(self.model, self.primary_key) == pk))
        return (await db.execute(stmt)).scalars().first()

    async def get_by(self, db: AsyncSession, **filters: Any) -> Optional[ModelType]:
        """按字段取单条"""
        stmt = self._build_query(filters)
        return (await db.execute(stmt)).scalars().first()

    async def exists(self, db: AsyncSession, **filters: Any) -> bool:
        """是否存在满足条件的记录"""
        return await self.count(db, **filters) > 0

    async def count(self, db: AsyncSession, **filters: Any) -> int:
        """计数（支持 keyword，与 list 的过滤条件保持一致）"""
        keyword = filters.pop("keyword", None)
        stmt = select(func.count()).select_from(self.model)
        stmt = self._apply_soft_delete(stmt)
        stmt = self._apply_filters(stmt, filters)
        stmt = self._apply_keyword(stmt, keyword)
        return int((await db.execute(stmt)).scalar() or 0)

    async def list(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[Mapping[str, Any]] = None,
        keyword: Optional[str] = None,
        order_by: Optional[str] = None,
        order: str = "desc",
        options: Optional[Sequence[Any]] = None,
    ) -> tuple[list[ModelType], int]:
        """分页列表，返回 ``(items, total)``

        ``options`` 用于传 ``selectinload`` 等加载策略；``page_size <= 0`` 表示不分页。
        """
        total = await self.count(db, keyword=keyword, **(dict(filters) if filters else {}))
        stmt = self._build_query(filters, keyword)
        stmt = self._apply_order(stmt, order_by, order)
        if options:
            stmt = stmt.options(*options)
        if page_size > 0:
            stmt = stmt.offset(max(page - 1, 0) * page_size).limit(page_size)
        rows = (await db.execute(stmt)).scalars().unique().all()
        return list(rows), total

    # ------------------------------------------------------------------ 写
    @staticmethod
    def _to_dict(obj_in: Any) -> dict:
        if isinstance(obj_in, BaseModel):
            return obj_in.model_dump(exclude_unset=True)
        return dict(obj_in or {})

    async def create(self, db: AsyncSession, obj_in: Any) -> ModelType:
        """新建并提交，返回带主键的实例"""
        obj = self.model(**self._to_dict(obj_in))
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    async def update(self, db: AsyncSession, db_obj: ModelType, obj_in: Any) -> ModelType:
        """按传入字段局部更新并提交"""
        for key, value in self._to_dict(obj_in).items():
            if hasattr(db_obj, key):
                setattr(db_obj, key, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, db_obj: ModelType) -> None:
        """删除：模型声明了软删除字段则打标记，否则物理删除"""
        if self.soft_delete_enabled:
            setattr(db_obj, self.soft_delete_field, self.soft_delete_value)
            db.add(db_obj)
        else:
            await db.delete(db_obj)
        await db.commit()

    async def remove_by_id(self, db: AsyncSession, pk: Any) -> bool:
        """按主键删除，返回是否命中"""
        obj = await self.get(db, pk)
        if obj is None:
            return False
        await self.remove(db, obj)
        return True

    async def bulk_remove(self, db: AsyncSession, ids: Iterable[Any]) -> int:
        """批量删除，返回实际处理条数"""
        count = 0
        for pk in list(ids):
            if await self.remove_by_id(db, pk):
                count += 1
        return count
