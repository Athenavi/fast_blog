#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""FastBlog 交互式测试运行器。

用法::

    python scripts/test.py                 # 交互式菜单（可多选，如 `1,5,7`）
    python scripts/test.py --list          # 只列出全部测试项
    python scripts/test.py --run 1,5       # 非交互执行（便于脚本 / CI 复用）
    python scripts/test.py --run backend   # 按别名执行打包项

设计要点：

- **纯标准库**，Windows 与 POSIX 都能跑；不需要额外依赖。
- 后端按「全部 / 路由契约 / 按域 / 单文件」组织；前端按
  「type-check / i18n / e2e 全量 / 单个 spec / visual / a11y」组织。
- 多选后**顺序执行**并汇总每项通过/失败与耗时；任一项失败不影响后续项。
- e2e 默认串行（``--workers=1``）：后端按 IP 计防爆破，9 个 worker 并发登录会被限流。
- e2e 凭证从 ``frontend/web/.env.e2e`` 读取；也可用环境变量
  ``E2E_ADMIN_USER`` / ``E2E_ADMIN_PASS`` 覆盖（已存在的环境变量优先）。
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB = ROOT / "frontend" / "web"
TESTS = ROOT / "tests"

PY = sys.executable or "python"


# --------------------------------------------------------------------- 工具
def npm_cmd(*args: str) -> list[str]:
    """Windows 上 npm 是 npm.cmd，需按可执行文件解析。"""
    npm = shutil.which("npm") or shutil.which("npm.cmd") or "npm"
    return [npm, *args]


def load_e2e_env() -> dict[str, str]:
    """把 frontend/web/.env.e2e 读进子进程环境（不覆盖已存在的环境变量）。"""
    env = dict(os.environ)
    for candidate in (WEB / ".env.e2e", ROOT / ".env.e2e"):
        if not candidate.exists():
            continue
        for line in candidate.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$", line)
            if m and m.group(1) not in env:
                env[m.group(1)] = m.group(2)
        break
    return env


def backend_files() -> list[str]:
    return sorted(p.name for p in TESTS.glob("test_*.py"))


def v3_files(domain: str) -> list[str]:
    """按域挑选后端测试文件（文件名前缀匹配 + 已知同族文件）。"""
    alias = {
        "system": ("system", "route_contract", "setting_runtime", "admin_menu", "accessibility",
                   "maintenance", "permission_scope", "group_scope", "write_scope", "screen_options",
                   "quota", "site_health", "slow_query", "web_vitals", "translation", "workflow",
                   "edge", "oauth", "utility", "help", "export", "base_crud"),
        "content": ("content", "amp", "article_preview", "recommend", "yjs", "rss_feed", "seo"),
        "commerce": ("commerce", "shop", "payment_tax", "tipping", "revenue"),
        "analytics": ("analytics", "query_optimizer", "seo"),
        "ops": ("backup", "migration", "supervisor", "upgrade", "deployment"),
        "chat": ("chat", "web_push"),
        "ai": ("ai",),
        "mobile": ("mobile", "follow", "feed", "user_home"),
        "extension": ("extension",),
        "marketing": ("certification", "gdpr_compliance", "security_anomaly", "third_party_publish"),
    }
    keys = alias.get(domain, (domain,))
    chosen = [f for f in backend_files() if any(k in f for k in keys)]
    return chosen


DOMAINS = ("system", "content", "commerce", "analytics", "ops", "chat", "ai", "mobile",
           "extension", "marketing")


# --------------------------------------------------------------------- 测试项
class Item:
    def __init__(self, key: str, title: str, cmd: list[str], cwd: pathlib.Path,
                 note: str = "", aliases: tuple[str, ...] = ()) -> None:
        self.key = key
        self.title = title
        self.cmd = cmd
        self.cwd = cwd
        self.note = note
        self.aliases = aliases


def build_items() -> list[Item]:
    items: list[Item] = []

    items.append(Item("1", "后端·全部（pytest tests/）",
                      [PY, "-m", "pytest", "tests/", "-q"], ROOT,
                      "约 15 分钟；需要 DB 的用例会失败", ("backend", "all-backend")))
    items.append(Item("2", "后端·路由契约（唯一权威，快）",
                      [PY, "-m", "pytest", "tests/test_v3_route_contract.py", "-q"], ROOT,
                      "登记完整性 / 无冲突遮蔽 / 882 条路由快照 / 鉴权分流", ("contract",)))

    for index, domain in enumerate(DOMAINS, start=3):
        files = v3_files(domain)
        if not files:
            continue
        items.append(Item(str(index), f"后端·{domain} 域（{len(files)} 文件）",
                          [PY, "-m", "pytest", *[f"tests/{f}" for f in files], "-q"], ROOT,
                          "", (f"backend-{domain}", domain)))

    nxt = 3 + len(DOMAINS)
    items.append(Item(str(nxt), "后端·单个文件…", [], ROOT, "二级菜单选择", ("backend-one",)))
    N = nxt

    items.append(Item(str(N + 1), "前端·type-check", npm_cmd("run", "type-check"), WEB,
                      "prescan + nuxt typecheck", ("type-check",)))
    items.append(Item(str(N + 2), "前端·check:i18n", npm_cmd("run", "check:i18n"), WEB,
                      "locale 对称 + key 齐备 + menu.* 存在", ("i18n",)))
    items.append(Item(str(N + 3), "前端·e2e 全量（串行）",
                      npm_cmd("run", "test:e2e", "--", "--workers=1"), WEB,
                      "9 个 spec；串行避免登录限流", ("e2e",)))
    items.append(Item(str(N + 4), "前端·单个 e2e spec…", [], WEB, "二级菜单选择", ("e2e-one",)))
    items.append(Item(str(N + 5), "前端·visual 快照（比对）",
                      npm_cmd("run", "test:e2e:visual"), WEB, "", ("visual",)))
    items.append(Item(str(N + 6), "前端·a11y 巡检",
                      npm_cmd("run", "test:e2e:a11y"), WEB,
                      "与 e2e/a11y-baseline.json 比对", ("a11y",)))
    items.append(Item(str(N + 7), "前端·visual 快照（重新生成基线）",
                      npm_cmd("run", "test:e2e:visual:update"), WEB,
                      "仅在确认 UI 变更可接受时使用", ("visual-update",)))
    items.append(Item(str(N + 8), "全部：后端契约 + type-check + i18n + e2e",
                      [], ROOT, "组合执行", ("smoke",)))
    return items


def list_specs() -> list[str]:
    if not (WEB / "e2e").exists():
        return []
    return sorted(p.name for p in (WEB / "e2e").glob("*.spec.ts"))


def list_markers() -> list[str]:
    return []


# --------------------------------------------------------------------- 执行
def run_item(item: Item) -> tuple[str, bool, float, str]:
    print(f"\n{'=' * 78}\n▶ {item.title}\n  {item.note or ''}\n  $ {' '.join(item.cmd)}\n{'=' * 78}")
    started = time.time()
    env = load_e2e_env() if item.cwd == WEB else None
    try:
        proc = subprocess.run(item.cmd, cwd=str(item.cwd), env=env)
        ok = proc.returncode == 0
        detail = f"exit {proc.returncode}"
    except KeyboardInterrupt:
        ok, detail = False, "被中断"
    except FileNotFoundError as exc:
        ok, detail = False, f"命令不存在：{exc}"
    elapsed = time.time() - started
    status = "✅ 通过" if ok else "❌ 失败"
    print(f"{status}  {item.title}  （{elapsed:.1f}s，{detail}）")
    return item.title, ok, elapsed, detail


def run_sequence(items: list[Item]) -> int:
    results = [run_item(item) for item in items]
    print(f"\n{'=' * 78}\n汇总\n{'=' * 78}")
    for title, ok, elapsed, detail in results:
        print(f"  {'✅' if ok else '❌'}  {title:<48} {elapsed:>7.1f}s  {detail}")
    failed = [r for r in results if not r[1]]
    print(f"\n共 {len(results)} 项，通过 {len(results) - len(failed)}，失败 {len(failed)}")
    return 1 if failed else 0


# --------------------------------------------------------------------- 交互
def choose(prompt: str, options: list[str]) -> list[str]:
    while True:
        print(f"\n{prompt}")
        for idx, opt in enumerate(options, start=1):
            print(f"  {idx}. {opt}")
        raw = input("选择（可多选，逗号分隔；回车返回）: ").strip()
        if not raw:
            return []
        picked: list[str] = []
        for token in re.split(r"[,，\s]+", raw):
            if token.isdigit() and 1 <= int(token) <= len(options):
                picked.append(options[int(token) - 1])
            else:
                print(f"  ! 忽略无效选择：{token}")
        if picked:
            return picked


def interactive(items: list[Item]) -> int:
    while True:
        print(f"\n{'=' * 78}\n FastBlog 测试运行器（工作区：{ROOT}）\n{'=' * 78}")
        for item in items:
            print(f"  {item.key:>2}. {item.title}" + (f"  — {item.note}" if item.note else ""))
        print("   l. 列出后端测试文件")
        print("   q. 退出")

        raw = input("\n选择（可多选，如 1,5,7 / 别名如 type-check / 回车刷新）: ").strip().lower()
        if raw in {"q", "quit", "exit"}:
            return 0
        if raw in {"l", "list"}:
            for name in backend_files():
                print(f"    {name}")
            continue
        if not raw:
            continue

        tokens = [t for t in re.split(r"[,，\s]+", raw) if t]
        picked: list[Item] = []
        for token in tokens:
            match = [i for i in items if i.key == token or token in i.aliases]
            if match:
                picked.extend(match)
                continue
            print(f"  ! 未知选择：{token}")

        expanded: list[Item] = []
        for item in picked:
            if item.title.startswith("后端·单个文件"):
                files = choose("后端测试文件", backend_files())
                for name in files:
                    expanded.append(Item("f", name, [PY, "-m", "pytest", f"tests/{name}", "-q"], ROOT))
            elif item.title.startswith("前端·单个 e2e"):
                specs = choose("e2e spec", list_specs())
                for name in specs:
                    expanded.append(Item("s", name,
                                         npm_cmd("run", "test:e2e", "--", f"e2e/{name}", "--workers=1"),
                                         WEB))
            elif item.title.startswith("全部：后端契约"):
                base = build_items()
                by_alias = {a: i for i in base for a in i.aliases}
                expanded.extend([by_alias["contract"], by_alias["type-check"], by_alias["i18n"],
                                 by_alias["e2e"]])
            else:
                expanded.append(item)

        if not expanded:
            continue
        return run_sequence(expanded)


def main() -> int:
    try:
        if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

    parser = argparse.ArgumentParser(description="FastBlog 交互式测试运行器")
    parser.add_argument("--list", action="store_true", help="列出全部可选项后退出")
    parser.add_argument("--run", help="不进入交互，直接执行（逗号分隔 key 或别名）")
    args = parser.parse_args()

    items = build_items()

    if args.list:
        for item in items:
            print(f"{item.key:>2}. {item.title}" + (f"  — {item.note}" if item.note else ""))
        return 0

    if args.run:
        tokens = [t for t in re.split(r"[,，\s]+", args.run) if t]
        picked: list[Item] = []
        for token in tokens:
            match = [i for i in items if i.key == token or token in i.aliases]
            if not match:
                print(f"未知选择：{token}", file=sys.stderr)
                return 2
            picked.extend(match)
        return run_sequence(picked)

    return interactive(items)


if __name__ == "__main__":
    sys.exit(main())
