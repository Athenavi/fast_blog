"""translation 模块路由（system 域：多语言 / 本地化 / 导入导出 / 进度 / 记忆库 / 机器翻译）

::

    # 语言 / 区域（公开读）
    GET    /api/v3/system/translation/languages                        支持语言列表
    GET    /api/v3/system/translation/languages/detect                 语言识别（Accept-Language 回退链）
    GET    /api/v3/system/translation/locales                          本地化区域信息列表
    GET    /api/v3/system/translation/localize?dt=&locale=&timezone=   按区域格式化时间点

    # 词条 / 语言包
    GET    /api/v3/system/translation/entry?key=&locale=&default=      取单条词条（回退链）
    GET    /api/v3/system/translation/bundle/{locale}                  整包词条（公开读）
    PUT    /api/v3/system/translation/bundle/{locale}                  覆盖 / 合并语言包（需 setting:edit）
    POST   /api/v3/system/translation/entry                            写单条词条（需 setting:edit）

    # 统计 / 缺失 / 模板
    GET    /api/v3/system/translation/stats                            各语言完成度统计
    GET    /api/v3/system/translation/missing?locale=&limit=           缺失 / 未翻译清单
    GET    /api/v3/system/translation/template/{locale}                生成翻译模板

    # 导入导出
    GET    /api/v3/system/translation/export?locale=&format=           导出词条（**真实文件下载**）
    POST   /api/v3/system/translation/import                           导入解析并落库（需 setting:edit）

    # 进度
    GET    /api/v3/system/translation/progress                         所有语言进度（需 setting:view）
    GET    /api/v3/system/translation/progress/{locale}                单语言进度（需 setting:view）
    GET    /api/v3/system/translation/report                           进度报告（需 setting:view）
    POST   /api/v3/system/translation/progress/{locale}                登记翻译状态（需 setting:edit）

    # 翻译记忆库
    GET    /api/v3/system/translation/memory                           记忆库统计（需 setting:view）
    GET    /api/v3/system/translation/memory/suggest                   相似匹配（需 setting:view）
    GET    /api/v3/system/translation/memory/export                    导出记忆库（需 setting:view）
    POST   /api/v3/system/translation/memory                           新增 / 更新记忆（需 setting:edit）
    DELETE /api/v3/system/translation/memory                           清空记忆（需 setting:edit）
    POST   /api/v3/system/translation/memory/import                    导入记忆（需 setting:edit）

    # 机器翻译
    GET    /api/v3/system/translation/mt/providers                     提供商可用性（公开读）
    POST   /api/v3/system/translation/mt/translate                     单条翻译（需 setting:edit）
    POST   /api/v3/system/translation/mt/batch                         批量翻译（需 setting:edit）

**权限码**：本模块没有专用的 ``translation:*`` 权限码（``core/permission/codes.py`` 里不存在），
取语义最近的 ``module_system:setting:view`` / ``module_system:setting:edit``：翻译内容本质是
系统级 key/value 配置（与 ``help.topics`` / ``edge.functions`` 同源）。

**机器翻译的诚实降级**：未配置提供商密钥时端点返回 ``available=false`` + 所需环境变量名，
``translated_text`` 为 ``null``，**绝不伪造译文**（v2 缺密钥时静默返回原文，本模块不沿用）。
"""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Query, Response

from src.api.v3.common import response as resp
from src.api.v3.common.response import ResponseModel
from src.api.v3.core.deps import AuthControl, CurrentUser, DBSession
from src.api.v3.core.permission import codes
from src.api.v3.core.router_class import OperationLogRoute
from src.api.v3.modules.system.translation.schema import (
    MachineBatchTranslateRequest,
    MachineTranslateRequest,
)
from src.api.v3.modules.system.translation.service import (
    SUPPORTED_FORMATS,
    translation_service,
)

router = APIRouter(prefix="/translation", tags=["system-translation"], route_class=OperationLogRoute)


# ================================================================ 语言 / 区域
@router.get("/languages", response_model=ResponseModel, summary="支持语言列表（公开）")
async def list_languages(db: DBSession) -> dict:
    """内置语言 + 自定义语言（自定义同 ``code`` 覆盖内置）"""
    return resp.success(await translation_service.languages(db))


@router.get("/languages/detect", response_model=ResponseModel, summary="语言识别（公开）")
async def detect_language(
    db: DBSession,
    accept_language: Optional[str] = Query(default=None, max_length=500, description="Accept-Language 请求头"),
) -> dict:
    """真实回退链：按 q 权重降序 → 精确匹配 → 主语言匹配 → 默认语言"""
    return resp.success(await translation_service.detect(db, accept_language))


@router.get("/locales", response_model=ResponseModel, summary="本地化区域信息列表（公开）")
async def list_locales() -> dict:
    """每个区域的城市时区 / 时区 / 货币 / 日期时间与数字格式"""
    return resp.success(translation_service.locales())


@router.get("/localize", response_model=ResponseModel, summary="按区域格式化时间点（公开）")
async def localize_time(
    dt: datetime = Query(..., description="要格式化的时间点（ISO 8601，无时区按 UTC 处理）"),
    locale: str = Query(default="en-US", max_length=20, description="区域，如 zh-CN"),
    timezone_name: Optional[str] = Query(default=None, alias="timezone", max_length=50, description="覆盖区域默认时区"),
) -> dict:
    """真实计算：日期 / 时间 / 日期时间 / 相对时间（按区域模板与时区转换）"""
    from src.api.v3.modules.system.translation.service import localize

    return resp.success(localize(dt, locale, timezone_name))


# ================================================================ 词条 / 语言包
@router.get("/entry", response_model=ResponseModel, summary="取单条词条（公开）")
async def get_entry(
    db: DBSession,
    key: str = Query(..., min_length=1, max_length=255, description="词条键"),
    locale: Optional[str] = Query(default=None, max_length=20, description="语言；缺省用默认语言"),
    default: Optional[str] = Query(default=None, max_length=200_000, description="回退文本"),
) -> dict:
    """回退链：指定语言 → 默认语言 → ``default``/键本身，返回命中的来源层级"""
    return resp.success(await translation_service.get_entry(db, key, locale, default))


@router.get("/bundle/{locale}", response_model=ResponseModel, summary="整包词条（公开）")
async def get_bundle(locale: str, db: DBSession) -> dict:
    """返回该语言的词条字典（``{键: 译文}``）与状态计数"""
    return resp.success(await translation_service.get_bundle(db, locale))


@router.put("/bundle/{locale}", response_model=ResponseModel, summary="覆盖 / 合并语言包")
async def replace_bundle(
    locale: str,
    db: DBSession,
    current: CurrentUser,
    payload: Dict[str, Any] = Body(
        ...,
        description="只接受 data / merge / status；未知字段会被明确拒绝（不是静默忽略）",
        examples=[{"data": {"home.title": "首页"}, "merge": True, "status": "translated"}],
    ),
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    """落 ``system_settings`` 键 ``translation.bundles``（JSON 对象）"""
    return resp.success(
        await translation_service.replace_bundle(db, locale, payload, user_id=getattr(current, "id", None)),
        msg="已保存",
    )


@router.post("/entry", response_model=ResponseModel, summary="写单条词条")
async def set_entry(
    db: DBSession,
    current: CurrentUser,
    payload: Dict[str, Any] = Body(
        ...,
        description="只接受 locale / key / value / status / translator_id / translator_name",
        examples=[{"locale": "zh-CN", "key": "home.title", "value": "首页"}],
    ),
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    """写入单个词条并落 ``translation.bundles``"""
    return resp.success(
        await translation_service.set_entry(db, payload, user_id=getattr(current, "id", None)),
        msg="已保存",
    )


# ================================================================ 统计 / 缺失 / 模板
@router.get("/stats", response_model=ResponseModel, summary="各语言完成度统计（公开）")
async def translation_stats(db: DBSession) -> dict:
    """相对源语言的键命中率（真实计算，非硬编码）"""
    return resp.success(await translation_service.stats(db))


@router.get("/missing", response_model=ResponseModel, summary="缺失 / 未翻译清单（公开）")
async def missing_translations(
    db: DBSession,
    locale: str = Query(..., min_length=1, max_length=20),
    limit: int = Query(default=100, ge=1, le=1000, description="每类清单返回条数上限"),
) -> dict:
    """相对源语言的缺失键与未翻译键（真实 diff）"""
    return resp.success(await translation_service.missing(db, locale, limit))


@router.get("/template/{locale}", response_model=ResponseModel, summary="生成翻译模板（公开）")
async def translation_template(locale: str, db: DBSession) -> dict:
    """以默认语言的键生成目标语言的空模板（便于交给译者填写）"""
    return resp.success(await translation_service.template(db, locale))


# ================================================================ 导入导出
@router.get("/export", summary="导出词条（真实文件下载）")
async def export_translations(
    db: DBSession,
    locale: str = Query(..., min_length=1, max_length=20, description="要导出的语言"),
    fmt: str = Query(default="json", alias="format", description=f"导出格式：{'/'.join(SUPPORTED_FORMATS)}"),
) -> Response:
    """返回真实文件内容（``Content-Disposition: attachment``）。

    ``csv`` 带 UTF-8 BOM 与中文表头（``键``/``译文``），Excel 可直接识别中文。
    """
    content, media_type, filename = await translation_service.export(db, locale, fmt)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=ResponseModel, summary="导入翻译")
async def import_translations(
    db: DBSession,
    current: CurrentUser,
    payload: Dict[str, Any] = Body(
        ...,
        description="只接受 content / format / locale / merge / status；格式 json / csv / po / xliff / yaml",
        examples=[{"content": "{\"language\":\"zh-CN\",\"translations\":{\"home.title\":\"首页\"}}", "format": "json"}],
    ),
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    """解析导入内容并真实落 ``translation.bundles``；解析失败如实报错（不静默吞错）"""
    return resp.success(
        await translation_service.import_bundle(db, payload, user_id=getattr(current, "id", None)),
        msg="已导入",
    )


@router.post("/languages", response_model=ResponseModel, summary="新增 / 覆盖自定义语言")
async def upsert_language(
    db: DBSession,
    current: CurrentUser,
    payload: Dict[str, Any] = Body(
        ...,
        description="只接受 code / name / native_name / direction",
        examples=[{"code": "pt-BR", "name": "Portuguese (Brazil)", "native_name": "Português", "direction": "ltr"}],
    ),
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    """落 ``system_settings`` 键 ``translation.locales``"""
    return resp.success(
        await translation_service.upsert_language(db, payload, user_id=getattr(current, "id", None)),
        msg="已保存",
    )


# ================================================================ 进度
@router.get("/progress", response_model=ResponseModel, summary="所有语言进度")
async def all_progress(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SETTING_VIEW),
) -> dict:
    return resp.success(await translation_service.progress(db))


@router.get("/progress/{locale}", response_model=ResponseModel, summary="单语言进度")
async def one_progress(
    locale: str,
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SETTING_VIEW),
) -> dict:
    return resp.success(await translation_service.progress_one(db, locale))


@router.get("/report", response_model=ResponseModel, summary="翻译进度报告")
async def progress_report(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SETTING_VIEW),
) -> dict:
    """汇总 + 各语言进度 + 贡献者排行（贡献者由词条作者真实聚合）"""
    return resp.success(await translation_service.report(db))


@router.post("/progress/{locale}", response_model=ResponseModel, summary="登记翻译状态")
async def register_progress(
    locale: str,
    db: DBSession,
    current: CurrentUser,
    payload: Dict[str, Any] = Body(
        ...,
        description="只接受 key / value / status / is_translated / translator_id / translator_name",
        examples=[{"key": "home.title", "is_translated": True, "translator_name": "张三"}],
    ),
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    """更新词条的 ``status``（进度直接由词条派生，无独立进度表）"""
    return resp.success(
        await translation_service.register_progress(
            db, locale, payload, user_id=getattr(current, "id", None)
        ),
        msg="已登记",
    )


# ================================================================ 翻译记忆库
@router.get("/memory", response_model=ResponseModel, summary="记忆库统计")
async def memory_stats(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SETTING_VIEW),
) -> dict:
    return resp.success(await translation_service.memory_stats(db))


@router.get("/memory/suggest", response_model=ResponseModel, summary="翻译记忆相似匹配")
async def memory_suggest(
    db: DBSession,
    _current: CurrentUser,
    source_text: str = Query(..., min_length=1, max_length=200_000, description="待翻译原文"),
    source_lang: str = Query(..., min_length=1, max_length=20),
    target_lang: str = Query(..., min_length=1, max_length=20),
    threshold: Optional[float] = Query(default=None, ge=0.0, le=1.0, description="相似度阈值，缺省用设置值"),
    limit: int = Query(default=10, ge=1, le=100),
    _perm=AuthControl(codes.SETTING_VIEW),
) -> dict:
    """精确 / 模糊匹配打分（Levenshtein 归一化相似度），按相似度降序返回"""
    return resp.success(
        await translation_service.memory_suggest(
            db, source_text, source_lang, target_lang, threshold, limit
        )
    )


@router.get("/memory/export", summary="导出记忆库（真实文件下载）")
async def memory_export(
    db: DBSession,
    _current: CurrentUser,
    _perm=AuthControl(codes.SETTING_VIEW),
) -> Response:
    content, filename = await translation_service.memory_export(db)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/memory", response_model=ResponseModel, summary="新增 / 更新翻译记忆")
async def memory_add(
    db: DBSession,
    current: CurrentUser,
    payload: Dict[str, Any] = Body(
        ...,
        description="只接受 source_text / target_text / source_lang / target_lang / context",
        examples=[{"source_text": "Hello", "target_text": "你好", "source_lang": "en", "target_lang": "zh-CN"}],
    ),
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    """同 ``(source_text, context)`` 覆盖，否则新增；落 ``translation.memory``"""
    return resp.success(
        await translation_service.memory_add(db, payload, user_id=getattr(current, "id", None)),
        msg="已保存",
    )


@router.delete("/memory", response_model=ResponseModel, summary="清空翻译记忆")
async def memory_clear(
    db: DBSession,
    _current: CurrentUser,
    language_pair: Optional[str] = Query(default=None, max_length=50, description="仅清空该语言对，如 en_zh-CN"),
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    """不带 ``language_pair`` 时清空整个记忆库"""
    return resp.success(await translation_service.memory_clear(db, language_pair), msg="已清空")


@router.post("/memory/import", response_model=ResponseModel, summary="导入翻译记忆")
async def memory_import(
    db: DBSession,
    current: CurrentUser,
    payload: Dict[str, Any] = Body(
        ...,
        description="只接受 content（JSON）/ merge",
        examples=[{"content": "{\"en_zh-CN\": [{\"source\": \"Hello\", \"target\": \"你好\"}]}", "merge": True}],
    ),
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    """``merge=True`` 时按 ``(source, context)`` 去重合并"""
    return resp.success(
        await translation_service.memory_import(db, payload, user_id=getattr(current, "id", None)),
        msg="已导入",
    )


# ================================================================ 机器翻译
@router.get("/mt/providers", response_model=ResponseModel, summary="机器翻译提供商可用性（公开）")
async def mt_providers() -> dict:
    """返回每个提供商是否已配置密钥（只读环境变量，**不返回明文**）"""
    return resp.success(translation_service.mt_providers())


@router.post("/mt/translate", response_model=ResponseModel, summary="机器翻译（单条）")
async def mt_translate(
    payload: MachineTranslateRequest,
    _current: CurrentUser,
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    """真实调用外部翻译 API；**未配置密钥时返回 ``available=false`` + 原因，绝不伪造译文**"""
    result = await translation_service.mt_translate(
        payload.text, payload.source_lang, payload.target_lang, payload.provider
    )
    if not result["success"]:
        return resp.success(result, msg=result.get("reason") or "翻译失败")
    return resp.success(result, msg="翻译成功")


@router.post("/mt/batch", response_model=ResponseModel, summary="机器翻译（批量）")
async def mt_batch(
    payload: MachineBatchTranslateRequest,
    _current: CurrentUser,
    _perm=AuthControl(codes.SETTING_EDIT),
) -> dict:
    """逐条真实调用；未配置密钥时整批如实返回 ``available=false`` + 原因"""
    result = await translation_service.mt_batch(
        payload.texts, payload.source_lang, payload.target_lang, payload.provider, payload.delay
    )
    return resp.success(result, msg=result.get("reason") or "翻译完成")
