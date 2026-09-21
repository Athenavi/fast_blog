"""content.third_party_publish 模块业务逻辑：多平台发布底座（渠道 / 任务 / 记录 / 重试）

两个 service，各自只管自己的表：

  - ``PublishChannelService``：渠道配置。凭据走 ``core/secret_box`` 加密落库，
    **永不回传**（出参只有 ``has_credentials``）；``adapter_ready`` 告诉前端该平台的
    适配器是否已接入。
  - ``PublishTaskService``：发布任务的状态机与执行。创建任务时**先冻结一份载荷快照**
    （标题 / 摘要 / 正文 / 链接 / 标签 / 作者），重试复用同一份 ——
    "重试发出去的就是当初那份内容"，期间文章被改动不会让重试变样。

**执行语义（不写假实现）**：

  - 平台有适配器 → 交给适配器，``PublishResult.success=False`` 即 ``failed``；
  - 平台**没有适配器** → 任务置 ``failed``，``last_error`` 写明
    ``未实现该平台的发布适配器（platform=xxx）``，并落一条 failed 日志；
  - 渠道停用 / 适配器抛异常 → 同样如实落 failed 日志。

底座里**没有任何"假装成功"的路径**（这也是平台适配器可以分期实现的前提）。
"""

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.article.article import Article
from shared.models.article.article_content import ArticleContent
from shared.models.third_party_publish import PublishChannel, PublishLog, PublishTask
from shared.models.user import User
from src.api.v3.core.exceptions import BadRequestError, ConflictError, NotFoundError
from src.api.v3.core.secret_box import decrypt_json, encrypt_json
from src.api.v3.modules.content.third_party_publish.adapters import (
    AdapterNotRegisteredError,
    ChannelConfig,
    PublishPayload,
    PublishResult,
    adapter_platforms,
    get_adapter,
)
from src.api.v3.modules.content.third_party_publish.crud import (
    publish_channel_crud,
    publish_log_crud,
    publish_task_crud,
)
from src.api.v3.modules.content.third_party_publish.schema import (
    PublishChannelCreate,
    PublishChannelOut,
    PublishChannelUpdate,
    PublishLogOut,
    PublishTaskCreate,
    PublishTaskOut,
)

#: 任务状态（与 models.yaml 的说明保持一致）
TASK_PENDING = "pending"
TASK_PUBLISHING = "publishing"
TASK_SUCCESS = "success"
TASK_FAILED = "failed"


# ---------------------------------------------------------------- 序列化
def _channel_out(row: PublishChannel) -> dict:
    data = PublishChannelOut.model_validate(row, from_attributes=True).model_dump(mode="json")
    data["has_credentials"] = bool(row.credentials_encrypted)
    data["adapter_ready"] = get_adapter(row.platform) is not None
    return data


def _task_out(row: PublishTask) -> dict:
    return PublishTaskOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _log_out(row: PublishLog) -> dict:
    return PublishLogOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def _load_snapshot(raw: Optional[str]) -> Optional[dict]:
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


class PublishChannelService:
    """发布渠道配置（content 域，管理端）"""

    async def list_channels(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        platform: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await publish_channel_crud.list(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            filters={"platform": platform, "is_active": is_active},
        )
        return [_channel_out(r) for r in rows], total

    async def get_channel(self, db: AsyncSession, channel_id: int) -> dict:
        return _channel_out(await self._channel_or_404(db, channel_id))

    async def create_channel(
        self, db: AsyncSession, payload: PublishChannelCreate, *, user_id: Optional[int] = None
    ) -> dict:
        if await publish_channel_crud.exists(db, platform=payload.platform, name=payload.name):
            raise ConflictError(f"该平台下已存在同名渠道: {payload.name}")
        now = datetime.now()
        row = await publish_channel_crud.create(
            db,
            {
                "name": payload.name,
                "platform": payload.platform,
                "endpoint": payload.endpoint,
                "credentials_encrypted": encrypt_json(payload.credentials),
                "is_active": payload.is_active,
                "created_by": user_id,
                "created_at": now,
                "updated_at": now,
            },
        )
        return _channel_out(row)

    async def update_channel(
        self, db: AsyncSession, channel_id: int, payload: PublishChannelUpdate
    ) -> dict:
        row = await self._channel_or_404(db, channel_id)
        data = payload.model_dump(exclude_unset=True)
        if data.get("name") and data["name"] != row.name:
            if await publish_channel_crud.exists(
                db, platform=row.platform, name=data["name"]
            ):
                raise ConflictError(f"该平台下已存在同名渠道: {data['name']}")
        # 凭据留空（或传空对象）表示保持原值 —— 密文永不回传，前端拿不到原值
        credentials = data.pop("credentials", None)
        if credentials:
            data["credentials_encrypted"] = encrypt_json(credentials)
        updated = await publish_channel_crud.update(
            db, row, data | {"updated_at": datetime.now()}
        )
        return _channel_out(updated)

    async def delete_channel(self, db: AsyncSession, channel_id: int) -> None:
        row = await self._channel_or_404(db, channel_id)
        await publish_channel_crud.remove(db, row)

    async def verify_channel(self, db: AsyncSession, channel_id: int) -> dict:
        """凭据 / 连通性自检（**不产生对外发布**）

        未注册适配器的平台直接抛 400 并说明原因 —— 不返回"看似成功"的假结果。
        """
        row = await self._channel_or_404(db, channel_id)
        adapter = get_adapter(row.platform)
        if adapter is None:
            raise BadRequestError(
                f"未实现该平台的发布适配器（platform={row.platform}），无法自检；"
                "平台适配器目前按清单分期接入"
            )
        result = await adapter.verify(self._channel_config(row))
        return {
            "success": bool(result.success),
            "message": result.message,
            "channel_id": row.id,
            "platform": row.platform,
        }

    @staticmethod
    def _channel_config(row: PublishChannel) -> ChannelConfig:
        """解密渠道凭据（**只给适配器用**，不要写进日志或响应）"""
        try:
            credentials = decrypt_json(row.credentials_encrypted or "")
        except ValueError as exc:
            raise BadRequestError(f"渠道凭据无法解密（{exc}）") from exc
        return ChannelConfig(
            id=row.id,
            name=row.name,
            platform=row.platform,
            endpoint=row.endpoint,
            credentials=credentials,
        )

    async def _channel_or_404(self, db: AsyncSession, channel_id: int) -> PublishChannel:
        row = await publish_channel_crud.get(db, channel_id)
        if row is None:
            raise NotFoundError("发布渠道不存在")
        return row


class PublishTaskService:
    """发布任务：创建（含载荷快照）/ 执行 / 手动重试 / 日志"""

    # ------------------------------------------------------------ 查询
    async def list_tasks(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        article_id: Optional[int] = None,
        channel_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        rows, total = await publish_task_crud.list(
            db,
            page=page,
            page_size=page_size,
            filters={"article_id": article_id, "channel_id": channel_id, "status": status},
        )
        items = [_task_out(r) for r in rows]
        await self._attach_labels(db, items)
        return items, total

    async def get_task(self, db: AsyncSession, task_id: int) -> dict:
        row = await self._task_or_404(db, task_id)
        data = _task_out(row)
        # 载荷快照是 Text 列（JSON 字符串），对外还原成对象；日志取最近 20 条
        data["payload"] = _load_snapshot(row.payload)
        logs, _total = await publish_log_crud.list(
            db, page=1, page_size=20, filters={"task_id": task_id}, order="desc"
        )
        data["logs"] = [_log_out(item) for item in logs]
        await self._attach_labels(db, [data])
        return data

    async def list_logs(
        self, db: AsyncSession, task_id: int, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict], int]:
        await self._task_or_404(db, task_id)
        rows, total = await publish_log_crud.list(
            db, page=page, page_size=page_size, filters={"task_id": task_id}, order="desc"
        )
        return [_log_out(r) for r in rows], total

    # ------------------------------------------------------------ 写
    async def create_task(
        self, db: AsyncSession, payload: PublishTaskCreate, *, user_id: Optional[int] = None
    ) -> tuple[dict, bool]:
        """创建发布任务并**立即尝试执行**；返回 ``(任务详情, 是否新建)``

        同一 (文章, 渠道) 已有任务时**复用**（幂等：连点"发布"不会堆任务），
        失败的任务请走 ``retry`` 端点重试。
        """
        channel = await publish_channel_crud.get(db, payload.channel_id)
        if channel is None:
            raise NotFoundError("发布渠道不存在")
        if not channel.is_active:
            raise BadRequestError("渠道已停用，无法发布")

        article = await db.get(Article, payload.article_id)
        if article is None:
            raise NotFoundError("文章不存在")

        existing = await publish_task_crud.get_by(
            db, article_id=payload.article_id, channel_id=payload.channel_id
        )
        if existing is not None:
            return await self.get_task(db, existing.id), False

        snapshot = await self._build_payload(db, article)
        now = datetime.now()
        row = await publish_task_crud.create(
            db,
            {
                "article_id": payload.article_id,
                "channel_id": payload.channel_id,
                "status": TASK_PENDING,
                "attempts": 0,
                "payload": json.dumps(snapshot.to_dict(), ensure_ascii=False),
                "created_by": user_id,
                "created_at": now,
                "updated_at": now,
            },
        )
        return await self.execute_task(db, row.id), True

    async def retry_task(self, db: AsyncSession, task_id: int) -> dict:
        """手动重试（复用创建时冻结的载荷快照）"""
        row = await self._task_or_404(db, task_id)
        if row.status == TASK_PUBLISHING:
            raise ConflictError("任务正在执行中，请稍后再试")
        return await self.execute_task(db, task_id)

    async def delete_task(self, db: AsyncSession, task_id: int) -> None:
        row = await self._task_or_404(db, task_id)
        if row.status == TASK_PUBLISHING:
            raise ConflictError("任务正在执行中，无法删除")
        await publish_task_crud.remove(db, row)

    async def execute_task(self, db: AsyncSession, task_id: int) -> dict:
        """执行一次发布：调用适配器并把结果如实落库 + 记日志

        **任何失败都写成 failed**，并把原因存进 ``last_error`` 与日志。
        """
        row = await self._task_or_404(db, task_id)
        started = datetime.now()
        row = await publish_task_crud.update(
            db,
            row,
            {
                "status": TASK_PUBLISHING,
                "attempts": int(row.attempts or 0) + 1,
                "started_at": started,
                "last_error": None,
                "updated_at": started,
            },
        )

        snapshot = _load_snapshot(row.payload) or {}
        payload = PublishPayload.from_dict(snapshot)

        channel = await publish_channel_crud.get(db, row.channel_id)
        if channel is None:
            await self._finish(db, row, PublishResult.fail("渠道不存在（可能已被删除）"), started)
        elif not channel.is_active:
            await self._finish(db, row, PublishResult.fail("渠道已停用"), started)
        else:
            try:
                adapter = get_adapter(channel.platform)
                if adapter is None:
                    # 平台适配器尚未接入 —— 如实失败，绝不假装成功
                    raise AdapterNotRegisteredError(
                        f"未实现该平台的发布适配器（platform={channel.platform}）"
                    )
                config = PublishChannelService._channel_config(channel)
                result = await adapter.publish(config, payload)
                if not isinstance(result, PublishResult):
                    result = PublishResult.fail("适配器返回了非法结果类型")
            except AdapterNotRegisteredError as exc:
                result = PublishResult.fail(str(exc))
            except ValueError as exc:  # 凭据解密失败
                result = PublishResult.fail(str(exc))
            except Exception as exc:  # noqa: BLE001 - 适配器异常一律记为失败
                result = PublishResult.fail(f"适配器执行异常: {exc}")
            await self._finish(db, row, result, started)

        return await self.get_task(db, task_id)

    # ------------------------------------------------------------ 内部
    async def _finish(
        self,
        db: AsyncSession,
        row: PublishTask,
        result: PublishResult,
        started: datetime,
    ) -> None:
        """把执行结果写回任务并落一条日志"""
        finished = datetime.now()
        data: dict[str, Any] = {
            "status": TASK_SUCCESS if result.success else TASK_FAILED,
            "finished_at": finished,
            "updated_at": finished,
            "last_error": None if result.success else (result.message or "发布失败")[:500],
        }
        if result.success:
            data["external_id"] = result.external_id
            data["external_url"] = result.external_url
        await publish_task_crud.update(db, row, data)
        await publish_log_crud.create(
            db,
            {
                "task_id": row.id,
                "status": TASK_SUCCESS if result.success else TASK_FAILED,
                "message": result.message,
                "duration_ms": int((finished - started).total_seconds() * 1000),
                "created_at": finished,
            },
        )

    async def _build_payload(self, db: AsyncSession, article: Article) -> PublishPayload:
        """从文章生成发布载荷快照"""
        content = (
            await db.execute(
                select(ArticleContent.content)
                .where(ArticleContent.article == article.id)
                .order_by(ArticleContent.id.asc())
                .limit(1)
            )
        ).scalar()
        author = None
        if article.user:
            author = (
                await db.execute(select(User.username).where(User.id == article.user))
            ).scalar()
        raw_tags = getattr(article, "tags_list", None) or []
        tags = [str(item) for item in raw_tags] if isinstance(raw_tags, list) else []
        url = (
            f"/articles/{article.slug}"
            if getattr(article, "slug", None)
            else f"/articles/id/{article.id}"
        )
        return PublishPayload(
            article_id=article.id,
            title=str(getattr(article, "title", "") or ""),
            slug=getattr(article, "slug", None),
            excerpt=getattr(article, "excerpt", None),
            content=content,
            url=url,
            author=author,
            tags=tags,
            published_at=(
                article.published_at.isoformat()
                if getattr(article, "published_at", None)
                else None
            ),
        )

    async def _attach_labels(self, db: AsyncSession, items: list[dict]) -> None:
        """给任务列表补上文章标题 / 渠道名与平台（批量查询，避免 N+1）"""
        article_ids = {item["article_id"] for item in items if item.get("article_id")}
        channel_ids = {item["channel_id"] for item in items if item.get("channel_id")}

        titles: dict[int, str] = {}
        if article_ids:
            rows = (
                await db.execute(
                    select(Article.id, Article.title).where(Article.id.in_(article_ids))
                )
            ).all()
            titles = {int(pk): str(title or "") for pk, title in rows}

        channels: dict[int, tuple[str, str]] = {}
        if channel_ids:
            rows = (
                await db.execute(
                    select(PublishChannel.id, PublishChannel.name, PublishChannel.platform).where(
                        PublishChannel.id.in_(channel_ids)
                    )
                )
            ).all()
            channels = {int(pk): (name or "", platform or "") for pk, name, platform in rows}

        for item in items:
            item["article_title"] = titles.get(item.get("article_id"))
            channel = channels.get(item.get("channel_id"))
            item["channel_name"] = channel[0] if channel else None
            item["channel_platform"] = channel[1] if channel else None

    async def _task_or_404(self, db: AsyncSession, task_id: int) -> PublishTask:
        row = await publish_task_crud.get(db, task_id)
        if row is None:
            raise NotFoundError("发布任务不存在")
        return row


publish_channel_service = PublishChannelService()
publish_task_service = PublishTaskService()

__all__ = [
    "TASK_FAILED",
    "TASK_PENDING",
    "TASK_PUBLISHING",
    "TASK_SUCCESS",
    "adapter_platforms",
    "publish_channel_service",
    "publish_task_service",
]
