<script lang="ts" setup>
/**
 * 注册页
 *
 * 调用 v3 的 `mobile/auth/register`：注册成功后后端直接下发 access/refresh token，
 * 因此这里注册完成即视为已登录，随后拉取用户信息并回到首页。
 */

import {mobileApi} from '@/api'
import {useUserStore} from '@/store/modules/user'

definePageMeta({layout: false, title: '注册'})

useSeoMeta({title: '注册 - FastBlog', robots: 'noindex'})

const userStore = useUserStore()

const form = reactive({username: '', email: '', password: '', confirm: ''})
const loading = ref(false)
const error = ref('')

/** 与后端 MobileRegisterRequest 的约束保持一致 */
const USERNAME_RE = /^[a-zA-Z0-9_]+$/

function validate(): string {
  const username = form.username.trim()
  if (username.length < 3 || username.length > 30) return '用户名需为 3-30 个字符'
  if (!USERNAME_RE.test(username)) return '用户名只能包含字母、数字与下划线'
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email.trim())) return '请输入有效的邮箱地址'
  if (form.password.length < 8) return '密码至少 8 位'
  if (form.password !== form.confirm) return '两次输入的密码不一致'
  return ''
}

async function onSubmit(): Promise<void> {
  error.value = validate()
  if (error.value) return

  loading.value = true
  try {
    const data = await mobileApi.register({
      username: form.username.trim(),
      email: form.email.trim(),
      password: form.password,
    })

    // 注册即登录：写入 token 并同步用户信息
    if (data?.access_token) {
      userStore.setToken(data.access_token, data.refresh_token || '')
      await userStore.fetchUserInfo().catch(() => undefined)
    }
    await navigateTo('/', {replace: true})
  } catch {
    error.value = '注册失败，用户名或邮箱可能已被占用'
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
        <p class="mt-1.5 text-sm text-fg-muted">创建账号，开始记录与交流</p>
      </div>

      <Card>
        <CardContent class="p-6">
          <form class="space-y-4" @submit.prevent="onSubmit">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">用户名</label>
              <Input v-model="form.username" placeholder="3-30 位字母、数字或下划线"/>
            </div>

            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">邮箱</label>
              <Input v-model="form.email" placeholder="用于登录与找回密码" type="email"/>
            </div>

            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">密码</label>
              <Input v-model="form.password" placeholder="至少 8 位" type="password"/>
            </div>

            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">确认密码</label>
              <Input v-model="form.confirm" placeholder="再次输入密码" type="password"/>
            </div>

            <p v-if="error" class="rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">{{ error }}</p>

            <Button :disabled="loading" class="w-full" type="submit">
              <Icon v-if="loading" class="h-4 w-4 animate-spin" name="loader-circle"/>
              {{ loading ? '注册中…' : '注册并登录' }}
            </Button>
          </form>

          <p class="mt-5 text-center text-sm text-fg-muted">
            已有账号？
            <NuxtLink class="font-medium text-fg hover:underline" to="/login">去登录</NuxtLink>
          </p>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
