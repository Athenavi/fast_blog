/**
 * 权限指令（客户端插件）
 *
 *   <el-button v-auth="'module_content:article:create'">新建</el-button>
 *   <el-button v-auth="['module_content:article:edit', 'module_content:article:publish']">发布</el-button>
 *   <el-button v-role="['admin']">仅管理员可见</el-button>
 *
 * 权限码与后端 `capabilities.code` 一致，超级管理员直接放行。
 *
 * **权限不足时的表现：保留控件并置为禁用，而不是把 DOM 摘掉。**
 * 摘掉 DOM 的老做法有两个实际代价：
 *   1. 用户上一秒看到的按钮下一秒消失，既不知道为什么，也没有申请入口；
 *   2. 布局会随权限抖动（工具栏留白/错位）。
 * 现在改为加 `is-disabled`（Element Plus 禁用视觉）+ `aria-disabled` + `title` 说明，
 * 并在**父元素捕获阶段**拦截点击/键盘，确保即使视觉上是禁用态也绝不可能触发动作。
 *
 * 为什么拦截器挂在父元素：同元素上 Vue 的 `@click` 监听先于本指令注册，
 * 在元素自身 `stopImmediatePropagation` 已经太晚；父元素的 capture 监听先于 target 执行，
 * 因此能真正阻断。同时控件本身仍可聚焦（`aria-disabled` 语义），键盘用户能读到原因。
 */
import type {Directive, DirectiveBinding} from 'vue'

import {useUserStore} from '@/store/modules/user'

type Translator = (key: string, named?: Record<string, unknown>) => string

/** 被禁用控件上挂载的拦截信息，卸载指令时清理 */
interface BlockerBinding {
  parent: HTMLElement
  handler: (event: Event) => void
}

const BLOCKERS = new WeakMap<HTMLElement, BlockerBinding>()

function attachBlocker(el: HTMLElement): void {
  const parent = el.parentElement
  if (!parent) return
  const handler = (event: Event): void => {
    if (event.target !== el && !el.contains(event.target as Node)) return
    // 阻断捕获传播后，事件不会到达控件自身（Vue 的 @click 也不会执行）
    event.stopImmediatePropagation()
    event.preventDefault()
  }
  parent.addEventListener('click', handler, true)
  parent.addEventListener('keydown', handler, true)
  BLOCKERS.set(el, {parent, handler})
}

function detachBlocker(el: HTMLElement): void {
  const binding = BLOCKERS.get(el)
  if (!binding) return
  binding.parent.removeEventListener('click', binding.handler, true)
  binding.parent.removeEventListener('keydown', binding.handler, true)
  BLOCKERS.delete(el)
}

/** 统一的"权限不足"表现：可聚焦、可悬停、不可触发 */
function deny(el: HTMLElement, translate: Translator, code: string): void {
  el.classList.add('is-disabled', 'admin-auth-disabled')
  el.setAttribute('aria-disabled', 'true')
  el.setAttribute('title', translate('admin.common.noPermission', {code}))
  attachBlocker(el)
}

function createAuthDirective(translate: Translator): Directive<HTMLElement, string | string[]> {
  return {
    mounted(el, binding: DirectiveBinding<string | string[]>) {
      const userStore = useUserStore()
      if (userStore.hasPermission(binding.value)) return
      deny(el, translate, Array.isArray(binding.value) ? binding.value.join(' / ') : binding.value)
    },
    unmounted(el) {
      detachBlocker(el)
    },
  }
}

function createRoleDirective(translate: Translator): Directive<HTMLElement, string | string[]> {
  return {
    mounted(el, binding: DirectiveBinding<string | string[]>) {
      const userStore = useUserStore()
      const required = Array.isArray(binding.value) ? binding.value : [binding.value]
      const owned = new Set(userStore.roles)
      if (userStore.isSuperuser || required.some((slug) => owned.has(slug))) return
      deny(el, translate, required.join(' / '))
    },
    unmounted(el) {
      detachBlocker(el)
    },
  }
}

export default defineNuxtPlugin((nuxtApp) => {
  /**
   * 指令运行期取 i18n（`$i18n` 由 @nuxtjs/i18n 注入）；
   * 取不到时退回 key，绝不让"提示文案缺失"演变成运行时报错。
   */
  const translate: Translator = (key, named) => {
    const composer = nuxtApp.$i18n as unknown as { t?: Translator } | undefined
    if (!composer?.t) return key
    return composer.t(key, named)
  }

  nuxtApp.vueApp.directive('auth', createAuthDirective(translate))
  nuxtApp.vueApp.directive('role', createRoleDirective(translate))
})
