import {ADMIN_CREDENTIALS, expect, test, waitForHydration} from './fixtures/auth'

/**
 * 登录流程 E2E（自 astro e2e/login.spec.ts 适配 Nuxt）
 *
 * 与 astro 版的差异：后台入口是 /dashboard（astro 是 /admin）；
 * 登录页为「用户名/邮箱 + 密码」输入框，校验与登录错误都是内联 .bg-danger-soft 提示。
 */
test.describe('登录流程', () => {
  test.beforeEach(async ({page}) => {
    await page.goto('/login')
    await waitForHydration(page)
  })

  test('登录页面正确渲染', async ({page}) => {
    await expect(page).toHaveURL(/\/login/)
    const usernameInput = page
      .locator('input[placeholder*="用户名"], input[name="username"], input[type="text"]')
      .first()
    const passwordInput = page.locator('input[type="password"]').first()
    await expect(usernameInput).toBeVisible()
    await expect(passwordInput).toBeVisible()
  })

  test('空凭据提交应显示验证错误', async ({page}) => {
    await page.locator('button[type="submit"]').first().click()
    await expect(page).toHaveURL(/\/login/)
    // 登录页把错误拆成了两级：字段级（`useFormErrors`，类名 `text-danger`）与提交级
    // （凭据错误/2FA，类名 `bg-danger-soft`）。空表单走字段级校验，因此这里两者都接受。
    await expect(page.locator('.text-danger, .bg-danger-soft').first()).toBeVisible()
  })

  test('错误密码登录应失败', async ({page}) => {
    // 用无关用户名：避免给真实账号累积失败计数（后端 5 次失败锁 30 分钟）
    await page.locator('input[placeholder*="用户名"]').first().fill('nonexistent_user_e2e')
    await page.locator('input[type="password"]').first().fill('wrong_password_12345')
    await page.locator('button[type="submit"]').first().click()
    await page.waitForTimeout(2000)
    // 不应进入后台（Nuxt 后台入口是 /dashboard）
    await expect(page).toHaveURL(/\/login/)
  })

  test('正确凭据登录成功后进入管理后台', async ({page}) => {
    await page.locator('input[placeholder*="用户名"]').first().fill(ADMIN_CREDENTIALS.username)
    await page.locator('input[type="password"]').first().fill(ADMIN_CREDENTIALS.password)
    await page.locator('button[type="submit"]').first().click()
    // 收紧断言（§17.5 遗留）：有效凭证必须进入 /dashboard；
    // 若凭证无效会停在 /login —— 那是凭证配置问题，必须让用例红。
    await page.waitForURL(/\/dashboard/, {timeout: 15000})
  })

  test('未认证访问后台应重定向到登录页', async ({page}) => {
    await page.goto('/dashboard')
    await page.waitForURL(/\/login/, {timeout: 15000})
    await expect(page).toHaveURL(/\/login/)
  })
})
