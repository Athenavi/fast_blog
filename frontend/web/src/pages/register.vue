<script lang="ts" setup>
const {t} = useI18n()
/**
 * 注册页
 *
 * 调用 v3 的 `mobile/auth/register`：注册成功后后端直接下发 access/refresh token，
 * 因此这里注册完成即视为已登录，随后拉取用户信息并回到首页。
 */

import {mobileApi} from '@/api'
import {useUserStore} from '@/store/modules/user'

definePageMeta({layout: false, title: '注册'})

useSeoMeta({title: t('register.seoTitle'), robots: 'noindex'})

const userStore = useUserStore()

const form = reactive({username: '', email: '', password: '', confirm: ''})
const loading = ref(false)
const error = ref('')

/** 与后端 MobileRegisterRequest 的约束保持一致 */
const USERNAME_RE = /^[a-zA-Z0-9_]+$/

function validate(): string {
  const username = form.username.trim()
  if (username.length < 3 || username.length > 30) return t('register.ruleUsernameLength')
  if (!USERNAME_RE.test(username)) return t('register.ruleUsernameChars')
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email.trim())) return t('register.ruleEmailInvalid')
  if (form.password.length < 8) return t('register.rulePasswordLength')
  if (form.password !== form.confirm) return t('register.rulePasswordMismatch')
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
    error.value = t('register.errorTaken')
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
        <p class="mt-1.5 text-sm text-fg-muted">{{ $t('register.tagline') }}</p>
      </div>

      <Card>
        <CardContent class="p-6">
          <form class="space-y-4" @submit.prevent="onSubmit">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('register.username') }}</label>
              <Input v-model="form.username" :placeholder="$t('register.usernameHint')"/>
            </div>

            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('register.email') }}</label>
              <Input v-model="form.email" :placeholder="$t('register.emailHint')" type="email"/>
            </div>

            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('register.password') }}</label>
              <Input v-model="form.password" :placeholder="$t('register.passwordHint')" type="password"/>
            </div>

            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('register.confirmPassword') }}</label>
              <Input v-model="form.confirm" :placeholder="$t('register.confirmPasswordPlaceholder')" type="password"/>
            </div>

            <p v-if="error" class="rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">{{ error }}</p>

            <Button :disabled="loading" class="w-full" type="submit">
              <Icon v-if="loading" class="h-4 w-4 animate-spin" name="loader-circle"/>
              {{ loading ? t('register.registering') : t('register.submit') }}
            </Button>
          </form>

          <p class="mt-5 text-center text-sm text-fg-muted">
            {{ $t('register.hasAccount') }}
            <NuxtLink class="font-medium text-fg hover:underline" to="/login">{{ $t('register.goLogin') }}</NuxtLink>
          </p>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
