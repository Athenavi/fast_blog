<script lang="ts" setup>
/**
 * 统一登录页
 *
 * 前台读者与后台管理员共用：登录后按是否具备后台权限分流。
 * 只使用 Tailwind + shadcn-vue，保证前台访客看到的风格一致（Element Plus 仅用于后台页面）。
 */

import {HOME_PATH} from '@/constants'
import {useUserStore} from '@/store/modules/user'

definePageMeta({layout: false, title: '登录'})

useSeoMeta({title: '登录 - FastBlog', robots: 'noindex'})

const route = useRoute()
const userStore = useUserStore()

const form = reactive({identifier: '', password: '', remember_me: true})
const loading = ref(false)
const error = ref('')

async function onSubmit(): Promise<void> {
  error.value = ''
  if (!form.identifier.trim() || !form.password) {
    error.value = '请输入用户名（或邮箱）与密码'
    return
  }

  loading.value = true
  try {
    const payload = form.identifier.includes('@')
      ? {email: form.identifier.trim(), password: form.password, remember_me: form.remember_me}
      : {username: form.identifier.trim(), password: form.password, remember_me: form.remember_me}

    const result = await userStore.login(payload)
    if (result.requires2fa) {
      error.value = '该账号启用了双因素认证，请前往移动端完成二次验证'
      return
    }

    // 管理员进后台，普通读者回前台
    const hasAdminAccess = userStore.isSuperuser || userStore.permissions.length > 0
    const fallback = hasAdminAccess ? HOME_PATH : '/'
    await navigateTo(String(route.query.redirect || fallback), {replace: true})
  } catch {
    // 具体错误由 request 拦截器提示，这里给出兜底文案
    error.value = error.value || '登录失败，请检查用户名与密码'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-surface-soft px-4">
    <div class="w-full max-w-sm">
      <div class="mb-6 text-center">
        <NuxtLink class="text-xl font-semibold tracking-tight text-fg" to="/">FastBlog</NuxtLink>
        <p class="mt-1.5 text-sm text-fg-muted">登录后可参与评论，管理员可进入后台</p>
      </div>

      <Card>
        <CardContent class="p-6">
          <form class="space-y-4" @submit.prevent="onSubmit">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">用户名 / 邮箱</label>
              <div class="relative">
                <Icon class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-subtle" name="user"/>
                <Input v-model="form.identifier" class="pl-9" placeholder="用户名或邮箱"/>
              </div>
            </div>

            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">密码</label>
              <div class="relative">
                <Icon class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-subtle" name="lock"/>
                <Input v-model="form.password" class="pl-9" placeholder="请输入密码" type="password"/>
              </div>
            </div>

            <label class="flex cursor-pointer items-center gap-2 text-sm text-fg-muted">
              <input v-model="form.remember_me" class="h-4 w-4 rounded border-line-strong" type="checkbox">
              保持登录
            </label>

            <p v-if="error" class="rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">{{ error }}</p>

            <Button :disabled="loading" class="w-full" type="submit">
              <Icon v-if="loading" class="h-4 w-4 animate-spin" name="loader-circle"/>
              {{ loading ? '登录中…' : '登录' }}
            </Button>
          </form>

          <p class="mt-5 text-center text-sm text-fg-muted">
            还没有账号？
            <NuxtLink class="font-medium text-fg hover:underline" to="/register">立即注册</NuxtLink>
          </p>
        </CardContent>
      </Card>

      <p class="mt-6 text-center text-sm">
        <NuxtLink class="text-fg-subtle hover:text-fg-muted" to="/">← 返回首页</NuxtLink>
      </p>
    </div>
  </div>
</template>
