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

definePageMeta({layout: false, title: 'register.title'})

useSeoMeta({title: t('register.seoTitle'), robots: 'noindex'})

const userStore = useUserStore()

const form = reactive({username: '', email: '', password: '', confirm: ''})
const loading = ref(false)
/** 提交级错误（如用户名/邮箱已被占用），字段级错误由 useFormErrors 承担 */
const submitError = ref('')
const {errors, validate, clearField, fieldProps, errorId} = useFormErrors()

/** 与后端 MobileRegisterRequest 的约束保持一致 */
const USERNAME_RE = /^[a-zA-Z0-9_]+$/

async function onSubmit(): Promise<void> {
  submitError.value = ''
  const passed = validate({
    username: () => {
      const username = form.username.trim()
      if (username.length < 3 || username.length > 30) return t('register.ruleUsernameLength')
      if (!USERNAME_RE.test(username)) return t('register.ruleUsernameChars')
      return null
    },
    email: () =>
      /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email.trim()) ? null : t('register.ruleEmailInvalid'),
    password: () => (form.password.length < 8 ? t('register.rulePasswordLength') : null),
    confirm: () => (form.password !== form.confirm ? t('register.rulePasswordMismatch') : null),
  })
  if (!passed) return

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
    submitError.value = t('register.errorTaken')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-dvh items-center justify-center bg-surface-soft px-4">
    <div class="w-full max-w-sm">
      <div class="mb-6 text-center">
        <NuxtLink class="text-xl font-semibold tracking-tight text-fg" to="/">FastBlog</NuxtLink>
        <p class="mt-1.5 text-sm text-fg-muted">{{ $t('register.tagline') }}</p>
      </div>

      <Card>
        <CardContent class="p-6">
          <form class="space-y-4" @submit.prevent="onSubmit">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg" for="register-username">{{
                  $t('register.username')
                }}</label>
              <Input
                v-model="form.username"
                id="register-username"
                :placeholder="$t('register.usernameHint')"
                v-bind="fieldProps('username')"
                @input="clearField('username')"
              />
              <p v-if="errors.username" :id="errorId('username')" class="mt-1.5 text-sm text-danger">
                {{ errors.username }}
              </p>
            </div>

            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg" for="register-email">{{
                  $t('register.email')
                }}</label>
              <Input
                v-model="form.email"
                id="register-email"
                :placeholder="$t('register.emailHint')"
                type="email"
                v-bind="fieldProps('email')"
                @input="clearField('email')"
              />
              <p v-if="errors.email" :id="errorId('email')" class="mt-1.5 text-sm text-danger">
                {{ errors.email }}
              </p>
            </div>

            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg" for="register-password">{{
                  $t('register.password')
                }}</label>
              <Input
                v-model="form.password"
                id="register-password"
                :placeholder="$t('register.passwordHint')"
                autocomplete="new-password"
                type="password"
                v-bind="fieldProps('password')"
                @input="clearField('password')"
              />
              <p v-if="errors.password" :id="errorId('password')" class="mt-1.5 text-sm text-danger">
                {{ errors.password }}
              </p>
            </div>

            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg"
                     for="register-confirm">{{ $t('register.confirmPassword') }}</label>
              <Input
                v-model="form.confirm"
                id="register-confirm"
                :placeholder="$t('register.confirmPasswordPlaceholder')"
                autocomplete="new-password"
                type="password"
                v-bind="fieldProps('confirm')"
                @input="clearField('confirm')"
              />
              <p v-if="errors.confirm" :id="errorId('confirm')" class="mt-1.5 text-sm text-danger">
                {{ errors.confirm }}
              </p>
            </div>

            <p v-if="submitError" class="rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
              {{ submitError }}
            </p>

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
