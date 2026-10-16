"""权限数据范围（用户组范围 / 写路径范围）

由同域多个测试文件合并（断言与注释原样保留，仅重排文件组织）。
"""

import inspect
import pytest
from fastapi import FastAPI
from sqlalchemy import select
from src.api.v3 import register_v3_routes
from src.api.v3.core.exceptions import ForbiddenError
from src.api.v3.core.permission import codes
from src.api.v3.core.permission.constants import (
    DATA_SCOPE_ALL,
    DATA_SCOPE_GROUP_AND_CHILD,
    DATA_SCOPE_SELF,
)
from src.api.v3.core.permission.constants import DATA_SCOPE_SELF
from src.api.v3.core.permission.scope import (
    _normalize_scopes,
    apply_data_scope,
    owner_field_of,
    register_data_scoped_models,
)
from src.api.v3.core.permission.scope import (
    ensure_write_in_scope,
    owner_field_of,
    register_data_scoped_models,
)
from src.api.v3.modules.content.article.service import article_service
from src.api.v3.modules.content.comment.service import comment_service
from src.api.v3.modules.content.media.service import media_service
from src.api.v3.modules.content.page.service import page_service

# ============================================================ 来自 test_v3_group_scope.py（6 项）
EXPECTED_GROUP_PATHS = {
    "/api/v3/system/group",
    "/api/v3/system/group/list",
    "/api/v3/system/group/tree",
    "/api/v3/system/group/create",
    "/api/v3/system/group/delete",
    "/api/v3/system/group/{group_id}",
    "/api/v3/system/group/detail/{group_id}",
    "/api/v3/system/group/update/{group_id}",
    "/api/v3/system/group/{group_id}/members",
    "/api/v3/system/group/{group_id}/members/{user_id}",
    "/api/v3/system/group/{group_id}/roles",
}


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


class FakeUser:
    def __init__(self, user_id: int = 1, is_superuser: bool = False) -> None:
        self.id = user_id
        self.is_superuser = is_superuser


# ------------------------------------------------------------------ 路由与权限


# ------------------------------------------------------------------ 权限码常量
def test_group_codes_are_non_empty_and_colon_separated():
    """权限码常量必须与 capabilities.code 同构（两段冒号，不做任何转换）"""
    for name in (
            "GROUP_VIEW",
            "GROUP_CREATE",
            "GROUP_EDIT",
            "GROUP_DELETE",
            "GROUP_MANAGE_MEMBERS",
            "GROUP_MANAGE_ROLES",
    ):
        code = getattr(codes, name)
        assert isinstance(code, str) and code
        assert ":" in code
        assert "." not in code


# ------------------------------------------------------------------ 数据范围
def test_data_scoped_models_registry():
    """登记表必须显式列出参与数据范围过滤的模型与归属字段"""
    registry = register_data_scoped_models()
    names = {model.__name__: field for model, field in registry.items()}
    # 核心内容模型（P2 起就在表内）
    assert {
               name: names.get(name)
               for name in ("Article", "Comment", "Media", "Pages")
           } == {
               "Article": "user",
               "Comment": "user_id",
               "Media": "user",
               "Pages": "author_id",
           }
    # 扩容后仍必须留在表外：审计日志与 RBAC 内部表（过滤它们会自锁或丢审计）
    assert names.keys().isdisjoint(
        {"AuditLog", "PermissionAuditLog", "PermissionGroup", "UserGroupMember", "UserRole"}
    )


def test_owner_field_of_unregistered_model():
    from shared.models.rbac.capability import Capability

    assert owner_field_of(Capability) is None


def test_normalize_scopes_treats_null_as_self():
    """data_scope 为 NULL（模型侧可空）时必须按"仅本人"处理"""
    assert _normalize_scopes({None}) == {DATA_SCOPE_SELF}
    assert _normalize_scopes({None, 3}) == {3, DATA_SCOPE_SELF}
    assert _normalize_scopes(set()) == {DATA_SCOPE_SELF}


@pytest.mark.asyncio
async def test_apply_data_scope_skips_unregistered_model():
    """未登记的模型明确不做数据级过滤（db=None 也不会被触碰）"""
    from shared.models.rbac.capability import Capability

    stmt = select(Capability)
    result = await apply_data_scope(stmt, Capability, db=None, user=FakeUser())  # type: ignore[arg-type]

    assert result is stmt


@pytest.mark.asyncio
async def test_apply_data_scope_superuser_skips():
    """超级管理员不追加范围条件（同样在触碰 db 之前返回）"""
    from shared.models.article.article import Article

    stmt = select(Article)
    result = await apply_data_scope(stmt, Article, db=None, user=FakeUser(is_superuser=True))  # type: ignore[arg-type]

    assert result is stmt


# ============================================================ 来自 test_v3_write_scope.py（12 项）
#: 四个核心内容模型的"操作他人数据"权限码
OTHERS_CODES: dict[str, tuple[str, ...]] = {
    "article": (codes.ARTICLE_EDIT_OTHERS, codes.ARTICLE_DELETE_OTHERS),
    "page": (codes.PAGE_EDIT_OTHERS, codes.PAGE_DELETE_OTHERS),
    "media": (codes.MEDIA_EDIT_OTHERS, codes.MEDIA_DELETE_OTHERS),
    "comment": (
        codes.COMMENT_APPROVE_OTHERS,
        codes.COMMENT_EDIT_OTHERS,
        codes.COMMENT_DELETE_OTHERS,
    ),
}

#: 写方法必须接受 ``scope_user``（否则管理端调用会漏掉范围校验）
WRITE_METHODS: list[tuple[object, tuple[str, ...]]] = [
    (
        article_service,
        (
            "update_article",
            "delete_article",
            "batch_delete",
            "batch_set_published",
            "set_published",
            "reorder",
        ),
    ),
    (
        comment_service,
        (
            "set_approved",
            "update_comment",
            "delete_comment",
            "batch_delete",
            "batch_set_approved",
            "reply_comment",
        ),
    ),
    (media_service, ("update_media", "delete_media", "batch_delete", "batch_update")),
    (page_service, ("update_page", "delete_page", "batch_delete", "set_published")),
]


class FakeUser__write_scope:
    def __init__(self, user_id: int = 1, is_superuser: bool = False) -> None:
        self.id = user_id
        self.is_superuser = is_superuser


class FakeRow:
    """带任意归属字段的轻量记录"""

    def __init__(self, **fields: object) -> None:
        self.__dict__.update(fields)


# ------------------------------------------------------------------ 权限码
def test_others_codes_are_three_segment_and_labelled():
    for model, code_list in OTHERS_CODES.items():
        assert code_list, model
        for code in code_list:
            parts = code.split(":")
            assert len(parts) == 3, code
            assert parts[0] == "module_content", code
            assert parts[-1].endswith("_others"), code
            # 码与中文标签必须成对，否则 seed_rbac 的 capabilities 同步会漏项
            assert code in codes.CODE_LABELS, code


# ------------------------------------------------------------------ 登记表
def test_registry_keeps_core_models():
    names = {model.__name__: field for model, field in register_data_scoped_models().items()}
    assert names["Article"] == "user"
    assert names["Comment"] == "user_id"
    assert names["Media"] == "user"
    assert names["Pages"] == "author_id"


def test_registry_covers_expanded_business_models():
    names = {model.__name__ for model in register_data_scoped_models()}
    expected = {
        "ArticleRevision",
        "Workspace",
        "WorkspaceMember",
        "CollaborationInvite",
        "UploadTask",
        "DownloadTask",
        "TeamComment",
        "FormSubmission",
        "ExpertCertification",
        "CertificationDocument",
        "Cart",
        "Order",
        "RevenueRecord",
        "PayoutRequest",
        "Tip",
        "TipWithdrawal",
        "VipPaymentOrder",
        "SupportTicket",
        "SupportTicketReply",
        "DeploymentLog",
        "MediaFolder",
        "ChatMessage",
        "AIConfig",
        "UserSession",
    }
    assert expected <= names, f"登记表缺少：{sorted(expected - names)}"


def test_registry_excludes_audit_and_rbac_internal():
    names = {model.__name__ for model in register_data_scoped_models()}
    assert names.isdisjoint(
        {"AuditLog", "PermissionAuditLog", "PermissionGroup", "UserGroupMember", "UserRole"}
    )


def test_owner_field_of_unregistered_model_returns_none():
    from shared.models.rbac.capability import Capability

    assert owner_field_of(Capability) is None


# ------------------------------------------------------------------ 内置角色
def test_builtin_roles_data_scope():
    from scripts.seed_rbac import ROLE_DEFS

    scopes = {rdef["slug"]: rdef.get("data_scope") for rdef in ROLE_DEFS}
    assert scopes == {
        "superadmin": DATA_SCOPE_ALL,
        "admin": DATA_SCOPE_ALL,
        "editor": DATA_SCOPE_GROUP_AND_CHILD,
        "user": DATA_SCOPE_SELF,
    }


def test_admin_and_editor_hold_others_codes():
    """AND 语义下管理员/编辑者必须同时持有 others 码，否则 data_scope 形同虚设"""
    from scripts.seed_rbac import ROLE_DEFS

    by_slug = {rdef["slug"]: set(rdef["capability_codes"]) for rdef in ROLE_DEFS}
    for slug in ("admin", "editor"):
        owned = by_slug[slug]
        for model, code_list in OTHERS_CODES.items():
            for code in code_list:
                assert code in owned, f"{slug} 缺少 {code}（{model}）"


# ------------------------------------------------------------------ 写路径校验
def test_services_accept_scope_user():
    for service, methods in WRITE_METHODS:
        for name in methods:
            sig = inspect.signature(getattr(service, name))
            assert "scope_user" in sig.parameters, f"{name} 缺少 scope_user 参数"


@pytest.mark.asyncio
async def test_ensure_write_in_scope_skips_unregistered_model():
    """未登记模型不做数据级校验（db 不会被触碰）"""
    from shared.models.rbac.capability import Capability

    await ensure_write_in_scope(
        None,  # type: ignore[arg-type]
        Capability,
        FakeRow(id=1),
        user=FakeUser__write_scope(user_id=2),
        others_code="",
    )


@pytest.mark.asyncio
async def test_ensure_write_in_scope_superuser_passes():
    from shared.models.article.article import Article

    await ensure_write_in_scope(
        None,  # type: ignore[arg-type]
        Article,
        FakeRow(user=999),
        user=FakeUser__write_scope(user_id=2, is_superuser=True),
        others_code=codes.ARTICLE_EDIT_OTHERS,
    )


@pytest.mark.asyncio
async def test_ensure_write_in_scope_own_record_passes_without_others_code():
    """自己的记录：即使没有 others 码也放行（"仅本人"档位天然覆盖）"""
    from shared.models.article.article import Article

    await ensure_write_in_scope(
        None,  # type: ignore[arg-type]
        Article,
        FakeRow(user=7),
        user=FakeUser__write_scope(user_id=7),
        others_code="",
    )


@pytest.mark.asyncio
async def test_ensure_write_in_scope_other_record_without_code_raises():
    """他人记录 + 未定义 others 码 → fail-closed"""
    from shared.models.article.article import Article

    with pytest.raises(ForbiddenError):
        await ensure_write_in_scope(
            None,  # type: ignore[arg-type]
            Article,
            FakeRow(user=999),
            user=FakeUser__write_scope(user_id=7),
            others_code="",
        )
