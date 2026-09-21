import {expect, test, waitForHydration} from './fixtures/auth'

/**
 * 用户成长与打赏（批次 15）
 *
 * 覆盖本批次新增/改动的页面：
 *  - 前台：`/experts`（公开列表）、`/certification`（我的认证）、`/tipping`（打赏与收益）、
 *    以及 `/points`、`/badges`（管理 tab 已移到后台，见下方断言）；
 *  - 后台：`/gamification/{points,badges,certifications}`、`/commerce/tipping`。
 *
 * 断言「页面能渲染出预期文案」+「整轮没有 console error / pageerror」——
 * 后者能抓住"接口 500 但页面不崩"这类静默失败（例如前端调用了不存在的端点）。
 */
const CASES: Array<{ path: string; text: RegExp }> = [
  {path: '/experts', text: /认证专家/},
  {path: '/certification', text: /我的专家认证/},
  {path: '/tipping', text: /打赏与收益/},
  {path: '/vip', text: /VIP/},
  {path: '/feed', text: /关注动态/},
  {path: '/chat', text: /群聊/},
  {path: '/home/admin', text: /admin/},
  {path: '/points', text: /积分/},
  {path: '/badges', text: /勋章/},
  {path: '/gamification/points', text: /积分统计/},
  {path: '/gamification/badges', text: /勋章统计/},
  {path: '/gamification/certifications', text: /认证统计/},
  {path: '/commerce/tipping', text: /打赏统计/},
]

test.describe('用户成长与打赏', () => {
  // 该用例要逐个访问 12 个页面（dev 模式下每页首次编译都要等），30s 默认超时不够
  test.describe.configure({timeout: 180_000})

  test('新增页面可渲染且无控制台错误', async ({authenticatedPage: page}) => {
    const problems: string[] = []
    page.on('pageerror', (error) => problems.push(`pageerror: ${String(error)}`))
    page.on('console', (message) => {
      if (message.type() === 'error') problems.push(`console: ${message.text()}`)
    })

    for (const item of CASES) {
      await page.goto(item.path)
      await waitForHydration(page)
      await expect(page.locator('body'), item.path).toContainText(item.text, {timeout: 20_000})
    }

    expect(problems).toEqual([])
  })

  test('积分中心不再内嵌「管理」tab（管理操作已移到后台）', async ({authenticatedPage: page}) => {
    await page.goto('/points')
    await waitForHydration(page)

    const text = await page.locator('body').innerText()
    expect(text).not.toContain('管理')
  })
})
