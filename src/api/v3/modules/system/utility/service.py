"""utility 模块业务逻辑（定义展开 / 命令解析 / 文章 Markdown 导出）

接线的 4 个"零散件"（均为**真实能力**，无占位 / 无 mock）：

1. ``shared/defs/block_pattern_defs.py`` —— 区块模式定义方法（``to_pattern_dict`` /
   ``get_blocks_data`` / ``get_keywords_list`` / ``is_custom_pattern`` …）。这些方法设计为
   **注入到生成的 ORM 模型**（见 ``config/models.yaml`` 的 ``def_list`` / ``defs_target``），
   但当前生成的 ``shared/models/widget/block_pattern.py`` **并未包含**它们。因此这里用
   :class:`_PatternDefsAdapter` 在调用点把源模块的函数绑定到行对象上——逻辑只在 defs 模块里，
   **不复制一份**（避免双份真相）。
2. ``shared/defs/user_defs.py`` —— 用户 ``is_vip`` 判定，直接调用源函数（无绑定方法，直接当纯函数用）。
3. ``shared/services/nlp/nlp_command_parser.py`` —— 自然语言命令解析，薄封装源单例
   ``nlp_parser.parse_command``（不重写语法）。
4. ``src/utils/http/generate_response.py`` —— ``send_chunk_md`` 流式导出 Markdown 附件；
   本模块只负责从**真表**取正文，响应构造在 controller 层调用源函数完成。

**纯函数与 DB 操作分离**：``intent_catalog`` / ``parse_command`` / ``evaluate_user_vip`` /
``expand_pattern`` 为无 DB 依赖的纯函数（可独立单测）；``UtilityService`` 负责按主键读真表。
"""

import types
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.defs import block_pattern_defs, user_defs
from shared.models.article.article import Article
from shared.models.article.article_content import ArticleContent
from shared.models.user import User
from shared.models.widget.block_pattern import BlockPattern
from shared.services.nlp.nlp_command_parser import IntentType, nlp_parser
from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.system.utility.schema import (
    BlockPatternDefOut,
    NlpIntentCatalogOut,
    NlpParseResultOut,
    UserVipStatusOut,
)

logger = get_logger("system.utility")

#: ``block_pattern_defs`` 提供、且设计用于注入 ORM 模型的方法名
#: （与 ``config/models.yaml`` 中 BlockPattern 的 ``def_list`` 一致）
_BLOCK_PATTERN_DEF_METHODS = (
    "get_blocks_data",
    "set_blocks_data",
    "get_keywords_list",
    "set_keywords_list",
    "is_custom_pattern",
    "to_pattern_dict",
)


class _PatternDefsAdapter:
    """把源 ``block_pattern_defs`` 的方法按调用点绑定到行对象（保持单一真相）

    生成的 ORM 模型当前未注入这些方法，因此不能直接把 ORM 行交给 ``to_pattern_dict``
    （它内部会调用 ``self.get_blocks_data()`` / ``self.get_keywords_list()``）。这里不复制实现，
    而是用 ``types.MethodType`` 把 defs 模块的同名函数绑到适配器上；未命中的属性访问回退到真实行。
    """

    def __init__(self, row: Any) -> None:
        self._row = row
        for name in _BLOCK_PATTERN_DEF_METHODS:
            setattr(self, name, types.MethodType(getattr(block_pattern_defs, name), self))

    def __getattr__(self, name: str) -> Any:
        # 仅当正常属性查找（含上面绑定的方法）失败时才会走到这里
        return getattr(self.__dict__["_row"], name)


# ------------------------------------------------------------------ 纯函数（无 DB 依赖）
def intent_catalog() -> dict:
    """NLP 解析器能力目录（**纯函数**）

    直接读取源解析器 ``nlp_parser`` 的意图 / 实体 / 时间表达式模式表，**不重写**任何语法。
    """
    return NlpIntentCatalogOut(
        intents=[intent.value for intent in IntentType],
        intent_patterns={
            intent.value: list(patterns)
            for intent, patterns in nlp_parser.intent_patterns.items()
        },
        entity_types=list(nlp_parser.entity_patterns.keys()),
        time_ranges=list(nlp_parser.time_patterns.keys()),
    ).model_dump()


def parse_command(command: str) -> dict:
    """解析自然语言命令（**纯函数**，薄封装源 ``nlp_parser.parse_command``）

    - 空白文本直接 ``BadRequestError``（源解析器不会自校验，这里补上）；
    - 无法识别意图时，源解析器会在结果里带 ``error`` 字段，原样透出。
    """
    text = (command or "").strip()
    if not text:
        raise BadRequestError("命令文本不能为空")
    raw = nlp_parser.parse_command(text)
    return NlpParseResultOut.model_validate(raw).model_dump()


def evaluate_user_vip(*, vip_level: Optional[int], vip_expires_at: Any = None) -> bool:
    """判定用户是否为 VIP（**纯函数**，真实复用 ``user_defs.is_vip``）

    源函数会处理 ``vip_expires_at`` 为字符串 / ``datetime`` / 缺失与解析失败的情形；
    这里构造一个仅含这两个属性的轻量对象传给它，**不重写**判定逻辑。
    """
    holder = types.SimpleNamespace(vip_level=vip_level, vip_expires_at=vip_expires_at)
    return bool(user_defs.is_vip(holder))


def expand_pattern(pattern: Any) -> dict:
    """把区块模式行对象展开为前端字典（**纯函数**）

    真实复用源 ``block_pattern_defs.to_pattern_dict``：``blocks`` 由 JSON 文本解析为列表，
    ``keywords`` 由逗号分隔文本解析为列表。
    """
    raw = block_pattern_defs.to_pattern_dict(_PatternDefsAdapter(pattern))
    return BlockPatternDefOut.model_validate(raw).model_dump(mode="json")


# ------------------------------------------------------------------ 服务（DB 读写）
class UtilityService:
    """utility 的真表读取（按主键读区块模式 / 用户 / 文章正文）"""

    async def block_pattern(self, db: AsyncSession, pattern_id: int) -> dict:
        """读取区块模式并展开定义（``blocks`` / ``keywords`` 解析为列表）"""
        row = await db.get(BlockPattern, pattern_id)
        if row is None:
            raise NotFoundError("区块模式不存在")
        return expand_pattern(row)

    async def user_vip_status(self, db: AsyncSession, user_id: int) -> dict:
        """读取用户并判定 VIP（调用源 ``user_defs.is_vip``）"""
        user = await db.get(User, user_id)
        if user is None:
            raise NotFoundError("用户不存在")
        expires = user.vip_expires_at
        return UserVipStatusOut(
            user_id=user.id,
            is_vip=evaluate_user_vip(vip_level=user.vip_level, vip_expires_at=expires),
            vip_level=user.vip_level,
            vip_expires_at=expires,
        ).model_dump(mode="json")

    async def article_markdown(
        self,
        db: AsyncSession,
        article_id: int,
        *,
        language: Optional[str] = None,
        include_title: bool = True,
    ) -> dict:
        """取文章正文（真表 ``article_content``）供 controller 交给 ``send_chunk_md`` 导出

        - ``language`` 指定时按 ``language_code`` 精确取；未命中直接 ``NotFoundError``；
        - 未指定时取第一条内容；
        - ``include_title`` 为真且正文未以 ``#`` 开头时，前置一级标题。
        """
        article = await db.get(Article, article_id)
        if article is None:
            raise NotFoundError("文章不存在")

        rows = (
            await db.execute(
                select(ArticleContent).where(ArticleContent.article == article_id)
            )
        ).scalars().all()
        if not rows:
            raise NotFoundError("文章内容不存在")

        content_row = rows[0]
        if language:
            matched = next((row for row in rows if row.language_code == language), None)
            if matched is None:
                raise NotFoundError(f"文章没有 language_code={language} 的内容")
            content_row = matched

        body = content_row.content or ""
        title = article.title or f"article-{article_id}"
        if include_title and body and not body.lstrip().startswith("#"):
            body = f"# {title}\n\n{body}"

        return {
            "article_id": article_id,
            "title": title,
            "language_code": content_row.language_code,
            "content": body,
            "aid": str(article_id),
            "iso": language or None,
        }


utility_service = UtilityService()
