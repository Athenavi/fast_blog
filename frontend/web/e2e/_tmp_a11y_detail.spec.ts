import AxeBuilder from '@axe-core/playwright'

import {expect, test, waitForHydration} from './fixtures/auth'

/**
 * 临时诊断：把每个页面**所有** axe 违规的节点 target 打出来。
 * 用完即删（不做断言，只输出）。
 */
test('a11y 违规详情', async ({authenticatedPage: page}) => {
  const paths = [
    '/content/article',
    '/content/article/new',
    '/content/media',
    '/dashboard',
    '/system/menu',
    '/ops/backup',
    '/extension/plugin',
    '/system/role',
    '/system/user',
    '/categories',
    '/search',
  ]

  for (const path of paths) {
    await page.goto(path)
    await waitForHydration(page)
    await page.waitForTimeout(2500)

    const results = await new AxeBuilder({page})
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
      .exclude('nuxt-devtools-frame')
      .exclude('nuxt-devtools-label-secondary')
      .analyze()

    for (const violation of results.violations) {
      console.log(`\n#### ${path} — ${violation.id} × ${violation.nodes.length}`)
      for (const node of violation.nodes.slice(0, 8)) {
        const detail = (node.any?.[0]?.message ?? node.failureSummary ?? '')
          .replace(/\s+/g, ' ')
          .slice(0, 130)
        console.log(`  [${node.target.join(' ')}] ${detail}`)
      }
    }
  }

  expect(true).toBe(true)
})
