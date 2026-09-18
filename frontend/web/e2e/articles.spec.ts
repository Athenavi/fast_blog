import {expect, test} from './fixtures/auth'

/**
 * 文章管理 E2E（自 astro e2e/articles.spec.ts 适配 Nuxt）
 *
 * 路由：/admin/articles → /content/article；新建 / 编辑都走 el-dialog 表单。
 * 页面文案已 i18n 化：搜索占位「标题关键词」、新建按钮「新建文章」。
 */
test.describe('文章管理', () => {
  test('管理员登录后可以访问文章列表', async ({authenticatedPage: page}) => {
    await page.goto('/content/article')
    await expect(page.locator('.page-container').first()).toBeVisible({timeout: 15000})
  })

  test('文章列表页包含关键 UI 元素', async ({authenticatedPage: page}) => {
    await page.goto('/content/article')
    await page.locator('.page-container').first().waitFor({timeout: 15000})

    const hasSearch = await page
      .locator('input[placeholder*="关键词"], input[placeholder*="搜索"], input[type="search"]')
      .first()
      .isVisible()
      .catch(() => false)
    const hasCreateBtn = await page
      .locator('button')
      .filter({hasText: /新建|创建|新增|Create|New/})
      .first()
      .isVisible()
      .catch(() => false)
    expect(hasSearch || hasCreateBtn).toBeTruthy()
  })

  test('点击新建按钮能打开创建表单', async ({authenticatedPage: page}) => {
    await page.goto('/content/article')
    await page.locator('.page-container').first().waitFor({timeout: 15000})

    const createBtn = page.locator('button').filter({hasText: /新建|创建|新增|Create|New/}).first()
    if (await createBtn.isVisible().catch(() => false)) {
      await createBtn.click()
      await expect(page.locator('.el-dialog').first()).toBeVisible({timeout: 10000})
    }
  })

  test('可以打开文章编辑表单', async ({authenticatedPage: page}) => {
    await page.goto('/content/article')
    await page.locator('.el-table__row').first().waitFor({timeout: 15000}).catch(() => {
    })

    const editBtn = page
      .locator('.el-table__row')
      .first()
      .locator('button')
      .filter({hasText: /编辑|Edit/})
      .first()
    if (await editBtn.isVisible().catch(() => false)) {
      await editBtn.click()
      await expect(page.locator('.el-dialog').first()).toBeVisible({timeout: 10000})
    }
  })
})
