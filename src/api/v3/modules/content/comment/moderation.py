"""内容自动审核（真实词库 + 可解释规则）

与 v2 的 ``shared/services/security/content_moderation.py`` 的区别：v2 的敏感词是
**硬编码示例集**（改词要改代码），这里读 ``sensitive_words`` 真表（后台可维护，带级别与
处理方式），并把结果**真的写回评论**（``spam_score`` / ``spam_reasons``），低分评论自动
进入待审核而不是无条件 ``is_approved=True``。

规则（命中即扣分并记录原因，全部可解释）：

  - **敏感词**：按词条级别扣分（1→10 / 2→25 / 3→50）；``action=block`` 直接判定不可通过
  - **刷屏特征**：感叹号/问号过多、ASCII 大写占比过高、内容重复度过高
  - **广告特征**：链接密度过高、短内容带链接、联系方式与营销关键词

分数语义：``>=80`` 自动通过；``40~79`` 进待审核；``<40`` 或命中 ``block`` 词一律待审核。
"""

import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.security.sensitive_word import SensitiveWord
from src.api.v3.core.logger import get_logger

logger = get_logger("comment.moderation")

#: 词库进程内缓存存活时间（秒）—— 审核位于评论提交热路径，避免每次查库
WORD_CACHE_TTL_SECONDS = 60

#: 自动通过阈值：>= AUTO_HOLD_BELOW 视为安全；< AUTO_REJECT_BELOW 视为高危
AUTO_HOLD_BELOW = 80
AUTO_REJECT_BELOW = 40

#: 敏感词级别 → 扣分
_LEVEL_PENALTY = {1: 10, 2: 25, 3: 50}

#: 广告/联系方式特征：(正则, 扣分, 说明)
_AD_PATTERNS: Tuple[Tuple[str, int, str], ...] = (
    (r"(加|扫)\s*(微信|weixin|wechat|qq|vx|v信)", 30, "广告：引导添加联系方式"),
    (r"(微信号|联系电话|手机号|支付宝账号)", 20, "广告：联系方式关键词"),
    (r"(免费|秒杀|优惠券|返利|刷单|代购|包过|私聊)", 15, "广告：营销词"),
)

_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)


def _repetition_ratio(text: str, chunk: int = 4) -> float:
    """相邻 ``chunk`` 片段的重复比例（0~1）"""
    if len(text) < chunk * 2:
        return 0.0
    pieces = [text[i:i + chunk] for i in range(0, len(text) - chunk + 1, chunk)]
    if len(pieces) < 2:
        return 0.0
    return 1 - (len(set(pieces)) / len(pieces))


def moderate_text(
    text: str, *, words: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """纯函数：给文本打分并给出可解释原因（不触碰 DB，便于测试与复用）

    返回 ``{"score": 0~100, "is_safe": bool, "blocked": bool, "issues": [...],
    "suggested_approved": bool}``。
    """
    content = (text or "").strip()
    issues: List[Dict[str, Any]] = []
    score = 100
    blocked = False

    # 1) 敏感词
    for item in words or []:
        word = str(item.get("word") or "").strip()
        if not word or word not in content:
            continue
        level = int(item.get("level") or 1)
        action = str(item.get("action") or "block").lower()
        penalty = _LEVEL_PENALTY.get(level, 10)
        score -= penalty
        if action == "block":
            blocked = True
        issues.append({
            "type": "sensitive_word",
            "word": word,
            "level": level,
            "action": action,
            "penalty": penalty,
            "message": f"命中敏感词「{word}」（级别 {level}，处理方式 {action}）",
        })

    # 2) 刷屏特征
    if content.count("!") + content.count("！") >= 5:
        score -= 10
        issues.append({"type": "spam", "reason": "exclamation_marks", "message": "感叹号过多（≥5）"})
    if content.count("?") + content.count("？") >= 5:
        score -= 10
        issues.append({"type": "spam", "reason": "question_marks", "message": "问号过多（≥5）"})

    letters = [ch for ch in content if ch.isascii() and ch.isalpha()]
    if len(letters) >= 10:
        caps_ratio = sum(1 for ch in letters if ch.isupper()) / len(letters)
        if caps_ratio >= 0.7:
            score -= 15
            issues.append({
                "type": "spam",
                "reason": "caps_ratio",
                "message": f"大写字母占比过高（{caps_ratio:.0%}）",
            })

    if _repetition_ratio(content) >= 0.5 and len(content) >= 20:
        score -= 15
        issues.append({"type": "spam", "reason": "repetition", "message": "内容重复度过高"})

    # 3) 链接与广告
    links = _URL_RE.findall(content)
    if links:
        density = sum(len(url) for url in links) / max(len(content), 1)
        if density >= 0.3:
            score -= 20
            issues.append({
                "type": "ads",
                "reason": "link_density",
                "message": f"链接密度过高（{density:.0%}）",
            })
        if len(content) <= 40:
            score -= 15
            issues.append({"type": "ads", "reason": "short_with_link", "message": "内容过短且含链接"})

    for pattern, penalty, message in _AD_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            score -= penalty
            issues.append({"type": "ads", "reason": pattern[:24], "message": message})

    score = max(0, min(100, score))
    suggested = (not blocked) and score >= AUTO_HOLD_BELOW
    return {
        "score": score,
        "is_safe": score >= AUTO_HOLD_BELOW and not blocked,
        "blocked": blocked,
        "issues": issues,
        "suggested_approved": suggested,
    }


class ContentModerationService:
    """内容审核：词库读取（带缓存）+ 打分 + 评论字段组装"""

    def __init__(self) -> None:
        self._cache: Optional[Tuple[datetime, List[Dict[str, Any]]]] = None

    async def load_words(self, db: AsyncSession, *, force: bool = False) -> List[Dict[str, Any]]:
        """读取启用中的敏感词（进程内短 TTL 缓存；``force=True`` 强制刷新）"""
        now = datetime.now()
        if not force and self._cache is not None and self._cache[0] > now:
            return self._cache[1]

        rows = (
            await db.execute(select(SensitiveWord).where(SensitiveWord.is_active.is_(True)))
        ).scalars().all()
        words = [
            {
                "word": row.word,
                "level": row.level,
                "action": row.action,
                "category": row.category,
            }
            for row in rows
            if row.word
        ]
        self._cache = (now + timedelta(seconds=WORD_CACHE_TTL_SECONDS), words)
        return words

    def invalidate_cache(self) -> None:
        """词库变更（后台增删改/批量导入）后调用，让下次审核读到新词"""
        self._cache = None

    async def moderate(self, db: AsyncSession, text: str) -> Dict[str, Any]:
        """对文本做一次完整审核（词库来自 DB）"""
        words = await self.load_words(db)
        result = moderate_text(text, words=words)
        result["checked_words"] = len(words)
        return result

    async def moderate_comment(
        self, db: AsyncSession, content: str, *, auto_approve: bool = False
    ) -> Dict[str, Any]:
        """评论提交前的审核：返回应写入评论表的字段（``spam_score`` / ``spam_reasons`` / ``is_approved``）"""
        result = await self.moderate(db, content)
        reasons = [str(issue.get("message")) for issue in result["issues"]][:5]
        return {
            "spam_score": result["score"],
            "spam_reasons": (json.dumps(reasons, ensure_ascii=False)[:255] or None) if reasons else None,
            "is_approved": True if auto_approve else result["suggested_approved"],
            "result": result,
        }


content_moderation_service = ContentModerationService()
