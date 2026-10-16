/**
 * Element Plus 函数式 API 的统一封装（动态加载）。
 *
 * 后台页面禁止静态 `import {ElMessage} from 'element-plus'`：静态导入会让
 * element-plus 成为共享 chunk 并被所有页面（含前台 SSR 页）modulepreload，
 * 前台首包因此多出约 1MB。统一改从本模块导入——内部 `await import('element-plus')`
 * 按需加载，调用形态与原 API 一致。
 *
 * - 模板里的 `el-*` 组件不受影响，仍由 `layouts/admin.vue` 动态注册；
 * - `ElMessage` 各方法返回 Promise（原 API 同步返回 handler），现有调用方均未使用返回值；
 * - `ElMessageBox.confirm/prompt` 的 resolve/reject 语义与原 API 完全一致
 *   （确认时 resolve，取消/关闭时 reject `'cancel'`/`'close'`）。
 */

import type {AppContext} from 'vue'
import type {ElMessageBoxOptions, MessageBoxData} from 'element-plus'

type ElementPlusModule = typeof import('element-plus')

type MessageFn = ElementPlusModule['ElMessage']
type MessageArgs = Parameters<MessageFn>
type MessageResult = ReturnType<MessageFn>

/** 调用形态与 ElMessage 一致，但全部异步返回。 */
export interface FeedbackMessage {
  (...args: MessageArgs): Promise<MessageResult>

  success(...args: MessageArgs): Promise<MessageResult>

  warning(...args: MessageArgs): Promise<MessageResult>

  info(...args: MessageArgs): Promise<MessageResult>

  error(...args: MessageArgs): Promise<MessageResult>
}

/** 与 ElMessageBox.confirm/prompt/alert 的常用签名一致（message + title + options）。 */
type MessageBoxMethod = (
  message: ElMessageBoxOptions['message'],
  title?: ElMessageBoxOptions['title'],
  options?: ElMessageBoxOptions,
  appContext?: AppContext | null,
) => Promise<MessageBoxData>

/** 只暴露后台页面用到的 confirm / prompt / alert。 */
export type FeedbackMessageBox = {
  confirm: MessageBoxMethod
  prompt: MessageBoxMethod
  alert: MessageBoxMethod
}

const load = (): Promise<ElementPlusModule> => import('element-plus')

export const ElMessage: FeedbackMessage = Object.assign(
  async (...args: MessageArgs) => (await load()).ElMessage(...args),
  {
    success: async (...args: MessageArgs) => (await load()).ElMessage.success(...args),
    warning: async (...args: MessageArgs) => (await load()).ElMessage.warning(...args),
    info: async (...args: MessageArgs) => (await load()).ElMessage.info(...args),
    error: async (...args: MessageArgs) => (await load()).ElMessage.error(...args),
  },
)

export const ElMessageBox: FeedbackMessageBox = {
  confirm: (message, title, options, appContext) =>
    load().then(({ElMessageBox: box}) => box.confirm(message, title, options, appContext)),
  prompt: (message, title, options, appContext) =>
    load().then(({ElMessageBox: box}) => box.prompt(message, title, options, appContext)),
  alert: (message, title, options, appContext) =>
    load().then(({ElMessageBox: box}) => box.alert(message, title, options, appContext)),
}

/** 后台表单页常用的 EP 类型（type-only 导出，不参与运行时打包）。 */
export type {FormInstance, FormRules} from 'element-plus'
