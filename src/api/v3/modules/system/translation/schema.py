"""translation 模块的请求 / 响应模型（Pydantic v2）

写端点分两类：

  - **严格校验类**（词条 / 语言包 / 语言 / 导入 / 记忆库）：controller 直接收
    ``Dict[str, Any] = Body(...)``，由 service 手写「未知字段 → 400」校验。
    原因见 ``help``/``quota`` 模块的说明：Pydantic 默认**静默丢弃**未知字段，
    若这里定义模型，service 里的未知字段校验就会成为死代码。
  - **结构化请求类**（机器翻译）：字段固定且未知字段无副作用，这里定义模型供
    OpenAPI 文档展示与类型校验。

下方 ``*Out`` 模型仅用于文档展示与字段说明，响应统一走 ``common/response`` 包装。
"""

from typing import Any, Dict, List, Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


# ------------------------------------------------------------------ 机器翻译
class MachineTranslateRequest(SchemaBase):
    """单条机器翻译请求（真实调用外部 API，需配置密钥）"""

    text: str = Field(min_length=1, max_length=5000, description="待翻译文本")
    source_lang: str = Field(default="auto", max_length=20, description="源语言，auto 表示自动检测")
    target_lang: str = Field(min_length=1, max_length=20, description="目标语言")
    provider: str = Field(default="baidu", description="提供商：baidu / youdao / deepl / google")


class MachineBatchTranslateRequest(SchemaBase):
    """批量机器翻译请求"""

    texts: List[str] = Field(min_length=1, max_length=200, description="待翻译文本列表")
    source_lang: str = Field(default="auto", max_length=20)
    target_lang: str = Field(min_length=1, max_length=20)
    provider: str = Field(default="baidu")
    delay: float = Field(default=0.2, ge=0.0, le=5.0, description="请求间隔秒数（防止触发限流）")


# ------------------------------------------------------------------ 文档用请求模型
class LanguageUpsert(SchemaBase):
    """新增 / 覆盖一个自定义语言区域（实际由 service 手写校验）"""

    code: str = Field(min_length=1, max_length=20, description="语言代码，如 zh-CN")
    name: str = Field(min_length=1, max_length=100, description="英文名")
    native_name: Optional[str] = Field(default=None, max_length=100, description="本地名")
    direction: str = Field(default="ltr", description="书写方向：ltr / rtl")


class TranslationEntryUpsert(SchemaBase):
    """写入单个词条"""

    locale: str = Field(min_length=1, max_length=20)
    key: str = Field(min_length=1, max_length=255)
    value: str = Field(default="", max_length=200_000)
    status: Optional[str] = Field(default=None, description="translated / pending / reviewed")
    translator_id: Optional[int] = None
    translator_name: Optional[str] = Field(default=None, max_length=100)


class BundleReplace(SchemaBase):
    """整体覆盖 / 合并一个语言包"""

    data: Dict[str, str] = Field(description="{词条键: 译文}")
    merge: bool = Field(default=True, description="True 合并，False 覆盖")
    status: Optional[str] = Field(default=None, description="写入词条的状态")


class TranslationImportRequest(SchemaBase):
    """导入翻译（json / csv / po / xliff / yaml）"""

    content: str = Field(min_length=1, description="文件内容")
    format: str = Field(default="json", description="json / csv / po / xliff / yaml")
    locale: Optional[str] = Field(default=None, description="目标语言；缺省时取内容里的 language")
    merge: bool = Field(default=True)
    status: Optional[str] = Field(default=None)


class ProgressRegister(SchemaBase):
    """登记 / 更新一条词条的翻译状态"""

    key: str = Field(min_length=1, max_length=255)
    value: Optional[str] = Field(default=None, max_length=200_000)
    status: Optional[str] = Field(default=None, description="translated / pending / reviewed")
    is_translated: Optional[bool] = Field(default=None, description="等价于 status=translated/pending")
    translator_id: Optional[int] = None
    translator_name: Optional[str] = Field(default=None, max_length=100)


class MemoryEntryUpsert(SchemaBase):
    """新增 / 更新一条翻译记忆"""

    source_text: str = Field(min_length=1, max_length=200_000)
    target_text: str = Field(default="", max_length=200_000)
    source_lang: str = Field(min_length=1, max_length=20)
    target_lang: str = Field(min_length=1, max_length=20)
    context: str = Field(default="", max_length=500)


class MemoryImportRequest(SchemaBase):
    """导入翻译记忆（``{语言对: [条目]}`` 形态的 JSON）"""

    content: str = Field(min_length=1, description="JSON 字符串")
    merge: bool = Field(default=True)


# ------------------------------------------------------------------ 文档用响应模型
class LanguageOut(SchemaBase):
    code: str
    name: str
    native_name: str
    direction: str = "ltr"
    is_default: bool = False


class LocaleOut(SchemaBase):
    locale: str
    timezone: str
    first_day_of_week: int = 1
    currency: Dict[str, Any] = Field(default_factory=dict)
    formats: Dict[str, Any] = Field(default_factory=dict)


class MemoryMatchOut(SchemaBase):
    source: str
    target: str
    similarity: float
    match_type: str = Field(description="exact / fuzzy")
    context: str = ""
    usage_count: int = 0


class TranslationStatOut(SchemaBase):
    total_keys: int = 0
    translated_keys: int = 0
    missing_keys: int = 0
    completion_rate: float = 0.0


class ProgressOut(SchemaBase):
    locale: str
    total_keys: int = 0
    present_keys: int = 0
    translated: int = 0
    pending: int = 0
    reviewed: int = 0
    untranslated_count: int = 0
    completion_rate: float = 0.0
    last_updated: Optional[str] = None


class MachineTranslateResultOut(SchemaBase):
    provider: str
    provider_name: Optional[str] = None
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    available: bool = False
    success: bool = False
    translated_text: Optional[str] = None
    reason: Optional[str] = None
