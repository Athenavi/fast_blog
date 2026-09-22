#!/usr/bin/env node
// 首屏 JS 包体预算检查（UI/UX 路线图 Batch 0.3）
//
// 为什么需要：后台 UI/UX 重构会持续往初始包里加东西（Element Plus 一次性带来过 1.1MB，
// 见 `src/layouts/admin.vue` 的说明），只靠"感觉快了"迟早翻车。这里从**真实构建产物**里
// 取首屏实际加载的脚本，比较 gzip 后的体积与预算。
//
// 做法：起 `.output/server/index.mjs`（node-server preset，自带 node_modules，可独立运行），
// 抓 SSR 输出的 HTML，解析 `<script src>` 与 `<link rel="modulepreload">` 指向的 `_nuxt/*.js`
// —— 这些就是浏览器首屏必须下载的脚本，其余 chunk 都是按需加载。
//
// 用法：
//   npm run build
//   node scripts/check-bundle-budget.mjs                  # 前台首页 + 后台仪表盘
//   node scripts/check-bundle-budget.mjs --json           # 机器可读输出（CI 归档用）
//   node scripts/check-bundle-budget.mjs --no-server --base-url http://localhost:3000
//   node scripts/check-bundle-budget.mjs --budget-initial-kb 240 --budget-total-kb 1600
//
// 退出码：0 通过；1 超预算；2 前置条件缺失（未 build / 服务起不来）

import {spawn} from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import zlib from 'node:zlib'

const ROOT = path.resolve(import.meta.dirname, '..')
const OUTPUT_DIR = path.join(ROOT, '.output')
const PUBLIC_DIR = path.join(OUTPUT_DIR, 'public')
const NUXT_DIR = path.join(PUBLIC_DIR, '_nuxt')
const SERVER_ENTRY = path.join(OUTPUT_DIR, 'server', 'index.mjs')

/** 首屏初始包预算（gzip KB）—— 超过即失败。基线见文件末尾的实测记录。 */
const DEFAULT_INITIAL_KB = 200
/** 全量 JS 预算（gzip KB）—— 防止 chunk 数量与体积无感膨胀。 */
const DEFAULT_TOTAL_KB = 1600

/** 被测路由：前台是 SSR、后台是 CSR（routeRules），但两者的首屏脚本都必须可解析。 */
const ROUTES = [
    {name: '前台首页', path: '/'},
    {name: '后台仪表盘', path: '/dashboard'},
]

function parseArgs(argv) {
    const args = {
        json: false, noServer: false, baseUrl: '', budgetInitialKb: DEFAULT_INITIAL_KB,
        budgetTotalKb: DEFAULT_TOTAL_KB, port: 3081, top: 8
    }
    for (let i = 0; i < argv.length; i += 1) {
        const key = argv[i]
        const next = () => argv[++i]
        if (key === '--json') args.json = true
        else if (key === '--no-server') args.noServer = true
        else if (key === '--base-url') args.baseUrl = next()
        else if (key === '--port') args.port = Number(next())
        else if (key === '--budget-initial-kb') args.budgetInitialKb = Number(next())
        else if (key === '--budget-total-kb') args.budgetTotalKb = Number(next())
        else if (key === '--top') args.top = Number(next())
        else if (key === '--help' || key === '-h') {
            console.log(fs.readFileSync(import.meta.filename, 'utf-8').split('\n').slice(1, 22).join('\n'))
            process.exit(0)
        }
    }
    return args
}

/** 从 SSR HTML 里取出首屏脚本路径（`/_nuxt/xxx.js`，去重且保序） */
export function extractInitialScripts(html) {
    const found = []
    const seen = new Set()
    const push = (href) => {
        if (!href || !href.includes('_nuxt/') || !href.endsWith('.js')) return
        const clean = href.split('?')[0]
        if (seen.has(clean)) return
        seen.add(clean)
        found.push(clean)
    }

    for (const match of html.matchAll(/<script[^>]*\ssrc="([^"]+)"/g)) push(match[1])
    for (const match of html.matchAll(/<link[^>]*>/g)) {
        const tag = match[0]
        if (!/\srel="(modulepreload|preload)"/.test(tag)) continue
        if (/\sas="(?!script)[^"]*"/.test(tag)) continue
        const href = tag.match(/\shref="([^"]+)"/)
        if (href) push(href[1])
    }
    return found
}

function gzipSize(buf) {
    // level 6 = zlib 默认，贴近 CDN/nginx 的 gzip 实际表现
    return zlib.gzipSync(buf, {level: 6}).length
}

function fileStats(urlPath) {
    const file = path.join(PUBLIC_DIR, urlPath.replace(/^\//, '').split('?')[0])
    if (!fs.existsSync(file)) return null
    const buf = fs.readFileSync(file)
    return {url: urlPath, file: path.relative(ROOT, file), raw: buf.length, gzip: gzipSize(buf)}
}

function totalJsStats() {
    if (!fs.existsSync(NUXT_DIR)) return {files: 0, raw: 0, gzip: 0}
    const result = {files: 0, raw: 0, gzip: 0}
    for (const entry of fs.readdirSync(NUXT_DIR, {withFileTypes: true, recursive: true})) {
        if (!entry.isFile() || !entry.name.endsWith('.js')) continue
        const full = path.join(entry.parentPath ?? NUXT_DIR, entry.name)
        const buf = fs.readFileSync(full)
        result.files += 1
        result.raw += buf.length
        result.gzip += gzipSize(buf)
    }
    return result
}

async function waitForServer(baseUrl, timeoutMs = 40_000) {
    const deadline = Date.now() + timeoutMs
    let lastError = ''
    while (Date.now() < deadline) {
        try {
            const resp = await fetch(baseUrl, {redirect: 'follow'})
            await resp.text()
            return true
        } catch (error) {
            lastError = error instanceof Error ? error.message : String(error)
            await new Promise((resolve) => setTimeout(resolve, 400))
        }
    }
    throw new Error(`服务在 ${timeoutMs}ms 内未就绪（${lastError}）`)
}

async function main() {
    const args = parseArgs(process.argv.slice(2))

    if (!fs.existsSync(SERVER_ENTRY) || !fs.existsSync(NUXT_DIR)) {
        console.error('[ERROR] 找不到 .output/server/index.mjs 或 .output/public/_nuxt')
        console.error('        请先构建：npm run build')
        return 2
    }

    let server = null
    let baseUrl = args.baseUrl
    if (!args.noServer) {
        const port = args.port
        server = spawn(process.execPath, [SERVER_ENTRY], {
            cwd: ROOT,
            env: {
                ...process.env,
                PORT: String(port),
                NITRO_PORT: String(port),
                HOST: '127.0.0.1',
                NITRO_HOST: '127.0.0.1'
            },
            stdio: ['ignore', 'pipe', 'pipe'],
        })
        server.stdout.on('data', () => {
        })
        server.stderr.on('data', () => {
        })
        baseUrl = `http://127.0.0.1:${port}`
    } else if (!baseUrl) {
        console.error('[ERROR] --no-server 时必须提供 --base-url')
        return 2
    }

    const cleanup = () => {
        if (server && !server.killed) server.kill()
    }
    process.on('exit', cleanup)

    const report = {routes: [], total: null, budget: {initialKb: args.budgetInitialKb, totalKb: args.budgetTotalKb}}
    const failures = []
    try {
        await waitForServer(baseUrl)

        for (const route of ROUTES) {
            let html = ''
            try {
                const resp = await fetch(`${baseUrl}${route.path}`, {redirect: 'follow'})
                html = await resp.text()
            } catch (error) {
                failures.push(`${route.name} ${route.path} 请求失败：${error instanceof Error ? error.message : error}`)
                continue
            }

            const urls = extractInitialScripts(html)
            const files = urls.map(fileStats).filter(Boolean)
            const gzipKb = Math.round(files.reduce((sum, item) => sum + item.gzip, 0) / 1024)
            const rawKb = Math.round(files.reduce((sum, item) => sum + item.raw, 0) / 1024)
            report.routes.push({route, scripts: files.length, initialGzipKb: gzipKb, initialRawKb: rawKb, files})

            if (files.length === 0) {
                failures.push(`${route.name} ${route.path} 未解析到首屏脚本（HTML 结构变了？）`)
            } else if (gzipKb > args.budgetInitialKb) {
                failures.push(`${route.name} 首屏 JS ${gzipKb}KB > 预算 ${args.budgetInitialKb}KB`)
            }
        }

        const total = totalJsStats()
        report.total = {...total, gzipKb: Math.round(total.gzip / 1024), rawKb: Math.round(total.raw / 1024)}
        if (report.total.gzipKb > args.budgetTotalKb) {
            failures.push(`全量 JS ${report.total.gzipKb}KB > 预算 ${args.budgetTotalKb}KB`)
        }
    } finally {
        cleanup()
    }

    if (args.json) {
        console.log(JSON.stringify({...report, failures}, null, 2))
    } else {
        console.log('== 首屏 JS 包体（gzip） ==')
        for (const item of report.routes) {
            console.log(
                `  ${item.route.name.padEnd(8)} ${String(item.initialGzipKb).padStart(5)}KB / 预算 ${args.budgetInitialKb}KB` +
                `  （${item.scripts} 个脚本，raw ${item.initialRawKb}KB）`,
            )
            const top = [...item.files].sort((a, b) => b.gzip - a.gzip).slice(0, args.top)
            for (const file of top) {
                console.log(`      ${String(Math.round(file.gzip / 1024)).padStart(5)}KB  ${file.file}`)
            }
        }
        console.log(`  ${'全量 JS'.padEnd(8)} ${String(report.total.gzipKb).padStart(5)}KB / 预算 ${args.budgetTotalKb}KB` +
            `  （${report.total.files} 个 chunk，raw ${report.total.rawKb}KB）`)
        if (failures.length) {
            console.log('\n[FAIL] 超预算：')
            for (const line of failures) console.log(`  - ${line}`)
        } else {
            console.log('\n[OK] 全部在预算内')
        }
    }

    return failures.length ? 1 : 0
}

process.exitCode = await main()

// ---------------------------------------------------------------------------
// 实测基线（改预算前先看这里，别为了让 CI 变绿而调高阈值）
//
// 2026-09-22 首次运行（win32 / node 25.2.1，构建产物 nitro 2026-09-22T09:28:33Z）：
//   前台首页 189KB / 后台仪表盘 158KB / 全量 JS 1110KB（177 个 chunk）
// 预算默认值 = 首屏 200KB、全量 1600KB；前台首页已用掉 95% 的首屏预算，
// 再往初始包里加东西就会红 —— 这正是 Batch 4.2（EP 按需引入 / 路由分割）要解决的。
// 注意：改预算前先看这里，别为了让 CI 变绿而调高阈值。
// ---------------------------------------------------------------------------
