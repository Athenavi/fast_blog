"""supervisor 模块业务逻辑：进程登记（system_settings JSON）+ 状态探测 + 受控启停

设计（用户拍板：JSON 配置 / 主应用内模块 + 部署命令 / 含 P1+P2）：

  - **登记**存 ``system_settings`` 的 ``supervisor.config``（``setting_type=json``，非公开）；
  - **状态**由三层健康检查（pid 存活 / 端口 / HTTP）判定，而不是进程句柄 ——
    进程生命周期归部署层（Docker / systemd）；
  - **动作**只按登记项执行（``start_command`` / ``stop_command`` / ``restart_command``），
    API 不接受任意命令；未登记该动作时如实返回"不可用"；
  - 日志读取走白名单目录（``logs/``、``storage/logs/``），防止变成任意文件读取。
"""

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v3.core.exceptions import BadRequestError, NotFoundError
from src.api.v3.core.logger import get_logger
from src.api.v3.modules.ops.supervisor import runtime
from src.api.v3.modules.ops.supervisor.schema import (
    SupervisorActionOut,
    SupervisorConfigOut,
    SupervisorConfigPayload,
    SupervisorHealthOut,
    SupervisorLogOut,
    SupervisorProcessOut,
)
from src.api.v3.modules.system.setting.service import setting_service

logger = get_logger("ops.supervisor")

#: 登记项的存储键（system_settings）
CONFIG_KEY = "supervisor.config"

#: 单条命令的最大长度（防超长命令绕过页面校验）
MAX_COMMAND_LENGTH = 500


def validate_processes(items: list[dict]) -> tuple[list[dict], list[str]]:
    """校验登记项，返回 ``(cleaned, issues)``（纯函数，便于单测）

    规则：名字唯一、命令长度上限、``log_file`` 必须落在 ``logs/`` 或 ``storage/logs/``、
    ``pid_file`` 必须在项目根内。**任何 issue 都意味着不落库**（避免"保存成功但其实无效"）。
    """
    issues: list[str] = []
    seen: set[str] = set()
    cleaned: list[dict] = []

    for data in items:
        name = str(data.get("name") or "")
        if name in seen:
            issues.append(f"进程名重复：{name}")
            continue
        seen.add(name)

        for field_name in ("start_command", "stop_command", "restart_command"):
            command = str(data.get(field_name) or "").strip()
            if command and len(command) > MAX_COMMAND_LENGTH:
                issues.append(f"{name}.{field_name} 超长（>{MAX_COMMAND_LENGTH}）")
            data[field_name] = command or None

        log_file = str(data.get("log_file") or "").strip()
        if log_file:
            resolved = runtime._safe_path(log_file)
            allowed = runtime.allowed_log_roots()
            if resolved is None or not any(resolved.is_relative_to(root) for root in allowed):
                issues.append(f"{name}.log_file 必须是 logs/ 或 storage/logs/ 下的路径：{log_file}")
                continue
        data["log_file"] = log_file or None

        pid_file = str(data.get("pid_file") or "").strip()
        if pid_file and runtime._safe_path(pid_file) is None:
            issues.append(f"{name}.pid_file 必须在项目根内：{pid_file}")
            continue
        data["pid_file"] = pid_file or None

        cleaned.append(data)

    return cleaned, issues


class SupervisorService:
    """进程监督（ops 域，无独立表）"""

    # ------------------------------------------------------------ 登记读取 / 保存
    async def _load(self, db: AsyncSession) -> tuple[list[dict], Optional[str]]:
        """读登记项；返回 ``(processes, updated_at)``"""
        try:
            setting = await setting_service.get_setting(db, CONFIG_KEY)
        except Exception:  # noqa: BLE001 - 键不存在即"尚未登记"
            return [], None
        value = setting.get("parsed_value")
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return [], None
        if not isinstance(value, dict):
            return [], None
        processes = value.get("processes")
        rows = processes if isinstance(processes, list) else []
        return rows, value.get("updated_at")

    async def list_processes(self, db: AsyncSession) -> dict:
        """登记项 + 实时探测（状态 / 健康 / 指标）"""
        rows, updated_at = await self._load(db)
        items: list[dict] = []
        for entry in rows:
            payload = dict(entry)
            probe = runtime.probe(entry)
            pid, _notes = runtime.read_pid(str(entry.get("pid_file") or ""))
            item = SupervisorProcessOut.model_validate(payload).model_dump(mode="json")
            item["probe"] = probe.to_dict()
            item["metrics"] = runtime.collect_metrics(pid) if probe.healthy else {
                "available": False,
                "detail": "进程未在运行（按探测结果），跳过指标采集",
            }
            items.append(item)
        out = SupervisorConfigOut(processes=items, total=len(items), updated_at=updated_at)
        return out.model_dump(mode="json")

    async def save_processes(self, db: AsyncSession, payload: SupervisorConfigPayload) -> dict:
        """整体保存登记项（校验见 ``validate_processes``；不通过则不落库）"""
        items = [item.model_dump(mode="json") for item in payload.processes]
        cleaned, issues = validate_processes(items)

        if issues:
            # 校验不过**不落库**：返回问题清单，让调用方修正（避免"保存成功但其实无效"）
            current = await self.list_processes(db)
            current["issues"] = issues
            return SupervisorConfigOut.model_validate(current).model_dump(mode="json")

        value = {"processes": cleaned, "updated_at": datetime.now().isoformat(timespec="seconds")}
        await setting_service.upsert(
            db,
            CONFIG_KEY,
            value=json.dumps(value, ensure_ascii=False),
            setting_type="json",
            description="进程监督登记（ops/supervisor 管理；命令会被真实执行）",
            is_public=False,
        )
        logger.info("supervisor 登记已更新：%s 个进程", len(cleaned))
        return await self.list_processes(db)

    # ------------------------------------------------------------ 动作
    async def act(self, db: AsyncSession, name: str, action: str, *, confirm: bool) -> dict:
        """按登记项执行 start/stop/restart（**真实执行**，需 ``confirm=true``）"""
        if not confirm:
            raise BadRequestError("启停/重启会真实执行部署命令；请在请求里显式传 confirm=true")
        entry = await self.entry_or_404(db, name)
        result = runtime.run_action(entry, action)
        logger.info(
            "supervisor 动作：%s %s → ok=%s (%s)", action, name, result.get("ok"), result.get("detail")
        )
        out = SupervisorActionOut.model_validate(
            {
                "ok": bool(result.get("ok")),
                "action": action,
                "process": name,
                "command": result.get("command"),
                "returncode": result.get("returncode"),
                "duration_ms": result.get("duration_ms"),
                "detail": str(result.get("detail") or ""),
                "output": result.get("output"),
            }
        )
        return out.model_dump(mode="json")

    async def health(self, db: AsyncSession, name: str) -> dict:
        """三层健康检查（只读）"""
        entry = await self.entry_or_404(db, name)
        probe = runtime.probe(entry)
        out = SupervisorHealthOut(
            process=name,
            healthy=probe.healthy,
            alive=probe.alive,
            port_open=probe.port_open,
            http_ok=probe.http_ok,
            detail=probe.detail,
        )
        return out.model_dump(mode="json")

    async def read_log(self, db: AsyncSession, name: str, lines: int = 200) -> dict:
        """读进程日志末尾 N 行（白名单目录内）"""
        entry = await self.entry_or_404(db, name)
        data = runtime.read_log(str(entry.get("log_file") or ""), lines)
        return SupervisorLogOut.model_validate(data).model_dump(mode="json")

    # ------------------------------------------------------------ 内部
    async def entry_or_404(self, db: AsyncSession, name: str) -> dict[str, Any]:
        """取登记项（供本模块与 ops/upgrade 的升级编排复用）；不存在则 404"""
        rows, _updated = await self._load(db)
        for entry in rows:
            if str(entry.get("name")) == name:
                return entry
        raise NotFoundError(f"未登记的进程：{name}")


supervisor_service = SupervisorService()
