"""edge 模块业务逻辑：边缘函数注册 / 代码校验 / 产物摘要 / 部署记录

对齐 v2 ``shared/services/integrations/edge_functions.py`` 的真实能力，并修正它的问题：

1. **注册表在进程内存字典里**（v2 ``self.functions``）→ 重启即丢 → v3 落 ``system_settings``
   键 ``edge.functions``（JSON 对象，键=函数名）。
2. v2 只有"生成 Cloudflare/Vercel 代码并**写盘**"和内存注册，**没有校验** → v3 增加**平台
   特定的静态校验**（体积上限 / 禁用 API / 必须的 fetch 入口），并给出规则名与严重级别。
3. v2 的 ``handler`` 是 Python 可调用对象——``edge_functions.py`` 从服务进程里 curl 外部平台
   （Cloudflare Workers / Vercel Edge，二者都**只认 JS 源码**），Python callable 根本没有落地
   渠道。v3 改为保存**源码**（``code``），并可生成"将部署的产物摘要"。

**安全取舍（重要）**：本模块**从不执行**用户提交的代码（不做 ``eval`` / ``exec`` /
``subprocess``）。``validate`` / ``deploy`` 只做静态检查 + 生成产物摘要（文件名 / 字节数 /
SHA-256），这是刻意的：边缘函数是外部平台的 JS，本地跑它既无意义又不安全。

**部署的诚实降级**：调用平台 API 需要凭据。凭据缺失（本进程环境变量未配置）时，
``deploy`` 如实返回 ``{"deployed": false, "reason": "未配置平台凭据"}``，**绝不伪造"已部署"**。

存储键（均 ``system_settings``，``setting_type=json``，``is_public=False``）：

  - ``edge.functions``   函数定义（``{name: definition}``）
  - ``edge.deployments`` 最近的部署记录（数组，最多 :data:`MAX_DEPLOYMENT_LOG` 条）
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.system.setting.service import setting_service

logger = get_logger("system.edge")

# ------------------------------------------------------------------ 存储键
FUNCTIONS_KEY = "edge.functions"
DEPLOYMENTS_KEY = "edge.deployments"

#: 部署记录保留条数（避免 ``system_settings`` 无限膨胀）
MAX_DEPLOYMENT_LOG = 200

# ------------------------------------------------------------------ 平台
PLATFORM_CLOUDFLARE = "cloudflare_workers"
PLATFORM_VERCEL = "vercel_edge"

#: 平台别名 → 标准名（v2 的 "Cloudflare Workers" / "Vercel Edge" 两种说法）
PLATFORM_ALIASES: Dict[str, str] = {
    "cloudflare_workers": PLATFORM_CLOUDFLARE,
    "cloudflare": PLATFORM_CLOUDFLARE,
    "cf": PLATFORM_CLOUDFLARE,
    "workers": PLATFORM_CLOUDFLARE,
    "vercel_edge": PLATFORM_VERCEL,
    "vercel": PLATFORM_VERCEL,
    "edge": PLATFORM_VERCEL,
}

#: 平台规格（体积上限为**源码字节数**的保守值；真实平台限制按压缩后计，这里从严）
PLATFORM_SPECS: Dict[str, Dict[str, Any]] = {
    PLATFORM_CLOUDFLARE: {
        "label": "Cloudflare Workers",
        "entry_file": "worker.js",
        "max_bytes": 1_048_576,  # 1 MiB
        "env": ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"),
        "console": "https://dash.cloudflare.com/",
    },
    PLATFORM_VERCEL: {
        "label": "Vercel Edge",
        "entry_file": None,  # 用 "<name>.js"
        "max_bytes": 1_048_576,  # 1 MiB
        "env": ("VERCEL_TOKEN",),
        "console": "https://vercel.com/dashboard",
    },
}

# ------------------------------------------------------------------ 禁用 API / 校验规则
#: (规则名, 正则, 严重级别, 说明)；error 阻断部署，warning 只提示
_FORBIDDEN_PATTERNS: List[tuple] = [
    ("eval", re.compile(r"\beval\s*\("), "error",
     "禁止使用 eval()：Edge runtime 不允许动态执行代码"),
    ("new-function", re.compile(r"\bnew\s+Function\s*\("), "error",
     "禁止使用 new Function()：Edge runtime 不允许动态生成函数"),
    ("require", re.compile(r"(?<![\w.])require\s*\("), "error",
     "Edge runtime 使用 ESM，不支持 CommonJS require()"),
    ("commonjs-exports", re.compile(r"\bmodule\.exports\b|\bexports\.\w+\s*="), "error",
     "Edge runtime 使用 ESM，不能用 module.exports / exports.*"),
    ("child-process", re.compile(r"\bchild_process\b"), "error",
     "禁止使用 child_process"),
    ("node-fs", re.compile(r"""\bfrom\s+['"]fs(?:/promises)?['"]"""), "error",
     "禁止使用 Node.js fs 模块（Edge runtime 无文件系统）"),
    ("node-builtin", re.compile(r"""\bfrom\s+['"]node:"""), "error",
     "Edge runtime 不支持 Node.js 内置模块（node:）"),
    ("process-env", re.compile(r"\bprocess\.env\b"), "warning",
     "Edge runtime 的环境变量需通过平台绑定（env / bindings）注入"),
    ("browser-dom", re.compile(r"\b(document|window|localStorage|sessionStorage)\b"), "warning",
     "Edge runtime 没有 DOM / 浏览器存储 API"),
    ("xhr", re.compile(r"\bXMLHttpRequest\b"), "warning",
     "请使用 fetch() 而不是 XMLHttpRequest"),
    ("debugger", re.compile(r"\bdebugger\b"), "warning",
     "请移除调试语句 debugger"),
]

_CF_ENTRY_RE = re.compile(
    r"addEventListener\s*\(\s*['\"]fetch['\"]" r"|\bexport\s+default\b" r"|\bexport\s*\{"
)
_DEFAULT_EXPORT_RE = re.compile(r"\bexport\s+default\b")
_VERCEL_RUNTIME_RE = re.compile(r"""runtime\s*:\s*['"]edge['"]""")


# ================================================================== 纯函数
def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def checksum(text: str) -> str:
    """源码的 SHA-256（产物摘要 / 部署记录用；纯函数，无副作用）"""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def normalize_platform(value: str) -> str:
    """平台别名 → 标准名；未知平台抛 ``BadRequestError``（不是静默接受）"""
    key = (value or "").strip().lower()
    platform = PLATFORM_ALIASES.get(key)
    if platform is None:
        raise BadRequestError(
            f"不支持的边缘平台「{value}」（可选：{sorted(set(PLATFORM_ALIASES.values()))}）"
        )
    return platform


def route_matches(pattern: str, path: str) -> bool:
    """路由匹配（与 v2 生成的 Worker 逻辑**完全一致**）

    - 精确匹配：``pattern == path``
    - 前缀通配：``pattern`` 以 ``*`` 结尾时匹配任何以 ``pattern[:-1]`` 开头的路径；
      单独一个 ``*`` 匹配全部路径
    """
    if not pattern or path is None:
        return False
    if pattern == path:
        return True
    if pattern.endswith("*"):
        return path.startswith(pattern[:-1])
    return False


def find_route(functions: Dict[str, Dict[str, Any]], path: str) -> Optional[str]:
    """返回**首个**匹配 ``path`` 的启用函数名（保持插入顺序，可预期）"""
    for name, definition in functions.items():
        if not definition.get("enabled", True):
            continue
        if route_matches(str(definition.get("route", "")), path):
            return name
    return None


def resolve_entry_code(platform: str, definition: Dict[str, Any]) -> str:
    """将要部署的**入口文件源码**：用户提供了 ``code`` 就用它，否则用平台转发模板"""
    code = str(definition.get("code") or "")
    if code.strip():
        return code
    if platform == PLATFORM_CLOUDFLARE:
        return _render_cloudflare_entry(definition)
    return _render_vercel_entry(definition)


def _render_cloudflare_entry(definition: Dict[str, Any]) -> str:
    """Cloudflare Worker 转发模板（等价 v2 的 ``worker.js``，但不写盘）"""
    routes = json.dumps(
        [{"route": definition.get("route", ""), "cache_ttl": int(definition.get("cache_ttl") or 0)}],
        ensure_ascii=False,
    )
    return (
        "// Cloudflare Worker - 由 FastBlog 生成（system/edge）\n"
        f"// 生成时间: {_now_iso()}\n"
        f"const ROUTES = {routes};\n\n"
        "export default {\n"
        "  async fetch(request, env, ctx) {\n"
        "    const url = new URL(request.url);\n"
        "    const route = ROUTES.find(r => r.route === url.pathname"
        " || (r.route.endsWith('*') && url.pathname.startsWith(r.route.slice(0, -1))));\n"
        "    if (!route) return new Response('Not Found', { status: 404 });\n"
        "    const cache = caches.default;\n"
        "    const key = new Request(request.url, request);\n"
        "    if (route.cache_ttl > 0) {\n"
        "      const hit = await cache.match(key);\n"
        "      if (hit) return hit;\n"
        "    }\n"
        "    const response = await fetch(request);\n"
        "    if (route.cache_ttl > 0) {\n"
        "      const copy = response.clone();\n"
        "      copy.headers.set('Cache-Control', 'public, max-age=' + route.cache_ttl);\n"
        "      ctx.waitUntil(cache.put(key, copy));\n"
        "    }\n"
        "    return response;\n"
        "  }\n"
        "};\n"
    )


def _render_vercel_entry(definition: Dict[str, Any]) -> str:
    """Vercel Edge Function 模板（等价 v2 的 ``<name>.js``，但不写盘）"""
    name = definition.get("name", "edge")
    ttl = int(definition.get("cache_ttl") or 0)
    return (
        f"// Vercel Edge Function - {name}\n"
        "// 由 FastBlog 生成（system/edge）\n"
        "export const config = { runtime: 'edge' };\n\n"
        "export default async function handler(request) {\n"
        f"  const cacheTTL = {ttl};\n"
        "  const headers = { 'Content-Type': 'application/json' };\n"
        "  if (cacheTTL > 0) {\n"
        "    headers['Cache-Control'] = 'public, s-maxage=' + cacheTTL"
        " + ', stale-while-revalidate=' + (cacheTTL * 2);\n"
        "  }\n"
        f"  return new Response(JSON.stringify({{ message: 'Edge Function: {name}' }}),"
        " { status: 200, headers });\n"
        "}\n"
    )


def _meta_files(platform: str, definition: Dict[str, Any], entry_name: str) -> List[Dict[str, str]]:
    """平台配置文件（wrangler.toml / vercel.json），与 v2 生成物等价"""
    name = definition.get("name", "edge")
    route = definition.get("route", "/")
    if platform == PLATFORM_CLOUDFLARE:
        wrangler = (
            f'name = "{name}"\n'
            'main = "worker.js"\n'
            'compatibility_date = "2024-01-01"\n\n'
            "[[routes]]\n"
            f'pattern = "{route}"\n'
        )
        return [{"path": "wrangler.toml", "role": "config", "content": wrangler}]
    vercel = json.dumps(
        {
            "version": 2,
            "functions": {entry_name: {"runtime": "edge"}},
            "routes": [{"src": route, "dest": f"/api/edge/{name}"}],
        },
        indent=2,
        ensure_ascii=False,
    )
    return [{"path": "vercel.json", "role": "config", "content": vercel}]


def build_artifact(platform: str, definition: Dict[str, Any]) -> Dict[str, Any]:
    """**将要部署的产物摘要**（文件名 / 字节数 / SHA-256；不写盘、不执行）

    这是"本地沙箱执行预览"的替代：边缘函数是外部平台的 JS，本地执行既无意义又不安全，
    因此这里只**静态**给出部署内容与体积，供编辑器/运维预览。
    """
    platform = normalize_platform(platform)
    name = definition.get("name", "edge")
    spec = PLATFORM_SPECS[platform]
    entry_name = spec["entry_file"] or f"{name}.js"
    entry_code = resolve_entry_code(platform, definition)

    files: List[Dict[str, Any]] = [
        {
            "path": entry_name,
            "role": "entry",
            "bytes": len(entry_code.encode("utf-8")),
            "sha256": checksum(entry_code),
        }
    ]
    for meta in _meta_files(platform, definition, entry_name):
        content = meta.pop("content")
        files.append(
            {
                "path": meta["path"],
                "role": meta["role"],
                "bytes": len(content.encode("utf-8")),
                "sha256": checksum(content),
            }
        )

    return {
        "platform": platform,
        "label": spec["label"],
        "name": name,
        "route": definition.get("route", ""),
        "cache_ttl": int(definition.get("cache_ttl") or 0),
        "entry": files[0]["path"],
        "entry_bytes": files[0]["bytes"],
        "entry_sha256": files[0]["sha256"],
        "files": files,
        "total_bytes": sum(f["bytes"] for f in files),
        "executed": False,
        "note": "静态产物摘要：不执行用户代码，仅给出将部署的文件与体积",
    }


def validate_code(platform: str, code: str) -> Dict[str, Any]:
    """平台特定的**静态**校验（体积 / 禁用 API / 入口契约）

    :returns: ``{valid, platform, errors, warnings, checks, byte_size, size_limit}``
    """
    platform = normalize_platform(platform)
    spec = PLATFORM_SPECS[platform]
    text = code or ""
    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []
    checks: List[Dict[str, str]] = []

    def _add(bucket: List[Dict[str, str]], rule: str, severity: str, message: str) -> None:
        item = {"rule": rule, "severity": severity, "message": message}
        bucket.append(item)
        checks.append(item)

    if not text.strip():
        _add(errors, "code-empty", "error", "边缘函数代码为空")
    else:
        for rule, pattern, severity, message in _FORBIDDEN_PATTERNS:
            if pattern.search(text):
                _add(errors if severity == "error" else warnings, rule, severity, message)

        if platform == PLATFORM_CLOUDFLARE:
            if not _CF_ENTRY_RE.search(text):
                _add(
                    errors, "entry-missing", "error",
                    "Cloudflare Worker 缺少 fetch 入口（addEventListener('fetch', ...) "
                    "或 export default { fetch }）",
                )
        else:
            if not _DEFAULT_EXPORT_RE.search(text):
                _add(errors, "entry-missing", "error", "Vercel Edge Function 需要 export default handler")
            if not _VERCEL_RUNTIME_RE.search(text):
                _add(warnings, "runtime-config", "warning",
                     "建议声明 export const config = { runtime: 'edge' }")

    byte_size = len(text.encode("utf-8"))
    limit = spec["max_bytes"]
    if byte_size > limit:
        _add(errors, "size-limit", "error", f"代码 {byte_size} 字节超过 {spec['label']} 上限 {limit} 字节")
    elif byte_size > limit * 0.8:
        _add(warnings, "size-warning", "warning", f"代码体积接近上限（{byte_size}/{limit} 字节）")

    return {
        "valid": not errors,
        "platform": platform,
        "byte_size": byte_size,
        "size_limit": limit,
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
        "summary": {"errors": len(errors), "warnings": len(warnings)},
    }


def credential_status(platform: str) -> Dict[str, Any]:
    """凭据是否就绪（只读环境变量，**不返回明文**）"""
    platform = normalize_platform(platform)
    env_names = PLATFORM_SPECS[platform]["env"]
    present = {name: bool(os.getenv(name)) for name in env_names}
    return {
        "platform": platform,
        "available": all(present.values()),
        "env": present,
        "required_env": list(env_names),
    }


# ================================================================== 服务
class EdgeFunctionService:
    """边缘函数注册 / 校验 / 产物摘要 / 部署（system 域，无表 —— 复用 ``system_settings``）"""

    # ------------------------------------------------------------ 存储
    async def _load_functions(self, db: AsyncSession) -> Dict[str, Dict[str, Any]]:
        try:
            setting = await setting_service.get_setting(db, FUNCTIONS_KEY)
        except Exception:  # noqa: BLE001 - 键不存在时视为空注册表
            return {}
        value = setting.get("parsed_value") or {}
        return value if isinstance(value, dict) else {}

    async def _save_functions(self, db: AsyncSession, functions: Dict[str, Dict[str, Any]]) -> None:
        await setting_service.upsert(
            db,
            FUNCTIONS_KEY,
            value=json.dumps(functions, ensure_ascii=False),
            setting_type="json",
            description="Edge Functions 定义（system/edge 模块管理）",
            is_public=False,
        )

    async def _load_deployments(self, db: AsyncSession) -> List[Dict[str, Any]]:
        try:
            setting = await setting_service.get_setting(db, DEPLOYMENTS_KEY)
        except Exception:  # noqa: BLE001 - 键不存在时视为空记录
            return []
        value = setting.get("parsed_value") or []
        return value if isinstance(value, list) else []

    async def _record_deployment(self, db: AsyncSession, entry: Dict[str, Any]) -> None:
        records = await self._load_deployments(db)
        records.append(entry)
        records = records[-MAX_DEPLOYMENT_LOG:]
        await setting_service.upsert(
            db,
            DEPLOYMENTS_KEY,
            value=json.dumps(records, ensure_ascii=False),
            setting_type="json",
            description="Edge Functions 部署记录",
            is_public=False,
        )

    # ------------------------------------------------------------ 视图
    @staticmethod
    def _summary(definition: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in definition.items() if k != "code"} | {
            "code_bytes": len(str(definition.get("code") or "").encode("utf-8")),
            "has_custom_code": bool(str(definition.get("code") or "").strip()),
        }

    @staticmethod
    def _detail(definition: Dict[str, Any]) -> Dict[str, Any]:
        return dict(definition)

    # ------------------------------------------------------------ CRUD
    async def list_functions(self, db: AsyncSession, *, path: Optional[str] = None) -> Dict[str, Any]:
        functions = await self._load_functions(db)
        items = [self._summary(d) for d in functions.values()]
        result: Dict[str, Any] = {"total": len(items), "items": items}
        if path:
            matched = find_route(functions, path)
            result["match"] = {"path": path, "function": matched}
        return result

    async def get_function(self, db: AsyncSession, name: str) -> Dict[str, Any]:
        definition = (await self._load_functions(db)).get(name)
        if definition is None:
            raise NotFoundError(f"Edge 函数「{name}」不存在")
        return self._detail(definition)

    async def create_function(
        self, db: AsyncSession, payload: Any, *, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        platform = normalize_platform(payload.platform)
        functions = await self._load_functions(db)
        if payload.name in functions:
            raise BadRequestError(f"Edge 函数「{payload.name}」已存在")

        # 同一路由不能绑定两个启用函数（否则路由匹配结果不可预期）
        for other in functions.values():
            if (
                other.get("enabled", True)
                and payload.enabled
                and str(other.get("route")) == payload.route
            ):
                raise BadRequestError(
                    f"路由「{payload.route}」已被函数「{other.get('name')}」占用"
                )

        now = _now_iso()
        definition: Dict[str, Any] = {
            "name": payload.name,
            "platform": platform,
            "route": payload.route,
            "code": payload.code or "",
            "cache_ttl": int(payload.cache_ttl or 0),
            "description": payload.description or "",
            "enabled": bool(payload.enabled),
            "created_at": now,
            "updated_at": now,
        }
        functions[payload.name] = definition
        await self._save_functions(db, functions)
        logger.info("注册 Edge 函数 %s（platform=%s 用户 %s）", payload.name, platform, user_id)

        entry_code = resolve_entry_code(platform, definition)
        return {
            "function": self._detail(definition),
            "validation": validate_code(platform, entry_code),
            "artifact": build_artifact(platform, definition),
        }

    async def delete_function(self, db: AsyncSession, name: str) -> None:
        functions = await self._load_functions(db)
        if name not in functions:
            raise NotFoundError(f"Edge 函数「{name}」不存在")
        del functions[name]
        await self._save_functions(db, functions)
        logger.info("删除 Edge 函数 %s", name)

    # ------------------------------------------------------------ 校验
    async def validate_function(
        self, db: AsyncSession, name: str, *, override_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """校验已保存（或临时覆盖）的代码，并给出产物摘要"""
        definition = (await self._load_functions(db)).get(name)
        if definition is None:
            raise NotFoundError(f"Edge 函数「{name}」不存在")
        platform = normalize_platform(definition["platform"])

        effective = dict(definition)
        if override_code is not None:
            effective["code"] = override_code
        code = resolve_entry_code(platform, effective)

        return {
            "name": name,
            "platform": platform,
            "overridden": override_code is not None,
            "validation": validate_code(platform, code),
            "artifact": build_artifact(platform, effective),
            "credentials": credential_status(platform),
        }

    # ------------------------------------------------------------ 部署
    async def deploy_function(self, db: AsyncSession, name: str) -> Dict[str, Any]:
        """校验 → 检查凭据 → （有凭据才）真实调用平台 API

        - 校验不通过：``{deployed: false, reason: "代码校验未通过", validation: ...}``
        - 无凭据：``{deployed: false, reason: "未配置平台凭据", ...}``（**绝不伪造已部署**）
        - 有凭据：真实 ``PUT`` / ``POST`` 平台 API，失败如实报错
        """
        definition = (await self._load_functions(db)).get(name)
        if definition is None:
            raise NotFoundError(f"Edge 函数「{name}」不存在")
        platform = normalize_platform(definition["platform"])
        code = resolve_entry_code(platform, definition)
        validation = validate_code(platform, code)
        artifact = build_artifact(platform, definition)

        base = {
            "name": name,
            "platform": platform,
            "route": definition.get("route", ""),
            "artifact": artifact,
            "validated": validation["valid"],
        }

        if not validation["valid"]:
            await self._record_deployment(
                db,
                {
                    "name": name, "platform": platform, "at": _now_iso(),
                    "deployed": False, "mode": "rejected",
                    "reason": "代码校验未通过", "checksum": artifact["entry_sha256"],
                    "bytes": artifact["entry_bytes"],
                },
            )
            return base | {
                "deployed": False,
                "reason": "代码校验未通过",
                "validation": validation,
            }

        creds = credential_status(platform)
        if not creds["available"]:
            await self._record_deployment(
                db,
                {
                    "name": name, "platform": platform, "at": _now_iso(),
                    "deployed": False, "mode": "skipped",
                    "reason": "未配置平台凭据", "checksum": artifact["entry_sha256"],
                },
            )
            logger.warning("Edge 函数 %s 未部署：缺少凭据 %s", name, creds["required_env"])
            return base | {
                "deployed": False,
                "reason": "未配置平台凭据",
                "credentials": creds,
                "hint": f"配置环境变量 {creds['required_env']} 后重试",
            }

        try:
            remote = await self._remote_deploy(platform, definition, code)
        except httpx.HTTPError as exc:
            await self._record_deployment(
                db,
                {
                    "name": name, "platform": platform, "at": _now_iso(),
                    "deployed": False, "mode": "remote_error",
                    "reason": f"平台 API 调用失败：{exc}", "checksum": artifact["entry_sha256"],
                },
            )
            return base | {"deployed": False, "reason": f"平台 API 调用失败：{exc}"}

        await self._record_deployment(
            db,
            {
                "name": name, "platform": platform, "at": _now_iso(),
                "deployed": True, "mode": "remote",
                "reason": None, "checksum": artifact["entry_sha256"],
                "remote": remote,
            },
        )
        logger.info("Edge 函数 %s 已部署到 %s：%s", name, platform, remote)
        return base | {"deployed": True, "remote": remote, "credentials": creds}

    async def _remote_deploy(
        self, platform: str, definition: Dict[str, Any], code: str
    ) -> Dict[str, Any]:
        """真实调用平台 API（仅在有凭据时进入这里）

        - Cloudflare Workers：``PUT /accounts/{account_id}/workers/scripts/{name}``（multipart 上传）
        - Vercel Edge：``POST /v13/deployments``（files 内联源码）

        .. note:: 这两条分支**未在本环境执行过**（无凭据、无法联网），签名按官方 REST 契约编写。
        """
        name = definition["name"]
        async with httpx.AsyncClient(timeout=30.0) as client:
            if platform == PLATFORM_CLOUDFLARE:
                account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
                token = os.environ["CLOUDFLARE_API_TOKEN"]
                url = (
                    "https://api.cloudflare.com/client/v4/accounts/"
                    f"{account_id}/workers/scripts/{name}"
                )
                metadata = {"main_module": "worker.js", "compatibility_date": "2024-01-01"}
                files = {
                    "metadata": (None, json.dumps(metadata), "application/json"),
                    "worker.js": ("worker.js", code.encode("utf-8"), "application/javascript+module"),
                }
                resp = await client.put(url, headers={"Authorization": f"Bearer {token}"}, files=files)
                resp.raise_for_status()
                body = resp.json() if resp.content else {}
                return {
                    "provider": "cloudflare",
                    "success": bool(body.get("success", True)),
                    "status_code": resp.status_code,
                    "script": name,
                    "console": PLATFORM_SPECS[platform]["console"],
                }

            token = os.environ["VERCEL_TOKEN"]
            project = name.replace("_", "-")
            entry_name = f"{name}.js"
            resp = await client.post(
                "https://api.vercel.com/v13/deployments?forceNew=1",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "name": project,
                    "target": "production",
                    "files": [{"file": entry_name, "data": code}],
                    "projectSettings": {"framework": None},
                },
            )
            resp.raise_for_status()
            body = resp.json() if resp.content else {}
            return {
                "provider": "vercel",
                "status_code": resp.status_code,
                "deployment_id": body.get("id"),
                "url": body.get("url"),
                "console": PLATFORM_SPECS[platform]["console"],
            }

    # ------------------------------------------------------------ 日志
    async def log_function(self, db: AsyncSession, name: str, *, limit: int = 50) -> Dict[str, Any]:
        """函数操作日志

        真实边缘运行日志需要平台凭据 + 平台日志 API；本模块**不伪造**远端日志，
        只返回**本地记录**（部署尝试 / 校验结果），并如实标注 ``remote: false``。
        """
        definition = (await self._load_functions(db)).get(name)
        if definition is None:
            raise NotFoundError(f"Edge 函数「{name}」不存在")

        entries = [e for e in await self._load_deployments(db) if e.get("name") == name]
        entries = entries[-max(1, limit):]
        return {
            "name": name,
            "platform": definition.get("platform"),
            "source": "local",
            "remote": False,
            "reason": "本地记录：真实边缘日志需要平台凭据与平台日志 API，本模块未接入",
            "deployment_count": len(entries),
            "entries": entries,
        }


edge_function_service = EdgeFunctionService()
