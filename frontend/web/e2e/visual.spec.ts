import type {Page} from '@playwright/test'

import {expect, test, waitForHydration} from './fixtures/auth'
import {PAGE_TARGETS, readySelector} from './fixtures/page-targets'

/**
 * 视觉回归（截图对比）—— UI/UX 路线图 Batch 0.1
 *
 * 为什么先立它：Batch 1/2 会改动 89 个页面里的绝大部分，没有像素级护栏就只能靠肉眼
 * 抽查。基线由 Playwright 存在 `e2e/visual.spec.ts-snapshots/`（**要入库**）。
 *
 * 首次生成 / 有意改动 UI 后：
 *   npx playwright test e2e/visual.spec.ts --update-snapshots
 * 日常与 CI：
 *   npx playwright test e2e/visual.spec.ts
 *
 * 后台页跑在**已登录（superadmin）**视角，前台页跑在**匿名访客**视角 —— 两者看到的
 * 导航与入口不同，混在一起会得到"谁都不像"的基线。
 *
 * 容忍度 `maxDiffPixelRatio: 0.02`：字体渲染有跨平台差异。若 CI 与本地不一致，
 * 正确做法是在 CI 同一镜像里生成基线，而不是把阈值调到永远绿。
 */

/** 会自然抖动的区域（登录名、主题切换、通知徽标）不参与像素比较 */
const MASK_SELECTORS = ['.layout__header']

async function shoot(page: Page, target: (typeof PAGE_TARGETS)[number]) {
  await page.goto(target.path)
  await waitForHydration(page)
  // 页面自身挂了（404/500）时选择器会超时 —— 不掩盖：截图会拍下错误态，
  // 与基线不一致自然让用例红，这正是想要的效果。
  await page.waitForSelector(readySelector(target), {timeout: 20_000}).catch(() => {
  })
  await page.waitForLoadState('networkidle', {timeout: 5_000}).catch(() => {
  })
  await page.evaluate(() => window.scrollTo(0, 0))

  await expect(page).toHaveScreenshot(`${target.slug}.png`, {
    animations: 'disabled',
    caret: 'hide',
    mask: MASK_SELECTORS.map((selector) => page.locator(selector)),
    maxDiffPixelRatio: 0.02,
  })
}

test.describe('视觉回归·后台（已登录）', () => {
  for (const target of PAGE_TARGETS.filter((item) => item.admin)) {
    test(`${target.name} ${target.path}`, async ({authenticatedPage: page}) => {
      await shoot(page, target)
    })
  }
})

test.describe('视觉回归·前台（匿名访客）', () => {
  for (const target of PAGE_TARGETS.filter((item) => !item.admin)) {
    test(`${target.name} ${target.path}`, async ({page}) => {
      await shoot(page, target)
    })
  }
})
