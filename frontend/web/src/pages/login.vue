<script lang="ts" setup>
const {t} = useI18n()
/**
 * 统一登录页
 *
 * 前台读者与后台管理员共用：登录后按是否具备后台权限分流。
 * 只使用 Tailwind + shadcn-vue，保证前台访客看到的风格一致（Element Plus 仅用于后台页面）。
 */

import {HOME_PATH} from '@/constants'
import {useUserStore} from '@/store/modules/user'

definePageMeta({layout: false, title: 'login.loginButton'})

useSeoMeta({title: t('login.seoTitle'), robots: 'noindex'})

const route = useRoute()
const userStore = useUserStore()

const form = reactive({identifier: '', password: '', remember_me: true})
const loading = ref(false)
/** 提交级错误（凭据错误 / 2FA 提示），字段级错误由 useFormErrors 承担 */
const submitError = ref('')
const {errors, validate, clearField, fieldProps, errorId} = useFormErrors()

async function onSubmit(): Promise<void> {
  submitError.value = ''
  const passed = validate({
    identifier: () => (form.identifier.trim() ? null : t('login.identifierRequired')),
    password: () => (form.password ? null : t('login.passwordRequired')),
  })
  if (!passed) return

  loading.value = true
  try {
    const payload = form.identifier.includes('@')
      ? {email: form.identifier.trim(), password: form.password, remember_me: form.remember_me}
      : {username: form.identifier.trim(), password: form.password, remember_me: form.remember_me}

    const result = await userStore.login(payload)
    if (result.requires2fa) {
      submitError.value = t('login.twoFactorMobileHint')
      return
    }

    // 管理员进后台，普通读者回前台
    const hasAdminAccess = userStore.isSuperuser || userStore.permissions.length > 0
    const fallback = hasAdminAccess ? HOME_PATH : '/'
    await navigateTo(String(route.query.redirect || fallback), {replace: true})
  } catch {
    // 具体错误由 request 拦截器提示，这里给出兜底文案
    submitError.value = submitError.value || t('login.errorInvalid')
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
        <p class="mt-1.5 text-sm text-fg-muted">{{ $t('login.subtitle') }}</p>
      </div>

      <Card>
        <CardContent class="p-6">
          <form class="space-y-4" @submit.prevent="onSubmit">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg"
                     for="login-identifier">{{ $t('login.usernameOrEmail') }}</label>
              <div class="relative">
                <Icon class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-subtle" name="user"/>
                <Input
                  v-model="form.identifier"
                  id="login-identifier"
                  :placeholder="$t('login.usernameOrEmailPlaceholder')"
                  class="pl-9"
                  autocomplete="username"
                  v-bind="fieldProps('identifier')"
                  @input="clearField('identifier')"
                />
              </div>
              <p v-if="errors.identifier" :id="errorId('identifier')" class="mt-1.5 text-sm text-danger">
                {{ errors.identifier }}
              </p>
            </div>

            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg" for="login-password">{{
                  $t('login.password')
                }}</label>
              <div class="relative">
                <Icon class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-subtle" name="lock"/>
                <Input
                  v-model="form.password"
                  id="login-password"
                  :placeholder="$t('login.passwordPlaceholder')"
                  autocomplete="current-password"
                  class="pl-9"
                  type="password"
                  v-bind="fieldProps('password')"
                  @input="clearField('password')"
                />
              </div>
              <p v-if="errors.password" :id="errorId('password')" class="mt-1.5 text-sm text-danger">
                {{ errors.password }}
              </p>
            </div>

            <label class="flex cursor-pointer items-center gap-2 text-sm text-fg-muted">
              <input v-model="form.remember_me" class="h-4 w-4 rounded border-line-strong" type="checkbox">
              {{ $t('login.keepSignedIn') }}
            </label>

            <p v-if="submitError" class="rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
              {{ submitError }}
            </p>

            <Button :disabled="loading" class="w-full" type="submit">
              <Icon v-if="loading" class="h-4 w-4 animate-spin" name="loader-circle"/>
              {{ loading ? t('login.loggingIn') : t('login.loginButton') }}
            </Button>
          </form>

          <p class="mt-5 text-center text-sm text-fg-muted">
            {{ $t('login.noAccount') }}
            <NuxtLink class="font-medium text-fg hover:underline" to="/register">{{
                $t('login.registerNow')
              }}
            </NuxtLink>
          </p>
        </CardContent>
      </Card>

      <p class="mt-6 text-center text-sm">
        <NuxtLink class="text-fg-subtle hover:text-fg-muted" to="/">{{ $t('login.backToHome') }}</NuxtLink>
      </p>
    </div>
  </div>
</template>
