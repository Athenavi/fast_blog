import {expect, test} from './fixtures/auth'

/**
 * 临时冒烟：本轮新增的 3 个页面（验证后即删，不入库）
 *
 * 断言口径：
 *   1. 页面骨架可见（`.page-container` 是本仓库 admin 布局的就绪标志）；
 *   2. 无 console error；
 *   3. 无 >=400 的请求 —— 但排除 `/market/`：插件市场未配置
 *      `PLUGIN_MARKETPLACE_URL` 时，后端**刻意**以 4xx 明确拒绝（这是设计好的降级），
 *      页面应显示「市场不可用」提示而不是崩溃。
 */
const IGNORED_PATTERNS = [/\/market\//]

const PAGES = [
  {name: 'API 令牌', path: '/system/api-token'},
  {name: '插件市场', path: '/extension/market'},
  {name: '字段值', path: '/content/custom-field-values'},
]

for (const target of PAGES) {
  test(`[冒烟] ${target.name}（${target.path}）`, async ({authenticatedPage: page}) => {
    const consoleErrors: string[] = []
    const badResponses: string[] = []

    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text())
    })
    page.on('response', (resp) => {
      const url = resp.url()
      if (resp.status() >= 400 && !IGNORED_PATTERNS.some((re) => re.test(url))) {
        badResponses.push(`${resp.status()} ${url}`)
      }
    })

    await page.goto(target.path)
    await expect(page.locator('.page-container').first()).toBeVisible({timeout: 20000})

    // 页面自己的异步请求（列表/配置读取）收尾
    await page.waitForTimeout(2000)

    expect(consoleErrors, `console errors:\n${consoleErrors.join('\n')}`).toEqual([])
    expect(badResponses, `bad responses:\n${badResponses.join('\n')}`).toEqual([])
  })
}
