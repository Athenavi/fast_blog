import {type Page, test as base} from '@playwright/test'

/**
 * E2E 测试共享 fixtures（自 astro e2e/fixtures/auth.ts 适配 Nuxt）
 *
 * 认证方式：直接调 v3 登录接口拿 JWT，写入前端使用的 localStorage 键
 * `fastblog.token`（= src/constants/index.ts 的 STORAGE_TOKEN，明文字符串存储）。
 * 后台的 auth 中间件只检查「token 存在」，userInfo 会由中间件自动调
 * `/system/auth/me` 拉取，因此无需再种用户信息。
 */
export const ADMIN_CREDENTIALS = {
  username: process.env.E2E_ADMIN_USER || 'admin',
  password: process.env.E2E_ADMIN_PASS || 'admin123',
}

const TOKEN_KEY = 'fastblog.token'

async function loginViaAPI(page: Page, baseURL: string, creds = ADMIN_CREDENTIALS): Promise<void> {
  // 先访问目标站点以设置 origin（dev 下 /api 由 devProxy 转发到 :9421）
  await page.goto(baseURL || '/')

  const resp = await page.evaluate(async ({url, username, password}) => {
    const r = await fetch(`${url}/api/v3/system/auth/login`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username, password}),
    })
    return r.json()
  }, {url: baseURL || '', username: creds.username, password: creds.password})

  const token = resp?.data?.access_token
  if (!token) {
    throw new Error(
      `e2e 登录失败（${creds.username}）：需要后端运行在 :9421 且凭证有效。` +
      '可用环境变量 E2E_ADMIN_USER / E2E_ADMIN_PASS 覆盖默认凭证。',
    )
  }
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
