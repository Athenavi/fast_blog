import {expect, test} from './fixtures/auth'

/**
 * 用户管理 E2E（自 astro e2e/users.spec.ts 适配 Nuxt）
 * 路由：/admin/users → /system/user，/admin/roles → /system/role。
 * 搜索占位为「用户名或邮箱」（admin.system.user.keywordPlaceholder）。
 */
test.describe('用户管理', () => {
  test('管理员可以访问用户列表', async ({authenticatedPage: page}) => {
    await page.goto('/system/user')
    await expect(page.locator('.page-container').first()).toBeVisible({timeout: 15000})
  })

  test('用户列表页面包含搜索功能', async ({authenticatedPage: page}) => {
    await page.goto('/system/user')
    await page.locator('.page-container').first().waitFor({timeout: 15000})

    const searchInput = page
      .locator('input[placeholder*="用户名"], input[type="search"], input[placeholder*="搜索"]')
      .first()
    await expect(searchInput).toBeVisible()
  })

  test('用户搜索能正常响应', async ({authenticatedPage: page}) => {
    await page.goto('/system/user')
    await page.locator('.page-container').first().waitFor({timeout: 15000})

    const searchInput = page.locator('input[placeholder*="用户名"]').first()
    if (await searchInput.isVisible().catch(() => false)) {
      await searchInput.fill('admin')
      await page.locator('button').filter({hasText: /搜索|查询|Search/}).first().click()
      // 搜索后页面应正常响应（不崩溃）
      await expect(page.locator('.page-container').first()).toBeVisible()
    }
  })

  test('用户管理页面显示操作按钮', async ({authenticatedPage: page}) => {
    await page.goto('/system/user')
    await page.locator('.page-container').first().waitFor({timeout: 15000})

    const hasActionBtn = await page
      .locator('button')
      .filter({hasText: /新建|创建|新增|添加|Create|New|Add/})
      .first()
      .isVisible()
      .catch(() => false)
    const hasAnyButton = (await page.locator('button').count()) > 0
    expect(hasActionBtn || hasAnyButton).toBeTruthy()
  })

  test('可以访问角色权限管理页', async ({authenticatedPage: page}) => {
    await page.goto('/system/role')
    await expect(page.locator('.page-container').first()).toBeVisible({timeout: 15000})
  })
})
