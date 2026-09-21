"""ops.supervisor 的进程运行时：状态探测、三层健康检查、登记命令执行（**真实实现**）

设计取向（用户拍板：主应用内模块 + 部署命令）：

  - **不 `Popen` 托管主应用**：进程生命周期由部署层（Docker / systemd）负责，本模块只
    「看状态」+「按登记好的命令启停」。因此页面上的"状态"由三层健康检查判定，而不是句柄存活。
  - **只执行登记过的命令**：API 不接受任意命令字符串，只能按 ``name`` 触发该登记项的命令 ——
    否则 ``supervisor:execute`` 就等价于远程命令执行。
  - **指标可选**：登记里给了 ``pid_file`` 就用它取 pid 并采集 CPU/内存（psutil 可用时）；
    没有 pid 或 psutil 缺失时**明确标注"不可用/原因"**，不返回假的 0。
"""

import os
import socket
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import httpx

from src.api.v3.core.logger import get_logger

logger = get_logger("ops.supervisor.runtime")

#: 命令执行超时（启停类动作；超时按失败上报）
COMMAND_TIMEOUT = 120

#: 健康检查默认超时（秒）
PROBE_TIMEOUT = 5.0

#: 动作名 → 登记项里的命令字段
ACTION_FIELDS = {
    "start": "start_command",
    "stop": "stop_command",
    "restart": "restart_command",
}


@dataclass
class ProbeResult:
    """一次三层健康检查结果"""

    alive: Optional[bool] = None
    port_open: Optional[bool] = None
    http_ok: Optional[bool] = None
    detail: list[str] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        """任一层给出明确"通"即视为在跑（三层都未配置时视为未知 → False + detail 说明）"""
        return bool(self.http_ok or self.port_open or self.alive)

    def to_dict(self) -> dict[str, Any]:
        return {
            "healthy": self.healthy,
            "alive": self.alive,
            "port_open": self.port_open,
            "http_ok": self.http_ok,
            "detail": self.detail,
        }


def project_root() -> Path:
    """项目根（与 ops/upgrade 同口径：version.txt 所在目录）"""
    from shared.utils.version_manager import version_manager

    return version_manager.version_file.parent


# ---------------------------------------------------------------- 进程存活与指标
def read_pid(pid_file: str) -> tuple[Optional[int], list[str]]:
    """从 pid 文件读 pid（**可选能力**：登记里没给 pid_file 就没有 pid）"""
    notes: list[str] = []
    if not pid_file:
        return None, ["未登记 pid_file：无法得知 pid（进程由部署层管理）"]
    path = _safe_path(pid_file)
    if path is None:
        return None, [f"pid_file 不在项目根内，已拒绝：{pid_file}"]
    if not path.is_file():
        return None, [f"pid 文件不存在：{pid_file}"]
    try:
        pid = int(path.read_text(encoding="utf-8").strip().split()[0])
    except (ValueError, IndexError, OSError) as exc:
        return None, [f"pid 文件内容无法解析：{exc}"]
    return pid, notes


def probe_alive(pid: Optional[int]) -> tuple[Optional[bool], list[str]]:
    """判断 pid 是否存活（psutil 缺失时退回 ``os.kill(pid, 0)``）"""
    if pid is None:
        return None, []
    try:
        import psutil  # 可选依赖
    except ImportError:
        try:
            os.kill(pid, 0)
        except OSError:
            return False, [f"pid {pid} 已不存在（psutil 未安装，用 os.kill 判定）"]
        return True, [f"pid {pid} 存活（psutil 未安装，无指标）"]
    try:
        proc = psutil.Process(pid)
        return proc.is_running(), [f"pid {pid} 存活"]
    except Exception:  # noqa: BLE001 - psutil 的 NoSuchProcess/AccessDenied 都算"读不到"
        return False, [f"pid {pid} 无法访问（进程不存在或无权限）"]


def collect_metrics(pid: Optional[int]) -> dict[str, Any]:
    """采集 CPU / 内存 / 运行时长；缺 pid 或 psutil 时**如实说明原因**"""
    if pid is None:
        return {"available": False, "detail": "无 pid（未登记 pid_file），无法采集指标"}
    try:
        import psutil  # 可选依赖
    except ImportError:
        return {"available": False, "detail": "psutil 未安装，无法采集指标"}
    try:
        proc = psutil.Process(pid)
        with proc.oneshot():
            memory = proc.memory_info()
            return {
                "available": True,
                "cpu_percent": proc.cpu_percent(interval=0.0),
                "memory_rss_mb": round(memory.rss / 1024 / 1024, 2),
                "threads": proc.num_threads(),
                "uptime_seconds": int(time.time() - proc.create_time()),
                "create_time": proc.create_time(),
            }
    except Exception as exc:  # noqa: BLE001 - 采集失败也是"不可用"，附原因
        return {"available": False, "detail": f"采集失败：{exc}"}


# ---------------------------------------------------------------- 三层健康检查
def check_port(host: str, port: int, timeout: float = PROBE_TIMEOUT) -> tuple[bool, str]:
    """端口是否可连"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, f"{host}:{port} 可连接"
    except OSError as exc:
        return False, f"{host}:{port} 不可连接（{exc}）"


def check_http(url: str, timeout: float = PROBE_TIMEOUT) -> tuple[bool, str]:
    """HTTP 端点是否返回 2xx/3xx"""
    try:
        resp = httpx.get(url, timeout=timeout, follow_redirects=True)
    except httpx.HTTPError as exc:
        return False, f"{url} 请求失败（{exc}）"
    if 200 <= resp.status_code < 400:
        return True, f"{url} → HTTP {resp.status_code}"
    return False, f"{url} → HTTP {resp.status_code}"


def probe(entry: dict[str, Any]) -> ProbeResult:
    """按登记项执行三层探测（未配置的层跳过，并在 detail 里说明）"""
    result = ProbeResult()

    pid, notes = read_pid(str(entry.get("pid_file") or ""))
    result.detail.extend(notes)
    if pid is not None:
        alive, alive_notes = probe_alive(pid)
        result.alive = alive
        result.detail.extend(alive_notes)

    health = entry.get("health") if isinstance(entry.get("health"), dict) else {}
    host = str(health.get("host") or "127.0.0.1")
    port = health.get("port")
    url = str(health.get("url") or "").strip()

    if isinstance(port, int) and port > 0:
        result.port_open, detail = check_port(host, port)
        result.detail.append(detail)
    if url:
        result.http_ok, detail = check_http(url)
        result.detail.append(detail)
    if not url and not isinstance(port, int):
        result.detail.append("未登记 health.port / health.url：只看 pid 存活（可能为未知）")
    return result


# ---------------------------------------------------------------- 登记命令执行
def run_action(entry: dict[str, Any], action: str) -> dict[str, Any]:
    """按登记项执行 start/stop/restart（**真实执行**；未登记该命令则如实拒绝）"""
    field_name = ACTION_FIELDS.get(action)
    if field_name is None:
        raise ValueError(f"不支持的动作：{action}")
    command = str(entry.get(field_name) or "").strip()
    name = str(entry.get("name") or "")
    if not command:
        return {
            "ok": False,
            "action": action,
            "command": None,
            "detail": f"进程「{name}」未登记 {field_name}：该动作不可用（不会假装成功）",
        }

    started = time.time()
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(project_root()),
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "action": action,
            "command": command,
            "duration_ms": int((time.time() - started) * 1000),
            "detail": f"命令超时（>{COMMAND_TIMEOUT}s）",
        }
    except Exception as exc:  # noqa: BLE001 - 执行不了也要如实报
        return {
            "ok": False,
            "action": action,
            "command": command,
            "duration_ms": int((time.time() - started) * 1000),
            "detail": f"命令执行失败：{exc}",
        }

    tail = _tail(proc.stdout, proc.stderr)
    return {
        "ok": proc.returncode == 0,
        "action": action,
        "command": command,
        "returncode": proc.returncode,
        "duration_ms": int((time.time() - started) * 1000),
        "output": tail,
        "detail": f"命令返回 {proc.returncode}" + ("" if proc.returncode == 0 else f"：{tail}"),
    }


def _tail(stdout: Optional[str], stderr: Optional[str], limit: int = 800) -> str:
    text = "\n".join(part.strip() for part in (stdout, stderr) if part and part.strip())
    return text[-limit:]


# ---------------------------------------------------------------- 日志读取
def allowed_log_roots() -> tuple[Path, ...]:
    """允许读取日志的根目录（**白名单**，防任意文件读取）"""
    root = project_root()
    return (root / "logs", root / "storage" / "logs")


def read_log(log_file: str, lines: int = 200) -> dict[str, Any]:
    """读日志文件末尾 N 行；路径必须在白名单目录内"""
    if not log_file:
        return {"available": False, "detail": "未登记 log_file", "lines": []}
    path = _safe_path(log_file)
    if path is None:
        return {"available": False, "detail": f"路径不在项目根内，已拒绝：{log_file}", "lines": []}
    if not any(path.is_relative_to(root) for root in allowed_log_roots()):
        allowed = ", ".join(str(item.relative_to(project_root())) for item in allowed_log_roots())
        return {
            "available": False,
            "detail": f"只允许读取 {allowed} 下的日志（收到 {log_file}）",
            "lines": [],
        }
    if not path.is_file():
        return {"available": False, "detail": f"日志文件不存在：{log_file}", "lines": []}

    limit = max(1, min(int(lines or 200), 2000))
    try:
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return {"available": False, "detail": f"读取失败：{exc}", "lines": []}
    return {
        "available": True,
        "path": str(path),
        "total_lines": len(content),
        "lines": content[-limit:],
    }


def _safe_path(raw: str) -> Optional[Path]:
    """把登记里的相对路径解析到项目内；越界（``..`` / 绝对路径到外部）返回 None"""
    candidate = Path(raw)
    root = project_root().resolve()
    resolved = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    if not resolved.is_relative_to(root):
        return None
    return resolved
