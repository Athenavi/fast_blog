"""数据范围过滤（唯一实现）

对应方案 §7.7.5：**采纳官方的"按创建人推导"**（业务表只记归属人，不为数据行加 group_id），
并强制补齐官方缺失的四项：

  ① **可访问组集合缓存**（Redis + 变更失效）—— 官方每次查库、每次全表拉部门算子树
  ② **子查询而非展开 id 列表** —— 避免成员规模放大 IN 列表
  ③ **无归属数据策略显式化** —— ``owner IS NULL``（或作者已被删除）默认**不可见**，
     只有 ``data_scope=全部`` 的用户可见；不再依赖"猜"
  ④ **``DATA_SCOPED_MODELS`` 显式登记** —— 未登记的模型明确不做数据级过滤，
     而不是像官方那样靠 ``hasattr(model, 'created_id')`` 静默 no-op

另有两个与官方一致的正确取舍：

  - 多角色取**并集**，且任一角色的档位为"全部"即不过滤（宽松优先）
  - 解析失败时**降级为最小授权（仅本人）**并留日志，绝不静默放宽

``data_scope`` 为 ``NULL``（模型侧可空，见方案 §8.2）时按 **1（仅本人）** 处理。
"""

from typing import Any, Optional, Set

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.logger import get_logger
from src.api.v3.core.permission.cache import native_client
from src.api.v3.core.permission.constants import (
    DATA_SCOPE_ALL,
    DATA_SCOPE_CUSTOM,
    DATA_SCOPE_GROUP_AND_CHILD,
    DATA_SCOPE_SELF,
)

logger = get_logger("permission.scope")

#: 组集合缓存（用户 → 其"组及子组"id 集合）
SCOPE_GROUP_CACHE_PREFIX = "rbac:scope:groups:"
#: 自定义组缓存（用户 → 由角色 role_groups 指定的组 id 集合）
SCOPE_CUSTOM_CACHE_PREFIX = "rbac:scope:custom:"
SCOPE_CACHE_TTL = 300

#: 参与数据范围过滤的模型 → 归属字段名（**显式登记**；不在表内即不做数据级过滤）
_data_scoped_models: dict[Any, str] = {}


def register_data_scoped_models() -> dict[Any, str]:
    """填充并返回登记表（延迟导入模型，避免与 ``shared.models`` 形成导入环）

    登记范围 = **有归属人字段的业务数据**（归属按创建人/作者推导，见模块 docstring 的 G3 裁决）。
    刻意**不登记**三类：

      - 审计日志（``audit_logs`` / ``permission_audit_logs``）—— 审计必须全量可查
      - RBAC 内部表（``permission_groups`` / ``user_group_members`` / ``user_role_assignments``）
        —— 它们是权限与范围解析自身的输入，过滤会自锁
      - 无归属字段的表（无法推导归属）

    登记只表示"该模型**允许**被数据范围过滤"；只有管理端查询主动传 ``scope_user`` 时才生效。
    """
    global _data_scoped_models
    if _data_scoped_models:
        return _data_scoped_models

    from shared.models.ai.ai_config import AIConfig
    from shared.models.ai.ai_workflow import AIWorkflow
    from shared.models.ad.ad_click import AdClick
    from shared.models.ad.ad_impression import AdImpression
    from shared.models.analytics.page_view import PageView
    from shared.models.analytics.user_activity import UserActivity
    from shared.models.article.article import Article
    from shared.models.article.article_annotation import ArticleAnnotation
    from shared.models.article.article_like import ArticleLike
    from shared.models.article.article_revision import ArticleRevision
    from shared.models.article.article_revision_note import ArticleRevisionNote
    from shared.models.certification.certification_document import CertificationDocument
    from shared.models.certification.certification_review import CertificationReview
    from shared.models.certification.expert_certification import ExpertCertification
    from shared.models.chat.chat_group_member import ChatGroupMember
    from shared.models.chat.chat_message import ChatMessage
    from shared.models.collaboration.invitation import CollaborationInvite
    from shared.models.collaboration.workspace import Workspace
    from shared.models.collaboration.workspace_member import WorkspaceMember
    from shared.models.comment.comment import Comment
    from shared.models.comment.comment_subscription import CommentSubscription
    from shared.models.comment.comment_vote import CommentVote
    from shared.models.comment.team_comment import TeamComment
    from shared.models.content.custom_field import CustomField
    from shared.models.content.custom_post_content import CustomPostContent
    from shared.models.ecommerce.cart import Cart
    from shared.models.ecommerce.order import Order
    from shared.models.enterprise.deployment_log import DeploymentLog
    from shared.models.enterprise.support_ticket import SupportTicket
    from shared.models.enterprise.support_ticket_reply import SupportTicketReply
    from shared.models.form.form_submission import FormSubmission
    from shared.models.media.download_task import DownloadTask
    from shared.models.media.media import Media
    from shared.models.media.media_folder import MediaFolder
    from shared.models.media.upload_task import UploadTask
    from shared.models.multisite.site_user import SiteUser
    from shared.models.notification.email_subscription import EmailSubscription
    from shared.models.page.pages import Pages
    from shared.models.payment.payment_transaction import PaymentTransaction
    from shared.models.revenue.payout_request import PayoutRequest
    from shared.models.revenue.revenue_record import RevenueRecord
    from shared.models.revenue.user_revenue_stats import UserRevenueStats
    from shared.models.search.search_history import SearchHistory
    from shared.models.security.gdpr_consent import GDPRConsent
    from shared.models.system.admin_settings import AdminSettings
    from shared.models.tipping.tip import Tip
    from shared.models.tipping.tip_withdrawal import TipWithdrawal
    from shared.models.user.o_auth_account import OAuthAccount
    from shared.models.user.user_session import UserSession
    from shared.models.vip.vip_payment_order import VipPaymentOrder
    from shared.models.vip.vip_subscription import VIPSubscription
    from shared.models.widget.block_pattern import BlockPattern

    _data_scoped_models = {
        # ---- 内容 ----
        Article: "user",
        Pages: "author_id",
        Media: "user",
        MediaFolder: "user",
        Comment: "user_id",
        CommentVote: "user",
        CommentSubscription: "user_id",
        ArticleRevision: "author_id",
        ArticleRevisionNote: "user_id",
        ArticleAnnotation: "user",
        ArticleLike: "user",
        CustomPostContent: "author_id",
        CustomField: "user",
        TeamComment: "author_id",
        BlockPattern: "user_id",
        # ---- 协作 ----
        Workspace: "owner_id",
        WorkspaceMember: "user_id",
        CollaborationInvite: "creator_id",
        # ---- 商务 / 收益 / 打赏 ----
        Cart: "user_id",
        Order: "user_id",
        PaymentTransaction: "user",
        RevenueRecord: "user_id",
        UserRevenueStats: "user_id",
        PayoutRequest: "user_id",
        VipPaymentOrder: "user_id",
        VIPSubscription: "user",
        Tip: "user_id",
        TipWithdrawal: "user_id",
        # ---- 认证（手写模型：``Column`` 风格，不在生成器产物里）----
        ExpertCertification: "user_id",
        CertificationDocument: "user_id",
        CertificationReview: "reviewer_id",
        # ---- 表单 / 客服 / 部署 ----
        FormSubmission: "user_id",
        SupportTicket: "user_id",
        SupportTicketReply: "user_id",
        DeploymentLog: "user_id",
        # ---- 媒体任务 ----
        UploadTask: "user_id",
        DownloadTask: "user_id",
        # ---- 聊天 / AI / 站点设置 ----
        ChatMessage: "user",
        ChatGroupMember: "user",
        AIConfig: "user_id",
        AIWorkflow: "user_id",
        AdminSettings: "user",
        # ---- 账号 / 会话 / 合规 / 订阅 ----
        OAuthAccount: "user_id",
        UserSession: "user_id",
        SiteUser: "user_id",
        GDPRConsent: "user_id",
        EmailSubscription: "user",
        # ---- 行为与统计埋点 ----
        PageView: "user",
        UserActivity: "user",
        SearchHistory: "user",
        AdClick: "user_id",
        AdImpression: "user_id",
    }
    return _data_scoped_models


def owner_field_of(model: Any) -> Optional[str]:
    """取模型的归属字段名；未登记返回 None（明确表示"该模型不做数据级过滤"）"""
    return register_data_scoped_models().get(model)


# ------------------------------------------------------------------ 缓存读写
async def _cache_get(key: str) -> Optional[Set[int]]:
    client = native_client()
    if client is None:
        return None
    try:
        raw = await client.get(key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("读取数据范围缓存失败 key=%s：%s", key, exc)
        return None
    if raw is None:
        return None
    if isinstance(raw, (list, tuple, set)):
        values = raw
    else:
        values = str(raw).split(",")
    result = set()
    for item in values:
        try:
            result.add(int(item))
        except (TypeError, ValueError):
            continue
    return result


async def _cache_set(key: str, values: Set[int]) -> None:
    client = native_client()
    if client is None:
        return
    try:
        await client.set(key, ",".join(str(v) for v in sorted(values)), ex=SCOPE_CACHE_TTL)
    except Exception as exc:  # noqa: BLE001
        logger.warning("写入数据范围缓存失败 key=%s：%s", key, exc)


# ------------------------------------------------------------------ 组集合解析
_GROUP_TREE_SQL = """
                  WITH RECURSIVE my_groups AS (SELECT g.id, g.parent_id
                                               FROM permission_groups g
                                                        JOIN user_group_members m ON m.group_id = g.id
                                               WHERE m.user_id = :user_id
                                                 AND g.is_active IS TRUE
                                               UNION
                                               SELECT child.id, child.parent_id
                                               FROM permission_groups child
                                                        JOIN my_groups parent ON child.parent_id = parent.id
                                               WHERE child.is_active IS TRUE)
                  SELECT id
                  FROM my_groups \
                  """

_CUSTOM_GROUPS_SQL = """
                     SELECT DISTINCT rg.group_id
                     FROM role_groups rg
                              JOIN user_role_assignments ur ON ur.role_id = rg.role_id
                              JOIN roles r ON r.id = rg.role_id
                     WHERE ur.user_id = :user_id
                       AND r.is_active IS TRUE \
                     """


async def resolve_scope_group_ids(db: AsyncSession, user_id: int) -> Set[int]:
    """用户"本组及以下"的组 id 集合（带 Redis 缓存）"""
    key = f"{SCOPE_GROUP_CACHE_PREFIX}{user_id}"
    cached = await _cache_get(key)
    if cached is not None:
        return cached

    from sqlalchemy import text

    rows = (await db.execute(text(_GROUP_TREE_SQL), {"user_id": user_id})).scalars().all()
    group_ids = {int(row) for row in rows if row is not None}
    await _cache_set(key, group_ids)
    return group_ids


async def resolve_custom_group_ids(db: AsyncSession, user_id: int) -> Set[int]:
    """``data_scope=5`` 时由角色指定的组 id 集合（带 Redis 缓存）"""
    key = f"{SCOPE_CUSTOM_CACHE_PREFIX}{user_id}"
    cached = await _cache_get(key)
    if cached is not None:
        return cached

    from sqlalchemy import text

    rows = (await db.execute(text(_CUSTOM_GROUPS_SQL), {"user_id": user_id})).scalars().all()
    group_ids = {int(row) for row in rows if row is not None}
    await _cache_set(key, group_ids)
    return group_ids


# ------------------------------------------------------------------ 档位解析
def _normalize_scopes(scopes: Set[Optional[int]]) -> Set[int]:
    """``NULL`` 视为 1（仅本人）；无任何档位时同样按 1 处理（最小授权）"""
    normalized = {int(scope) if scope is not None else DATA_SCOPE_SELF for scope in scopes}
    return normalized or {DATA_SCOPE_SELF}


async def resolve_data_scopes(db: AsyncSession, user_id: int) -> Set[int]:
    """用户所有（含继承的父角色）有效角色的 data_scope 集合"""
    from sqlalchemy import text

    sql = """
          WITH RECURSIVE role_tree AS (SELECT r.id, r.parent_id, r.data_scope
                                       FROM roles r
                                                JOIN user_role_assignments ur ON ur.role_id = r.id
                                       WHERE ur.user_id = :user_id
                                         AND r.is_active IS TRUE
                                       UNION
                                       SELECT parent.id, parent.parent_id, parent.data_scope
                                       FROM roles parent
                                                JOIN role_tree child ON parent.id = child.parent_id
                                       WHERE parent.is_active IS TRUE)
          SELECT DISTINCT data_scope
          FROM role_tree \
          """
    rows = (await db.execute(text(sql), {"user_id": user_id})).scalars().all()
    return _normalize_scopes(set(rows))


# ------------------------------------------------------------------ 查询过滤
async def apply_data_scope(stmt: Select, model: Any, *, db: AsyncSession, user: Any) -> Select:
    """按当前用户的数据范围，给查询追加过滤条件

    - 未登记的模型：**明确不追加**（调用方若要求数据范围，应在启动期审计里被发现）
    - 超级管理员与 ``data_scope=全部``：不追加条件
    - 解析异常：降级为"仅本人"并记录日志（最小授权）
    """
    owner_name = owner_field_of(model)
    if owner_name is None:
        logger.debug("模型 %s 未登记数据范围，跳过过滤", getattr(model, "__name__", model))
        return stmt

    if getattr(user, "is_superuser", False):
        return stmt

    owner_column = getattr(model, owner_name)
    try:
        scopes = await resolve_data_scopes(db, user.id)
        if DATA_SCOPE_ALL in scopes:
            return stmt

        conditions = []
        if DATA_SCOPE_SELF in scopes:
            conditions.append(owner_column == user.id)

        group_ids: Set[int] = set()
        if DATA_SCOPE_GROUP_AND_CHILD in scopes:
            group_ids |= await resolve_scope_group_ids(db, user.id)
        if DATA_SCOPE_CUSTOM in scopes:
            group_ids |= await resolve_custom_group_ids(db, user.id)

        if group_ids:
            from shared.models.rbac.user_group_member import UserGroupMember

            member_ids = select(UserGroupMember.user_id).where(
                UserGroupMember.group_id.in_(sorted(group_ids))
            )
            conditions.append(owner_column.in_(member_ids))

        if not conditions:
            # 档位不认识或组为空 → 最小授权
            conditions.append(owner_column == user.id)

        return stmt.where(or_(*conditions))
    except Exception:  # noqa: BLE001 - 失败必须收紧，绝不放宽
        logger.exception("数据范围解析失败，降级为仅本人 user=%s model=%s", user.id, model)
        return stmt.where(owner_column == user.id)


async def ensure_object_in_scope(db: AsyncSession, model: Any, obj: Any, *, user: Any) -> None:
    """校验**单条记录**是否在用户的数据范围内；不在则抛 ``ForbiddenError``

    与 ``apply_data_scope`` 共用同一套档位解析，堵住"列表已过滤、但详情可直接猜 id 访问"的缺口。
    无归属字段（``owner IS NULL``）的记录只有 ``data_scope=全部`` 可见。
    """
    from src.api.v3.core.exceptions import ForbiddenError

    owner_name = owner_field_of(model)
    if owner_name is None or obj is None:
        return
    if getattr(user, "is_superuser", False):
        return

    owner_id = getattr(obj, owner_name, None)
    own = owner_id is not None and int(owner_id) == int(user.id)

    try:
        scopes = await resolve_data_scopes(db, user.id)
        if DATA_SCOPE_ALL in scopes:
            return
        if own and DATA_SCOPE_SELF in scopes:
            return

        needs_group = DATA_SCOPE_GROUP_AND_CHILD in scopes or DATA_SCOPE_CUSTOM in scopes
        if needs_group and owner_id is not None:
            group_ids: Set[int] = set()
            if DATA_SCOPE_GROUP_AND_CHILD in scopes:
                group_ids |= await resolve_scope_group_ids(db, user.id)
            if DATA_SCOPE_CUSTOM in scopes:
                group_ids |= await resolve_custom_group_ids(db, user.id)
            if group_ids:
                from shared.models.rbac.user_group_member import UserGroupMember

                exists = await db.scalar(
                    select(UserGroupMember.id).where(
                        UserGroupMember.group_id.in_(sorted(group_ids)),
                        UserGroupMember.user_id == owner_id,
                    )
                )
                if exists is not None:
                    return
    except Exception:  # noqa: BLE001 - 失败必须收紧
        logger.exception("数据范围校验失败 user=%s model=%s", getattr(user, "id", None), model)
        if own:
            return
        raise ForbiddenError("数据范围校验失败") from None

    raise ForbiddenError("无权访问该数据")


async def ensure_write_in_scope(
    db: AsyncSession,
    model: Any,
    obj: Any,
    *,
    user: Any,
    others_code: str,
) -> None:
    """**写路径**的数据范围 + 他人数据权限校验（``data_scope`` 与 others 码取 **AND**）

    判定顺序：

      1. 未登记模型 / 超管 → 放行
      2. 记录归属自己 → 放行（"仅本人"档位天然覆盖自己的数据，无需 others 码）
      3. 归属他人 → 必须**同时在数据范围内**（复用 ``ensure_object_in_scope``）
         且**持有 ``others_code``**；任一不满足即 403

    语义分工：``others_code`` 决定"能否碰他人数据"，``data_scope`` 决定"能碰到哪些人的数据"。
    因此内置角色需要**两者同时具备**才能管理他人内容（见 ``scripts/seed_rbac.py``）。

    fail-closed：权限码加载失败、未提供 others 码，一律拒绝。
    """
    from src.api.v3.core.exceptions import ForbiddenError
    from src.api.v3.core.permission.constants import WILDCARD_CODES
    from src.api.v3.core.permission.loader import load_codes

    owner_name = owner_field_of(model)
    if owner_name is None or obj is None:
        return
    if getattr(user, "is_superuser", False):
        return

    owner_id = getattr(obj, owner_name, None)
    own = owner_id is not None and int(owner_id) == int(getattr(user, "id", 0))
    if own:
        return

    if not others_code:
        raise ForbiddenError("该模型未定义他人数据的写权限码")

    # 1) 数据范围必须允许（ensure_object_in_scope 内部同样 fail-closed）
    await ensure_object_in_scope(db, model, obj, user=user)

    # 2) 且必须持有"操作他人数据"的权限码
    try:
        owned = await load_codes(db, user.id)
    except Exception:  # noqa: BLE001 - fail-closed
        logger.exception("他人数据权限码加载失败 user=%s", getattr(user, "id", None))
        raise ForbiddenError("权限校验失败") from None

    if others_code in owned or WILDCARD_CODES.intersection(owned):
        return
    raise ForbiddenError(f"无权操作他人数据：需要 {others_code}")


async def invalidate_scope_cache(user_id: Optional[int] = None) -> None:
    """失效数据范围缓存（组/成员/角色变更后必须调用）

    ``user_id=None`` 时按前缀清理（组结构变更会影响多个用户）。
    """
    client = native_client()
    if client is None:
        # Redis 不可用时依赖 TTL（300s）自然过期
        return
    try:
        if user_id is not None:
            await client.delete(f"{SCOPE_GROUP_CACHE_PREFIX}{user_id}")
            await client.delete(f"{SCOPE_CUSTOM_CACHE_PREFIX}{user_id}")
            return

        # 组结构/成员变更：按前缀清理（规模可控：单实例权限组数量通常很小）
        for prefix in (SCOPE_GROUP_CACHE_PREFIX, SCOPE_CUSTOM_CACHE_PREFIX):
            keys = await client.keys(f"{prefix}*")
            if keys:
                await client.delete(*keys)
    except Exception as exc:  # noqa: BLE001
        logger.warning("失效数据范围缓存失败：%s", exc)


__all__ = [
    "apply_data_scope",
    "ensure_object_in_scope",
    "ensure_write_in_scope",
    "invalidate_scope_cache",
    "owner_field_of",
    "register_data_scoped_models",
    "resolve_custom_group_ids",
    "resolve_data_scopes",
    "resolve_scope_group_ids",
]
