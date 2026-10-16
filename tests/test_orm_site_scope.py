"""ORM 级租户隔离兜底的回归测试

覆盖 `install_orm_site_scope` 所用到的纯函数 `apply_site_scope_to_statement`：
它决定"这次查询要不要按站点收窄"。这里不需要数据库 —— 只断言语句上是否挂上了
`with_loader_criteria`（真正展开成 SQL 的 WHERE 由 SQLAlchemy 负责）。
"""
import pytest
from sqlalchemy import select
from sqlalchemy.orm import LoaderCriteriaOption

from shared.models.article.article import Article
from shared.models.system.audit_log import AuditLog
from src.api.v3.core import tenancy


def _criteria_count(stmt) -> int:
    return sum(1 for opt in stmt._with_options if isinstance(opt, LoaderCriteriaOption))


class TestStatementScoping:
    def test_without_site_context_nothing_is_added(self):
        """后台任务 / CLI 没有站点上下文 → 必须完全不介入"""
        tenancy.set_current_site(None)
        assert _criteria_count(tenancy.apply_site_scope_to_statement(select(Article))) == 0

    def test_with_site_context_adds_loader_criteria(self):
        tenancy.set_current_site(7)
        assert _criteria_count(tenancy.apply_site_scope_to_statement(select(Article))) == 1

    def test_bypass_skips_scoping(self):
        tenancy.set_current_site(7, bypass=True)
        assert _criteria_count(tenancy.apply_site_scope_to_statement(select(Article))) == 0

    def test_global_table_is_never_scoped(self):
        """audit_logs 属跨站点治理数据（GLOBAL_TABLES），不应被收窄"""
        tenancy.set_current_site(7)
        assert _criteria_count(tenancy.apply_site_scope_to_statement(select(AuditLog))) == 0

    def test_multiple_scoped_entities_all_get_criteria(self):
        from shared.models.category.category import Category

        tenancy.set_current_site(3)
        stmt = select(Article, Category)
        assert _criteria_count(tenancy.apply_site_scope_to_statement(stmt)) == 2


@pytest.fixture(autouse=True)
def _clean_site_context():
    """每条用例前后清空站点上下文，避免 ContextVar 跨用例残留"""
    tenancy.set_current_site(None)
    yield
    tenancy.set_current_site(None)


class TestInstall:
    def test_install_is_idempotent(self):
        """重复安装不应重复注册事件（否则条件会被叠加）"""
        assert tenancy.install_orm_site_scope() is True
        assert tenancy.install_orm_site_scope() is False


def test_event_actually_filters_rows_end_to_end():
    """端到端：装上事件后，数据库里**别的站点**的行确实查不出来

    前面的用例只能证明"语句被挂上了 criteria"；这里用一个独立的 SQLite 临时表真正
    执行一次查询，证明事件在 SQL 层生效 —— 用的是全局 ``Session`` 类，与项目里
    ``async_sessionmaker`` 产出的会话同一套事件机制。
    """
    from sqlalchemy import BigInteger, Column, String, create_engine
    from sqlalchemy import select as sa_select
    from sqlalchemy.orm import DeclarativeBase, sessionmaker

    tenancy.install_orm_site_scope()

    class _ProbeBase(DeclarativeBase):
        pass

    class _Widget(_ProbeBase):
        __tablename__ = "orm_scope_probe"
        id = Column(BigInteger, primary_key=True)
        site_id = Column(BigInteger)
        name = Column(String(50))

    engine = create_engine("sqlite://")
    _ProbeBase.metadata.create_all(engine)
    session_factory = sessionmaker(engine)

    with session_factory() as session:
        session.add_all([
            _Widget(id=1, site_id=1, name="site-1"),
            _Widget(id=2, site_id=2, name="site-2"),
        ])
        session.commit()

    # 有站点上下文：只应看到本站数据
    tenancy.set_current_site(1)
    with session_factory() as session:
        visible = [row.name for row in session.execute(sa_select(_Widget)).scalars().all()]
    assert visible == ["site-1"]

    # 没有站点上下文（等价于后台任务 / CLI）：不应被收窄
    tenancy.set_current_site(None)
    with session_factory() as session:
        visible = [row.name for row in session.execute(sa_select(_Widget)).scalars().all()]
    assert sorted(visible) == ["site-1", "site-2"]
