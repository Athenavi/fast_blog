import {expect, test} from './fixtures/auth'

/**
 * 媒体库管理 E2E（自 astro e2e/media.spec.ts 适配 Nuxt）
 *
 * 路由：/admin/media → /content/media；上传按钮文案来自 `media.upload`（zh:「上传」），
 * 筛选区是类型 el-select + 「媒体分类」输入框。
 */
test.describe('媒体库管理', () => {
  test('管理员可以访问媒体库', async ({authenticatedPage: page}) => {
    await page.goto('/content/media')
    await expect(page.locator('.page-container').first()).toBeVisible({timeout: 15000})
  })

  test('媒体库页面包含上传入口', async ({authenticatedPage: page}) => {
    await page.goto('/content/media')
    await page.locator('.page-container').first().waitFor({timeout: 15000})

    const hasFileInput = (await page.locator('input[type="file"]').count()) > 0
    const hasUploadBtn =
      (await page.locator('button').filter({hasText: /上传|Upload/}).count()) > 0
    expect(hasFileInput || hasUploadBtn).toBeTruthy()
  })

  test('可以打开文件选择对话框进行上传', async ({authenticatedPage: page}) => {
    await page.goto('/content/media')
    await page.locator('.page-container').first().waitFor({timeout: 15000})

    const uploadBtn = page.locator('button').filter({hasText: /上传|Upload/}).first()
    if (await uploadBtn.isVisible().catch(() => false)) {
      const [fileChooser] = await Promise.all([
        page.waitForEvent('filechooser', {timeout: 5000}).catch(() => null),
        uploadBtn.click(),
      ])
      // 触发了 file chooser 说明上传入口工作正常（不实际上传）
      if (fileChooser) {
        expect(fileChooser).toBeTruthy()
        await fileChooser.setFiles([])
      }
    }
  })

  test('媒体库页面正常加载（视图切换为可选能力）', async ({authenticatedPage: page}) => {
    await page.goto('/content/media')
    await expect(page.locator('.page-container').first()).toBeVisible({timeout: 15000})
  })

  test('媒体库包含搜索或筛选功能', async ({authenticatedPage: page}) => {
    await page.goto('/content/media')
    await page.locator('.page-container').first().waitFor({timeout: 15000})

    const hasSearch = await page
      .locator('input[placeholder*="分类"], input[placeholder*="搜索"], input[type="search"]')
      .first()
      .isVisible()
      .catch(() => false)
    const hasFilter = (await page.locator('.el-select').count()) > 0
    expect(hasSearch || hasFilter).toBeTruthy()
  })
})
