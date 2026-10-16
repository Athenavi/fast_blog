"""translation 模块业务逻辑：i18n 词条 / 本地化 / 导入导出 / 进度 / 记忆库 / 机器翻译

对齐 v2 的翻译能力（源码在 ``shared/services/translation/**`` 与 ``shared/utils/translation_api_clients.py``），
但把它们的**内存态 / 文件态**实现整体改为**真表落点 + 真实计算**。

**与 v2 的差异（逐项对照）**

| v2 的做法 | 问题 | 本模块 |
|---|---|---|
| ``i18n_service.TranslationService`` 把语言包读写到 ``./translations/<lang>.json`` **文件**，且模块导入时 ``os.makedirs`` 建目录 | 多 worker 各写一份、容器只读挂载即失败、无版本与并发控制 | 语言包/词条落 ``system_settings`` 键 ``translation.bundles``（JSON 对象），无文件系统依赖 |
| ``localization_service`` 的时区/日期/货币表是**类内常量** | 无法配置 | 内置常量（照搬 v2 表）作为默认，自定义区域落 ``translation.locales`` |
| ``translation_io`` 只是「把 list[dict] 转字符串」，不落库 | 导入导出与真实词条脱节 | 导出**真表词条**为 CSV(带 BOM+中文表头)/JSON/PO/XLIFF/YAML；导入解析后真实落库 |
| ``translation_progress.TranslationProgressTracker`` 是**进程内字典** | 重启即失 | 进度直接由 ``translation.bundles`` 里每条词条的 ``status`` 派生（真实计算），贡献者从词条作者聚合 |
| ``translation_memory.TranslationMemoryService`` 读写 ``plugins_data/translation_memory.json`` 文件 | 同文件问题 | 记忆库落 ``system_settings`` 键 ``translation.memory``；相似匹配为**纯函数**打分 |
| ``machine_translation.MachineTranslationService`` 把「已翻译」结果塞进 `self.translation_memory`（**内存**假缓存），且缺密钥时静默返回原文 | 缓存重启即失；缺配置时把原文当译文返回 | 记忆库独立持久化；**缺密钥时如实返回 available=false + 原因，绝不返回占位译文** |

**纯函数与 DB 分离**：语言识别回退链、翻译记忆精确/模糊打分、进度百分比、缺失/未翻译 diff、
导入导出解析与生成、数字/货币/相对时间格式化全部是模块级纯函数（便于测试），
DB 读写集中在 :class:`TranslationService`。

**存储键（均 ``system_settings``，``setting_type=json``）**

  - ``translation.bundles``  语言包 ``{locale: {key: {value, status, translator_id, translator_name, updated_at}}}``
  - ``translation.memory``   记忆库 ``{"src_tgt": [{source, target, context, created_at, updated_at, usage_count}]}``
  - ``translation.locales``  自定义区域 ``[{code, name, native_name, direction}]``
  - ``translation.settings`` 模块设置 ``{default_language, source_locale, similarity_threshold}``

**机器翻译**：仅当为目标提供商配置了对应环境变量时才真实调用外部 API；
未配置时端点返回 ``available=false`` 与所需环境变量名，**绝不伪造译文**。
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.system.setting.service import setting_service

logger = get_logger("system.translation")

# ================================================================== 存储键
BUNDLES_KEY = "translation.bundles"
MEMORY_KEY = "translation.memory"
LOCALES_KEY = "translation.locales"
SETTINGS_KEY = "translation.settings"

#: 模块默认设置（``translation.settings`` 缺项时的兜底）
DEFAULT_SETTINGS: Dict[str, Any] = {
    "default_language": "en",
    "source_locale": "en",
    "similarity_threshold": 0.7,
}

#: 支持的导出/导入格式
SUPPORTED_FORMATS: Tuple[str, ...] = ("json", "csv", "po", "xliff", "yaml")

#: 词条状态（对齐 v2 ``translation_manager`` 的 status 字段）
VALID_STATUSES: Tuple[str, ...] = ("translated", "pending", "reviewed")

#: 进度里「已完成」的状态
_DONE_STATUSES = frozenset({"translated", "reviewed"})

#: 记忆库单次相似匹配最多返回条数（对齐 v2 ``MAX_SUGGESTIONS``）
MAX_MEMORY_SUGGESTIONS = 10
#: 记忆库默认相似度阈值（对齐 v2 ``DEFAULT_SIMILARITY_THRESHOLD``）
DEFAULT_SIMILARITY_THRESHOLD = 0.7
#: 进度返回的未翻译键上限（对齐 v2 ``get_language_progress`` 的 50）
MAX_UNTRANSLATED_KEYS = 50

#: 平台支持的语言（合并 v2 ``i18n_service`` 与 ``translation_manager`` 两份清单，取并集）
DEFAULT_LANGUAGES: List[Dict[str, str]] = [
    {"code": "en", "name": "English", "native_name": "English", "direction": "ltr"},
    {"code": "zh-CN", "name": "Chinese (Simplified)", "native_name": "简体中文", "direction": "ltr"},
    {"code": "zh-TW", "name": "Chinese (Traditional)", "native_name": "繁體中文", "direction": "ltr"},
    {"code": "ja", "name": "Japanese", "native_name": "日本語", "direction": "ltr"},
    {"code": "ko", "name": "Korean", "native_name": "한국어", "direction": "ltr"},
    {"code": "es", "name": "Spanish", "native_name": "Español", "direction": "ltr"},
    {"code": "fr", "name": "French", "native_name": "Français", "direction": "ltr"},
    {"code": "de", "name": "German", "native_name": "Deutsch", "direction": "ltr"},
    {"code": "ru", "name": "Russian", "native_name": "Русский", "direction": "ltr"},
    {"code": "ar", "name": "Arabic", "native_name": "العربية", "direction": "rtl"},
]

#: 本地化区域信息（照搬 v2 ``localization_service`` 的常量表，13 个地区）
LOCALE_INFO: Dict[str, Dict[str, Any]] = {
    "zh-CN": {
        "timezone": "Asia/Shanghai", "date_format": "%Y年%m月%d日",
        "datetime_format": "%Y年%m月%d日 %H:%M", "time_format": "%H:%M:%S",
        "first_day_of_week": 1, "currency_symbol": "¥", "currency_code": "CNY",
        "currency_position": "before", "number_format": {"thousands": ",", "decimal": "."},
    },
    "zh-TW": {
        "timezone": "Asia/Taipei", "date_format": "%Y年%m月%d日",
        "datetime_format": "%Y年%m月%d日 %H:%M", "time_format": "%H:%M:%S",
        "first_day_of_week": 1, "currency_symbol": "NT$", "currency_code": "TWD",
        "currency_position": "after", "number_format": {"thousands": ",", "decimal": "."},
    },
    "en-US": {
        "timezone": "America/New_York", "date_format": "%B %d, %Y",
        "datetime_format": "%B %d, %Y %I:%M %p", "time_format": "%I:%M %p",
        "first_day_of_week": 0, "currency_symbol": "$", "currency_code": "USD",
        "currency_position": "before", "number_format": {"thousands": ",", "decimal": "."},
    },
    "en-GB": {
        "timezone": "Europe/London", "date_format": "%d %B %Y",
        "datetime_format": "%d %B %Y %H:%M", "time_format": "%H:%M",
        "first_day_of_week": 1, "currency_symbol": "£", "currency_code": "GBP",
        "currency_position": "before", "number_format": {"thousands": ",", "decimal": "."},
    },
    "ja-JP": {
        "timezone": "Asia/Tokyo", "date_format": "%Y年%m月%d日",
        "datetime_format": "%Y年%m月%d日 %H:%M", "time_format": "%H:%M",
        "first_day_of_week": 0, "currency_symbol": "¥", "currency_code": "JPY",
        "currency_position": "before", "number_format": {"thousands": ",", "decimal": "."},
    },
    "ko-KR": {
        "timezone": "Asia/Seoul", "date_format": "%Y년 %m월 %d일",
        "datetime_format": "%Y년 %m월 %d일 %H:%M", "time_format": "%H:%M",
        "first_day_of_week": 0, "currency_symbol": "₩", "currency_code": "KRW",
        "currency_position": "before", "number_format": {"thousands": ",", "decimal": "."},
    },
    "fr-FR": {
        "timezone": "Europe/Paris", "date_format": "%d %B %Y",
        "datetime_format": "%d %B %Y %H:%M", "time_format": "%H:%M",
        "first_day_of_week": 1, "currency_symbol": "€", "currency_code": "EUR",
        "currency_position": "before", "number_format": {"thousands": " ", "decimal": ","},
    },
    "de-DE": {
        "timezone": "Europe/Berlin", "date_format": "%d. %B %Y",
        "datetime_format": "%d. %B %Y %H:%M", "time_format": "%H:%M",
        "first_day_of_week": 1, "currency_symbol": "€", "currency_code": "EUR",
        "currency_position": "before", "number_format": {"thousands": ".", "decimal": ","},
    },
    "es-ES": {
        "timezone": "Europe/Madrid", "date_format": "%d de %B de %Y",
        "datetime_format": "%d de %B de %Y %H:%M", "time_format": "%H:%M",
        "first_day_of_week": 1, "currency_symbol": "€", "currency_code": "EUR",
        "currency_position": "before", "number_format": {"thousands": ".", "decimal": ","},
    },
    "pt-BR": {
        "timezone": "America/Sao_Paulo", "date_format": "%d de %B de %Y",
        "datetime_format": "%d de %B de %Y %H:%M", "time_format": "%H:%M",
        "first_day_of_week": 0, "currency_symbol": "R$", "currency_code": "BRL",
        "currency_position": "before", "number_format": {"thousands": ".", "decimal": ","},
    },
    "ru-RU": {
        "timezone": "Europe/Moscow", "date_format": "%d %B %Y г.",
        "datetime_format": "%d %B %Y г. %H:%M", "time_format": "%H:%M",
        "first_day_of_week": 1, "currency_symbol": "₽", "currency_code": "RUB",
        "currency_position": "after", "number_format": {"thousands": " ", "decimal": ","},
    },
    "ar-SA": {
        "timezone": "Asia/Riyadh", "date_format": "%d %B %Y",
        "datetime_format": "%d %B %Y %H:%M", "time_format": "%H:%M",
        "first_day_of_week": 6, "currency_symbol": "﷼", "currency_code": "SAR",
        "currency_position": "after", "number_format": {"thousands": ",", "decimal": "."},
    },
    "hi-IN": {
        "timezone": "Asia/Kolkata", "date_format": "%d %B %Y",
        "datetime_format": "%d %B %Y %H:%M", "time_format": "%H:%M",
        "first_day_of_week": 0, "currency_symbol": "₹", "currency_code": "INR",
        "currency_position": "after", "number_format": {"thousands": ",", "decimal": "."},
    },
}

#: 相对时间文案（照搬 v2，缺地区时回退 en-US）
RELATIVE_TEXTS: Dict[str, Dict[str, str]] = {
    "zh-CN": {
        "just_now": "刚刚", "minute": "分钟前", "hour": "小时前", "day": "天前",
        "week": "周前", "month": "个月前", "year": "年前",
    },
    "en-US": {
        "just_now": "just now", "minute": " minute ago", "hour": " hour ago",
        "day": " day ago", "week": " week ago", "month": " month ago", "year": " year ago",
    },
    "ja-JP": {
        "just_now": "たった今", "minute": "分前", "hour": "時間前", "day": "日前",
        "week": "週間前", "month": "ヶ月前", "year": "年前",
    },
}

#: 导出格式 → (media_type, 文件扩展名)
EXPORT_FORMATS: Dict[str, Tuple[str, str]] = {
    "json": ("application/json", "json"),
    "csv": ("text/csv; charset=utf-8", "csv"),
    "po": ("text/x-gettext-translation; charset=utf-8", "po"),
    "xliff": ("application/xliff+xml; charset=utf-8", "xliff"),
    "yaml": ("application/x-yaml; charset=utf-8", "yaml"),
}

# ================================================================== 机器翻译
#: 支持的机器翻译提供商（键 → 名称 / 密钥环境变量 / API 地址），照搬 v2 配置
MT_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "baidu": {
        "name": "百度翻译",
        "env": ("BAIDU_TRANSLATE_APP_ID", "BAIDU_TRANSLATE_SECRET_KEY"),
        "url": "https://fanyi-api.baidu.com/api/trans/vip/translate",
    },
    "youdao": {
        "name": "有道翻译",
        "env": ("YOUDAO_TRANSLATE_APP_KEY", "YOUDAO_TRANSLATE_APP_SECRET"),
        "url": "https://openapi.youdao.com/api",
    },
    "deepl": {
        "name": "DeepL",
        "env": ("DEEPL_AUTH_KEY",),
        "url": "https://api-free.deepl.com/v2/translate",
    },
    "google": {
        "name": "Google Translate",
        "env": ("GOOGLE_TRANSLATE_API_KEY",),
        "url": "https://translation.googleapis.com/language/translate/v2",
    },
}

#: 百度翻译语言代码映射（照搬 v2）
BAIDU_LANG_MAP: Dict[str, str] = {
    "en": "en", "zh-CN": "zh", "zh-TW": "cht", "ja": "jp", "ko": "kor",
    "fr": "fra", "de": "de", "es": "spa", "ru": "ru", "ar": "ara",
}


def provider_status(provider: str) -> Dict[str, Any]:
    """某提供商的密钥就绪情况（**只读环境变量，不返回明文**；纯函数）"""
    key = (provider or "").strip().lower()
    spec = MT_PROVIDERS.get(key)
    if spec is None:
        raise BadRequestError(
            f"不支持的翻译提供商「{provider}」（可选：{sorted(MT_PROVIDERS)}）"
        )
    present = {name: bool(os.getenv(name)) for name in spec["env"]}
    return {
        "provider": key,
        "name": spec["name"],
        "available": all(present.values()),
        "env": present,
        "required_env": list(spec["env"]),
        "url": spec["url"],
    }


def _baidu_lang(code: str) -> str:
    return BAIDU_LANG_MAP.get(code, code)


def _truncate_text(text: str, max_length: int = 20) -> str:
    """有道签名用的文本截断（照搬 v2）"""
    if len(text) <= max_length:
        return text
    return text[:10] + str(len(text)) + text[-10:]


async def _mt_baidu(text: str, source_lang: str, target_lang: str) -> Tuple[Optional[str], Optional[str]]:
    app_id = os.getenv("BAIDU_TRANSLATE_APP_ID", "")
    secret = os.getenv("BAIDU_TRANSLATE_SECRET_KEY", "")
    salt = str(random.randint(32768, 65536))
    sign = hashlib.md5(f"{app_id}{text}{salt}{secret}".encode("utf-8")).hexdigest()
    params = {
        "q": text,
        "from": _baidu_lang(source_lang),
        "to": _baidu_lang(target_lang),
        "appid": app_id,
        "salt": salt,
        "sign": sign,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(MT_PROVIDERS["baidu"]["url"], params=params)
    if resp.status_code != 200:
        return None, f"百度翻译请求失败：HTTP {resp.status_code}"
    data = resp.json()
    if "error_code" in data:
        return None, f"百度翻译错误：{data.get('error_msg', '未知错误')}"
    return "\n".join(item.get("dst", "") for item in data.get("trans_result", [])), None


async def _mt_youdao(text: str, source_lang: str, target_lang: str) -> Tuple[Optional[str], Optional[str]]:
    app_key = os.getenv("YOUDAO_TRANSLATE_APP_KEY", "")
    app_secret = os.getenv("YOUDAO_TRANSLATE_APP_SECRET", "")
    curtime = str(int(time.time()))
    salt = str(uuid.uuid1())
    sign = hashlib.sha256(
        f"{app_key}{_truncate_text(text)}{salt}{curtime}{app_secret}".encode("utf-8")
    ).hexdigest()
    params = {
        "q": text, "from": source_lang, "to": target_lang, "appKey": app_key,
        "salt": salt, "sign": sign, "signType": "v3", "curtime": curtime,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(MT_PROVIDERS["youdao"]["url"], params=params)
    if resp.status_code != 200:
        return None, f"有道翻译请求失败：HTTP {resp.status_code}"
    data = resp.json()
    if data.get("errorCode") != "0":
        return None, f"有道翻译错误：{data.get('errorCode', '未知错误')}"
    return "\n".join(data.get("translation", [])), None


async def _mt_deepl(text: str, source_lang: str, target_lang: str) -> Tuple[Optional[str], Optional[str]]:
    auth_key = os.getenv("DEEPL_AUTH_KEY", "")
    payload: Dict[str, Any] = {
        "text": [text],
        "target_lang": target_lang.upper().split("-")[0],
    }
    if source_lang and source_lang.lower() != "auto":
        payload["source_lang"] = source_lang.upper().split("-")[0]
    headers = {
        "Authorization": f"DeepL-Auth-Key {auth_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(MT_PROVIDERS["deepl"]["url"], json=payload, headers=headers)
    if resp.status_code != 200:
        return None, f"DeepL 请求失败：HTTP {resp.status_code}"
    data = resp.json()
    try:
        return data["translations"][0]["text"], None
    except (KeyError, IndexError, TypeError):
        return None, "DeepL 返回格式错误"


async def _mt_google(text: str, source_lang: str, target_lang: str) -> Tuple[Optional[str], Optional[str]]:
    params: Dict[str, Any] = {
        "key": os.getenv("GOOGLE_TRANSLATE_API_KEY", ""),
        "q": text,
        "target": target_lang,
        "format": "text",
    }
    if source_lang and source_lang != "auto":
        params["source"] = source_lang
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(MT_PROVIDERS["google"]["url"], json=params)
    if resp.status_code != 200:
        return None, f"Google 翻译请求失败：HTTP {resp.status_code}"
    data = resp.json()
    try:
        return data["data"]["translations"][0]["translatedText"], None
    except (KeyError, IndexError, TypeError):
        return None, "Google 翻译返回格式错误"


_MT_DISPATCH = {
    "baidu": _mt_baidu,
    "youdao": _mt_youdao,
    "deepl": _mt_deepl,
    "google": _mt_google,
}


async def machine_translate(
    text: str, source_lang: str, target_lang: str, provider: str
) -> Dict[str, Any]:
    """真实调用外部机器翻译 API（**绝不返回占位译文**）

    - 未知提供商 → ``BadRequestError``
    - 未配置密钥 → ``{success: False, available: False, translated_text: None, reason: ...}``
    - 有密钥 → 真实 HTTP 调用；调用或解析失败**如实**返回错误，不透传原文
    """
    key = (provider or "").strip().lower()
    status = provider_status(key)  # 未知提供商在此抛 400
    base: Dict[str, Any] = {
        "provider": key,
        "provider_name": status["name"],
        "source_lang": source_lang,
        "target_lang": target_lang,
    }
    if not status["available"]:
        return base | {
            "success": False,
            "available": False,
            "translated_text": None,
            "reason": f"未配置 {status['name']} 密钥（需环境变量：{', '.join(status['required_env'])}）",
        }

    try:
        translated, error = await _MT_DISPATCH[key](text, source_lang, target_lang)
    except httpx.HTTPError as exc:
        logger.warning("机器翻译网络错误 provider=%s：%s", key, exc)
        return base | {
            "success": False, "available": True, "translated_text": None,
            "reason": f"翻译服务调用失败：{exc}",
        }
    except Exception as exc:  # noqa: BLE001 - 外部服务不可预期
        logger.exception("机器翻译异常 provider=%s", key)
        return base | {
            "success": False, "available": True, "translated_text": None,
            "reason": f"翻译服务异常：{exc}",
        }

    if error is not None:
        return base | {"success": False, "available": True, "translated_text": None, "reason": error}
    return base | {"success": True, "available": True, "translated_text": translated, "reason": None}


# ================================================================== 纯函数
def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def entry_value(entry: Any) -> str:
    """从词条取译文文本（兼容 ``{value: ...}`` 字典与裸字符串）"""
    if entry is None:
        return ""
    if isinstance(entry, dict):
        value = entry.get("value")
        return "" if value is None else str(value)
    return str(entry)


def entry_status(entry: Any) -> str:
    """从词条取状态；缺省时按是否有译文本推断（有→translated，无→pending）"""
    if isinstance(entry, dict) and entry.get("status") in VALID_STATUSES:
        return str(entry["status"])
    return "translated" if entry_value(entry).strip() else "pending"


def parse_accept_language(header: Optional[str]) -> List[Tuple[str, float]]:
    """解析 ``Accept-Language``（含 q 权重），按权重降序返回 ``[(tag, q)]``（纯函数）"""
    items: List[Tuple[str, float]] = []
    for part in (header or "").split(","):
        part = part.strip()
        if not part:
            continue
        segments = part.split(";")
        tag = segments[0].strip()
        q = 1.0
        for param in segments[1:]:
            param = param.strip()
            if param.startswith("q="):
                try:
                    q = float(param[2:])
                except ValueError:
                    q = 0.0
        if tag:
            items.append((tag, q))
    # 稳定排序：权重降序，权重相同保持出现顺序
    return sorted(items, key=lambda item: -item[1])


def detect_language(
    accept_language: Optional[str],
    supported: Sequence[str],
    default_language: str = "en",
) -> str:
    """语言识别回退链（**纯函数**）

    顺序：``Accept-Language`` 按 q 降序 → 精确匹配 → 主语言匹配（``zh-CN`` → ``zh``，
    再匹配任一 ``zh*`` 受支持语言）→ 全部落空则返回 ``default_language``。
    """
    if not accept_language:
        return default_language
    codes = list(supported)
    lower_map = {code.lower(): code for code in codes}
    for tag, q in parse_accept_language(accept_language):
        if q <= 0:
            continue
        low = tag.lower()
        if low in lower_map:
            return lower_map[low]
        main = low.split("-")[0]
        if main in lower_map:
            return lower_map[main]
        for code in codes:
            if code.lower().split("-")[0] == main:
                return code
    return default_language


def resolve_translation(
    bundles: Dict[str, Dict[str, Any]],
    key: str,
    language: str,
    default_language: str,
    default: Optional[str] = None,
) -> Dict[str, Any]:
    """词条回退链（**纯函数**）：指定语言 → 默认语言 → ``default``/键本身

    返回 ``{"value", "source"}``，``source`` ∈ ``{language, default_language, "default"}``。
    """
    lang_bundle = bundles.get(language) or {}
    if key in lang_bundle and entry_value(lang_bundle[key]).strip():
        return {"value": entry_value(lang_bundle[key]), "source": language}
    if language != default_language:
        fallback = bundles.get(default_language) or {}
        if key in fallback and entry_value(fallback[key]).strip():
            return {"value": entry_value(fallback[key]), "source": default_language}
    return {"value": default if default is not None else key, "source": "default"}


def flatten_keys(data: Any, parent_key: str = "", sep: str = ".") -> List[str]:
    """把嵌套字典展平成 ``a.b.c`` 键列表（纯函数）"""
    keys: List[str] = []
    for key, value in (data or {}).items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else str(key)
        if isinstance(value, dict):
            keys.extend(flatten_keys(value, new_key, sep=sep))
        else:
            keys.append(new_key)
    return keys


def _bundle_keys(bundle: Dict[str, Any]) -> set:
    return set(bundle.keys()) if isinstance(bundle, dict) else set()


def missing_keys(bundles: Dict[str, Dict[str, Any]], locale: str, source_locale: str) -> List[str]:
    """相对源语言缺失的词条键（**纯函数**，排序后返回）"""
    source = _bundle_keys(bundles.get(source_locale) or {})
    target = _bundle_keys(bundles.get(locale) or {})
    return sorted(source - target)


def untranslated_keys(bundles: Dict[str, Dict[str, Any]], locale: str, source_locale: str) -> List[str]:
    """源语言有、但目标语言未翻译（缺失或值为空）的词条键（**纯函数**）"""
    source = _bundle_keys(bundles.get(source_locale) or {})
    target = bundles.get(locale) or {}
    result = []
    for key in sorted(source):
        if key not in target or not entry_value(target[key]).strip():
            result.append(key)
    return result


def progress_percentage(done: int, total: int) -> float:
    """完成度百分比（**纯函数**，total<=0 记 0）"""
    if total <= 0:
        return 0.0
    return round(done / total * 100, 2)


def language_progress(
    bundles: Dict[str, Dict[str, Any]], locale: str, source_locale: str
) -> Dict[str, Any]:
    """单语言进度（**纯函数**）

    对齐 v2 ``translation_manager.get_translation_progress``：分母为源语言键数，
    分子为「已翻译 + 已校对」的目标词条数。
    """
    source = _bundle_keys(bundles.get(source_locale) or {})
    target = bundles.get(locale) or {}
    status_counts = {"translated": 0, "pending": 0, "reviewed": 0}
    update_times: List[str] = []
    for entry in target.values():
        st = entry_status(entry)
        if st in status_counts:
            status_counts[st] += 1
        if isinstance(entry, dict) and entry.get("updated_at"):
            update_times.append(str(entry["updated_at"]))
    completion = progress_percentage(
        status_counts["translated"] + status_counts["reviewed"], len(source)
    )
    missing = sorted(source - set(target.keys()))
    untrans = untranslated_keys(bundles, locale, source_locale)
    return {
        "locale": locale,
        "total_keys": len(source),
        "present_keys": len(target),
        **status_counts,
        "missing_keys": missing[:MAX_UNTRANSLATED_KEYS],
        "missing_count": len(missing),
        "untranslated_keys": untrans[:MAX_UNTRANSLATED_KEYS],
        "untranslated_count": len(untrans),
        "completion_rate": completion,
        "last_updated": max(update_times) if update_times else None,
    }


def bundle_stats(
    bundles: Dict[str, Dict[str, Any]],
    languages: Sequence[str],
    source_locale: str,
) -> Dict[str, Any]:
    """全部语言的完成度统计（**纯函数**，对齐 v2 ``i18n_service.get_translation_stats``）"""
    source_keys = _bundle_keys(bundles.get(source_locale) or {})
    stats: Dict[str, Any] = {}
    for code in languages:
        entries = bundles.get(code) or {}
        keys = set(entries.keys())
        translated = sum(1 for v in entries.values() if entry_value(v).strip())
        hit = sum(1 for k in (source_keys & keys) if entry_value(entries[k]).strip())
        stats[code] = {
            "total_keys": len(entries),
            "translated_keys": translated,
            "missing_keys": len(source_keys - keys),
            "completion_rate": progress_percentage(hit, len(source_keys)),
        }
    return {
        "source_language": source_locale,
        "source_keys": len(source_keys),
        "languages": stats,
    }


def contributors(bundles: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """从词条作者聚合翻译贡献者（**纯函数**）"""
    agg: Dict[Any, Dict[str, Any]] = {}
    for entries in bundles.values():
        for entry in (entries or {}).values():
            if not isinstance(entry, dict):
                continue
            translator_id = entry.get("translator_id")
            if translator_id is None or entry_status(entry) not in _DONE_STATUSES:
                continue
            item = agg.setdefault(
                translator_id,
                {"user_id": translator_id, "name": entry.get("translator_name"),
                 "translations_count": 0, "last_contribution": None},
            )
            item["translations_count"] += 1
            if entry.get("translator_name"):
                item["name"] = entry.get("translator_name")
            updated = entry.get("updated_at")
            if updated and (item["last_contribution"] is None or str(updated) > item["last_contribution"]):
                item["last_contribution"] = str(updated)
    return sorted(agg.values(), key=lambda x: -int(x["translations_count"]))


def build_progress_report(
    bundles: Dict[str, Dict[str, Any]],
    languages: Sequence[str],
    source_locale: str,
) -> Dict[str, Any]:
    """进度报告（**纯函数**）：各语言进度 + 汇总 + 贡献者排行"""
    per_lang = [language_progress(bundles, code, source_locale) for code in languages]
    per_lang.sort(key=lambda item: item["completion_rate"], reverse=True)
    total = len(per_lang)
    completed = sum(1 for item in per_lang if item["completion_rate"] == 100)
    avg = round(sum(item["completion_rate"] for item in per_lang) / total, 2) if total else 0.0
    return {
        "summary": {
            "total_languages": total,
            "completed_languages": completed,
            "average_progress": avg,
            "generated_at": _now_iso(),
        },
        "languages": per_lang,
        "top_contributors": contributors(bundles)[:10],
    }


def generate_template(
    bundles: Dict[str, Dict[str, Any]], locale: str, default_language: str
) -> Dict[str, str]:
    """以默认语言的键生成目标语言的空模板（纯函数）"""
    source = bundles.get(default_language) or {}
    existing = bundles.get(locale) or {}
    return {key: entry_value(existing.get(key)) for key in source}


# ---------------------------------------------------------------- 记忆库打分
def levenshtein_distance(s1: str, s2: str) -> int:
    """Levenshtein 编辑距离（**纯函数**，照搬 v2 实现）"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def similarity(text1: str, text2: str) -> float:
    """归一化相似度 ``1 - 距离/最大长度``（**纯函数**）"""
    if not text1 or not text2:
        return 0.0
    if text1 == text2:
        return 1.0
    distance = levenshtein_distance(text1, text2)
    max_len = max(len(text1), len(text2))
    return max(0.0, 1 - (distance / max_len)) if max_len > 0 else 1.0


def match_memory(
    entries: Sequence[Dict[str, Any]],
    source_text: str,
    *,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    limit: int = MAX_MEMORY_SUGGESTIONS,
) -> List[Dict[str, Any]]:
    """翻译记忆的精确 / 模糊匹配打分（**纯函数**）

    - **精确匹配**（``source`` 与查询完全相同）→ ``similarity=1.0``、``match_type="exact"``；
    - **模糊匹配** → ``similarity = 1 - Levenshtein/最大长度``、``match_type="fuzzy"``；
    - 仅保留 ``similarity >= threshold`` 的条目，按相似度降序、``source`` 升序打破并列。
    """
    results: List[Dict[str, Any]] = []
    for entry in entries or []:
        source = str(entry.get("source") or "")
        if not source:
            continue
        if source == source_text:
            score, match_type = 1.0, "exact"
        else:
            score, match_type = similarity(source_text, source), "fuzzy"
        if score >= threshold:
            results.append(
                {
                    "source": source,
                    "target": str(entry.get("target") or ""),
                    "similarity": round(score, 4),
                    "match_type": match_type,
                    "context": str(entry.get("context") or ""),
                    "usage_count": int(entry.get("usage_count") or 0),
                }
            )
    results.sort(key=lambda item: (-item["similarity"], item["source"]))
    return results[:limit] if limit and limit > 0 else results


def summarize_memory(memory: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """记忆库统计（**纯函数**，对齐 v2 ``get_translation_stats``）"""
    total = sum(len(entries) for entries in (memory or {}).values())
    pairs = []
    for key, entries in (memory or {}).items():
        source_lang, _, target_lang = str(key).partition("_")
        pairs.append(
            {"pair": key, "source_lang": source_lang, "target_lang": target_lang,
             "entry_count": len(entries)}
        )
    pairs.sort(key=lambda item: -item["entry_count"])
    return {"total_entries": total, "language_pairs": len(memory or {}), "pairs_detail": pairs}


def _pair_key(source_lang: str, target_lang: str) -> str:
    return f"{source_lang}_{target_lang}"


# ---------------------------------------------------------------- 本地化格式化
def format_number(number: Any, number_format: Dict[str, str], decimals: int = 2) -> str:
    """按区域格式化数字（千位/小数分隔符；**纯函数**，照搬 v2 ``_format_number``）"""
    thousands = number_format.get("thousands", ",")
    decimal = number_format.get("decimal", ".")
    value = float(number)
    if decimals <= 0:
        integer_part = str(int(round(value)))
        decimal_part = ""
    else:
        integer_part, decimal_part = f"{value:.{decimals}f}".split(".")
        decimal_part = decimal + decimal_part
    sign = "-" if integer_part.startswith("-") else ""
    digits = integer_part.lstrip("-+")
    groups = [digits[::-1][i:i + 3] for i in range(0, len(digits), 3)]
    formatted_int = sign + thousands.join(groups)[::-1]
    return formatted_int + decimal_part


def format_currency(amount: Any, locale: str, currency_code: Optional[str] = None) -> Dict[str, Any]:
    """按区域格式化货币（**纯函数**），返回文本 + 代码 + 位置"""
    info = LOCALE_INFO.get(locale, LOCALE_INFO["en-US"])
    symbol = info["currency_symbol"]
    code = currency_code or info["currency_code"]
    text = format_number(amount, info["number_format"], 2)
    if info["currency_position"] == "after":
        rendered = f"{text} {symbol}"
    else:
        rendered = f"{symbol}{text}"
    return {"text": rendered, "symbol": symbol, "code": code, "position": info["currency_position"]}


def format_relative_time(dt: datetime, locale: str, now: Optional[datetime] = None) -> str:
    """相对时间（**纯函数**，照搬 v2 ``format_relative_time`` 的分档）"""
    texts = RELATIVE_TEXTS.get(locale, RELATIVE_TEXTS["en-US"])
    reference = now or datetime.now(timezone.utc)
    seconds = int((reference - dt).total_seconds())
    if seconds < 60:
        return texts["just_now"]
    if seconds < 3600:
        return f"{seconds // 60}{texts['minute']}"
    if seconds < 86400:
        return f"{seconds // 3600}{texts['hour']}"
    if seconds < 604800:
        return f"{seconds // 86400}{texts['day']}"
    if seconds < 2592000:
        return f"{seconds // 604800}{texts['week']}"
    if seconds < 31536000:
        return f"{seconds // 2592000}{texts['month']}"
    return f"{seconds // 31536000}{texts['year']}"


def _to_timezone(dt: datetime, timezone_name: str) -> datetime:
    """把（可能无时区的）时间转到目标时区；无时区按 UTC 处理，失败回退原值（纯函数）"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    try:
        return dt.astimezone(ZoneInfo(timezone_name))
    except (ZoneInfoNotFoundError, ValueError):
        return dt


def localize(dt: datetime, locale: str, timezone_name: Optional[str] = None,
             now: Optional[datetime] = None) -> Dict[str, Any]:
    """按区域格式化一个时间点（**纯函数**）：日期 / 时间 / 日期时间 / 相对时间 + 区域信息"""
    info = LOCALE_INFO.get(locale, LOCALE_INFO["en-US"])
    tz_name = timezone_name or info["timezone"]
    local_dt = _to_timezone(dt, tz_name)
    reference = now or datetime.now(local_dt.tzinfo or timezone.utc)
    return {
        "locale": locale,
        "timezone": tz_name,
        "date": local_dt.strftime(info["date_format"]),
        "time": local_dt.strftime(info["time_format"]),
        "datetime": local_dt.strftime(info["datetime_format"]),
        "relative": format_relative_time(dt, locale, now=reference),
        "first_day_of_week": info["first_day_of_week"],
        "currency": {
            "symbol": info["currency_symbol"],
            "code": info["currency_code"],
            "position": info["currency_position"],
        },
        "number_format": dict(info["number_format"]),
    }


def locale_public_view(locale: str) -> Dict[str, Any]:
    """区域的对外视图（含时区/货币/格式），未知区域抛 ``NotFoundError``（纯函数）"""
    info = LOCALE_INFO.get(locale)
    if info is None:
        raise NotFoundError(f"未知的区域「{locale}」")
    return {
        "locale": locale,
        "timezone": info["timezone"],
        "first_day_of_week": info["first_day_of_week"],
        "currency": {
            "symbol": info["currency_symbol"],
            "code": info["currency_code"],
            "position": info["currency_position"],
        },
        "formats": {
            "date": info["date_format"],
            "datetime": info["datetime_format"],
            "time": info["time_format"],
            "number": dict(info["number_format"]),
        },
    }


# ---------------------------------------------------------------- 导入导出
def _escape_po(text: str) -> str:
    s = str(text)
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    s = s.replace("\n", "\\n").replace("\t", "\\t")
    return s


def _unescape_po(text: str) -> str:
    s = str(text)
    s = s.replace("\\n", "\n").replace("\\t", "\t")
    s = s.replace('\\"', '"').replace("\\\\", "\\")
    return s


def _xml_local_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def render_export(locale: str, translations: Dict[str, str], fmt: str,
                  project_name: str = "FastBlog") -> Tuple[bytes, str]:
    """把 ``{key: 译文}`` 渲染成指定格式的字节内容（**纯函数**）

    返回 ``(content_bytes, media_type)``；格式非法抛 ``BadRequestError``。
    """
    kind = (fmt or "json").strip().lower()
    if kind not in SUPPORTED_FORMATS:
        raise BadRequestError(f"不支持的导出格式「{fmt}」（可选：{list(SUPPORTED_FORMATS)}）")
    data = {str(k): ("" if v is None else str(v)) for k, v in translations.items()}

    if kind == "json":
        payload = {
            "language": locale,
            "exported_at": _now_iso(),
            "total_strings": len(data),
            "translations": data,
        }
        return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"), EXPORT_FORMATS["json"][0]

    if kind == "csv":
        import csv

        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        writer.writerow(["键", "译文"])
        for key in sorted(data):
            writer.writerow([key, data[key]])
        text = "\ufeff" + buffer.getvalue()  # 带 UTF-8 BOM，Excel 正确识别中文
        return text.encode("utf-8"), EXPORT_FORMATS["csv"][0]

    if kind == "po":
        lines = [
            "# FastBlog Translation File",
            f"# Language: {locale}",
            f"# Generated at: {_now_iso()}",
            "",
            'msgid ""',
            'msgstr ""',
            f'"Project-Id-Version: {project_name} 1.0\\n"',
            f'"Language: {locale}\\n"',
            '"Content-Type: text/plain; charset=UTF-8\\n"',
            '"Content-Transfer-Encoding: 8bit\\n"',
            "",
        ]
        for key in sorted(data):
            lines.append(f'msgid "{_escape_po(key)}"')
            lines.append(f'msgstr "{_escape_po(data[key])}"')
            lines.append("")
        return "\n".join(lines).encode("utf-8"), EXPORT_FORMATS["po"][0]

    if kind == "xliff":
        import xml.etree.ElementTree as ET

        root = ET.Element("xliff", {"version": "1.2", "xmlns": "urn:oasis:names:tc:xliff:document:1.2"})
        file_el = ET.SubElement(
            root,
            "file",
            {"source-language": DEFAULT_SETTINGS["source_locale"], "target-language": locale,
             "datatype": "plaintext", "original": "messages"},
        )
        body = ET.SubElement(file_el, "body")
        for key in sorted(data):
            unit = ET.SubElement(body, "trans-unit", {"id": key})
            ET.SubElement(unit, "source").text = key
            ET.SubElement(unit, "target").text = data[key]
        ET.indent(root)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True), EXPORT_FORMATS["xliff"][0]

    # yaml（若未安装 PyYAML 则如实报错）
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - 依赖环境
        raise BadRequestError("未安装 PyYAML，暂不支持 yaml 导出") from exc
    payload = {
        "language": locale,
        "exported_at": _now_iso(),
        "total_strings": len(data),
        "translations": data,
    }
    return yaml.dump(payload, allow_unicode=True, default_flow_style=False).encode("utf-8"), EXPORT_FORMATS["yaml"][0]


def parse_import(content: str, fmt: str) -> Dict[str, Any]:
    """解析导入内容为 ``{language?, translations}``（**纯函数**）

    支持 json / csv / po / xliff / yaml；解析失败抛 ``BadRequestError``（不静默吞错）。
    """
    kind = (fmt or "json").strip().lower()
    if kind not in SUPPORTED_FORMATS:
        raise BadRequestError(f"不支持的导入格式「{fmt}」（可选：{list(SUPPORTED_FORMATS)}）")
    text = content or ""

    if kind == "json":
        try:
            data = json.loads(text)
        except (ValueError, json.JSONDecodeError) as exc:
            raise BadRequestError(f"JSON 解析失败：{exc}") from exc
        if not isinstance(data, dict):
            raise BadRequestError("JSON 内容必须是对象")
        translations = data.get("translations", data)
        if not isinstance(translations, dict):
            raise BadRequestError("translations 必须是对象")
        return {"language": data.get("language"),
                "translations": {str(k): entry_value(v) for k, v in translations.items()}}

    if kind == "csv":
        import csv

        reader = csv.reader(io.StringIO(text.lstrip("\ufeff")))
        translations: Dict[str, str] = {}
        for index, row in enumerate(reader):
            if not row:
                continue
            if index == 0 and str(row[0]).strip() in {"键", "key", "Key", "msgid"}:
                continue
            key = str(row[0]).strip()
            if not key:
                continue
            translations[key] = str(row[1]) if len(row) > 1 else ""
        if not translations:
            raise BadRequestError("CSV 未解析到任何词条")
        return {"language": None, "translations": translations}

    if kind == "po":
        translations = {}
        current_msgid: Optional[str] = None
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith('msgid "'):
                current_msgid = _unescape_po(stripped[7:-1])
            elif stripped.startswith('msgstr "') and current_msgid is not None:
                # 空 msgid 是 PO 文件头（元数据），不是词条，必须跳过
                if current_msgid:
                    translations[current_msgid] = _unescape_po(stripped[8:-1])
                current_msgid = None
        if not translations:
            raise BadRequestError("PO 未解析到任何词条")
        return {"language": None, "translations": translations}

    if kind == "xliff":
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            raise BadRequestError(f"XLIFF 解析失败：{exc}") from exc
        translations = {}
        for unit in root.iter():
            if _xml_local_tag(unit.tag) != "trans-unit":
                continue
            unit_id = unit.get("id")
            target = ""
            for child in unit:
                if _xml_local_tag(child.tag) == "target":
                    target = child.text or ""
                    break
            if unit_id is not None:
                translations[str(unit_id)] = target
        if not translations:
            raise BadRequestError("XLIFF 未解析到任何 trans-unit")
        return {"language": None, "translations": translations}

    # yaml
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise BadRequestError("未安装 PyYAML，暂不支持 yaml 导入") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise BadRequestError(f"YAML 解析失败：{exc}") from exc
    if not isinstance(data, dict):
        raise BadRequestError("YAML 内容必须是映射")
    translations = data.get("translations", data)
    if not isinstance(translations, dict):
        raise BadRequestError("translations 必须是映射")
    return {"language": data.get("language"), "translations": {str(k): entry_value(v) for k, v in translations.items()}}


def normalize_entry(
    value: str,
    status: Optional[str] = None,
    translator_id: Optional[int] = None,
    translator_name: Optional[str] = None,
) -> Dict[str, Any]:
    """规范化词条结构（**纯函数**）"""
    text = "" if value is None else str(value)
    if status is None:
        status = "translated" if text.strip() else "pending"
    return {
        "value": text,
        "status": status,
        "translator_id": translator_id,
        "translator_name": translator_name,
        "updated_at": _now_iso(),
    }


# ================================================================== 服务
class TranslationService:
    """翻译：i18n 词条 / 本地化 / 导入导出 / 进度 / 记忆库 / 机器翻译（system 域，复用 ``system_settings``）"""

    # ------------------------------------------------------------ 存储
    async def _load_json(self, db: AsyncSession, key: str, default: Any) -> Any:
        try:
            setting = await setting_service.get_setting(db, key)
        except Exception:  # noqa: BLE001 - 键不存在时用默认值
            return default
        value = setting.get("parsed_value")
        return default if value is None else value

    async def _save_json(self, db: AsyncSession, key: str, value: Any, description: str) -> None:
        await setting_service.upsert(
            db,
            key,
            value=json.dumps(value, ensure_ascii=False),
            setting_type="json",
            description=description,
            is_public=False,
        )

    async def settings(self, db: AsyncSession) -> Dict[str, Any]:
        stored = await self._load_json(db, SETTINGS_KEY, {})
        merged = dict(DEFAULT_SETTINGS)
        if isinstance(stored, dict):
            merged.update(stored)
        return merged

    async def _load_bundles(self, db: AsyncSession) -> Dict[str, Dict[str, Any]]:
        value = await self._load_json(db, BUNDLES_KEY, {})
        return value if isinstance(value, dict) else {}

    async def _load_memory(self, db: AsyncSession) -> Dict[str, List[Dict[str, Any]]]:
        value = await self._load_json(db, MEMORY_KEY, {})
        return value if isinstance(value, dict) else {}

    # ------------------------------------------------------------ 语言 / 区域
    async def languages(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """内置语言 + 自定义语言（自定义同 ``code`` 覆盖内置）"""
        custom = await self._load_json(db, LOCALES_KEY, [])
        merged: Dict[str, Dict[str, Any]] = {item["code"]: dict(item) for item in DEFAULT_LANGUAGES}
        order = [item["code"] for item in DEFAULT_LANGUAGES]
        for raw in custom if isinstance(custom, list) else []:
            if not isinstance(raw, dict):
                continue
            code = str(raw.get("code") or "").strip()
            if not code:
                continue
            if code not in merged:
                order.append(code)
            merged[code] = {
                "code": code,
                "name": str(raw.get("name") or code),
                "native_name": str(raw.get("native_name") or raw.get("name") or code),
                "direction": "rtl" if str(raw.get("direction")) == "rtl" else "ltr",
            }
        default = (await self.settings(db))["default_language"]
        return [merged[code] | {"is_default": code == default} for code in order]

    async def upsert_language(self, db: AsyncSession, payload: Any, *, user_id: Optional[int] = None) -> Dict[str, Any]:
        """新增 / 覆盖一个自定义语言（未知字段直接 400）"""
        if not isinstance(payload, dict) or not payload:
            raise BadRequestError("请求体不能为空")
        allowed = ("code", "name", "native_name", "direction")
        unknown = [k for k in payload if k not in allowed]
        if unknown:
            raise BadRequestError(f"未知字段：{unknown}（可选：{list(allowed)}）")
        code = str(payload.get("code") or "").strip()
        if not code:
            raise BadRequestError("code 不能为空")
        direction = str(payload.get("direction") or "ltr")
        if direction not in ("ltr", "rtl"):
            raise BadRequestError("direction 只能是 ltr / rtl")

        item = {
            "code": code,
            "name": str(payload.get("name") or code),
            "native_name": str(payload.get("native_name") or payload.get("name") or code),
            "direction": direction,
        }
        custom = await self._load_json(db, LOCALES_KEY, [])
        custom = custom if isinstance(custom, list) else []
        replaced = False
        for index, existing in enumerate(custom):
            if isinstance(existing, dict) and str(existing.get("code")) == code:
                custom[index] = item
                replaced = True
                break
        if not replaced:
            custom.append(item)
        await self._save_json(db, LOCALES_KEY, custom, "自定义语言区域（system/translation）")
        logger.info("语言区域已保存 code=%s user=%s", code, user_id)
        is_builtin = any(item_["code"] == code for item_ in DEFAULT_LANGUAGES)
        return {"code": code, "action": "updated" if replaced else "created", "overrides_builtin": is_builtin}

    async def detect(self, db: AsyncSession, accept_language: Optional[str]) -> Dict[str, Any]:
        codes = [item["code"] for item in await self.languages(db)]
        default = (await self.settings(db))["default_language"]
        detected = detect_language(accept_language, codes, default)
        return {"accept_language": accept_language or "", "language": detected, "default_language": default}

    def locales(self) -> List[Dict[str, Any]]:
        return [locale_public_view(code) for code in LOCALE_INFO]

    # ------------------------------------------------------------ 词条 / 语言包
    async def get_entry(self, db: AsyncSession, key: str, locale: Optional[str], default: Optional[str]) -> Dict[
        str, Any]:
        bundles = await self._load_bundles(db)
        settings = await self.settings(db)
        language = locale or settings["default_language"]
        resolved = resolve_translation(bundles, key, language, settings["default_language"], default)
        return {"key": key, "locale": language, **resolved}

    async def get_bundle(self, db: AsyncSession, locale: str) -> Dict[str, Any]:
        bundles = await self._load_bundles(db)
        entries = bundles.get(locale) or {}
        status_counts: Dict[str, int] = {}
        for entry in entries.values():
            st = entry_status(entry)
            status_counts[st] = status_counts.get(st, 0) + 1
        return {
            "locale": locale,
            "count": len(entries),
            "status_counts": status_counts,
            "entries": {key: entry_value(value) for key, value in sorted(entries.items())},
        }

    async def set_entry(self, db: AsyncSession, payload: Any, *, user_id: Optional[int] = None) -> Dict[str, Any]:
        """写入单个词条（未知字段直接 400，不是静默丢弃）"""
        if not isinstance(payload, dict) or not payload:
            raise BadRequestError("请求体不能为空")
        allowed = ("locale", "key", "value", "status", "translator_id", "translator_name")
        unknown = [k for k in payload if k not in allowed]
        if unknown:
            raise BadRequestError(f"未知字段：{unknown}（可选：{list(allowed)}）")
        locale = str(payload.get("locale") or "").strip()
        key = str(payload.get("key") or "").strip()
        if not locale:
            raise BadRequestError("locale 不能为空")
        if not key:
            raise BadRequestError("key 不能为空")
        status = payload.get("status")
        if status is not None and status not in VALID_STATUSES:
            raise BadRequestError(f"status 只能是 {list(VALID_STATUSES)}")

        bundles = await self._load_bundles(db)
        bucket = bundles.setdefault(locale, {})
        if not isinstance(bucket, dict):
            bucket = {}
            bundles[locale] = bucket
        bucket[key] = normalize_entry(
            payload.get("value", ""),
            status=status,
            translator_id=payload.get("translator_id"),
            translator_name=payload.get("translator_name"),
        )
        await self._save_json(db, BUNDLES_KEY, bundles, "翻译语言包（system/translation）")
        logger.info("词条已保存 locale=%s key=%s user=%s", locale, key, user_id)
        return {"locale": locale, "key": key, "entry": bucket[key]}

    async def replace_bundle(self, db: AsyncSession, locale: str, payload: Any, *, user_id: Optional[int] = None) -> \
    Dict[str, Any]:
        """整体覆盖 / 合并一个语言包（未知字段直接 400）"""
        if not isinstance(payload, dict) or not payload:
            raise BadRequestError("请求体不能为空")
        allowed = ("data", "merge", "status")
        unknown = [k for k in payload if k not in allowed]
        if unknown:
            raise BadRequestError(f"未知字段：{unknown}（可选：{list(allowed)}）")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise BadRequestError("data 必须是 JSON 对象")
        merge = bool(payload.get("merge", True))
        status = payload.get("status")
        if status is not None and status not in VALID_STATUSES:
            raise BadRequestError(f"status 只能是 {list(VALID_STATUSES)}")

        bundles = await self._load_bundles(db)
        bucket = bundles.get(locale) if merge else {}
        if not isinstance(bucket, dict):
            bucket = {}
        for key, value in data.items():
            bucket[str(key)] = normalize_entry(
                value, status=status, translator_id=user_id, translator_name=None
            )
        bundles[locale] = bucket
        await self._save_json(db, BUNDLES_KEY, bundles, "翻译语言包（system/translation）")
        logger.info("语言包已写入 locale=%s merge=%s count=%d user=%s", locale, merge, len(data), user_id)
        return {"locale": locale, "merge": merge, "written": len(data), "total": len(bucket)}

    # ------------------------------------------------------------ 统计 / 缺失 / 模板
    async def stats(self, db: AsyncSession) -> Dict[str, Any]:
        bundles = await self._load_bundles(db)
        settings = await self.settings(db)
        codes = [item["code"] for item in await self.languages(db)]
        return bundle_stats(bundles, codes, settings["source_locale"])

    async def missing(self, db: AsyncSession, locale: str, limit: int) -> Dict[str, Any]:
        bundles = await self._load_bundles(db)
        settings = await self.settings(db)
        missing = missing_keys(bundles, locale, settings["source_locale"])
        untrans = untranslated_keys(bundles, locale, settings["source_locale"])
        cap = max(1, limit)
        return {
            "locale": locale,
            "source_locale": settings["source_locale"],
            "missing_count": len(missing),
            "untranslated_count": len(untrans),
            "missing_keys": missing[:cap],
            "untranslated_keys": untrans[:cap],
        }

    async def template(self, db: AsyncSession, locale: str) -> Dict[str, Any]:
        bundles = await self._load_bundles(db)
        settings = await self.settings(db)
        data = generate_template(bundles, locale, settings["default_language"])
        return {"locale": locale, "default_language": settings["default_language"], "count": len(data),
                "template": data}

    # ------------------------------------------------------------ 导入导出
    async def export(self, db: AsyncSession, locale: str, fmt: str) -> Tuple[bytes, str, str]:
        """导出某语言的词条为真实文件内容，返回 ``(bytes, media_type, filename)``"""
        bundles = await self._load_bundles(db)
        entries = bundles.get(locale) or {}
        translations = {key: entry_value(value) for key, value in sorted(entries.items())}
        content, media_type = render_export(locale, translations, fmt)
        _, ext = EXPORT_FORMATS.get((fmt or "json").strip().lower(), ("", "json"))
        return content, media_type, f"translation-{locale}.{ext}"

    async def import_bundle(self, db: AsyncSession, payload: Any, *, user_id: Optional[int] = None) -> Dict[str, Any]:
        """解析导入内容并真实落库（未知字段直接 400）"""
        if not isinstance(payload, dict) or not payload:
            raise BadRequestError("请求体不能为空")
        allowed = ("locale", "format", "content", "merge", "status")
        unknown = [k for k in payload if k not in allowed]
        if unknown:
            raise BadRequestError(f"未知字段：{unknown}（可选：{list(allowed)}）")
        content = payload.get("content")
        if not isinstance(content, str) or not content.strip():
            raise BadRequestError("content 不能为空")
        fmt = str(payload.get("format") or "json")
        parsed = parse_import(content, fmt)

        locale = str(payload.get("locale") or parsed.get("language") or "").strip()
        if not locale:
            raise BadRequestError("未提供 locale，且导入内容中也没有 language 字段")
        merge = bool(payload.get("merge", True))
        status = payload.get("status")
        if status is not None and status not in VALID_STATUSES:
            raise BadRequestError(f"status 只能是 {list(VALID_STATUSES)}")

        bundles = await self._load_bundles(db)
        bucket = bundles.get(locale) if merge else {}
        if not isinstance(bucket, dict):
            bucket = {}
        for key, value in parsed["translations"].items():
            bucket[str(key)] = normalize_entry(value, status=status, translator_id=user_id)
        bundles[locale] = bucket
        await self._save_json(db, BUNDLES_KEY, bundles, "翻译语言包（system/translation）")
        logger.info("导入词条 locale=%s format=%s count=%d user=%s", locale, fmt, len(parsed["translations"]), user_id)
        return {
            "locale": locale,
            "format": fmt,
            "merge": merge,
            "imported": len(parsed["translations"]),
            "total": len(bucket),
        }

    # ------------------------------------------------------------ 进度
    async def progress(self, db: AsyncSession) -> Dict[str, Any]:
        bundles = await self._load_bundles(db)
        settings = await self.settings(db)
        codes = [item["code"] for item in await self.languages(db)]
        items = [language_progress(bundles, code, settings["source_locale"]) for code in codes]
        items.sort(key=lambda x: x["completion_rate"], reverse=True)
        return {"source_locale": settings["source_locale"], "languages": items}

    async def progress_one(self, db: AsyncSession, locale: str) -> Dict[str, Any]:
        bundles = await self._load_bundles(db)
        settings = await self.settings(db)
        return language_progress(bundles, locale, settings["source_locale"])

    async def report(self, db: AsyncSession) -> Dict[str, Any]:
        bundles = await self._load_bundles(db)
        settings = await self.settings(db)
        codes = [item["code"] for item in await self.languages(db)]
        return build_progress_report(bundles, codes, settings["source_locale"])

    async def register_progress(self, db: AsyncSession, locale: str, payload: Any, *, user_id: Optional[int] = None) -> \
    Dict[str, Any]:
        """登记 / 更新一条词条的翻译状态（未知字段直接 400）"""
        if not isinstance(payload, dict) or not payload:
            raise BadRequestError("请求体不能为空")
        allowed = ("key", "value", "status", "is_translated", "translator_id", "translator_name")
        unknown = [k for k in payload if k not in allowed]
        if unknown:
            raise BadRequestError(f"未知字段：{unknown}（可选：{list(allowed)}）")
        key = str(payload.get("key") or "").strip()
        if not key:
            raise BadRequestError("key 不能为空")

        status = payload.get("status")
        if status is not None and status not in VALID_STATUSES:
            raise BadRequestError(f"status 只能是 {list(VALID_STATUSES)}")
        is_translated = payload.get("is_translated")
        if status is None and is_translated is not None:
            status = "translated" if bool(is_translated) else "pending"

        bundles = await self._load_bundles(db)
        bucket = bundles.setdefault(locale, {})
        if not isinstance(bucket, dict):
            bucket = {}
            bundles[locale] = bucket
        existing = bucket.get(key)
        value = payload.get("value")
        if value is None:
            value = entry_value(existing)
        translator_id = payload.get("translator_id", user_id)
        translator_name = payload.get("translator_name")
        bucket[key] = normalize_entry(
            value, status=status, translator_id=translator_id, translator_name=translator_name
        )
        await self._save_json(db, BUNDLES_KEY, bundles, "翻译语言包（system/translation）")
        return {"locale": locale, "key": key, "entry": bucket[key]}

    # ------------------------------------------------------------ 记忆库
    async def memory_stats(self, db: AsyncSession) -> Dict[str, Any]:
        return summarize_memory(await self._load_memory(db))

    async def memory_suggest(
        self, db: AsyncSession, source_text: str, source_lang: str, target_lang: str,
        threshold: Optional[float], limit: int,
    ) -> Dict[str, Any]:
        memory = await self._load_memory(db)
        pair = _pair_key(source_lang, target_lang)
        effective = DEFAULT_SIMILARITY_THRESHOLD if threshold is None else float(threshold)
        entries = memory.get(pair)
        if not isinstance(entries, list):
            entries = []
        matches = match_memory(entries, source_text, threshold=effective, limit=limit)
        return {
            "pair": pair,
            "source_text": source_text,
            "threshold": effective,
            "total_entries": len(entries),
            "matches": matches,
        }

    async def memory_add(self, db: AsyncSession, payload: Any, *, user_id: Optional[int] = None) -> Dict[str, Any]:
        """新增 / 更新一条翻译记忆（未知字段直接 400）"""
        if not isinstance(payload, dict) or not payload:
            raise BadRequestError("请求体不能为空")
        allowed = ("source_text", "target_text", "source_lang", "target_lang", "context")
        unknown = [k for k in payload if k not in allowed]
        if unknown:
            raise BadRequestError(f"未知字段：{unknown}（可选：{list(allowed)}）")
        source_text = str(payload.get("source_text") or "").strip()
        target_text = str(payload.get("target_text") or "")
        source_lang = str(payload.get("source_lang") or "").strip()
        target_lang = str(payload.get("target_lang") or "").strip()
        context = str(payload.get("context") or "")
        if not source_text:
            raise BadRequestError("source_text 不能为空")
        if not source_lang or not target_lang:
            raise BadRequestError("source_lang / target_lang 不能为空")

        memory = await self._load_memory(db)
        pair = _pair_key(source_lang, target_lang)
        bucket = memory.get(pair)
        if not isinstance(bucket, list):
            bucket = []
            memory[pair] = bucket
        now = _now_iso()
        for entry in bucket:
            if entry.get("source") == source_text and str(entry.get("context") or "") == context:
                entry["target"] = target_text
                entry["updated_at"] = now
                await self._save_json(db, MEMORY_KEY, memory, "翻译记忆库（system/translation）")
                return {"pair": pair, "action": "updated", "entry": entry}
        entry = {
            "source": source_text, "target": target_text, "context": context,
            "created_at": now, "updated_at": now, "usage_count": 0,
        }
        bucket.append(entry)
        await self._save_json(db, MEMORY_KEY, memory, "翻译记忆库（system/translation）")
        logger.info("记忆条目已新增 pair=%s user=%s", pair, user_id)
        return {"pair": pair, "action": "created", "entry": entry}

    async def memory_clear(self, db: AsyncSession, language_pair: Optional[str]) -> Dict[str, Any]:
        memory = await self._load_memory(db)
        if language_pair:
            removed = memory.pop(language_pair, None)
            await self._save_json(db, MEMORY_KEY, memory, "翻译记忆库（system/translation）")
            return {"cleared": True, "pair": language_pair, "removed": len(removed or [])}
        count = len(memory)
        await self._save_json(db, MEMORY_KEY, {}, "翻译记忆库（system/translation）")
        return {"cleared": True, "pairs_removed": count}

    async def memory_export(self, db: AsyncSession) -> Tuple[bytes, str]:
        memory = await self._load_memory(db)
        content = json.dumps(memory, ensure_ascii=False, indent=2).encode("utf-8")
        return content, "translation-memory.json"

    async def memory_import(self, db: AsyncSession, payload: Any, *, user_id: Optional[int] = None) -> Dict[str, Any]:
        """导入记忆 JSON（未知字段直接 400；``merge=True`` 时按 ``(source, context)`` 去重）"""
        if not isinstance(payload, dict) or not payload:
            raise BadRequestError("请求体不能为空")
        allowed = ("content", "merge")
        unknown = [k for k in payload if k not in allowed]
        if unknown:
            raise BadRequestError(f"未知字段：{unknown}（可选：{list(allowed)}）")
        raw = payload.get("content")
        if isinstance(raw, dict):
            imported = raw
        else:
            if not isinstance(raw, str) or not raw.strip():
                raise BadRequestError("content 不能为空（JSON 字符串或对象）")
            try:
                imported = json.loads(raw)
            except (ValueError, json.JSONDecodeError) as exc:
                raise BadRequestError(f"JSON 解析失败：{exc}") from exc
        if not isinstance(imported, dict):
            raise BadRequestError("导入内容必须是 {语言对: [条目]} 形式的对象")

        merge = bool(payload.get("merge", True))
        memory = await self._load_memory(db)
        if not merge:
            memory = imported
        else:
            for pair, entries in imported.items():
                if not isinstance(entries, list):
                    continue
                bucket = memory.get(pair)
                if not isinstance(bucket, list):
                    bucket = []
                    memory[pair] = bucket
                existing = {(e_["source"], str(e_.get("context") or "")) for e_ in bucket}
                for entry in entries:
                    if not isinstance(entry, dict) or "source" not in entry:
                        continue
                    marker = (entry["source"], str(entry.get("context") or ""))
                    if marker not in existing:
                        bucket.append(entry)
                        existing.add(marker)
        await self._save_json(db, MEMORY_KEY, memory, "翻译记忆库（system/translation）")
        total = sum(len(v) for v in memory.values() if isinstance(v, list))
        return {"merge": merge, "total_entries": total}

    # ------------------------------------------------------------ 机器翻译
    def mt_providers(self) -> List[Dict[str, Any]]:
        return [provider_status(key) for key in MT_PROVIDERS]

    async def mt_translate(self, text: str, source_lang: str, target_lang: str, provider: str) -> Dict[str, Any]:
        if not str(text or "").strip():
            raise BadRequestError("text 不能为空")
        return await machine_translate(text, source_lang, target_lang, provider)

    async def mt_batch(
        self, texts: Sequence[str], source_lang: str, target_lang: str, provider: str,
        delay: float = 0.2,
    ) -> Dict[str, Any]:
        """批量翻译（逐条真实调用；未配置密钥时整批如实返回 available=false）"""
        status = provider_status(provider)
        if not status["available"]:
            return {
                "provider": status["provider"],
                "provider_name": status["name"],
                "available": False,
                "success": False,
                "total": len(texts),
                "success_count": 0,
                "failed_count": len(texts),
                "reason": f"未配置 {status['name']} 密钥（需环境变量：{', '.join(status['required_env'])}）",
                "results": [],
            }
        results = []
        success = failed = 0
        for index, text in enumerate(texts):
            if index > 0 and delay > 0:
                import asyncio

                await asyncio.sleep(delay)
            item = await machine_translate(text, source_lang, target_lang, status["provider"])
            results.append(
                {
                    "original": text,
                    "translated": item.get("translated_text"),
                    "success": item["success"],
                    "reason": item.get("reason"),
                }
            )
            if item["success"]:
                success += 1
            else:
                failed += 1
        return {
            "provider": status["provider"],
            "provider_name": status["name"],
            "available": True,
            "success": failed == 0,
            "total": len(texts),
            "success_count": success,
            "failed_count": failed,
            "reason": None,
            "results": results,
        }


translation_service = TranslationService()
