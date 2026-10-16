// i18n key 校验：确保代码里用到的 key 都在 locale 文件里存在
//
// 用法：node scripts/check-i18n.mjs
// 退出码非 0 表示有缺失 key（便于挂到 CI / pre-commit）。
//
// 为什么需要：`$t('a.b.c')` 拼错时 i18n **不会报错**，只会把 key 原样渲染到界面上。
// 这个脚本把这类问题在提交前就抓出来。

import fs from 'node:fs'
import path from 'node:path'

const ROOT = path.resolve(import.meta.dirname, '..')
const LOCALE_DIR = path.join(ROOT, 'i18n', 'locales')
const SRC_DIR = path.join(ROOT, 'src')
const LOCALE_FILES = ['zh-CN.json', 'en.json']

/** 把嵌套对象摊平成 `a.b.c` 形式的 key 集合 */
function flatten(node, prefix = '', out = new Set()) {
    if (node && typeof node === 'object' && !Array.isArray(node)) {
        for (const [key, value] of Object.entries(node)) {
            flatten(value, prefix ? `${prefix}.${key}` : key, out)
        }
    } else if (prefix) {
        out.add(prefix)
    }
    return out
}

function walk(dir, out = []) {
    for (const entry of fs.readdirSync(dir, {withFileTypes: true})) {
        const full = path.join(dir, entry.name)
        if (entry.isDirectory()) {
            if (['node_modules', '.nuxt', '.output', '.plugin-pages'].includes(entry.name)) continue
            walk(full, out)
        } else if (/\.(vue|ts)$/.test(entry.name)) {
            out.push(full)
        }
    }
    return out
}

// 1) 汇总两份 locale 的 key（并要求两边一致）
const localeKeys = new Map()
for (const file of LOCALE_FILES) {
    const data = JSON.parse(fs.readFileSync(path.join(LOCALE_DIR, file), 'utf-8'))
    localeKeys.set(file, flatten(data))
}

const [first, ...rest] = LOCALE_FILES
const base = localeKeys.get(first)
let asymmetric = []
for (const file of rest) {
    const other = localeKeys.get(file)
    for (const key of base) if (!other.has(key)) asymmetric.push(`${key} 只在 ${first} 里`)
    for (const key of other) if (!base.has(key)) asymmetric.push(`${key} 只在 ${file} 里`)
}

// 2) 扫描代码里用到的 key
const USAGE_RE = /(?:\$t|\bt)\(\s*['"`]([a-zA-Z0-9_.]+)['"`]/g
const used = new Set()
for (const file of walk(SRC_DIR)) {
    const text = fs.readFileSync(file, 'utf-8')
    for (const match of text.matchAll(USAGE_RE)) {
        // 跳过明显不是 i18n key 的调用（要求至少一个点，且首段为已知命名空间）
        if (match[1].includes('.') && base.has(match[1])) used.add(match[1])
        else if (match[1].includes('.')) used.add(match[1])
    }
}

// 3) 菜单是动态 key（`menu.${name}`），静态扫描覆盖不到，单独校验
const menusFile = path.join(SRC_DIR, 'utils', 'menus.ts')
let menuNames = []
let missingMenus = []
if (fs.existsSync(menusFile)) {
    const menuText = fs.readFileSync(menusFile, 'utf-8')
    menuNames = [...menuText.matchAll(/name:\s*'([^']+)'/g)].map((m) => m[1])
    missingMenus = menuNames.filter((name) => !base.has(`menu.${name}`))
}

// 5) 模板里出现 `{ $t(`（**单**花括号）说明替换时把 {{ }} 写坏了 ——
//    Vue 会把它当纯文本渲染，界面上直接显示 key，而 type-check 抓不到
const malformed = []
for (const file of walk(SRC_DIR)) {
    const lines = fs.readFileSync(file, 'utf-8').split('\n')
    lines.forEach((line, idx) => {
        if (/>\s*\{\s*\$t\(/.test(line)) {
            malformed.push(`${path.relative(ROOT, file).replace(/\\/g, '/')}:${idx + 1}`)
        }
    })
}

// 6) 文案必须能被 vue-i18n **编译**：像 `JSON，如 {"a": "b"}` 这种"看着像插值"的文本，
//    会让页面在渲染期直接抛错（Vite overlay + 白屏）；key 存在、type-check 也发现不了。
//    这里用真正的 message-compiler 逐个过一遍（字面量花括号要写成 `{'{'}`）。
const compileErrors = []
{
    // 用 vue-i18n 真正的编译入口（`@intlify/core-base` 的 `compile`，vue-i18n 依赖它）：
    // `@intlify/message-compiler` 的 `baseCompile` 对这种文本**不报错**，抓不住问题。
    const {compile} = await import('@intlify/core-base')
    for (const file of LOCALE_FILES) {
        const data = JSON.parse(fs.readFileSync(path.join(LOCALE_DIR, file), 'utf-8'))
        const stack = [[data, '']]
        while (stack.length) {
            const [node, prefix] = stack.pop()
            for (const [key, value] of Object.entries(node)) {
                const full = prefix ? `${prefix}.${key}` : key
                if (typeof value === 'string') {
                    try {
                        compile(value, {})
                    } catch (error) {
                        compileErrors.push(`${file}: ${full} -> ${String(error.message).split('\n')[0]}`)
                    }
                } else if (value && typeof value === 'object') {
                    stack.push([value, full])
                }
            }
        }
    }
}

// 7) 报告
const missing = [...used].filter((key) => !base.has(key)).sort()
console.log(`locale 文件：${LOCALE_FILES.join(', ')}`)
console.log(`key 总数：${base.size}（${first}）`)
console.log(`代码引用：${used.size} 个 key`)
console.log(`菜单项：${menuNames.length} 个（动态 key，单独校验）`)

if (asymmetric.length) {
    console.log('\n⚠️  两份 locale 的 key 不对称：')
    for (const line of asymmetric) console.log(`  - ${line}`)
}

if (missingMenus.length) {
    console.log('\n❌ menus.ts 里这些菜单缺少 `menu.<name>` 翻译：')
    for (const name of missingMenus) console.log(`  - menu.${name}`)
}

if (malformed.length) {
    console.log('\n❌ 模板里出现单花括号的 `{ $t(...)`（应为 `{{ $t(...) }}`）：')
    for (const line of malformed) console.log(`  - ${line}`)
}

if (compileErrors.length) {
    console.log('\n❌ 这些文案无法被 vue-i18n 编译（多半是写了 `{...}` 字面量，需转义为 `{\'{\'}`）：')
    for (const line of compileErrors) console.log(`  - ${line}`)
}

if (missing.length) {
    console.log('\n❌ 代码里用到但 locale 缺失的 key：')
    for (const key of missing) console.log(`  - ${key}`)
}

if (missing.length || missingMenus.length || malformed.length || asymmetric.length || compileErrors.length) {
    process.exit(1)
}

console.log('\n✅ 所有引用的 key 都存在（含菜单动态 key），两份 locale 对称，且无单花括号问题')
