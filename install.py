#!/usr/bin/env python3
"""FastBlog 交互式安装 / 初始化脚本（跨平台，仅依赖标准库）。

引导内容：

  1. 环境自检            —— Python 版本、Docker / Compose、.env、项目依赖、数据库端口
  2. 生成 .env           —— 从 .env.example 复制并写入强随机密钥（SECRET_KEY / JWT_SECRET_KEY /
                            DB_PASSWORD / REDIS_PASSWORD）；已存在时备份并按需补齐缺失项
  3. 启动服务（可选）    —— docker compose up -d --build（含静态 ffmpeg 包检查），等待 /api/v3/health
  4. 数据库迁移          —— alembic upgrade head
  5. 种子数据导入        —— RBAC 基础 / 后台菜单与授权 / 成长体系 / 历史批次菜单（可多选）
  6. 创建用户            —— 按内置角色（superadmin / admin / editor / user）创建并绑定角色

用法::

    python install.py                       # 全交互引导
    python install.py --check               # 只做环境自检，不修改任何东西
    python install.py --mode init           # 只做数据库初始化（服务已在别处运行）
    python install.py --yes --mode init --seeds rbac,menus --admin-user admin

非交互模式（``--yes``）不会提问；需要密码时从 ``--admin-password-env``（默认
``FASTBLOG_ADMIN_PASSWORD``）读取，缺失则直接失败，绝不用弱密码兜底。

退出码：0 全部成功；1 有步骤失败；2 环境不满足前置条件。
"""

from __future__ import annotations

import argparse
import getpass
import importlib.util
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"
ENV_FILE = PROJECT_ROOT / ".env"
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"
FFMPEG_TARBALL = PROJECT_ROOT / "tools" / "ffmpeg" / "ffmpeg-release-amd64-static.tar.xz"
FFMPEG_URL = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"

#: 必须由安装脚本写入强随机值的键（.env.example 中的占位/空值会被替换）
SECRET_KEYS = ("SECRET_KEY", "JWT_SECRET_KEY", "DB_PASSWORD", "REDIS_PASSWORD")
#: 视为"未配置"的占位值
PLACEHOLDERS = {"", "your_secure_password_here", "your_app_password", "changeme", "fastblog_secret"}

#: 运行后端所需的第三方包（用于判断本地是否已装依赖）
REQUIRED_PACKAGES = ("sqlalchemy", "alembic", "asyncpg", "pydantic")

BUILTIN_ROLES = (
    ("superadmin", "超级管理员（拥有全部权限，is_superuser=True）"),
    ("admin", "管理员（管理类权限，不含敏感系统设置）"),
    ("editor", "编辑（内容相关权限）"),
    ("user", "普通用户（前台默认角色）"),
)

#: 历史批次菜单脚本（batch3–5 没有 __main__ 入口，需显式调用 main()）
BATCH_MENU_COMMANDS: list[tuple[str, list[str]]] = [
    ("seed_batch3_menus", ["-c", "import asyncio, scripts.seed_batch3_menus as m; asyncio.run(m.main())"]),
    ("seed_batch4_menus", ["-c", "import asyncio, scripts.seed_batch4_menus as m; asyncio.run(m.main())"]),
    ("seed_batch5_menus", ["-c", "import asyncio, scripts.seed_batch5_menus as m; asyncio.run(m.main())"]),
    ("seed_batch6_menus", ["-m", "scripts.seed_batch6_menus", "--apply"]),
    ("seed_batch7_menus", ["-m", "scripts.seed_batch7_menus", "--apply"]),
    ("seed_batch8_menus", ["-m", "scripts.seed_batch8_menus", "--apply"]),
    ("seed_batch9_menus", ["-m", "scripts.seed_batch9_menus", "--apply"]),
    ("seed_batch10_menus", ["-m", "scripts.seed_batch10_menus", "--apply"]),
]

#: 可选的种子数据（key, 说明, 命令, 是否默认选中）
SEED_OPTIONS: list[tuple[str, str, list[str], bool]] = [
    (
        "rbac",
        "RBAC 基础：194 条权限码 + 4 个内置角色（幂等，覆盖内置角色能力清单）",
        ["-m", "scripts.seed_rbac"],
        True,
    ),
    (
        "menus",
        "后台菜单 + 系统角色授权（从 frontend/web/src/utils/menus.ts 同步，不授权则谁都看不到菜单）",
        ["-m", "scripts.seed_admin_menus", "--apply", "--grant-system-roles"],
        True,
    ),
    (
        "gamification",
        "成长体系：积分规则 + 勋章定义",
        ["-m", "scripts.seed_gamification", "--apply"],
        True,
    ),
    (
        "batch-menus",
        "历史批次菜单（seed_batch3–10，早期遗留的补插脚本，菜单内容通常已被 menus 覆盖）",
        [],
        False,
    ),
]

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_PRECONDITION = 2


# ---------------------------------------------------------------------------
# 交互工具
# ---------------------------------------------------------------------------
def out(message: str = "") -> None:
    print(message, flush=True)


def step(index: int, total: int, title: str) -> None:
    out("")
    out(f"=== [{index}/{total}] {title} " + "=" * max(0, 48 - len(title)))


def ok(message: str) -> None:
    out(f"  [OK] {message}")


def warn(message: str) -> None:
    out(f"  [!] {message}")


def fail(message: str) -> None:
    out(f"  [x] {message}")


def ask_yes_no(question: str, *, default: bool = True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        answer = input(f"{question} {hint} ").strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes", "是"):
            return True
        if answer in ("n", "no", "否"):
            return False
        out("  请输入 y 或 n")


def ask_text(question: str, *, default: str | None = None, required: bool = True) -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        answer = input(f"{question}{suffix}: ").strip()
        if answer:
            return answer
        if default is not None:
            return default
        if not required:
            return ""
        out("  该项不能为空")


def ask_choice(question: str, options: list[tuple[str, str]], *, default_index: int = 0) -> str:
    out(question)
    for idx, (_, label) in enumerate(options, start=1):
        mark = "（默认）" if idx - 1 == default_index else ""
        out(f"  {idx}) {label}{mark}")
    while True:
        answer = input(f"请选择 [1-{len(options)}]: ").strip()
        if not answer:
            return options[default_index][0]
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1][0]
        out("  输入无效，请输入序号")


def ask_multi(question: str, options: list[tuple[str, str, bool]]) -> list[str]:
    """多选：输入序号（逗号或空格分隔）、all、none；回车使用默认项。"""
    out(question)
    for idx, (_, label, selected) in enumerate(options, start=1):
        mark = "[x]" if selected else "[ ]"
        out(f"  {idx}) {mark} {label}")
    default_keys = [key for key, _, selected in options if selected]
    while True:
        answer = input("选择（如 1,3；all=全选；none=跳过；回车=默认）: ").strip().lower()
        if not answer:
            return default_keys
        if answer in ("all", "*"):
            return [key for key, _, _ in options]
        if answer in ("none", "-"):
            return []
        picked: list[str] = []
        for token in re.split(r"[,\s]+", answer):
            if not token.isdigit() or not 1 <= int(token) <= len(options):
                picked = []
                break
            key = options[int(token) - 1][0]
            if key not in picked:
                picked.append(key)
        if picked:
            return picked
        out("  输入无效，请输入序号（如 1,3）")


def ask_password(question: str = "请输入密码") -> str:
    if not sys.stdin.isatty():
        raise RuntimeError("非交互环境下无法输入密码")
    while True:
        first = getpass.getpass(f"{question}: ")
        second = getpass.getpass("请再次输入确认: ")
        if first != second:
            out("  两次输入不一致，请重试")
            continue
        if len(first) < 8:
            out("  密码至少 8 位，请重试")
            continue
        return first


# ---------------------------------------------------------------------------
# 环境自检
# ---------------------------------------------------------------------------
def detect_compose_command() -> list[str] | None:
    """返回可用的 compose 命令前缀，例如 ['docker', 'compose'] 或 ['docker-compose']。"""
    if shutil.which("docker") is None:
        return None
    if run_silent(["docker", "compose", "version"]):
        return ["docker", "compose"]
    if shutil.which("docker-compose") and run_silent(["docker-compose", "version"]):
        return ["docker-compose"]
    return None


def run_silent(cmd: list[str]) -> bool:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def read_env_values() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_FILE.exists():
        return values
    for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def check_database_port(values: dict[str, str]) -> tuple[bool, str]:
    host = values.get("DB_HOST") or "localhost"
    port = int(values.get("DB_PORT") or 5432)
    if host in ("postgres", "db"):
        return False, f"DB_HOST={host} 是容器内地址，宿主机不可直接连（属正常）"
    try:
        with socket.create_connection((host, port), timeout=3):
            return True, f"{host}:{port} 可连接"
    except OSError as exc:
        return False, f"{host}:{port} 不可连接（{exc.__class__.__name__}）"


def missing_packages() -> list[str]:
    return [name for name in REQUIRED_PACKAGES if importlib.util.find_spec(name) is None]


def gather_environment() -> dict[str, object]:
    values = read_env_values()
    db_ok, db_note = check_database_port(values) if ENV_FILE.exists() else (False, "尚未生成 .env")
    return {
        "python": sys.version.split()[0],
        "python_ok": sys.version_info >= (3, 11),
        "compose": detect_compose_command(),
        "env_exists": ENV_FILE.exists(),
        "env_values": values,
        "missing_packages": missing_packages(),
        "ffmpeg": FFMPEG_TARBALL.exists(),
        "db_ok": db_ok,
        "db_note": db_note,
    }


def print_environment(env: dict[str, object]) -> None:
    out("环境自检")
    out(f"  Python             : {env['python']}" + ("" if env["python_ok"] else "  <- 需要 3.11+"))
    compose = env["compose"]
    out(f"  Docker Compose     : {' '.join(compose) if compose else '未检测到（仅能执行 --mode init）'}")  # type: ignore[arg-type]
    out(f"  .env               : {'已存在' if env['env_exists'] else '尚未生成'}")
    missing = env["missing_packages"]
    out(f"  本地 Python 依赖   : {'齐全' if not missing else '缺少 ' + ', '.join(missing)}")  # type: ignore[arg-type]
    out(f"  ffmpeg 静态包      : {'已就绪' if env['ffmpeg'] else '缺失（Docker 构建需要）'}")
    out(f"  数据库连接         : {env['db_note']}")


# ---------------------------------------------------------------------------
# .env 生成
# ---------------------------------------------------------------------------
def _random_secret(length: int = 43) -> str:
    """URL 安全的强随机串（不含需要转义的字符，可直接进连接串）。"""
    return secrets.token_urlsafe(length)[:length]


def _set_env_value(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    if pattern.search(text):
        return pattern.sub(f"{key}={value}", text)
    if not text.endswith("\n"):
        text += "\n"
    return f"{text}{key}={value}\n"


def prepare_env_file(env: dict[str, object], *, non_interactive: bool) -> tuple[bool, Path | None]:
    """生成或补齐 .env。返回 (是否有改动, 备份路径)。"""
    generated: dict[str, str] = {}
    for key in SECRET_KEYS:
        generated[key] = _random_secret(24 if key in ("DB_PASSWORD", "REDIS_PASSWORD") else 43)

    if not ENV_FILE.exists():
        if not ENV_EXAMPLE.exists():
            fail(f"找不到模板 {ENV_EXAMPLE.name}，无法生成 .env")
            return False, None
        text = ENV_EXAMPLE.read_text(encoding="utf-8")
        for key, value in generated.items():
            text = _set_env_value(text, key, value)
        ENV_FILE.write_text(text, encoding="utf-8")
        ok(f"已生成 {ENV_FILE.name} 并写入 4 个强随机密钥（SECRET_KEY / JWT_SECRET_KEY / DB_PASSWORD / REDIS_PASSWORD）")
        return True, None

    values = env["env_values"]
    weak_keys = [key for key in SECRET_KEYS if (values.get(key, "") in PLACEHOLDERS)]  # type: ignore[union-attr]
    if not weak_keys:
        ok(".env 已存在，4 个密钥均已配置，无需改动")
        return False, None

    if non_interactive:
        warn(f".env 中以下键为空或仍是占位值: {', '.join(weak_keys)}（非交互模式不改动）")
        return False, None

    warn(f".env 中以下键为空或仍是占位值: {', '.join(weak_keys)}")
    if not ask_yes_no("是否备份并用强随机值覆盖这些键？", default=True):
        return False, None

    backup = ENV_FILE.with_name(f"{ENV_FILE.name}.bak-{time.strftime('%Y%m%d%H%M%S')}")
    shutil.copy2(ENV_FILE, backup)
    text = ENV_FILE.read_text(encoding="utf-8")
    for key in weak_keys:
        text = _set_env_value(text, key, generated[key])
    ENV_FILE.write_text(text, encoding="utf-8")
    ok(f"已更新 {', '.join(weak_keys)}，原文件备份为 {backup.name}")
    return True, backup


# ---------------------------------------------------------------------------
# Docker 流程
# ---------------------------------------------------------------------------
def ensure_ffmpeg(non_interactive: bool, allow_download: bool) -> bool:
    if FFMPEG_TARBALL.exists():
        ok("ffmpeg 静态包已就绪")
        return True
    warn(f"缺少 {FFMPEG_TARBALL.relative_to(PROJECT_ROOT)}（后端镜像构建需要，约 40MB）")
    if not allow_download or non_interactive:
        out(f"  请手动下载: {FFMPEG_URL}")
        return False
    if not ask_yes_no("是否现在下载？", default=True):
        return False
    FFMPEG_TARBALL.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(FFMPEG_URL, timeout=60) as response, open(FFMPEG_TARBALL, "wb") as target:
            total = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                target.write(chunk)
                downloaded += len(chunk)
                if total:
                    print(f"\r  下载中 {downloaded * 100 // total}%", end="", flush=True)
        out("")
        ok(f"已下载到 {FFMPEG_TARBALL.relative_to(PROJECT_ROOT)}")
        return True
    except Exception as exc:  # noqa: BLE001 - 网络问题属可预期失败
        fail(f"下载失败: {exc}")
        out(f"  请手动下载并放到该路径: {FFMPEG_URL}")
        FFMPEG_TARBALL.unlink(missing_ok=True)
        return False


def docker_up(compose_cmd: list[str], compose_file: str) -> bool:
    cmd = [*compose_cmd, "-f", compose_file, "up", "-d", "--build"]
    out(f"  执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        fail("docker compose 启动失败，请查看上面的输出")
        return False
    ok("容器已启动")
    return True


def wait_for_backend(env: dict[str, object], *, timeout: int = 240) -> bool:
    values = env["env_values"]  # type: ignore[assignment]
    port = int(values.get("BACKEND_PORT") or 9421)  # type: ignore[union-attr]
    url = f"http://127.0.0.1:{port}/api/v3/health"
    out(f"  等待后端就绪: {url}（最多 {timeout}s）")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200:
                    ok("后端已就绪")
                    return True
        except Exception:  # noqa: BLE001 - 轮询期间的任何异常都视为"还没起来"
            pass
        print(".", end="", flush=True)
        time.sleep(3)
    out("")
    fail("等待超时；请执行 docker compose logs backend 查看日志")
    return False


# ---------------------------------------------------------------------------
# 数据初始化
# ---------------------------------------------------------------------------
def ensure_python_deps(non_interactive: bool, auto_install: bool) -> bool:
    missing = missing_packages()
    if not missing:
        ok("本地 Python 依赖齐全")
        return True

    warn(f"缺少依赖: {', '.join(missing)}")
    out("  迁移与种子脚本需要项目依赖（pip install -r requirements.txt）")
    if not auto_install or non_interactive:
        out("  请先安装依赖后重跑本脚本（或加 --install-deps）")
        return False
    if not ask_yes_no(f"是否现在执行 pip install -r {REQUIREMENTS.name}？", default=True):
        return False
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)]
    out(f"  执行: {' '.join(cmd)}")
    if subprocess.run(cmd, cwd=PROJECT_ROOT).returncode != 0:
        fail("依赖安装失败")
        return False
    ok("依赖安装完成")
    return True


def run_python_step(title: str, args: list[str], *, env: dict[str, str] | None = None) -> bool:
    cmd = [sys.executable, *args]
    out(f"  {title}: {' '.join(args)}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, env={**os.environ, **(env or {})})
    if result.returncode != 0:
        fail(f"{title} 失败（退出码 {result.returncode}）")
        return False
    ok(f"{title} 完成")
    return True


def run_migrations(non_interactive: bool) -> bool:
    out("  数据库迁移: python -m alembic upgrade head")
    if not run_python_step("迁移", ["-m", "alembic", "upgrade", "head"]):
        if non_interactive or not ask_yes_no("迁移失败，是否继续后续步骤？", default=False):
            return False
    return True


def run_seeds(labels: dict[str, str], selected: list[str]) -> bool:
    if not selected:
        out("  未选择任何种子数据，跳过")
        return True

    failed: list[str] = []
    for key in selected:
        if key == "batch-menus":
            for name, args in BATCH_MENU_COMMANDS:
                if not run_python_step(name, args):
                    failed.append(name)
            continue
        command = next(cmd for k, _, cmd, _ in SEED_OPTIONS if k == key)
        if not run_python_step(labels[key], command):
            failed.append(labels[key])

    if failed:
        fail(f"以下种子步骤失败: {', '.join(failed)}")
        return False
    return True


def create_user(*, username: str, role: str, email: str, password: str) -> bool:
    env = {"FASTBLOG_INSTALL_PASSWORD": password}
    cmd_args = ["-m", "scripts.create_user", "-u", username, "-r", role, "--password-env", "FASTBLOG_INSTALL_PASSWORD"]
    if email:
        cmd_args += ["-e", email]
    if role == "superadmin":
        cmd_args += ["--superuser"]
    return run_python_step(f"创建用户 {username}（{role}）", cmd_args, env=env)


def interactive_create_users() -> bool:
    created_any = False
    while True:
        granted = ask_yes_no("是否创建一个用户？", default=not created_any)
        if not granted:
            return True

        role = ask_choice("选择用户类型（角色）:", [(slug, label) for slug, label in BUILTIN_ROLES])
        username = ask_text("用户名")
        email = ask_text("邮箱（可留空）", default="", required=False)
        try:
            password = ask_password("设置密码（至少 8 位）")
        except RuntimeError as exc:
            fail(str(exc))
            return False

        if not create_user(username=username, role=role, email=email, password=password):
            return False
        created_any = True

        if not ask_yes_no("是否继续创建下一个用户？", default=False):
            return True


def non_interactive_create_users(args: argparse.Namespace) -> bool:
    if not args.admin_user:
        out("  未指定 --admin-user，跳过用户创建")
        return True
    password = os.environ.get(args.admin_password_env, "")
    if not password:
        fail(f"非交互模式创建用户需要密码：请设置环境变量 {args.admin_password_env}")
        return False
    return create_user(
        username=args.admin_user,
        role=args.admin_role,
        email=args.admin_email or "",
        password=password,
    )


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python install.py",
        description="FastBlog 交互式安装 / 初始化脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python install.py                                  # 全交互引导\n"
            "  python install.py --check                          # 仅环境自检\n"
            "  python install.py --mode init --seeds rbac,menus   # 只初始化已有环境\n"
            "  FASTBLOG_ADMIN_PASSWORD=xxx python install.py --yes --mode init --admin-user admin\n"
        ),
    )
    parser.add_argument("--mode", choices=("docker", "init"), help="docker=构建并启动容器；init=只做数据库初始化")
    parser.add_argument(
        "--compose-file",
        default="docker-compose.yml",
        help="docker 模式使用的 compose 文件（默认 docker-compose.yml，生产用 docker-compose.prod.yml）",
    )
    parser.add_argument(
        "--seeds",
        default=None,
        help="逗号分隔的种子项：rbac,menus,gamification,batch-menus（none 表示跳过；默认前三项）",
    )
    parser.add_argument("--skip-migrations", action="store_true", help="跳过数据库迁移")
    parser.add_argument("--skip-seeds", action="store_true", help="跳过种子数据导入")
    parser.add_argument("--skip-users", action="store_true", help="跳过创建用户")
    parser.add_argument("--admin-user", help="非交互模式下创建的用户名")
    parser.add_argument("--admin-role", default="superadmin", help="非交互模式下创建的用户角色（默认 superadmin）")
    parser.add_argument("--admin-email", help="非交互模式下创建的用户邮箱")
    parser.add_argument(
        "--admin-password-env",
        default="FASTBLOG_ADMIN_PASSWORD",
        help="从该环境变量读取管理员密码（默认 FASTBLOG_ADMIN_PASSWORD）",
    )
    parser.add_argument("--check", action="store_true", help="只做环境自检后退出")
    parser.add_argument("--yes", action="store_true", help="非交互模式，全部采用默认值")
    parser.add_argument("--install-deps", action="store_true",
                        help="缺少依赖时自动执行 pip install -r requirements.txt")
    parser.add_argument("--no-download", action="store_true", help="不自动下载 ffmpeg 静态包")
    return parser


def parse_seeds(raw: str | None, non_interactive: bool) -> tuple[dict[str, str], list[str]]:
    labels = {key: label.split("：")[0].split("（")[0] for key, label, _, _ in SEED_OPTIONS}
    if raw is None:
        if non_interactive:
            return labels, [key for key, _, _, default in SEED_OPTIONS if default]
        return labels, ask_multi("选择要导入的种子数据:",
                                 [(key, label, default) for key, label, _, default in SEED_OPTIONS])

    if raw.strip().lower() in ("none", ""):
        return labels, []
    selected = [item.strip() for item in raw.split(",") if item.strip()]
    unknown = [item for item in selected if item not in labels]
    if unknown:
        raise SystemExit(f"未知的种子项: {', '.join(unknown)}（可选: {', '.join(labels)}）")
    return labels, selected


def print_summary(env: dict[str, object], *, mode: str) -> None:
    values = env["env_values"]  # type: ignore[assignment]
    backend_port = values.get("BACKEND_PORT") or 9421  # type: ignore[union-attr]
    frontend_port = values.get("FRONTEND_PORT") or 4321  # type: ignore[union-attr]
    out("")
    out("=" * 60)
    out("安装完成" if mode == "docker" else "初始化完成")
    out("=" * 60)
    out(f"  站点入口      : http://localhost:{frontend_port}（nginx）")
    out(f"  后端 API      : http://localhost:{backend_port}/api/v3")
    out(f"  API 文档      : http://localhost:{backend_port}/api/v3/docs（ENVIRONMENT=production 时关闭）")
    out(f"  健康检查      : http://localhost:{backend_port}/api/v3/health")
    out("")
    out("  后台登录      : 使用上面创建的用户；超管可在「系统 → 角色」中分配权限")
    out("  常用命令      :")
    out("    docker compose logs -f backend        查看后端日志")
    out("    docker compose down                   停止服务")
    out("    python -m cli user list-users         列出用户")
    out("    python -m scripts.create_user -u X -r editor   再建一个编辑")
    out("    python -m scripts.seed_admin_menus --apply --grant-system-roles   同步后台菜单")
    out("")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    non_interactive = args.yes

    out("=" * 60)
    out("FastBlog 安装向导")
    out("=" * 60)
    out(f"项目目录: {PROJECT_ROOT}")

    env = gather_environment()
    out("")
    print_environment(env)

    if not env["python_ok"]:
        fail("Python 版本过低（需要 3.11+）")
        return EXIT_PRECONDITION
    if args.check:
        return EXIT_OK

    mode = args.mode
    if mode is None:
        if non_interactive:
            mode = "docker"
        elif env["compose"] is None:
            warn("未检测到 Docker Compose，只能执行数据库初始化（--mode init）")
            mode = "init"
        else:
            mode = ask_choice(
                "选择部署形态:",
                [
                    ("docker", "Docker Compose：构建并启动容器，再完成数据库初始化"),
                    ("init", "仅初始化：服务已在别处运行，只做迁移 / 种子 / 建用户"),
                ],
            )

    if mode == "docker" and args.compose_file == "docker-compose.yml" and not non_interactive:
        args.compose_file = ask_choice(
            "选择 compose 文件:",
            [
                ("docker-compose.yml", "默认形态（HTTP 4321，单 worker，适合内网 / 反代后）"),
                ("docker-compose.prod.yml", "生产形态（80/443，强制密钥，多 worker + Redis 密码）"),
            ],
        )

    plan_steps = ["生成 / 检查 .env"]
    if mode == "docker":
        plan_steps.append("准备并启动容器")
    plan_steps.append("检查项目依赖")
    if not args.skip_migrations:
        plan_steps.append("数据库迁移")
    if not args.skip_seeds:
        plan_steps.append("种子数据导入")
    if not args.skip_users:
        plan_steps.append("创建用户")
    steps = len(plan_steps)
    index = 1

    step(index, steps, "生成 / 检查 .env")
    index += 1
    env_changed, _ = prepare_env_file(env, non_interactive=non_interactive)
    if env_changed:
        env = gather_environment()

    if mode == "docker":
        step(index, steps, "准备并启动容器")
        index += 1
        if not ensure_ffmpeg(non_interactive=non_interactive, allow_download=not args.no_download):
            if not non_interactive and not ask_yes_no("ffmpeg 未就绪，仍要继续构建吗？", default=False):
                return EXIT_FAILED
        compose_cmd = env["compose"] or detect_compose_command()
        if compose_cmd is None:
            fail("Docker Compose 不可用，无法执行 docker 模式；可改用 --mode init")
            return EXIT_PRECONDITION
        if not docker_up(compose_cmd, args.compose_file):  # type: ignore[arg-type]
            return EXIT_FAILED
        wait_for_backend(env)

    step(index, steps, "检查项目依赖")
    index += 1
    if not ensure_python_deps(non_interactive=non_interactive, auto_install=args.install_deps or not non_interactive):
        return EXIT_PRECONDITION

    if args.skip_migrations:
        out("")
        out("按参数要求跳过: 数据库迁移")
    else:
        step(index, steps, "数据库迁移")
        index += 1
        if not run_migrations(non_interactive):
            return EXIT_FAILED

    if args.skip_seeds:
        out("")
        out("按参数要求跳过: 种子数据导入")
    else:
        step(index, steps, "种子数据导入")
        index += 1
        labels, selected = parse_seeds(args.seeds, non_interactive)
        if not run_seeds(labels, selected):
            return EXIT_FAILED

    if args.skip_users:
        out("")
        out("按参数要求跳过: 创建用户")
    else:
        step(index, steps, "创建用户")
        index += 1
        created = non_interactive_create_users(args) if non_interactive else interactive_create_users()
        if not created:
            return EXIT_FAILED

    print_summary(env, mode=mode)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
