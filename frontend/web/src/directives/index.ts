/**
 * 权限指令
 *
 *   <el-button v-auth="'module_content:article:create'">新建</el-button>
 *   <el-button v-auth="['module_content:article:edit', 'module_content:article:publish']">发布</el-button>   <!-- AND -->
 *   <el-button v-role="['admin']">仅管理员可见</el-button>
 *
 * 权限码与后端 `capabilities.code` 一致（`resource:action`），超级管理员直接放行。
 */

import type {App, Directive, DirectiveBinding} from 'vue'

import {useUserStore} from '@/store/modules/user'

const auth: Directive<HTMLElement, string | string[]> = {
  mounted(el, binding: DirectiveBinding<string | string[]>) {
    const userStore = useUserStore()
    if (!userStore.hasPermission(binding.value)) {
      el.parentNode?.removeChild(el)
    }
  },
}

const role: Directive<HTMLElement, string | string[]> = {
  mounted(el, binding: DirectiveBinding<string | string[]>) {
    const userStore = useUserStore()
    const required = Array.isArray(binding.value) ? binding.value : [binding.value]
    const owned = new Set(userStore.roles)
    const allowed = userStore.isSuperuser || required.some((slug) => owned.has(slug))
    if (!allowed) {
      el.parentNode?.removeChild(el)
    }
  },
}

export function setupDirectives(app: App): void {
  app.directive('auth', auth)
  app.directive('role', role)
}

export {auth, role}
