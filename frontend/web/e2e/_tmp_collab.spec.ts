import {expect, test} from './fixtures/auth'

/**
 * 临时 e2e：Yjs 实时协同是否**真的端到端可用**（验证后即删）。
 *
 * 为什么必须用两个独立浏览器上下文：协同的意义就是"两个客户端看到同一份文档"。
 * 同一页面里改两次证明不了任何东西。
 *
 * 流程：
 *   1. 用 API 建一篇测试文章（当前账号即作者 —— 后端只允许作者或持有效邀请者进房间）；
 *   2. 两个 context 各自登录、各自打开 /content/collab-editor、加入同一文章；
 *   3. A 输入 → 断言 B 的 textarea 出现同一文本（CRDT 实时合并）；
 *   4. B 再输入 → 断言 A 也看到（双向）；
 *   5. 软删测试文章，避免污染。
 */

const ARTICLE_API = '/api/v3/content/article'

async function tokenOf(page: import('@playwright/test').Page): Promise<string> {
  const token = await page.evaluate(() => localStorage.getItem('fastblog.token'))
  expect(token, 'e2e 账号应已登录').toBeTruthy()
  return token as string
}

/** 新建一个已登录的独立上下文（模拟另一位协作者） */
async function newCollaborator(browser: import('@playwright/test').Browser, token: string) {
  const context = await browser.newContext()
  const page = await context.newPage()
  await page.goto('/')
  await page.evaluate((value) => localStorage.setItem('fastblog.token', value), token)
  return {context, page}
}

test('[协同] 两个客户端实时同步同一篇正文', async ({authenticatedPage: pageA, browser, baseURL}) => {
  const token = await tokenOf(pageA)
  const authHeaders = {Authorization: `Bearer ${token}`}
  const marker = `collab-${Date.now()}`

  // 1) 建测试文章（作者 = 当前 e2e 账号）
  const created = await pageA.request.post(`${baseURL}${ARTICLE_API}`, {
    headers: authHeaders,
    data: {title: `协同测试 ${marker}`, content: '初始正文', status: 0},
  })
  expect(created.ok(), `创建测试文章失败：${created.status()} ${await created.text()}`).toBeTruthy()
  const body = await created.json()
  const articleId: number = body?.data?.id
  expect(articleId, '应返回文章 id').toBeTruthy()

  const {context: contextB, page: pageB} = await newCollaborator(browser, token)
  try {
    // 2) 两个客户端加入同一篇的协同
    for (const p of [pageA, pageB]) {
      p.on('websocket', (ws) => {
        const tag = ws.url().includes('/collaboration/yjs/ws/') ? 'YJS' : 'OTHER'
        console.log(`[WS ${tag}] open ${ws.url().slice(0, 80)}`)
        ws.on('close', () => console.log(`[WS ${tag}] closed`))
        ws.on('socketerror', (err) => console.log(`[WS ${tag}] socketerror ${err}`))
      })
      p.on('pageerror', (err) => console.log(`[pageerror] ${err.message}`))
      p.on('console', (msg) => {
        const text = msg.text()
        if (/\[collab\]/.test(text) || msg.type() === 'error' || msg.type() === 'warning') {
          console.log(`[console.${msg.type()}] ${text.slice(0, 200)}`)
        }
      })
    }
    for (const page of [pageA, pageB]) {
      const tag = page === pageA ? 'A' : 'B'
      await page.goto('/content/collab-editor')
      await page.locator('input[type="number"]').first().fill(String(articleId))
      await page.getByRole('button', {name: '加入协同'}).click()
      // 诊断：状态词只在 joined（provider 非空）时渲染，观察它的变化能区分
      // 「连接建立失败」/「连上又被服务端关闭」/「provider 被卸载」
      for (const wait of [500, 2500, 5000]) {
        await page.waitForTimeout(wait)
        const text = (await page.locator('body').innerText()).replace(/\s+/g, ' ')
        const states = text.match(/(连接中|已连接|已同步|已断开|被拒绝)[^ ]*/g)
        const areaCount = await page.locator('textarea').count()
        console.log(`[${tag} +${wait}ms] textarea=${areaCount} 状态=${states?.join(' | ') ?? '(无)'}`)
      }
      // 直接读 DOM 里的实际值，区分「Vue 状态有值但没写进 DOM」与「确实没值」
      const dom = await page.evaluate(() => {
        const el = document.querySelector('textarea') as HTMLTextAreaElement | null
        return {count: document.querySelectorAll('textarea').length, domLen: el?.value.length ?? -1}
      })
      console.log(`[${tag} DOM] ${JSON.stringify(dom)}`)
      await expect(page.locator('text=已同步')).toBeVisible({timeout: 20000})
      await expect(page.locator('textarea')).toBeVisible({timeout: 10000})
    }

    // 3) A 输入 → B 必须实时看到（这是协同的核心断言）
    const fromA = `A-${marker}`
    await pageA.locator('textarea').click()
    await pageA.locator('textarea').fill(fromA)
    await pageA.waitForTimeout(2500)
    const [valA, valB] = await Promise.all([
      pageA.locator('textarea').inputValue(),
      pageB.locator('textarea').inputValue(),
    ])
    console.log(`[fill 后] A=${valA.length} 字符 B=${valB.length} 字符`)
    console.log(`[fill 后 A 内容] ${JSON.stringify(valA).slice(0, 90)}`)
    console.log(`[fill 后 B 内容] ${JSON.stringify(valB).slice(0, 90)}`)
    await expect(pageB.locator('textarea')).toHaveValue(new RegExp(fromA), {timeout: 15000})

    // 4) B 追加 → A 也必须看到（双向，排除"单向广播"的假象）
    const merged = `B-${marker}`
    await pageB.locator('textarea').fill(merged)
    await expect(pageA.locator('textarea')).toHaveValue(new RegExp(merged), {timeout: 15000})

    // 5) 同一份文档：两边最终内容一致（CRDT 收敛）
    const [valueA, valueB] = [
      await pageA.locator('textarea').inputValue(),
      await pageB.locator('textarea').inputValue(),
    ]
    expect(valueA).toBe(valueB)
    expect(valueA).toContain(merged)
  } finally {
    await contextB.close()
    // 清理：软删测试文章。**容错**：清理失败不应掩盖真正的断言结果，
    // 也避免清理（或网络抖动）把整测拖到超时而报错在清理行上。
    await pageA.request
      .delete(`${baseURL}${ARTICLE_API}/${articleId}`, {headers: authHeaders, timeout: 15000})
      .catch(() => undefined)
  }
})

test('[协同] 未加入时给出可达性提示', async ({authenticatedPage: page}) => {
  await page.goto('/content/collab-editor')
  await expect(page.locator('text=协同编辑').first()).toBeVisible({timeout: 20000})
  await expect(page.locator('textarea')).toHaveCount(0)
})
