import {defineConfig, devices} from '@playwright/test'

/**
 * E2E 回归网（T2-4，自 astro e2e 迁移适配 Nuxt，见 HANDOVER §17）
 *
 * 运行：
 *   npm run test:e2e                    # 自动复用 / 拉起 dev 服务器（5173）
 *   set E2E_ADMIN_USER=... & set E2E_ADMIN_PASS=... & npm run test:e2e
 *
 * 前提：
 *   - 后端 API 运行在 :9421（devProxy 把 /api 转发过去；生产形态由 nginx 反代承担）
 *   - 带认证的 spec 需要有效凭证（默认 admin/admin123 沿用 astro 版，通常要用环境变量覆盖）
 *   - 浏览器：npx playwright install chromium
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: {timeout: 10_000},
  retries: process.env.CI ? 1 : 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
    trace: 'retain-on-failure',
  },
  projects: [{name: 'chromium', use: {...devices['Desktop Chrome']}}],
  webServer: process.env.E2E_NO_WEB_SERVER
    ? undefined
    : {
      command: 'npm run dev',
      url: process.env.E2E_BASE_URL || 'http://localhost:5173',
      reuseExistingServer: true,
      timeout: 180_000,
    },
})
