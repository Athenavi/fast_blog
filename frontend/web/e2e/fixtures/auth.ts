import {readFileSync} from 'node:fs'
import {resolve} from 'node:path'
import {type Page, test as base} from '@playwright/test'

/**
 * E2E 测试共享 fixtures（自 astro e2e/fixtures/auth.ts 适配 Nuxt）
 *
 * 认证方式：直接调 v3 登录接口拿 JWT，写入前端使用的 localStorage 键
 * `fastblog.token`（= src/constants/index.ts 的 STORAGE_TOKEN，明文字符串存储）。
 * 后台的 auth 中间件只检查「token 存在」，userInfo 会由中间件自动调
 * `/system/auth/me` 拉取，因此无需再种用户信息。
 *
 * 凭证来源：环境变量 E2E_ADMIN_USER / E2E_ADMIN_PASS，或本地 `.env.e2e`
 * （该文件已 gitignore）。env 在**本模块（worker 进程）**读取——
 * playwright.config.ts 里的 process.env 修改不会传递到 test worker。
 */

function loadDotEnvE2E(): void {
  const candidates = [
    resolve(process.cwd(), '.env.e2e'),
    resolve(process.cwd(), 'frontend', 'web', '.env.e2e'),
  ]
  for (const path of candidates) {
    try {
      for (const line of readFileSync(path, 'utf-8').split(/\r?\n/)) {
        const m = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$/)
        if (m && !(m[1] in process.env)) process.env[m[1]] = m[2]
      }
      return
    } catch {
      /* 尝试下一个候选路径 */
    }
  }
}

loadDotEnvE2E()

export const ADMIN_CREDENTIALS = {
  username: process.env.E2E_ADMIN_USER || 'admin',
  password: process.env.E2E_ADMIN_PASS || 'admin123',
}

const TOKEN_KEY = 'fastblog.token'

// 每 worker 只登录一次（后端防爆破按 IP 计数，能省则省）
let tokenPromise: Promise<string> | null = null

async function fetchToken(baseURL: string): Promise<string> {
  const {username, password} = ADMIN_CREDENTIALS
  const resp = await fetch(`${baseURL}/api/v3/system/auth/login`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({username, password}),
  })
  const body = await resp.json().catch(() => ({}))
  const token = body?.data?.access_token
  if (!token) {
    throw new Error(
      `e2e 登录失败（${username}，HTTP ${resp.status}）：需要后端运行在 :9421 且凭证有效。` +
      '可用环境变量 E2E_ADMIN_USER / E2E_ADMIN_PASS 或 frontend/web/.env.e2e 覆盖默认凭证。',
    )
  }
  return token as string
}

async function loginViaAPI(page: Page, baseURL: string): Promise<void> {
  // 先访问目标站点以设置 origin（dev 下 /api 由 devProxy 转发到 :9421）
  await page.goto(baseURL || '/')
  const token = await (tokenPromise ??= fetchToken(baseURL || 'http://localhost:5173'))
  await page.evaluate(([key, value]) => localStorage.setItem(key, value), [TOKEN_KEY, token])
}

/** 自定义 test fixture，注入已认证的 page */
export const test = base.extend<{ authenticatedPage: Page }>({
  authenticatedPage: async ({page, baseURL}, use) => {
    await loginViaAPI(page, baseURL!)
    await use(page)
  },
})

/**
 * 等待 Nuxt 应用水合完成。
 *
 * SSR 页面在 `load` 事件后 Vue 仍在异步加载模块（dev 下尤甚），
 * 过早点击会落到未挂监听的 DOM 上、触发原生表单提交（整页刷新），
 * 断言因此假阴/假阳（`__vue_app__` 在 hydrate 同步完成后才赋值，见 Vue runtime-core）。
 */
export async function waitForHydration(page: Page): Promise<void> {
  await page.waitForFunction(
    () =>
      Boolean(
        (document.getElementById('__nuxt') as unknown as { __vue_app__?: unknown } | null)
          ?.__vue_app__,
      ),
    undefined,
    {timeout: 15_000},
  )
  await page.waitForTimeout(100)
}

export {expect} from '@playwright/test'
