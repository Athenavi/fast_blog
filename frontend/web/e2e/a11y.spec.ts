import fs from 'node:fs'
import path from 'node:path'

import AxeBuilder from '@axe-core/playwright'
import type {Page} from '@playwright/test'

import {expect, test, waitForHydration} from './fixtures/auth'
import {PAGE_TARGETS, type PageTarget, readySelector} from './fixtures/page-targets'

/**
 * a11y 巡检（axe-core，WCAG 2.1/2.2 A+AA）—— UI/UX 路线图 Batch 0.2
 *
 * 为什么是"基线对比"而不是"零违规"：现有页面本就有大量历史违规，直接断言 0 会让整套
 * 测试一开始就红、随后被无视。这里把**现状冻结成基线**，只让"新增/加重的违规"失败 ——
 * 重构（Batch 1/2）才有可能在护栏内推进。
 *
 * 首次使用（仓库里还没有 `e2e/a11y-baseline.json`）：
 *   A11Y_UPDATE_BASELINE=1 npx playwright test e2e/a11y.spec.ts
 *   # 然后把生成的 e2e/a11y-baseline.json 一并提交
 *
 * 日常 / CI：
 *   npx playwright test e2e/a11y.spec.ts      # 只报"比基线更差"的规则
 * 修完一批违规后收紧基线：同样的 UPDATE 命令重跑即可（数字只会变小才算收紧）。
 *
 * 后台页跑在**已登录（superadmin）**视角、前台页跑在**匿名访客**视角。
 */

const BASELINE_PATH = path.join(import.meta.dirname, 'a11y-baseline.json')

type RuleCounts = Record<string, number>
type Baseline = Record<string, RuleCounts>

const UPDATE_BASELINE = process.env.A11Y_UPDATE_BASELINE === '1'

function loadBaseline(): Baseline {
  try {
    return JSON.parse(fs.readFileSync(BASELINE_PATH, 'utf-8')) as Baseline
  } catch {
    return {}
  }
}

/** 违规规则 → 受影响节点数（节点数增加同样算回归） */
function summarize(violations: ReadonlyArray<{ id: string; nodes: unknown[] }>): RuleCounts {
  const counts: RuleCounts = {}
  for (const violation of violations) {
    counts[violation.id] = (counts[violation.id] ?? 0) + violation.nodes.length
  }
  return counts
}

/** 键排序，让基线文件的 diff 可读 */
function sorted(record: Baseline): Baseline {
  const out: Baseline = {}
  for (const slug of Object.keys(record).sort()) {
    out[slug] = Object.fromEntries(
      Object.entries(record[slug] ?? {}).sort(([a], [b]) => a.localeCompare(b)),
    )
  }
  return out
}

const baseline = loadBaseline()
const collected: Baseline = {}

async function audit(page: Page, target: PageTarget): Promise<void> {
  await page.goto(target.path)
  await waitForHydration(page)
  // 就绪选择器等不到不失败：页面本身挂了是别的用例的事，这里只取"当前 DOM 的无障碍状态"。
  await page.waitForSelector(readySelector(target), {timeout: 20_000}).catch(() => {
  })
  await page.waitForTimeout(400)

  const results = await new AxeBuilder({page})
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze()

  const current = summarize(results.violations)
  collected[target.slug] = current

  if (UPDATE_BASELINE) return

  const allowed = baseline[target.slug] ?? {}
  const regressions = Object.entries(current)
    .filter(([rule, count]) => count > (allowed[rule] ?? 0))
    .map(([rule, count]) => `${rule}: ${allowed[rule] ?? 0} → ${count}`)

  expect(
    regressions,
    `${target.name}（${target.path}）出现新的 a11y 违规。\n` +
    '请修复；若确属"已知且暂不修"，用 A11Y_UPDATE_BASELINE=1 重跑并提交基线（不要在 PR 里静默放行）。',
  ).toEqual([])
}

test.describe('a11y 巡检·后台（已登录）', () => {
  for (const target of PAGE_TARGETS.filter((item) => item.admin)) {
    test(`${target.name} ${target.path}`, async ({authenticatedPage: page}) => {
      await audit(page, target)
    })
  }
})

test.describe('a11y 巡检·前台（匿名访客）', () => {
  for (const target of PAGE_TARGETS.filter((item) => !item.admin)) {
    test(`${target.name} ${target.path}`, async ({page}) => {
      await audit(page, target)
    })
  }
})

test.afterAll(() => {
  if (!UPDATE_BASELINE) return
  fs.writeFileSync(BASELINE_PATH, `${JSON.stringify(sorted({...baseline, ...collected}), null, 2)}\n`, 'utf-8')
  console.log(`[a11y] 基线已写入 ${path.relative(process.cwd(), BASELINE_PATH)}`)
})
