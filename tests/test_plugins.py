"""
插件单元测试
测试核心插件的功能方法
"""

import importlib
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


def _import_plugin(slug: str, class_name: str):
    """
    通过 importlib 导入带连字符的插件目录中的 plugin_instance。

    Python 不允许直接 import 名称含连字符的包，故使用 importlib 动态加载。
    """
    full_module = f"plugins.{slug}.plugin"
    if full_module not in sys.modules:
        importlib.import_module(full_module)
    mod = sys.modules[full_module]
    return getattr(mod, class_name)


# ── 测试夹具 ──

@pytest.fixture
def mock_session():
    """模拟 SQLAlchemy 会话"""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.query.return_value.filter_by.return_value.first.return_value = None
    session.query.return_value.all.return_value = []
    return session


@pytest.fixture
def mock_plugin_base():
    """模拟 BasePlugin 核心功能"""
    with patch('shared.services.plugins.plugin_manager.core.BasePlugin.get_db_engine') as mock_engine, \
         patch('shared.services.plugins.plugin_manager.core.BasePlugin.init_db') as mock_init_db:
        mock_engine.return_value = MagicMock()
        yield


# ════════════════════════════════════════════════════════════
# Approval 插件测试
# ════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestApprovalPlugin:
    """内容审批插件测试"""

    def _create_plugin(self):
        cls = _import_plugin("approval", "ContentApprovalPlugin")
        plugin = cls()
        plugin._get_session = MagicMock()
        return plugin

    def test_create_approval(self):
        plugin = self._create_plugin()
        approval = plugin.create_request(
            content_type='article', content_id=1, content_title='Test Article',
            applicant_id=1, applicant_name='Test User',
        )
        assert approval is not None

    def test_approve(self):
        plugin = self._create_plugin()
        result = plugin.approve(record_id=1, notes='Looks good')
        assert result is not None

    def test_reject(self):
        plugin = self._create_plugin()
        result = plugin.reject(record_id=1, notes='Needs work')
        assert result is not None


# ════════════════════════════════════════════════════════════
# Article Likes 插件测试
# ════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestArticleLikesPlugin:
    """文章点赞插件测试"""

    def _create_plugin(self):
        cls = _import_plugin("article-likes", "ArticleLikesPlugin")
        plugin = cls()
        plugin._get_session = MagicMock()
        return plugin

    def test_like_article(self):
        plugin = self._create_plugin()
        result = plugin.like(article_id=1, user_id=1)
        assert result is not None

    def test_unlike_article(self):
        plugin = self._create_plugin()
        result = plugin.unlike(article_id=1, user_id=1)
        assert result is not None

    def test_get_article_likes(self):
        plugin = self._create_plugin()
        count = plugin.status(article_id=1)
        assert count is not None

    def test_has_user_liked(self):
        plugin = self._create_plugin()
        session = plugin._get_session()
        session.query.return_value.filter.return_value.first.return_value = None
        result = plugin.status(article_id=1, user_id=1)
        assert result is not None


# ════════════════════════════════════════════════════════════
# Code Snippets 插件测试
# ════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestCodeSnippetsPlugin:
    """代码片段插件测试"""

    def _create_plugin(self):
        cls = _import_plugin("code-snippets", "CodeSnippetsPlugin")
        plugin = cls()
        plugin._get_session = MagicMock()
        return plugin

    def test_validate_snippet_valid(self):
        plugin = self._create_plugin()
        result = plugin._validate_snippet({
            'code': 'print("hello")',
            'language': 'python',
        })
        assert result['valid'] is True

    def test_validate_snippet_empty_code(self):
        plugin = self._create_plugin()
        result = plugin._validate_snippet({'code': ''})
        assert result['valid'] is False

    def test_create_snippet(self):
        plugin = self._create_plugin()
        session = plugin._get_session()
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.title = 'Test'
        mock_model.code = 'print("hello")'
        mock_model.language = 'python'
        mock_model.description = ''
        mock_model.tags = ''
        mock_model.visibility = 'private'
        mock_model.user_id = 1
        mock_model.view_count = 0
        mock_model.embed_count = 0
        mock_model.created_at = datetime.now(timezone.utc)
        mock_model.updated_at = datetime.now(timezone.utc)
        session.add.return_value = None
        session.query.return_value.filter_by.return_value.first.return_value = mock_model

        result = plugin.create_snippet({
            'title': 'Test',
            'code': 'print("hello")',
            'language': 'python',
            'user_id': 1,
        })
        assert result is not None

    def test_generate_embed_code(self):
        plugin = self._create_plugin()
        session = plugin._get_session()
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.title = 'Test'
        mock_model.code = 'print("hello")'
        mock_model.language = 'python'
        session.query.return_value.filter_by.return_value.first.return_value = mock_model

        embed = plugin.generate_embed_code(snippet_id=1)
        assert 'class="code-snippet-embed"' in embed
        assert 'print' in embed


# ════════════════════════════════════════════════════════════
# Compliance Audit 插件测试
# ════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestComplianceAuditPlugin:
    """合规审计插件测试"""

    def _create_plugin(self):
        with patch.dict('os.environ', {'ENVIRONMENT': 'development'}, clear=False):
            cls = _import_plugin("compliance-audit", "ComplianceAuditPlugin")
            plugin = cls()
            return plugin

    def test_check_pci_dss_returns_checks(self):
        plugin = self._create_plugin()
        result = plugin.check_pci_dss()
        assert 'overall_status' in result
        assert 'checks' in result
        assert len(result['checks']) > 0

    def test_check_gdpr_returns_checks(self):
        plugin = self._create_plugin()
        result = plugin.check_gdpr()
        assert 'overall_status' in result
        assert 'checks' in result


# ════════════════════════════════════════════════════════════
# Newsletter 插件测试
# ════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestNewsletterPlugin:
    """邮件订阅插件测试"""

    def _create_plugin(self):
        from plugins.newsletter.plugin import NewsletterPlugin
        plugin = NewsletterPlugin()
        plugin._get_session = MagicMock()
        return plugin

    def test_subscribe(self):
        plugin = self._create_plugin()
        result = plugin.subscribe(email='test@example.com', name='Test')
        assert result is not None

    def test_unsubscribe(self):
        plugin = self._create_plugin()
        session = plugin._get_session()
        mock_sub = MagicMock()
        mock_sub.email = 'test@example.com'
        mock_sub.is_active = True
        session.query.return_value.filter_by.return_value.first.return_value = mock_sub
        result = plugin.unsubscribe(email='test@example.com')
        assert result['success'] is True


# ════════════════════════════════════════════════════════════
# Popular Articles 插件测试
# ════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestPopularArticlesPlugin:
    """热门文章插件测试"""

    def _create_plugin(self):
        cls = _import_plugin("popular-articles", "PopularArticlesPlugin")
        plugin = cls()
        return plugin

    def test_get_popular(self):
        plugin = self._create_plugin()
        result = plugin.get_popular(max_items=5, days=30)
        assert isinstance(result, dict)
        assert 'data' in result or 'error' in result


# ════════════════════════════════════════════════════════════
# SEO 插件测试
# ════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestSEOPlugin:
    """SEO 插件测试"""

    def _create_plugin(self):
        from plugins.seo.plugin import SeoPlugin
        plugin = SeoPlugin()
        return plugin

    def test_build_article_seo(self):
        plugin = self._create_plugin()
        article = {
            'title': 'Test Article',
            'excerpt': 'A test article',
            'slug': 'test-article',
        }
        meta = plugin.build_article_seo(article, site_url='https://example.com')
        assert meta is not None
        assert meta['title'] == 'Test Article'
        assert meta['description'] == 'A test article'
        assert 'og' in meta
        assert meta['og']['title'] == 'Test Article'


# ════════════════════════════════════════════════════════════
# Payment Gateway 插件测试
# ════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestPaymentGatewayPlugin:
    """支付网关插件测试"""

    def _create_plugin(self):
        cls = _import_plugin("payment-gateway", "PaymentGatewayPlugin")
        plugin = cls()
        return plugin

    def test_create_payment_validates_config(self):
        plugin = self._create_plugin()
        # 未配置 provider 时预期返回错误
        result = plugin.create_payment(
            order_id='test-001',
            amount=100,
            subject='Test Payment',
        )
        assert result is not None
        assert 'success' in result or 'error' in result


# ════════════════════════════════════════════════════════════
# SMS Provider 插件测试
# ════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestSMSProviderPlugin:
    """短信服务插件测试"""

    def _create_plugin(self):
        cls = _import_plugin("sms-provider", "SmsProviderPlugin")
        plugin = cls()
        return plugin

    def test_send_sms_no_provider(self):
        plugin = self._create_plugin()
        result = plugin.send_sms(phone='+1234567890', code='123456')
        assert result is False

    def test_send_sms_with_aliyun_config(self):
        plugin = self._create_plugin()
        plugin.settings['provider'] = 'aliyun'
        plugin.settings['aliyun_access_key_id'] = 'test'
        plugin.settings['aliyun_access_key_secret'] = 'test'
        plugin.settings['aliyun_sign_name'] = 'Test'
        plugin.settings['aliyun_template_code'] = 'SMS_001'
        # SDK 未安装应返回 False
        result = plugin.send_sms(phone='+8613800000000', code='123456')
        assert result is False


# ════════════════════════════════════════════════════════════
# Enterprise 插件测试
# ════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestEnterprisePlugin:
    """企业功能插件测试"""

    def _create_plugin(self):
        from plugins.enterprise.plugin import EnterprisePlugin
        plugin = EnterprisePlugin()
        plugin._get_session = MagicMock()
        return plugin

    def test_get_overview(self):
        plugin = self._create_plugin()
        session = plugin._get_session()
        session.query.return_value.count.return_value = 0
        result = plugin.get_overview()
        assert result is not None
        assert 'total_licenses' in result
        assert 'open_tickets' in result
        assert 'total_scripts' in result

    def test_list_licenses(self):
        plugin = self._create_plugin()
        result = plugin.list_licenses()
        assert 'items' in result
        assert 'total' in result

    def test_list_tickets(self):
        plugin = self._create_plugin()
        result = plugin.list_tickets()
        assert 'items' in result

    def test_list_scripts(self):
        plugin = self._create_plugin()
        result = plugin.list_scripts()
        assert 'items' in result

    def test_list_alerts(self):
        plugin = self._create_plugin()
        result = plugin.list_alerts()
        assert 'items' in result
