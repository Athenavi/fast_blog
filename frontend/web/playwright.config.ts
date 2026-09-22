import {defineConfig, devices} from '@playwright/test'
import {readFileSync} from 'node:fs'
import {resolve} from 'node:path'

/**
 * E2E 回归网（Astro 版 e2e 迁移适配 Nuxt）
 *
 * 运行：
 *   npm run test:e2e                    # 自动复用 / 拉起 dev 服务器（5173）
 *   set E2E_ADMIN_USER=... & set E2E_ADMIN_PASS=... & npm run test:e2e
 *
 * 前提：
 *   - 后端 API 运行在 :9421（devProxy 把 /api 转发过去；生产形态由 nginx 反代承担）
 *   - 带认证的 spec 需要有效凭证：优先环境变量，其次本地 .env.e2e（已 gitignore，不入库）
 *   - 浏览器：npx playwright install chromium
 */

// 读取本地 .env.e2e（KEY=VALUE 每行一条）；已存在的环境变量优先，不被覆盖
for (const line of (() => {
  try {
    return readFileSync(resolve(__dirname, '.env.e2e'), 'utf-8').split(/\r?\n/)
  } catch {
    return []
  }
})()) {
  const m = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$/)
  if (m && !(m[1] in process.env)) process.env[m[1]] = m[2]
}

/**
 * 被测端口：
 *   - 默认 5173（= `.env.development` 的 `VITE_PORT`），可用 `E2E_PORT` 覆盖；
 *   - **不要假设 5173 一定是本项目的**：同一台机器上并行开发多个前端时，该端口常被
 *     别的项目占用，而 `reuseExistingServer: true` 会把**别人的** dev server 当成被测目标
 *     （实测症状：页面里没有 `#__nuxt`、`waitForHydration` 超时，整份 spec 一起红）。
 *     换端口：`E2E_PORT=5273 npx playwright test`（webServer 会自动带上 VITE_PORT）。
 */
const E2E_PORT = Number(process.env.E2E_PORT || process.env.VITE_PORT || 5173)
const BASE_URL = process.env.E2E_BASE_URL || `http://localhost:${E2E_PORT}`

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: {timeout: 10_000},
  retries: process.env.CI ? 1 : 0,
  reporter: [['list']],
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
  },
  projects: [{name: 'chromium', use: {...devices['Desktop Chrome']}}],
  webServer: process.env.E2E_NO_WEB_SERVER
    ? undefined
    : {
      command: 'npm run dev',
      url: BASE_URL,
      reuseExistingServer: true,
      timeout: 180_000,
      env: {VITE_PORT: String(E2E_PORT)},
    },
})
