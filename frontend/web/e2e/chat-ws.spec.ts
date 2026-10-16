import type {Page} from '@playwright/test'

import {expect, test} from './fixtures/auth'

/**
 * 群聊 WebSocket 准入 E2E（批次 17 遗留项）
 *
 * 批次 17 时 4401 / 4403 只有 starlette `TestClient` 的单测覆盖，**未在真实浏览器验证**。
 * 这里断言浏览器实际观测到的 `CloseEvent.code`：
 *  - 无凭据 → `4401`（鉴权失败必须关闭连接）
 *  - 有凭据但不是群成员（用不存在的群 id）→ `4403`
 *  - 有凭据且是成员 → 连接可用（发 `ping` 收到 `pong`；没有群时临时建一个，用例结束前解散）
 *
 * 服务端**先 accept 再 close**（`core/ws_auth.py::accept_then_close`）：未 accept 就 close
 * 会被 uvicorn 按 ASGI 规范转成 HTTP 403 拒绝握手，浏览器只看到 `1006`（2026-09-21 实测）。
 *
 * 三个用例都**直连后端**（`ws://127.0.0.1:9421`），因为 dev 下 WS 本来就不经代理
 * （`Upgrade` 事件既不进 `nitro.devProxy` 也不进 Vite 的 `server.proxy`，实测后者连
 * `configure` 回调都不触发），前端自己也是按 `NUXT_PUBLIC_WS_BASE_URL` 直连后端。
 * HTTP 部分仍走页面同源（devProxy），与前端一致。
 */

/** 后端直连地址（可用 E2E_API_BASE_URL 覆盖，与 fixtures 里的代理目标保持一致） */
const BACKEND_HTTP = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:9421'
const BACKEND_WS = BACKEND_HTTP.replace(/^http/, 'ws')
const WS_PATH = '/api/v3/chat/message/ws'
const TOKEN_KEY = 'fastblog.token'

/** 在页面里发起一次 WS 连接，返回浏览器观测到的关闭码（超时未关闭记 -1） */
function wsCloseCode(page: Page, url: string): Promise<number> {
  return page.evaluate(
    (target) =>
      new Promise<number>((resolve) => {
        const ws = new WebSocket(target)
        const timer = window.setTimeout(() => {
          resolve(-1)
          try {
            ws.close()
          } catch {
            /* 已关闭 */
          }
        }, 10_000)
        ws.onclose = (event) => {
          window.clearTimeout(timer)
          resolve(event.code)
        }
        ws.onerror = () => {
          /* 出错后 onclose 紧随其后，结论由 onclose 给出 */
        }
      }),
    url,
  )
}

test.describe('群聊 WebSocket 准入', () => {
  test('匿名连接应以 4401 关闭', async ({page}) => {
    await page.goto('/login') // 建立 origin（本 context 未写入 token）
    expect(await wsCloseCode(page, `${BACKEND_WS}${WS_PATH}/1`)).toBe(4401)
  })

  test('已登录但非群成员应以 4403 关闭', async ({authenticatedPage: page}) => {
    const token = await page.evaluate((key) => localStorage.getItem(key), TOKEN_KEY)
    expect(token).toBeTruthy()
    // 用一个不可能存在的群 id：`is_member` 对不存在的群返回 False → 4403
    const url = `${BACKEND_WS}${WS_PATH}/999999999?token=${encodeURIComponent(String(token))}`
    expect(await wsCloseCode(page, url)).toBe(4403)
  })

  test('已登录且是群成员时连接可用（ping / pong 往返）', async ({authenticatedPage: page}) => {
    const bearer = String(await page.evaluate((key) => localStorage.getItem(key), TOKEN_KEY))

    // "取群 → 连 WS → 收 pong → 清理"放在一次 evaluate 里，避免多次往返的时序竞态
    const outcome = await page.evaluate(
      async ({token, wsBase, path}) => {
        const headers = {Authorization: `Bearer ${token}`, 'Content-Type': 'application/json'}
        const api = async (
          method: string,
          path: string,
          body?: unknown,
        ): Promise<{ code?: number; data?: unknown }> => {
          const resp = await fetch(path, {
            method,
            headers,
            body: body === undefined ? undefined : JSON.stringify(body),
          })
          return await resp.json().catch(() => ({}))
        }

        const me = await api('GET', '/api/v3/system/auth/me')
        const meId = (me.data as { id?: number } | undefined)?.id ?? null
        const mine = await api('GET', '/api/v3/chat/message/my-groups')
        const list = (mine.data as Array<{ id: number }> | undefined) ?? []

        let groupId: number | null = list[0]?.id ?? null
        let temporary = false
        if (groupId === null && meId !== null) {
          // 没有现成的群就临时建一个（建群会把创建者写成 owner 成员），用完立刻解散
          const created = await api('POST', '/api/v3/chat/group', {
            name: `e2e-ws-${Date.now()}`,
            creator: meId,
          })
          if (created.code === 200) {
            groupId = (created.data as { id: number }).id
            temporary = true
          }
        }
        if (groupId === null) return 'no-group'

        try {
          const url = `${wsBase}${path}/${groupId}?token=${encodeURIComponent(token)}`
          return await new Promise<string>((resolve) => {
            const ws = new WebSocket(url)
            const timer = window.setTimeout(() => {
              resolve('timeout')
              try {
                ws.close()
              } catch {
                /* 已关闭 */
              }
            }, 10_000)
            ws.onopen = () => ws.send(JSON.stringify({type: 'ping'}))
            ws.onmessage = (event) => {
              window.clearTimeout(timer)
              resolve(String(event.data))
              ws.close()
            }
            ws.onclose = (event) => {
              window.clearTimeout(timer)
              resolve(`closed:${event.code}`)
            }
          })
        } finally {
          if (temporary && groupId !== null) {
            await api('DELETE', `/api/v3/chat/group/${groupId}`)
          }
        }
      },
      {token: bearer, wsBase: BACKEND_WS, path: WS_PATH},
    )

    expect(outcome).toContain('pong')
  })
})
