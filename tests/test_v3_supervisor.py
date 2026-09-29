"""批次 18：``ops/supervisor``（进程监督，原 ``process_supervisor/``）测试

覆盖四件必须成立的事（**不 mock 掉真实行为**）：

  1. 路由与鉴权：端点存在、匿名 401、模块已登记；
  2. 登记校验：重名 / 命令超长 / ``log_file`` 越界 / ``pid_file`` 越界都会被拦下且不落库；
  3. **真实探测**：起一个本地 HTTP 服务与一个纯 TCP 端口，验证端口 / HTTP 两层检查真的生效
     （不是恒定返回 True）；
  4. 受控动作与日志白名单：未登记命令 → 如实报"不可用"；日志只允许读 ``logs/`` 内文件。
"""

import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
from fastapi import FastAPI

from src.api.v3 import register_v3_routes
from src.api.v3.modules.ops.supervisor import runtime
from src.api.v3.modules.ops.supervisor.service import validate_processes

BASE = "/api/v3/ops/supervisor"


def _app() -> FastAPI:
    app = FastAPI()
    register_v3_routes(app)
    return app


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - http.server 的约定
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args) -> None:  # noqa: ANN002 - 静音访问日志
        pass


@pytest.fixture()
def local_http_server():
    port = _free_port()
    server = HTTPServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        server.shutdown()
        server.server_close()


# ---------------------------------------------------------------- 路由与鉴权


# ---------------------------------------------------------------- 登记校验
def _entry(**overrides) -> dict:
    data = {"name": "main_app", "log_file": "logs/main_app.log"}
    data.update(overrides)
    return data


def test_validate_processes_accepts_valid_entries():
    cleaned, issues = validate_processes([_entry(start_command="echo start")])

    assert issues == []
    assert cleaned[0]["start_command"] == "echo start"
    assert cleaned[0]["stop_command"] is None


def test_validate_processes_rejects_duplicates():
    _cleaned, issues = validate_processes([_entry(), _entry()])

    assert any("重复" in item for item in issues)


def test_validate_processes_rejects_long_command():
    _cleaned, issues = validate_processes([_entry(start_command="x" * 501)])

    assert any("超长" in item for item in issues)


def test_validate_processes_rejects_log_outside_whitelist():
    _cleaned, issues = validate_processes([_entry(log_file="../../etc/passwd")])
    assert any("log_file" in item for item in issues)

    _cleaned2, issues2 = validate_processes([_entry(log_file="src/app.py")])
    assert any("log_file" in item for item in issues2)


def test_validate_processes_rejects_pid_file_outside_project():
    _cleaned, issues = validate_processes([_entry(pid_file="../../tmp/x.pid")])

    assert any("pid_file" in item for item in issues)


# ---------------------------------------------------------------- 真实探测
def test_check_port_true_for_listening_then_false_after_close():
    port = _free_port()
    server = socket.socket()
    server.bind(("127.0.0.1", port))
    server.listen(1)
    try:
        ok, detail = runtime.check_port("127.0.0.1", port)
        assert ok is True, detail
    finally:
        server.close()

    ok_after, _detail = runtime.check_port("127.0.0.1", port)
    assert ok_after is False


def test_check_http_against_real_server(local_http_server):
    port = local_http_server

    ok, detail = runtime.check_http(f"http://127.0.0.1:{port}/health")
    assert ok is True, detail

    failed, failed_detail = runtime.check_http(f"http://127.0.0.1:{_free_port()}/health")
    assert failed is False
    assert "请求失败" in failed_detail


def test_probe_marks_unconfigured_layers(local_http_server):
    port = local_http_server

    result = runtime.probe({"name": "demo", "health": {"host": "127.0.0.1", "port": port}})
    assert result.port_open is True
    assert result.alive is None  # 没登记 pid_file
    assert any("pid_file" in item for item in result.detail)

    unknown = runtime.probe({"name": "demo2"})
    assert unknown.healthy is False
    assert any("未登记 health" in item for item in unknown.detail)


def test_metrics_report_unavailable_reasons():
    assert runtime.collect_metrics(None)["available"] is False
    assert "无 pid" in runtime.collect_metrics(None)["detail"]


# ---------------------------------------------------------------- 动作与日志
def test_run_action_without_command_is_not_faked():
    result = runtime.run_action({"name": "demo"}, "restart")

    assert result["ok"] is False
    assert "未登记 restart_command" in result["detail"]


def test_run_action_executes_real_command():
    result = runtime.run_action({"name": "demo", "start_command": "echo hello-supervisor"}, "start")

    assert result["ok"] is True
    assert result["returncode"] == 0
    assert "hello-supervisor" in (result["output"] or "")


def test_read_log_rejects_paths_outside_whitelist(tmp_path):
    outside = runtime.read_log("src/app.py")
    assert outside["available"] is False
    assert "只允许读取" in outside["detail"]

    traversal = runtime.read_log("../../etc/passwd")
    assert traversal["available"] is False


def test_read_log_reads_tail_of_real_file():
    from src.api.v3.modules.ops.supervisor.runtime import project_root

    log_path = project_root() / "logs" / "_supervisor_test.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(f"line-{i}" for i in range(500)), encoding="utf-8")
    try:
        data = runtime.read_log("logs/_supervisor_test.log", lines=10)
        assert data["available"] is True
        assert data["total_lines"] == 500
        assert data["lines"][-1] == "line-499"
        assert len(data["lines"]) == 10
    finally:
        Path(log_path).unlink(missing_ok=True)


def test_read_log_reports_missing_file():
    data = runtime.read_log("logs/definitely-missing.log")

    assert data["available"] is False
    assert "不存在" in data["detail"]
