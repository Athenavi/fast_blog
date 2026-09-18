#!/usr/bin/env python3
"""i18n 批量工具：抽取候选文案 → 应用替换 → 校验。

在此之前每个页面都要手写一个一次性替换脚本，效率低且容易漏。
这个工具把它固化成三步：

    # 1) 扫描页面，列出所有「含中文的 UI 候选」（跳过代码注释），生成草稿
    python scripts/i18n_tool.py extract src/pages/system/user/index.vue \
        --prefix admin.system.user --out draft.json

    # 2) 填好草稿里的 key / en（zh 默认取原文），一条命令完成替换 + 写 locale
    python scripts/i18n_tool.py apply draft.json [--skip-invalid]

    # 3) 校验（与 scripts/check-i18n.mjs 等价，纯 Python 版）
    python scripts/i18n_tool.py check

草稿条目结构：

    {
      "file": "src/pages/system/user/index.vue",
      "line": 42,
      "raw": "新增用户",            # 原文（中文）
      "mode": "text",               # text | attr | expr
      "attr": "placeholder",        # 仅 attr 模式：属性名
      "key": "admin.system.user.create",   # ← 需要你填
      "zh": "新增用户",             # 默认 = raw
      "en": "Create user",          # ← 需要你填（留空则跳过英文）
      "all": false                  # true = 替换文件里所有同串出现
    }

要点：
  - **注释里的中文不会被抽取**（`<!-- -->`、`//`、`/* */`、`*` 行），避免把说明文字误当文案；
  - `text` 形态（`>中文<`）替换为 `{{ $t('key') }}`；
    `attr` 形态（`placeholder="中文"`）替换为 `:placeholder="$t('key')"`（自动加冒号）；
    `expr` 形态（脚本里的 `'中文'`）替换为 `t('key')`；
  - 每条替换都会校验命中次数，命中数不符就**整批中止**（不会改出半成品）；
  - 写 locale 时**保留已有 key**，只新增/更新本次涉及的，支持增量补页。
"""

import argparse
import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent  # frontend/web
LOCALE_DIR = ROOT / "i18n" / "locales"
LOCALE_FILES = ("zh-CN.json", "en.json")

CJK = re.compile(r"[\u4e00-\u9fff]")

# 抽取模式：(正则, 形态)；组 1 = 属性名（attr 专用），组 2 = 文案
PATTERNS = [
    (re.compile(r">\s*([^<>\n]*?[\u4e00-\u9fff][^<>\n]*?)\s*<"), "text", None),
    (re.compile(r"\b([A-Za-z][A-Za-z0-9-]*)=\"([^\"\n]*[\u4e00-\u9fff][^\"\n]*)\""), "attr", 1),
    (re.compile(r"'([^'\n]*[\u4e00-\u9fff][^'\n]*)'"), "expr", None),
    (re.compile(r"`([^`\n]*[\u4e00-\u9fff][^`\n]*)`"), "expr", None),
]

# 这些行里的中文是注释或非 UI 内容，跳过
SKIP_LINE = re.compile(
    r"^\s*(//|/\*|\*|<!--)"
    r"|console\.(log|warn|error)"
    r"|^\s*#"
)


def strip_line_comments(line: str, in_block: bool) -> tuple[str, bool]:
    """剥掉行内注释；返回 (可见代码, 是否仍处于多行注释中)"""
    text = line
    if in_block:
        end = text.find("*/")
        if end == -1:
            return "", True
        text = text[end + 2:]
        in_block = False

    # 块注释 /* ... */（可能同行闭合）
    while True:
        start = text.find("/*")
        if start == -1:
            break
        end = text.find("*/", start + 2)
        if end == -1:
            text = text[:start]
            in_block = True
            break
        text = text[:start] + text[end + 2:]

    # 行注释（不处理 URL 里的 //：只在前面不是 : 时切）
    for marker in ("//", "<!--"):
        idx = text.find(marker)
        while idx != -1:
            if marker == "//" and idx > 0 and text[idx - 1] == ":":
                idx = text.find(marker, idx + 2)
                continue
            text = text[:idx]
            break

    return text, in_block


COMMON_FILE = pathlib.Path(__file__).with_name("i18n-common.json")


def load_common() -> dict:
    """通用文案表：命中就自动填 key/en，省掉每页重复填「取消/保存」这类词"""
    if not COMMON_FILE.exists():
        return {}
    return json.loads(COMMON_FILE.read_text(encoding="utf-8"))


def derive_prefix(rel_path: str) -> str:
    """按文件路径推导 key 前缀

    src/pages/system/log.vue          → admin.system.log
    src/pages/system/role/index.vue   → admin.system.role
    src/pages/content/article.vue     → admin.content.article
    """
    path = rel_path.replace("\\", "/")
    for pre in ("src/pages/", "src/components/"):
        if path.startswith(pre):
            path = path[len(pre):]
            break
    if path.endswith(".vue"):
        path = path[: -4]
    parts = [part for part in path.split("/") if part and part != "index"]
    return "admin." + ".".join(parts)


def scan_file(path: pathlib.Path):
    """扫描单个文件，产出候选条目（不含 key/en）"""
    lines = path.read_text(encoding="utf-8").splitlines()
    entries = []
    in_block = False

    for lineno, line in enumerate(lines, 1):
        code, in_block = strip_line_comments(line, in_block)
        if not code or not CJK.search(code):
            continue
        if SKIP_LINE.search(code):
            continue

        candidates = []
        for pattern, mode, attr_group in PATTERNS:
            for match in pattern.finditer(code):
                if attr_group:
                    attr, raw = match.group(attr_group), match.group(2)
                    # 已有绑定（:placeholder=）的不再处理
                    if code[max(0, match.start() - 1):match.start()] == ":":
                        continue
                else:
                    attr, raw = None, match.group(1)

                raw = raw.strip()
                if not raw or not CJK.search(raw):
                    continue
                candidates.append((match.start(), match.end(), attr, raw, mode))

        # 含 `${}` 的模板串内部可能还嵌着字面量（`${x ? 'A' : 'B'}`）——
        # 若两者都抽出来会互相冲突（整串被拒、内层却被替换，留下半截中文），
        # 所以把落在插值串内部的候选丢掉，只保留整串这一条。
        interp_spans = [
            (start, end) for start, end, _attr, raw, _mode in candidates if "${" in raw
        ]
        for start, end, attr, raw, mode in candidates:
            if any(start > span_start and end <= span_end for span_start, span_end in interp_spans):
                continue
            entries.append(
                {
                    "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "line": lineno,
                    "raw": raw,
                    "mode": mode,
                    "attr": attr,
                    "key": "",
                    "zh": raw,
                    "en": "",
                    "all": False,
                    # 含 `${...}` 的模板串不能整体替换，apply 会拒绝、提示人工拆分
                    "interpolation": "${" in raw or "{{" in raw,
                }
            )

    return entries


def dedupe(entries):
    """同一文件里相同 (raw, mode) 只留一条（提示可以 all=true 一次替换）"""
    seen = {}
    for item in entries:
        # 注意：attr 必须进签名 —— `label="状态"` 与 `placeholder="状态"` 是两处不同的替换
        sig = (item["file"], item["raw"], item["mode"], item.get("attr"))
        if sig in seen:
            seen[sig]["occurrences"] = seen[sig].get("occurrences", 1) + 1
            continue
        item["occurrences"] = 1
        seen[sig] = item
    return list(seen.values())


def load_locale():
    data = {}
    for name in LOCALE_FILES:
        path = LOCALE_DIR / name
        data[name] = json.loads(path.read_bytes().decode("utf-8")) if path.exists() else {}
    return data


def set_key(tree: dict, dotted: str, value) -> None:
    parts = dotted.split(".")
    node = tree
    for part in parts[:-1]:
        nxt = node.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            node[part] = nxt
        node = nxt
    node[parts[-1]] = value


def cmd_extract(args) -> int:
    common = load_common()
    all_entries = []
    auto_filled = 0

    for target in args.files:
        path = ROOT / target if not pathlib.Path(target).is_absolute() else pathlib.Path(target)
        if not path.exists():
            print(f"跳过（不存在）：{target}")
            continue

        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        prefix = args.prefix or derive_prefix(rel)
        found = scan_file(path)
        print(f"{rel}: {len(found)} 处候选   (prefix={prefix})")

        for item in found:
            item["prefix"] = prefix
            hit = common.get(item["raw"])
            if hit:
                item["key"] = hit["key"]
                item["en"] = hit.get("en", "")
                auto_filled += 1
            item["suggested_key"] = f"{prefix}.{len(all_entries) + 1}"

        all_entries.extend(found)

    all_entries = dedupe(all_entries)
    print(f"通用文案表自动填了 {auto_filled} 处（取消/保存这类）")

    payload = {"prefix": prefix, "entries": all_entries}
    out = pathlib.Path(args.out) if args.out else ROOT / "i18n-draft.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    interp = [item for item in all_entries if item.get("interpolation")]
    print(f"\n草稿已写出：{out}（{len(all_entries)} 条，去重后）")
    if interp:
        print(f"⚠️  其中 {len(interp)} 条含 ${{}} 插值，不能整体替换，需人工拆分（apply 会拒绝）：")
        for item in interp:
            print(f"   - {item['file']}:{item['line']} 「{item['raw'][:40]}」")
    print("下一步：填好每条 key / en，再跑 apply")
    return 0


SCRIPT_SETUP_RE = re.compile(r"(<script[^>]*\bsetup\b[^>]*>\r?\n)")


def ensure_use_i18n(source: str) -> tuple[str, bool]:
    """`<script setup>` 里用到 `t()` 时必须显式解构 useI18n

    模板里的 `$t()` 是 i18n 全局注入的，但 `<script>` 里的 `t()` 不是 ——
    漏了会在 type-check 报 `Cannot find name 't'`。
    """
    if "useI18n()" in source:
        return source, False
    new, n = SCRIPT_SETUP_RE.subn(r"\1const {t} = useI18n()\n", source, count=1)
    return new, bool(n)


def cmd_apply(args) -> int:
    draft_path = pathlib.Path(args.draft)
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    entries = draft.get("entries", [])
    if not entries:
        print("草稿里没有条目")
        return 1

    # 只处理填了 key 的条目
    todo = [item for item in entries if item.get("key")]
    skipped = len(entries) - len(todo)
    if skipped:
        print(f"跳过未填 key 的 {skipped} 条")
    if not todo:
        print("没有可应用的条目（都还没填 key）")
        return 1

    # 按文件分组，逐个文件一次性替换（避免多次读写）
    by_file: dict[str, list] = {}
    for item in todo:
        by_file.setdefault(item["file"], []).append(item)

    failures = []
    changed_files = {}
    replaced = 0
    for rel, items in by_file.items():
        path = ROOT / rel
        text = path.read_bytes().decode("utf-8")
        original = text

        for item in items:
            if item.get("interpolation"):
                failures.append((rel, item, "含 ${} 插值，需人工拆成带参数的 key（如 xxxWithName）"))
                continue

            raw, mode, key = item["raw"], item["mode"], item["key"]
            if mode == "text":
                old = f">{raw}<"
                # ⚠️ 这里**不能**用 f-string：`">{{ ... }}"` 里的 {{ }} 会被转义成单个花括号
                new = ">{{ $t('" + key + "') }}<"
            elif mode == "attr":
                attr = item.get("attr") or ""
                if not attr:
                    failures.append((rel, item, "attr 模式缺少属性名"))
                    continue
                old = f'{attr}="{raw}"'
                new = f":{attr}=\"$t('{key}')\""
            else:  # expr
                old = f"'{raw}'"
                new = f"t('{key}')"

            count = text.count(old)
            if count == 0:
                # --allow-missing：把「未命中」当成「已经替换过」（幂等重跑），静默跳过
                if getattr(args, "allow_missing", False):
                    continue
                failures.append((rel, item, "未命中"))
                continue
            if count > 1 and not item.get("all"):
                failures.append((rel, item, f"命中 {count} 次（要全部替换请在草稿里置 all=true）"))
                continue
            text = text.replace(old, new)
            replaced += count if item.get("all") else 1

        if text != original:
            changed_files[rel] = text

    if failures and not args.skip_invalid:
        print("\n❌ 以下条目未应用（**整批未写入**，避免改出半成品）：")
        for rel, item, why in failures:
            print(f"  - {rel}:{item['line']} 「{item['raw']}」 → {why}")
        print("\n（这些条目要么补 key、要么人工处理；确认要忽略它们可加 --skip-invalid）")
        return 1

    if failures:
        print(f"\n⚠️  按 --skip-invalid 跳过 {len(failures)} 条：")
        for rel, item, why in failures:
            print(f"  - {rel}:{item['line']} 「{item['raw'][:34]}」 → {why}")

    # 写文件（若改动引入了 script 里的 t()，顺带注入 useI18n）
    for rel, content in changed_files.items():
        if re.search(r"(?<![\w$.])t\('", content):
            content, injected = ensure_use_i18n(content)
            if injected:
                print(f"  已在 {rel} 注入 const {{t}} = useI18n()")
        changed_files[rel] = content
        (ROOT / rel).write_bytes(content.encode("utf-8"))
    print(f"已替换 {replaced} 处，改动 {len(changed_files)} 个文件")

    # 写 locale（保留已有 key）
    locales = load_locale()
    added = 0
    # 只写**真正应用成功**的条目 —— 失败/跳过的条目若也写入，
    # 会造成「zh 有、en 没有」的不对称（check 会报出来）
    failed_sigs = {
        (rel, item["raw"], item["mode"], item.get("attr")) for rel, item, _why in failures
    }
    for item in todo:
        sig = (item["file"], item["raw"], item["mode"], item.get("attr"))
        if sig in failed_sigs:
            continue
        key = item["key"]
        zh = item.get("zh") or item["raw"]
        set_key(locales["zh-CN.json"], key, zh)
        if item.get("en"):
            set_key(locales["en.json"], key, item["en"])
        added += 1

    for name, tree in locales.items():
        path = LOCALE_DIR / name
        path.write_bytes(json.dumps(tree, ensure_ascii=False, indent=2).encode("utf-8"))
        print(f"  locale {name}: 已更新")

    print(f"\n✅ 完成：{added} 条 key 写入 locale；请跑 `npm run check:i18n` 校验")
    return 0


def cmd_check(_args) -> int:
    locales = load_locale()
    base = flatten(locales["zh-CN.json"])
    other = flatten(locales["en.json"])

    asymmetric = [f"{k} 只在 zh-CN 里" for k in sorted(base - other)]
    asymmetric += [f"{k} 只在 en 里" for k in sorted(other - base)]

    used = set()
    usage_re = re.compile(r"(?:\$t|\bt)\(\s*['\"`]([A-Za-z0-9_.]+)['\"`]")
    for path in (ROOT / "src").rglob("*"):
        if path.suffix not in (".vue", ".ts") or not path.is_file():
            continue
        if any(part in ("node_modules", ".nuxt", ".output", ".plugin-pages") for part in path.parts):
            continue
        for match in usage_re.finditer(path.read_text(encoding="utf-8")):
            used.add(match.group(1))

    menus_file = ROOT / "src" / "utils" / "menus.ts"
    menu_names = []
    missing_menus = []
    if menus_file.exists():
        menu_names = re.findall(r"name:\s*'([^']+)'", menus_file.read_text(encoding="utf-8"))
        missing_menus = [n for n in menu_names if f"menu.{n}" not in base]

    missing = sorted(k for k in used if k not in base)

    print(f"key 总数：{len(base)}（zh-CN.json）")
    print(f"代码引用：{len(used)} 个 key")
    print(f"菜单项：{len(menu_names)} 个（动态 key）")
    if asymmetric:
        print("\n⚠️  两份 locale 不对称：")
        for line in asymmetric[:40]:
            print(f"  - {line}")
    if missing_menus:
        print("\n❌ 菜单缺少翻译：")
        for name in missing_menus:
            print(f"  - menu.{name}")
    if missing:
        print("\n❌ 代码引用但 locale 缺失：")
        for key in missing:
            print(f"  - {key}")
    if missing or missing_menus:
        return 1
    print("\n✅ 所有引用的 key 都存在（含菜单动态 key）")
    return 0


def flatten(node, prefix="", out=None):
    if out is None:
        out = set()
    if isinstance(node, dict):
        for key, value in node.items():
            flatten(value, f"{prefix}.{key}" if prefix else key, out)
    elif prefix:
        out.add(prefix)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="i18n 批量工具")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_extract = sub.add_parser("extract", help="扫描页面生成草稿")
    p_extract.add_argument("files", nargs="+")
    p_extract.add_argument("--prefix", default="", help="key 前缀，如 admin.system.user")
    p_extract.add_argument("--out", default="", help="草稿输出路径")
    p_extract.set_defaults(func=cmd_extract)

    p_apply = sub.add_parser("apply", help="按草稿执行替换并写 locale")
    p_apply.add_argument("draft")
    p_apply.add_argument(
        "--allow-missing",
        action="store_true",
        help="把「未命中」视为已替换过（幂等重跑用），静默跳过",
    )
    p_apply.add_argument(
        "--skip-invalid",
        action="store_true",
        help="跳过无法应用的条目（如含 ${} 插值），继续处理其余；默认整批拒绝",
    )
    p_apply.set_defaults(func=cmd_apply)

    p_check = sub.add_parser("check", help="校验 locale 与引用")
    p_check.set_defaults(func=cmd_check)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
