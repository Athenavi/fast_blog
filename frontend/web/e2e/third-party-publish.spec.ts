import {expect, test, waitForHydration} from './fixtures/auth'

/**
 * 多平台发布底座（批次 18）
 *
 * 断言：
 *  - `/content/third-party-publish` 渲染出两个 tab（渠道配置 / 发布任务）；
 *  - 当前**没有已接入的平台适配器**时，页面如实提示（而不是伪造可用平台）；
 *  - 整轮无 console error / pageerror（能抓住"调用了不存在的端点"这类静默失败）。
 */
test.describe('多平台发布', () => {
  test.describe.configure({timeout: 180_000})

  test('页面可渲染并如实提示适配器未接入', async ({authenticatedPage: page}) => {
    const problems: string[] = []
    page.on('pageerror', (error) => problems.push(`pageerror: ${String(error)}`))
    page.on('console', (message) => {
      if (message.type() === 'error') problems.push(`console: ${message.text()}`)
    })

    await page.goto('/content/third-party-publish')
    await waitForHydration(page)

    const body = page.locator('body')
    await expect(body).toContainText('多平台发布', {timeout: 20_000})
    await expect(body).toContainText('渠道配置')
    await expect(body).toContainText('发布任务')
    // 平台适配器分期接入：当前应为空，页面顶部如实说明
    await expect(body).toContainText('没有已接入的平台适配器')

    expect(problems).toEqual([])
  })
})
