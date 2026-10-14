"""多租户站点上下文与隔离判定的回归测试

核心回归点：**默认收窄**。只要"模型有 site_id 列 + 上下文有站点 + 未显式跨站点"，
读路径就必须带过滤；三者缺一才放行。
"""
import pytest

from src.api.v3.core import tenancy


def _fake_model(table: str, columns=("id", "site_id")):
    """构造一个满足 is_site_scoped_model 探测接口的假模型（不注册进 metadata）"""

    class _Table:
        pass

    class _Model:
        __tablename__ = table

    _Model.__table__ = _Table()
    _Table.columns = tuple(type("_Column", (), {"key": name})() for name in columns)
    return _Model


@pytest.fixture(autouse=True)
def _clean_context():
    """每个用例前后都把站点上下文置空

    ``ContextVar`` 在测试进程内是**跨用例共享**的：用例里 set 过而没 reset 时，
    下一个用例会继承残留值。用 assert 去验证"进来时是干净的"会过于脆弱，
    直接强制置空即可。
    """
    tenancy.set_current_site(None)
    yield
    tenancy.set_current_site(None)


class TestScopedModelDetection:
    def test_model_with_site_id_is_scoped(self):
        assert tenancy.is_site_scoped_model(_fake_model("articles")) is True

    def test_model_without_site_id_is_not_scoped(self):
        assert tenancy.is_site_scoped_model(_fake_model("users", columns=("id",))) is False

    def test_global_tables_are_never_scoped(self):
        assert tenancy.is_site_scoped_model(_fake_model("audit_logs")) is False
        assert tenancy.is_site_scoped_model(_fake_model("system_settings")) is False

    def test_model_without_table_is_not_scoped(self):
        class _Bare:
            pass

        assert tenancy.is_site_scoped_model(_Bare) is False


class TestSiteFilterValue:
    def test_no_context_means_no_filter(self):
        """后台任务 / CLI 没有请求上下文 → 不放过滤条件（否则什么都看不到）"""
        assert tenancy.site_filter_value(_fake_model("articles")) is None

    def test_context_site_filters_scoped_model(self):
        tenancy.set_current_site(7)
        assert tenancy.site_filter_value(_fake_model("articles")) == 7

    def test_context_site_does_not_filter_unscoped_model(self):
        tenancy.set_current_site(7)
        assert tenancy.site_filter_value(_fake_model("users", columns=("id",))) is None

    def test_bypass_disables_filtering(self):
        tenancy.set_current_site(7, bypass=True)
        assert tenancy.is_site_scope_bypassed() is True
        assert tenancy.site_filter_value(_fake_model("articles")) is None


class TestContextLifecycle:
    def test_reset_restores_previous_state(self):
        tenancy.set_current_site(1)
        tokens = tenancy.set_current_site(2)
        assert tenancy.get_current_site_id() == 2
        tenancy.reset_current_site(tokens)
        assert tenancy.get_current_site_id() == 1

    def test_bypass_does_not_leak_after_reset(self):
        tokens = tenancy.set_current_site(1, bypass=True)
        tenancy.reset_current_site(tokens)
        assert tenancy.is_site_scope_bypassed() is False
        assert tenancy.get_current_site_id() is None
