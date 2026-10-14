#!/usr/bin/env node
/**
 * 拆分 i18n 文案：把后台专属命名空间从「前台要加载的那份」里摘出去，
 * 并把默认语言的前台文案转成**构建期内联**。
 *
 * ## 背景（为什么之前每个前台页面都要多下 193 KB）
 *
 * `@nuxtjs/i18n` 用 `locales[].file` 提供文案时，该语言的文案**不在任何客户端 chunk 里**，
 * 而是由 entry 执行后额外发一次请求去取：
 *     GET /_i18n/<hash>/zh-CN/messages.json   → 193 KB raw / 66 KB gzip
 * 这份文案里 **`admin` 命名空间占 77.5%**，而前台访客永远看不到。
 *
 * ## 拆成三份
 *
 *  1. `i18n/site/<默认语言>.json` —— 默认语言的前台文案，由 `i18n/i18n.config.ts`
 *     直接 import **内联进 bundle**。首屏就有，不需要等请求。
 *  2. `i18n/messages/<locale>.json` —— `langDir` 指向这里，作为 `locales[].file`。
 *     - 默认语言：写一个**空占位** `{}`。原因是 `@nuxtjs/i18n` 有硬校验
 *       「使用 `langDir` 时每个 locale 都必须有 `file`/`files`」（见模块 `checkLayerOptions`），
 *       而 `loadMessagesFromServer` 的入口是 `if (locale in localeLoaders === false) return`
 *       —— 只要有 `file` 就必然发一次请求，躲不掉。既然躲不掉，就让这次请求的响应体
 *       小到可忽略（真正的文案已经在 bundle 里了，空对象 merge 进去无任何影响）。
 *     - 非默认语言：前台文案本体，切过去时才加载（不为每个访客的 bundle 加体积）。
 *  3. `public/i18n/admin/<locale>.json` —— 后台命名空间，由 `layouts/admin.vue`
 *     在进入后台时按需 `$fetch` + `mergeLocaleMessage`。
 *
 * ## 真相源不变
 *
 * 唯一真相源仍是 `i18n/locales/<locale>.json`（`scripts/i18n_tool.py` 抽取/替换的那份）。
 * 本脚本只做**构建期派生**，派生文件不入库（见 `.gitignore`），
 * 由 `package.json` 的 `prescan` 在每次构建前重新生成。
 *
 * ## 护栏
 *
 * 递归统计叶子键数量，三份加起来必须等于原文件；不等就非零退出，
 * 避免"悄悄丢一批文案"这种最难查的问题。
 */
import fs from 'node:fs'
import path from 'node:path'

const ROOT = path.resolve(import.meta.dirname, '..')
const SRC_DIR = path.join(ROOT, 'i18n', 'locales')
const SITE_DIR = path.join(ROOT, 'i18n', 'site')
const MSG_DIR = path.join(ROOT, 'i18n', 'messages')
const ADMIN_DIR = path.join(ROOT, 'public', 'i18n', 'admin')

/** 后台专属的顶级命名空间；其余都视为前台也需要（前后台共用的 `common`/`article` 等留在前台包里） */
const ADMIN_NAMESPACES = new Set(['admin'])

/** 默认语言：前台文案内联进 bundle，`langDir` 下只放空占位 */
const DEFAULT_LOCALE = 'zh-CN'

const LOCALES = ['zh-CN', 'en']

/** 递归数叶子键（对象/数组按成员展开，其余算一个叶子） */
function countLeaves(value) {
    if (value === null || typeof value !== 'object') return 1
    if (Array.isArray(value)) return value.reduce((sum, item) => sum + countLeaves(item), 0)
    return Object.values(value).reduce((sum, item) => sum + countLeaves(item), 0)
}

function readJson(file) {
    return JSON.parse(fs.readFileSync(file, 'utf-8'))
}

function writeJson(file, data) {
    fs.mkdirSync(path.dirname(file), {recursive: true})
    fs.writeFileSync(file, `${JSON.stringify(data, null, 2)}\n`, 'utf-8')
}

function sizeKB(file) {
    return (fs.statSync(file).size / 1024).toFixed(1)
}

function main() {
    for (const dir of [SITE_DIR, MSG_DIR, ADMIN_DIR]) fs.mkdirSync(dir, {recursive: true})

    const report = []
    let failed = false

    for (const locale of LOCALES) {
        const srcFile = path.join(SRC_DIR, `${locale}.json`)
        if (!fs.existsSync(srcFile)) {
            console.error(`[split-i18n] 缺少真相源文件：${path.relative(ROOT, srcFile)}`)
            failed = true
            continue
        }

        const source = readJson(srcFile)
        const front = {}
        const admin = {}

        for (const [namespace, value] of Object.entries(source)) {
            if (ADMIN_NAMESPACES.has(namespace)) admin[namespace] = value
            else front[namespace] = value
        }

        const sourceLeaves = countLeaves(source)
        const splitLeaves = countLeaves(front) + countLeaves(admin)
        if (sourceLeaves !== splitLeaves) {
            console.error(
                `[split-i18n] ${locale}: 拆分前后叶子键数不一致（${sourceLeaves} vs ${splitLeaves}）—— 拒绝继续`,
            )
            failed = true
            continue
        }

        writeJson(path.join(ADMIN_DIR, `${locale}.json`), admin)

        const isDefault = locale === DEFAULT_LOCALE
        if (isDefault) {
            // 真实文案给 i18n.config.ts 内联；langDir 下留空占位满足模块校验
            writeJson(path.join(SITE_DIR, `${locale}.json`), front)
            writeJson(path.join(MSG_DIR, `${locale}.json`), {})
        } else {
            writeJson(path.join(MSG_DIR, `${locale}.json`), front)
        }

        report.push({
            locale,
            namespaces: Object.keys(source).length,
            frontLeaves: countLeaves(front),
            adminLeaves: countLeaves(admin),
            inlineKB: isDefault ? sizeKB(path.join(SITE_DIR, `${locale}.json`)) : '—',
            lazyKB: isDefault ? sizeKB(path.join(MSG_DIR, `${locale}.json`)) : sizeKB(path.join(MSG_DIR, `${locale}.json`)),
            adminKB: sizeKB(path.join(ADMIN_DIR, `${locale}.json`)),
            mode: isDefault ? '内联（langDir 下为空占位）' : 'lazy file',
        })
    }

    if (failed) process.exit(1)

    console.log('[split-i18n] 文案已拆分（真相源 i18n/locales/*.json 未改动）')
    for (const row of report) {
        console.log(
            `  ${row.locale.padEnd(6)} 命名空间 ${row.namespaces} 个 | ` +
            `前台 ${row.frontLeaves} 键（内联 ${row.inlineKB} KB / langDir ${row.lazyKB} KB，${row.mode}）| ` +
            `后台 ${row.adminLeaves} 键 / ${row.adminKB} KB（按需加载）`,
        )
    }
}

main()
