"""屏幕选项（screen options）：用户级的「每页 UI 偏好」持久化

源能力来自 v2 的 ``shared/services/system/screen_options_service.py``：按 ``page``
分组的用户偏好（显示哪些列、每页条数、排序等），提供 get/set/delete 单项、
取整页、取全部。

**v2 的存储选择被 v3 换掉了**：v2 把偏好写进 ``custom_fields`` 表
（``field_name = "{page}.{option_key}"``、``field_value``）。但那是一张**内容域的 CPT
字段值表**（列 ``post_type_id`` / ``content_id`` 指向具体内容），拿它存「用户界面偏好」
语义错位；更关键的是 ``field_value`` 只有 ``String(255)``——一页的列清单 / 排序序列化后
很容易超过 255 字符被**静默截断**，读回来即坏数据。

v3 改存 ``system_settings``：**每个用户一行**，键 ``screen_options.{user_id}``，
值是 ``{page: {option_key: value}}`` 的 JSON（``setting_value`` 是 ``Text``，不会截断）。
落点列名 ``setting_key`` / ``setting_value`` 取自
``shared/models/system/system_settings.py`` 的模型定义（与初始迁移一致），不是猜的。

纯函数（``validate_page`` / ``validate_option_key`` / ``normalize_options`` /
``merge_default_options``）与 DB 读写彻底分离，便于在无数据库场景下测试。
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger

logger = get_logger("system.screen_options")

#: 每个用户在 ``system_settings`` 里的键前缀（键 = ``screen_options.{user_id}``）
KEY_PREFIX = "screen_options."

#: ``page`` 名称长度上限（如 articles / users / content.article）
MAX_PAGE_LEN = 64
#: 单个选项键长度上限
MAX_OPTION_KEY_LEN = 64
#: 单个页面允许的选项条目数上限
MAX_OPTIONS_PER_PAGE = 100
#: 单个选项值序列化后的字节上限（防止塞大对象）
MAX_VALUE_BYTES = 8 * 1024
#: 单个页面全部选项序列化后的字节上限
MAX_PAGE_BYTES = 16 * 1024

#: ``page`` 允许的字符：字母 / 数字 / 下划线 / 点 / 连字符
_PAGE_RE = re.compile(r"^[A-Za-z0-9_.-]+$")

#: 任一页面缺省值（存里没有再取用；``get_page`` 会用它补齐）
DEFAULT_OPTIONS: Dict[str, Any] = {
    "columns": [],
    "per_page": 20,
    "order_by": None,
    "order": "desc",
}


def validate_page(page: Any) -> str:
    """校验并归一化 ``page`` 名称，非法时抛 ``BadRequestError``

    ``page`` 必填、去首尾空白后不得为空、长度受限，且只允许
    ``[A-Za-z0-9_.-]``（不含斜杠，避免污染 URL 路径）。
    """
    if not isinstance(page, str):
        raise BadRequestError("page 必须是字符串")
    page = page.strip()
    if not page:
        raise BadRequestError("page 不能为空")
    if len(page) > MAX_PAGE_LEN:
        raise BadRequestError(f"page 长度不能超过 {MAX_PAGE_LEN}，收到 {len(page)}")
    if not _PAGE_RE.match(page):
        raise BadRequestError(
            f"page 只允许字母、数字、下划线、点与连字符，收到「{page}」"
        )
    return page


def validate_option_key(key: Any) -> str:
    """校验并归一化单个选项键，非法时抛 ``BadRequestError``"""
    if not isinstance(key, str):
        raise BadRequestError("选项键必须是字符串")
    key = key.strip()
    if not key:
        raise BadRequestError("选项键不能为空")
    if len(key) > MAX_OPTION_KEY_LEN:
        raise BadRequestError(
            f"选项键长度不能超过 {MAX_OPTION_KEY_LEN}，收到 {len(key)}"
        )
    return key


def _json_size(value: Any) -> int:
    """返回 ``value`` 的 JSON 序列化字节数（不允许 NaN / Infinity）"""
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
    return len(encoded.encode("utf-8"))


def normalize_options(options: Any) -> Dict[str, Any]:
    """校验并归一化一页的 ``options``，返回可安全落库的新 dict

    规则：

      - 必须是 ``dict``（``None`` 视为空 dict）；
      - 每个键经 ``validate_option_key`` 归一化（去空白、限长）；
      - 每个值必须可 JSON 序列化（不接受 set / 自定义对象 / NaN）；
      - 单个值不得超 ``MAX_VALUE_BYTES``，整页不得超 ``MAX_PAGE_BYTES`` / ``MAX_OPTIONS_PER_PAGE``。
    """
    if options is None:
        return {}
    if not isinstance(options, dict):
        raise BadRequestError("options 必须是 JSON 对象（dict）")
    if len(options) > MAX_OPTIONS_PER_PAGE:
        raise BadRequestError(
            f"单个页面最多 {MAX_OPTIONS_PER_PAGE} 个选项，收到 {len(options)}"
        )

    clean: Dict[str, Any] = {}
    for raw_key, value in options.items():
        key = validate_option_key(raw_key)
        try:
            size = _json_size(value)
        except (TypeError, ValueError) as exc:
            raise BadRequestError(f"选项「{key}」的值无法序列化为 JSON：{exc}") from exc
        if size > MAX_VALUE_BYTES:
            raise BadRequestError(
                f"选项「{key}」的值过大（{size} 字节，上限 {MAX_VALUE_BYTES}）"
            )
        clean[key] = value

    total = _json_size(clean)
    if total > MAX_PAGE_BYTES:
        raise BadRequestError(
            f"单个页面的选项合计过大（{total} 字节，上限 {MAX_PAGE_BYTES}）"
        )
    return clean


def merge_default_options(
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """把用户已存的选项合并到默认值之上（未知键原样保留）

    返回**新 dict**，其列表值也是副本，改动返回值不会污染 ``DEFAULT_OPTIONS``。
    """
    merged: Dict[str, Any] = {
        key: (list(value) if isinstance(value, list) else value)
        for key, value in DEFAULT_OPTIONS.items()
    }
    if options:
        merged.update(options)
    return merged


class ScreenOptionsService:
    """用户级屏幕选项的读写（每用户一行 JSON）"""

    @staticmethod
    def storage_key(user_id: int) -> str:
        """该用户在 ``system_settings`` 里的键"""
        return f"{KEY_PREFIX}{user_id}"

    # ------------------------------------------------------------------ 存储
    async def _load(self, db: AsyncSession, user_id: int) -> Dict[str, Dict[str, Any]]:
        """读出该用户的整份偏好 ``{page: {key: value}}``（缺失 / 损坏时返回空 dict）"""
        from shared.models.system.system_settings import SystemSettings

        row = (
            await db.execute(
                select(SystemSettings)
                .where(SystemSettings.setting_key == self.storage_key(user_id))
                .limit(1)
            )
        ).scalars().first()
        if row is None or not row.setting_value:
            return {}
        try:
            parsed = json.loads(row.setting_value)
        except ValueError:
            logger.warning(
                "用户 %s 的屏幕选项不是合法 JSON，按空处理：%s",
                user_id,
                (row.setting_value or "")[:80],
            )
            return {}
        if not isinstance(parsed, dict):
            logger.warning("用户 %s 的屏幕选项不是对象，按空处理", user_id)
            return {}
        return {
            str(page): dict(opts)
            for page, opts in parsed.items()
            if isinstance(opts, dict)
        }

    async def _save(
        self, db: AsyncSession, user_id: int, data: Dict[str, Dict[str, Any]]
    ) -> None:
        """把整份偏好写回 ``system_settings``（不存在则新建该用户的行）"""
        from shared.models.system.system_settings import SystemSettings

        key = self.storage_key(user_id)
        row = (
            await db.execute(
                select(SystemSettings).where(SystemSettings.setting_key == key).limit(1)
            )
        ).scalars().first()
        now = datetime.now()
        value = json.dumps(data, ensure_ascii=False)
        if row is None:
            db.add(
                SystemSettings(
                    setting_key=key,
                    setting_value=value,
                    setting_type="json",
                    description=f"用户 {user_id} 的屏幕选项（每页 UI 偏好）",
                    is_public=False,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            row.setting_value = value
            row.setting_type = "json"
            row.updated_at = now
        await db.commit()

    # ------------------------------------------------------------------ 读
    async def get_all(
        self, db: AsyncSession, user_id: int
    ) -> Dict[str, Dict[str, Any]]:
        """按 ``page`` 分组返回全部偏好（存里怎么存就怎么回，不做默认值补齐）"""
        return await self._load(db, user_id)

    async def get_page(
        self, db: AsyncSession, user_id: int, page: str
    ) -> Dict[str, Any]:
        """单页偏好（用 ``DEFAULT_OPTIONS`` 补齐缺省项）"""
        page = validate_page(page)
        data = await self._load(db, user_id)
        return merge_default_options(data.get(page))

    # ------------------------------------------------------------------ 写
    async def set_page(
        self,
        db: AsyncSession,
        user_id: int,
        page: str,
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """**整体覆盖**单页偏好；未知 ``page`` 自动新建。返回落库后的该项"""
        page = validate_page(page)
        clean = normalize_options(options)
        data = await self._load(db, user_id)
        data[page] = clean
        await self._save(db, user_id, data)
        logger.info("屏幕选项整体覆盖（用户 %s，page %s，%d 项）", user_id, page, len(clean))
        return clean

    async def patch_option(
        self,
        db: AsyncSession,
        user_id: int,
        page: str,
        key: str,
        value: Any,
    ) -> Dict[str, Any]:
        """修改单项（未知 ``page`` 自动新建）；返回该页更新后的全部选项"""
        page = validate_page(page)
        key = validate_option_key(key)
        single = normalize_options({key: value})
        data = await self._load(db, user_id)
        page_options = data.setdefault(page, {})
        page_options.update(single)
        # 合并后整页可能变大，按同一套规则再校验一次
        normalize_options(page_options)
        await self._save(db, user_id, data)
        logger.info("屏幕选项更新单项（用户 %s，page %s，key %s）", user_id, page, key)
        return page_options

    async def delete_option(
        self, db: AsyncSession, user_id: int, page: str, key: str
    ) -> Dict[str, Any]:
        """删除单项；不存在抛 ``NotFoundError``。返回该页剩余选项（页空了则移除该页）"""
        page = validate_page(page)
        key = validate_option_key(key)
        data = await self._load(db, user_id)
        page_options = data.get(page)
        if not page_options or key not in page_options:
            raise NotFoundError(f"屏幕选项不存在：{page}.{key}")
        del page_options[key]
        if page_options:
            data[page] = page_options
        else:
            data.pop(page, None)
        await self._save(db, user_id, data)
        logger.info("屏幕选项删除单项（用户 %s，page %s，key %s）", user_id, page, key)
        return data.get(page, {})

    async def delete_page(self, db: AsyncSession, user_id: int, page: str) -> None:
        """删除整页偏好；该页不存在抛 ``NotFoundError``"""
        page = validate_page(page)
        data = await self._load(db, user_id)
        if page not in data:
            raise NotFoundError(f"屏幕选项页不存在：{page}")
        data.pop(page)
        await self._save(db, user_id, data)
        logger.info("屏幕选项删除整页（用户 %s，page %s）", user_id, page)

    async def reset(self, db: AsyncSession, user_id: int) -> int:
        """重置全部偏好（删除该用户的整行）；返回被移除的页面数"""
        from shared.models.system.system_settings import SystemSettings

        data = await self._load(db, user_id)
        removed = len(data)
        await db.execute(
            delete(SystemSettings).where(
                SystemSettings.setting_key == self.storage_key(user_id)
            )
        )
        await db.commit()
        logger.info("屏幕选项已重置（用户 %s，移除 %d 页）", user_id, removed)
        return removed


#: 单例实例
screen_options_service = ScreenOptionsService()
