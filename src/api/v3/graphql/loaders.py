"""DataLoader：批量加载，消除 GraphQL 嵌套字段的 N+1。

目前接在 ``Article.category`` 上：一页 N 篇文章只发**一次** IN 查询，
而不是 N 次单条查询 —— 项目在 REST 侧已经吃过 N+1 的亏（见 P2 那批优化），
这里从一开始就按批加载。
"""

from typing import Any, List, Optional

from sqlalchemy import select
from strawberry.dataloader import DataLoader


async def _load_categories(db: Any, keys: List[int]) -> List[Optional[dict]]:
    """一次 IN 查询加载全部分类，再按请求顺序对齐（DataLoader 约定）。"""
    from shared.models import Category as CategoryModel

    rows = (
        await db.execute(select(CategoryModel).where(CategoryModel.id.in_(keys)))
    ).scalars().all()
    by_id = {int(getattr(row, "id", 0)): row for row in rows}

    out: List[Optional[dict]] = []
    for key in keys:
        row = by_id.get(int(key))
        if row is None:
            out.append(None)
        else:
            out.append(
                {
                    "id": int(getattr(row, "id", 0) or 0),
                    "name": str(getattr(row, "name", "") or ""),
                    "slug": getattr(row, "slug", None),
                    "parent_id": getattr(row, "parent", None),
                }
            )
    return out


class CategoryLoader(DataLoader):
    """分类批量加载器（每个请求一个实例）"""

    def __init__(self, db: Any) -> None:
        super().__init__(load_fn=lambda keys: _load_categories(db, list(keys)))


async def load_category(context: Any, category_id: int) -> Optional[dict]:
    """从上下文取 loader 并加载；上下文未挂载 loader 时返回 None（不抛）。"""
    loader = getattr(context, "category_loader", None)
    if loader is None:
        return None
    return await loader.load(int(category_id))
