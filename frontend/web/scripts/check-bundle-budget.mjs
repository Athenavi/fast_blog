#!/usr/bin/env node
/**
 * 包体预算检查（UI/UX 路线图 Batch 0.3；B3 扩成**双口径**）
 *
 * ## 为什么要有两道口径
 *
 * 原来只解析 SSR HTML 里的 `<script src>` + `<link rel="modulepreload">`，量的是
 * 「首屏关键路径上的 JS」。它有明确的盲区 —— **HTML 里查不到、但用户实际会下载**的东西：
 *
 *  - 懒加载的 chunk（`defineAsyncComponent` / 动态 `import()`）。实测教训：首页 Hero 曾用
 *    `defineAsyncComponent` 懒加载 three.js，HTML 里一个字都没有，而用户真实下载了
 *    736 KB（184 KB gzip）—— 静态口径完全量不到；
 *  - 运行时 fetch 的 JSON（i18n 文案曾是一份 193 KB 的 `messages.json`）；
 *  - CSS、字体、图片。
 *
 * 所以现在两道一起跑：
 *
 *  1. **首屏关键路径**（静态，解析 HTML）—— 严格预算，防止初包被无感塞大；
 *  2. **单页完整资源图**（真实浏览器加载后取 `performance` 资源列表）—— 量用户真正付的钱，
 *     并额外卡**请求数**（首屏请求数失控同样拖慢可交互时间）。
 *
 * ## 用法
 *
 *   npm run build
 *   node scripts/check-bundle-budget.mjs                     # 前台首页 + 后台仪表盘
 *   node scripts/check-bundle-budget.mjs --json              # 机器可读输出（CI 归档用）
 *   node scripts/check-bundle-budget.mjs --no-server --base-url http://localhost:3000
 *   node scripts/check-bundle-budget.mjs --budget-page-kb 320 --budget-requests 120
 *
 * 退出码：0 通过；1 超预算；2 前置条件缺失（未 build / 服务起不来 / 浏览器不可用）
 */

import {spawn} from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import zlib from 'node:zlib'

const ROOT = path.resolve(import.meta.dirname, '..')
const OUTPUT_DIR = path.join(ROOT, '.output')
const PUBLIC_DIR = path.join(OUTPUT_DIR, 'public')
const NUXT_DIR = path.join(PUBLIC_DIR, '_nuxt')
const SERVER_ENTRY = path.join(OUTPUT_DIR, 'server', 'index.mjs')

/** 首屏关键路径 JS 预算（gzip KB）—— 解析 SSR HTML 得到，超过即失败。基线见文件末尾。 */
const DEFAULT_INITIAL_KB = 180
/** 全量 JS 预算（gzip KB）—— 防止 chunk 数量与体积无感膨胀。 */
const DEFAULT_TOTAL_KB = 1520
/**
 * **单页完整 gzip 传输**预算（KB，含 JS/CSS/JSON/字体/图片）。
 * 这是用户真正付的钱，基线见文件末尾的实测记录。
 *
 * ⚠️ **这个口径必须带后台凭据测**（`.env.e2e` 或 E2E_ADMIN_USER/E2E_ADMIN_PASS）。
 * 匿名跑时后台那一路会被 middleware 重定向到 `/login`，采到的是登录页的资源图 ——
 * 脚本会打 WARN，但数值看着"很小、很正常"，极易被当成真值用。
 *
 * 现值 620 是**已登录态实测**（前台首页 267 / 后台仪表盘 528，见文件末尾），留约 17% 余量。
 *
 * 曾经踩过的坑（2026-10-15 更正）：上一版把这里收紧到 360，依据的是**匿名态**测出的
 * 后台 262KB，并顺手把差额归因成"整包 ECharts"。两处都错了：
 *   - 262KB 是未登录的假值；带上凭据再测就是 528KB，于是阈值必然失败；
 *   - 那 266KB 的大 chunk 是 **Element Plus 全量**（`layouts/admin.vue` 里
 *     `import('element-plus')` 整包动态引入），与 ECharts 无关 ——
 *     `components/admin/DonutChart.vue` 早已改成只 `import('echarts/core')` + PieChart 按需。
 *
 * 真正尚未解决的性能问题就是那 266KB 的 Element Plus 整包：进后台任何一页都要下载它。
 * 要压下来得给 Element Plus 配按需引入（unplugin-vue-components 的 resolver），
 * 那是一次横跨所有后台页面的改动，不在本次范围。
 */
const DEFAULT_PAGE_KB = 620
/** **单页请求数**上限 —— 首屏请求数失控同样拖慢可交互时间。 */
const DEFAULT_REQUESTS = 90

/** 被测路由：前台是 SSR、后台是 CSR（routeRules），两者的资源图都要量。 */
const ROUTES = [
    {name: '前台首页', path: '/'},
    {name: '后台仪表盘', path: '/dashboard'},
]

function parseArgs(argv) {
    const args = {
        json: false, noServer: false, baseUrl: '', port: 3081, top: 8,
        budgetInitialKb: DEFAULT_INITIAL_KB, budgetTotalKb: DEFAULT_TOTAL_KB,
        budgetPageKb: DEFAULT_PAGE_KB, budgetRequests: DEFAULT_REQUESTS,
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
        else if (key === '--budget-page-kb') args.budgetPageKb = Number(next())
        else if (key === '--budget-requests') args.budgetRequests = Number(next())
        else if (key === '--top') args.top = Number(next())
        else if (key === '--help' || key === '-h') {
            console.log(fs.readFileSync(import.meta.filename, 'utf-8').split('\n').slice(1, 25).join('\n'))
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

/** 按扩展名/路径给资源分类（输出里分行显示，便于一眼看出钱花在哪） */
export function classifyResource(urlPath) {
    if (urlPath.endsWith('.js')) return 'js'
    if (urlPath.endsWith('.css')) return 'css'
    if (urlPath.endsWith('.json')) return 'json'
    if (/\.(woff2?|ttf|otf)$/.test(urlPath)) return 'font'
    if (/\.(png|jpe?g|webp|avif|gif|svg|ico)$/.test(urlPath)) return 'image'
    return 'other'
}

function fileStats(urlPath) {
    const file = path.join(PUBLIC_DIR, urlPath.replace(/^\//, '').split('?')[0])
    if (!fs.existsSync(file)) return null
    const buf = fs.readFileSync(file)
    return {url: urlPath, file: path.relative(ROOT, file), raw: buf.length, gzip: gzipSize(buf)}
}

/**
 * 取一条资源的体积。
 *
 * 优先从构建产物落盘的文件读（那就是浏览器会拿到的那个文件）；落盘找不到的
 * （走 Nitro 动态路由的，如 `/_i18n/<hash>/<locale>/messages.json`）就实际取一次
 * 再就地压缩 —— 否则这类资源会被算成 0，正是最该被盯住的一类。
 */
async function resourceStats(baseUrl, urlPath) {
    const local = fileStats(urlPath)
    if (local) return local
    try {
        const resp = await fetch(`${baseUrl}${urlPath}`)
        if (!resp.ok) return null
        const buf = Buffer.from(await resp.arrayBuffer())
        return {url: urlPath, file: '（动态路由）', raw: buf.length, gzip: gzipSize(buf)}
    } catch {
        return null
    }
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

/**
 * 后台路由是 CSR 且需要登录：不注入凭据的话采到的是未登录态，
 * 会漏掉「只有进后台才会加载」的资源（Element Plus、后台文案 187 KB 等）——
 * 而口径 2 的意义恰恰是量这些。凭据来源与 e2e 保持一致：环境变量优先，其次 `.env.e2e`。
 */
function loadAdminCredentials() {
    if (process.env.E2E_ADMIN_USER && process.env.E2E_ADMIN_PASS) {
        return {username: process.env.E2E_ADMIN_USER, password: process.env.E2E_ADMIN_PASS}
    }
    try {
        const raw = fs.readFileSync(path.join(ROOT, '.env.e2e'), 'utf-8')
        const env = {}
        for (const line of raw.split(/\r?\n/)) {
            const matched = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$/)
            if (matched) env[matched[1]] = matched[2]
        }
        if (env.E2E_ADMIN_USER && env.E2E_ADMIN_PASS) {
            return {username: env.E2E_ADMIN_USER, password: env.E2E_ADMIN_PASS}
        }
    } catch {
        // 没有 .env.e2e 就当作匿名测量（后台那一路会偏小，属已知限制）
    }
    return null
}

/** 与 `e2e/fixtures/auth.ts` 的 TOKEN_KEY 保持一致 */
const TOKEN_STORAGE_KEY = 'fastblog.token'

async function fetchAdminToken() {
    const credentials = loadAdminCredentials()
    if (!credentials) return null
    // ⚠️ 不能打脚本自己起的那个 server —— 它是**构建产物**（.output/server/index.mjs），
    // 没有 `nitro.devProxy`，`/api` 只有 dev 模式才被代理过去。这里直连后端，
    // 地址与 e2e 的 E2E_API_BASE_URL / .env.production 的 NUXT_PUBLIC_API_BASE_URL 对齐。
    const apiBase = (
        process.env.E2E_API_BASE_URL
        || process.env.NUXT_PUBLIC_API_BASE_URL
        || 'http://127.0.0.1:9421'
    ).replace(/\/$/, '')
    try {
        const resp = await fetch(`${apiBase}/api/v3/system/auth/login`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(credentials),
        })
        const body = await resp.json()
        return body?.data?.access_token ?? null
    } catch {
        return null
    }
}

/**
 * 用真实浏览器加载页面，收集**实际发生的**资源请求。
 * 这一步是静态口径的必要补充：懒加载 chunk、运行时 fetch 的 JSON 都不在 SSR HTML 里，
 * 只有真跑一遍才看得见。多等 1.5s 是为了让「挂载后才触发」的懒加载落地。
 *
 * ⚠️ 已知限制：后台布局的 `admin` 文案（`/i18n/admin/<locale>.json`，约 55 KB gzip）
 * 在实测里没被这条口径记到 —— 而它是确实加载了的（构建产物里有该文件、
 * 后台页面文案正常渲染）。所以后台那一路的 json 数字偏小，别据此判断文案体积。
 * 前台那一路的 json 记录是准的（能看到 `/_i18n/<hash>/zh-CN/messages.json`）。
 */
async function collectPageResources(browser, baseUrl, routePath, token) {
    const page = await browser.newPage()
    try {
        if (token) {
            await page.addInitScript(
                ([key, value]) => localStorage.setItem(key, value),
                [TOKEN_STORAGE_KEY, token],
            )
        }
        const pageErrors = []
        page.on('pageerror', (error) => pageErrors.push(String(error)))
        await page.goto(`${baseUrl}${routePath}`, {waitUntil: 'load', timeout: 30_000})
        await page.waitForTimeout(1500)
        const urls = await page.evaluate(() =>
            performance.getEntriesByType('resource').map((entry) => entry.name),
        )
        return {urls, pageErrors}
    } finally {
        await page.close()
    }
}

async function main() {
    const args = parseArgs(process.argv.slice(2))

    if (!fs.existsSync(SERVER_ENTRY) || !fs.existsSync(NUXT_DIR)) {
        console.error('[ERROR] 找不到 .output/server/index.mjs 或 .output/public/_nuxt')
        console.error('        请先构建：npm run build')
        return 2
    }

    let chromium
    try {
        ({chromium} = await import('@playwright/test'))
    } catch {
        console.error('[ERROR] 无法加载 @playwright/test —— 单页完整资源图口径需要它。')
        console.error('        安装：npm i -D @playwright/test && npx playwright install chromium')
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

    const report = {
        routes: [], total: null,
        budget: {
            initialKb: args.budgetInitialKb, totalKb: args.budgetTotalKb,
            pageKb: args.budgetPageKb, requests: args.budgetRequests,
        },
    }
    const failures = []
    let browser = null

    try {
        await waitForServer(baseUrl)
        browser = await chromium.launch()
        const adminToken = await fetchAdminToken()
        if (!adminToken) {
            console.warn('[WARN] 未取得后台登录凭据（E2E_ADMIN_USER/E2E_ADMIN_PASS 或 .env.e2e）——' +
                '后台那一路采到的是未登录态，会偏小。')
        }

        for (const route of ROUTES) {
            // ---- 口径 1：首屏关键路径（静态解析 SSR HTML）----------------------
            let html = ''
            try {
                const resp = await fetch(`${baseUrl}${route.path}`, {redirect: 'follow'})
                html = await resp.text()
            } catch (error) {
                failures.push(`${route.name} ${route.path} 请求失败：${error instanceof Error ? error.message : error}`)
                continue
            }

            const initialFiles = extractInitialScripts(html).map(fileStats).filter(Boolean)
            const initialGzipKb = Math.round(initialFiles.reduce((sum, item) => sum + item.gzip, 0) / 1024)
            const initialRawKb = Math.round(initialFiles.reduce((sum, item) => sum + item.raw, 0) / 1024)

            // ---- 口径 2：单页完整资源图（真实浏览器）--------------------------
            let pageItems = []
            let pageRequests = 0
            let foreign = []
            let pageErrors = []
            try {
                const collected = await collectPageResources(browser, baseUrl, route.path, adminToken)
                pageErrors = collected.pageErrors
                const seen = new Set()
                for (const url of collected.urls) {
                    if (url.startsWith('data:')) continue
                    if (!url.startsWith(baseUrl)) {
                        foreign.push(url)
                        continue
                    }
                    const urlPath = url.slice(baseUrl.length).split('?')[0].split('#')[0]
                    if (seen.has(urlPath)) continue
                    seen.add(urlPath)
                    pageRequests += 1
                    const stats = await resourceStats(baseUrl, urlPath)
                    if (stats) pageItems.push({...stats, kind: classifyResource(urlPath)})
                }
            } catch (error) {
                failures.push(`${route.name} 浏览器加载失败：${error instanceof Error ? error.message : error}`)
            }

            const pageGzipKb = Math.round(pageItems.reduce((sum, item) => sum + item.gzip, 0) / 1024)
            const byKind = {}
            for (const item of pageItems) {
                byKind[item.kind] = (byKind[item.kind] ?? 0) + item.gzip
            }

            report.routes.push({
                route,
                initial: {
                    scripts: initialFiles.length,
                    gzipKb: initialGzipKb,
                    rawKb: initialRawKb,
                    files: initialFiles
                },
                page: {
                    requests: pageRequests, gzipKb: pageGzipKb,
                    byKind: Object.fromEntries(Object.entries(byKind).map(([k, v]) => [k, Math.round(v / 1024)])),
                    files: [...pageItems].sort((a, b) => b.gzip - a.gzip),
                    foreign, pageErrors,
                },
            })

            // ---- 判定 --------------------------------------------------------
            if (initialFiles.length === 0) {
                failures.push(`${route.name} ${route.path} 未解析到首屏脚本（HTML 结构变了？）`)
            } else if (initialGzipKb > args.budgetInitialKb) {
                failures.push(`${route.name} 首屏关键路径 JS ${initialGzipKb}KB > 预算 ${args.budgetInitialKb}KB`)
            }
            if (pageRequests === 0) {
                failures.push(`${route.name} 未采集到任何资源（浏览器口径失效？）`)
            } else {
                if (pageGzipKb > args.budgetPageKb) {
                    failures.push(`${route.name} 单页 gzip 总量 ${pageGzipKb}KB > 预算 ${args.budgetPageKb}KB`)
                }
                if (pageRequests > args.budgetRequests) {
                    failures.push(`${route.name} 单页请求数 ${pageRequests} > 预算 ${args.budgetRequests}`)
                }
            }
            for (const message of pageErrors) {
                failures.push(`${route.name} 页面运行时报错：${message}`)
            }
        }

        const total = totalJsStats()
        report.total = {...total, gzipKb: Math.round(total.gzip / 1024), rawKb: Math.round(total.raw / 1024)}
        if (report.total.gzipKb > args.budgetTotalKb) {
            failures.push(`全量 JS ${report.total.gzipKb}KB > 预算 ${args.budgetTotalKb}KB`)
        }
    } finally {
        if (browser) await browser.close().catch(() => {
        })
        cleanup()
    }

    if (args.json) {
        console.log(JSON.stringify({...report, failures}, null, 2))
    } else {
        console.log('== 口径 1：首屏关键路径 JS（gzip，解析 SSR HTML） ==')
        for (const item of report.routes) {
            console.log(
                `  ${item.route.name.padEnd(8)} ${String(item.initial.gzipKb).padStart(5)}KB / 预算 ${args.budgetInitialKb}KB` +
                `  （${item.initial.scripts} 个脚本，raw ${item.initial.rawKb}KB）`,
            )
            const top = [...item.initial.files].sort((a, b) => b.gzip - a.gzip).slice(0, args.top)
            for (const file of top) {
                console.log(`      ${String(Math.round(file.gzip / 1024)).padStart(5)}KB  ${file.file}`)
            }
        }
        console.log(`  ${'全量 JS'.padEnd(8)} ${String(report.total.gzipKb).padStart(5)}KB / 预算 ${args.budgetTotalKb}KB` +
            `  （${report.total.files} 个 chunk，raw ${report.total.rawKb}KB）`)

        console.log('\n== 口径 2：单页完整资源图（gzip，真实浏览器加载后实测） ==')
        for (const item of report.routes) {
            const kinds = Object.entries(item.page.byKind)
                .sort((a, b) => b[1] - a[1])
                .map(([kind, kb]) => `${kind} ${kb}KB`)
                .join(' / ')
            console.log(
                `  ${item.route.name.padEnd(8)} ${String(item.page.gzipKb).padStart(5)}KB / 预算 ${args.budgetPageKb}KB` +
                `  （${item.page.requests} 个请求 / 预算 ${args.budgetRequests}；${kinds}）`,
            )
            const top = item.page.files.slice(0, args.top)
            for (const file of top) {
                console.log(`      ${String(Math.round(file.gzip / 1024)).padStart(5)}KB  [${file.kind.padEnd(5)}] ${file.url}`)
            }
        }

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
// 2026-09-22 首次运行（win32 / node 25.2.1）：
//   首屏关键路径 前台首页 189KB / 后台仪表盘 158KB / 全量 JS 1110KB（177 个 chunk）
//
// 2026-10-14（B1–B3 之后）：
//   首屏关键路径 前台首页 198KB / 后台仪表盘 161KB / 全量 JS 1482KB（208 个 chunk）
//   单页完整资源图 前台首页约 215KB / 62 个请求（three.js 184KB 已移除；
//                 i18n messages.json 由 66KB 降到约 0.3KB）
//
// 2026-10-15（P0 收口后，预算随之收紧）：
//   首屏关键路径 前台首页 166KB / 25 个脚本；后台仪表盘 139KB / 6 个脚本
//   全量 JS 1452KB（203 个 chunk）
//   单页完整资源图 前台首页 254KB / 63 个请求；后台仪表盘 262KB / 56 个请求
//   阈值：首屏 200→180、全量 1600→1520、单页 600→360、请求数 100→80
//
//   首屏掉下来的 33KB / 13 个脚本来自两处，都不是"少写代码"换来的：
//     a) 封面接回 `ResponsiveImage`（此前全站 0 引用，走的是 `DeferredImage` 直接拉原图；
//        现在有 200/480/800/1600 四档 + avif→webp 协商，且首屏图带 fetchpriority=high）；
//     b) `store/modules/user.ts` 不再静态 import `@/api/modules/auth` ——
//        该 store 被全局指令插件与 SiteHeader 引用，那一行曾让 **axios（约 20KB gzip）
//        出现在每个页面（含匿名访客）的首屏**，改为 action 内动态 import 后消失。
//
//   注意：单页完整资源图只降了 2KB，因为真实浏览器里 axios 仍会被 NuxtLink 的
//   路由预取带下来（不占首屏关键路径）。要继续压需要关掉非关键链接的 prefetch。
//
// ⚠️ 同日更正：上面那两个「单页完整资源图」数字（前台 254 / 后台 262）是**匿名态**测的，
//   作废。当次跑 check:bundle 时没有后台凭据（脚本打了 WARN），后台那一路被 middleware
//   重定向到 `/login`，采到的是**登录页**的资源图 —— 后台"262KB"因此是个偏小的假值，
//   而我据此把单页预算从 600 收到 360，只要带上凭据就必然失败。
//
//   带凭据（`.env.e2e`）重测的真实值：
//     首屏关键路径 前台首页 166KB / 后台仪表盘 139KB（此口径解析 SSR HTML，与登录态无关）
//     全量 JS 1453KB / 203 个 chunk（同上，与登录态无关）
//     单页完整资源图 前台首页 267KB / 70 个请求；后台仪表盘 **528KB** / 59 个请求
//   阈值随之更正：单页 360→620、请求数 80→90（首屏 180 与全量 1520 不动）。
//
//   后台多出来的那 266KB 是**一个** chunk：Element Plus 全量（`layouts/admin.vue` 里的
//   `import('element-plus')`）。匿名态下它永远加载不到（进不了后台主页），所以这条
//   口径不测已登录态，就等于没测。
//
//   教训：**口径 2 的数字必须连同登录态一起记**。只写 KB、不写「带凭据 / 匿名」，
//   下一次就会拿假值去改阈值 —— 这次就是这么踩进去的。
//
// 两道口径都要盯：只看首屏关键路径时，three.js（异步 chunk，184KB gzip）与
// i18n 文案（运行时 fetch 的 JSON，66KB gzip）都是隐形的 —— 这正是口径 2 存在的原因。
// ---------------------------------------------------------------------------
