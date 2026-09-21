<script lang="ts" setup>
const {t} = useI18n()
/**
 * 个人中心
 *
 * 使用 v3 的 `mobile/user` 域：资料读写与统计。
 * 该页依赖登录态（存于本地存储），在 `nuxt.config.ts` 中已设为 `ssr: false`，
 * 并由 `middleware: 'auth'` 负责未登录时跳转登录页。
 */

import {mobileApi, type MobileProfile, type MobileProfileUpdate, type MobileUserStats} from '@/api'
import {useUserStore} from '@/store/modules/user'

definePageMeta({layout: 'default', middleware: 'auth', title: 'user.center'})

const userStore = useUserStore()

const loading = ref(true)
const saving = ref(false)
const toast = useToast()
const {errors, validate, clearField, fieldProps, errorId} = useFormErrors()

const profile = ref<MobileProfile | null>(null)
const stats = ref<MobileUserStats | null>(null)

const form = reactive({bio: '', profile_picture: '', locale: '', password: ''})

onMounted(async () => {
  try {
    const [detail, summary] = await Promise.all([mobileApi.profile(), mobileApi.stats()])
    profile.value = detail
    stats.value = summary
    form.bio = detail.bio || ''
    form.profile_picture = detail.profile_picture || ''
    form.locale = detail.locale || ''
  } catch {
    toast.error(t('user.loadFailed'))
  } finally {
    loading.value = false
  }
})

async function save(): Promise<void> {
  const passed = validate({
    password: () =>
      form.password && form.password.length < 8 ? t('user.passwordMinLength') : null,
  })
  if (!passed) return

  // 只提交发生变化的字段
  const payload: MobileProfileUpdate = {}
  if (form.bio !== (profile.value?.bio || '')) payload.bio = form.bio
  if (form.profile_picture !== (profile.value?.profile_picture || '')) {
    payload.profile_picture = form.profile_picture
  }
  if (form.locale !== (profile.value?.locale || '')) payload.locale = form.locale
  if (form.password) payload.password = form.password

  if (!Object.keys(payload).length) {
    toast.info(t('user.noChanges'))
    return
  }

  saving.value = true
  try {
    profile.value = await mobileApi.updateProfile(payload)
    form.password = ''
    toast.success(t('user.saved'))
  } catch {
    toast.error(t('user.saveFailed'))
  } finally {
    saving.value = false
  }
}

async function logout(): Promise<void> {
  await userStore.logout()
  await navigateTo('/', {replace: true})
}

useSeoMeta({title: t('user.center'), robots: 'noindex'})
</script>

<template>
  <div class="mx-auto max-w-3xl px-4 py-10">
    <h1 class="text-2xl font-bold tracking-tight text-fg">{{ $t('user.center') }}</h1>

    <div v-if="loading" class="mt-6 space-y-3">
      <Skeleton class="h-24 w-full"/>
      <Skeleton class="h-64 w-full"/>
    </div>

    <template v-else>
      <!-- 概览 -->
      <Card class="mt-6">
        <CardContent class="flex flex-wrap items-center gap-5 p-5">
          <div class="flex h-14 w-14 items-center justify-center overflow-hidden rounded-pill bg-surface-soft">
            <img v-if="profile?.profile_picture" :alt="$t('user.avatar')" :src="profile.profile_picture"
                 class="h-full w-full object-cover" decoding="async" loading="lazy">
            <span v-else class="text-lg font-semibold text-fg-muted">
              {{ (profile?.username || '?').slice(0, 1).toUpperCase() }}
            </span>
          </div>

          <div class="min-w-0 flex-1">
            <p class="text-base font-semibold text-fg">{{ profile?.username }}</p>
            <p class="truncate text-sm text-fg-muted">{{ profile?.email }}</p>
          </div>

          <div class="flex gap-6">
            <div class="text-center">
              <p class="text-lg font-semibold text-fg">{{ stats?.articles ?? 0 }}</p>
              <p class="text-xs text-fg-subtle">{{ $t('user.articles') }}</p>
            </div>
            <div class="text-center">
              <p class="text-lg font-semibold text-fg">{{ stats?.comments ?? 0 }}</p>
              <p class="text-xs text-fg-subtle">{{ $t('user.comments') }}</p>
            </div>
            <div class="text-center">
              <p class="text-lg font-semibold text-fg">{{ stats?.likes_received ?? 0 }}</p>
              <p class="text-xs text-fg-subtle">{{ $t('user.likesReceived') }}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- 我的入口（认证 / 打赏收益 / 关注粉丝） -->
      <Card class="mt-5">
        <CardHeader>
          <CardTitle class="text-base">{{ $t('user.quickLinks') }}</CardTitle>
        </CardHeader>
        <CardContent class="grid gap-3 sm:grid-cols-3">
          <NuxtLink
            class="rounded-card border border-line bg-surface p-4 transition-colors hover:border-primary"
            to="/certification"
          >
            <p class="flex items-center gap-2 text-sm font-medium text-fg">
              <Icon class="h-4 w-4" name="badge-check"/>
              {{ $t('certification.title') }}
            </p>
            <p class="mt-1 text-xs text-fg-muted">{{ $t('user.quickCertificationHint') }}</p>
          </NuxtLink>
          <NuxtLink
            class="rounded-card border border-line bg-surface p-4 transition-colors hover:border-primary"
            to="/tipping"
          >
            <p class="flex items-center gap-2 text-sm font-medium text-fg">
              <Icon class="h-4 w-4" name="gift"/>
              {{ $t('tipping.title') }}
            </p>
            <p class="mt-1 text-xs text-fg-muted">{{ $t('user.quickTippingHint') }}</p>
          </NuxtLink>
          <NuxtLink
            class="rounded-card border border-line bg-surface p-4 transition-colors hover:border-primary"
            to="/fans"
          >
            <p class="flex items-center gap-2 text-sm font-medium text-fg">
              <Icon class="h-4 w-4" name="user"/>
              {{ $t('fans.title') }}
            </p>
            <p class="mt-1 text-xs text-fg-muted">{{ $t('user.quickFansHint') }}</p>
          </NuxtLink>
        </CardContent>
      </Card>

      <!-- 编辑资料 -->
      <Card class="mt-5">
        <CardHeader>
          <CardTitle class="text-base">{{ $t('user.editProfile') }}</CardTitle>
          <CardDescription>{{ $t('user.editHint') }}</CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <div>
            <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('user.avatarUrl') }}</label>
            <Input v-model="form.profile_picture" :placeholder="$t('user.avatarUrlPlaceholder')"/>
          </div>

          <div>
            <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('user.bio') }}</label>
            <textarea
              v-model="form.bio"
              class="w-full rounded-control border border-line px-3 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
              maxlength="500"
              :placeholder="$t('user.bioPlaceholder')"
              rows="3"
            />
          </div>

          <div class="grid gap-4 sm:grid-cols-2">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('user.locale') }}</label>
              <Input v-model="form.locale" :placeholder="$t('user.localePlaceholder')"/>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">{{ $t('user.newPassword') }}</label>
              <Input
                v-model="form.password"
                :placeholder="$t('user.newPasswordPlaceholder')"
                type="password"
                v-bind="fieldProps('password')"
                @input="clearField('password')"
              />
              <p v-if="errors.password" :id="errorId('password')" class="mt-1.5 text-sm text-danger">
                {{ errors.password }}
              </p>
            </div>
          </div>

          <div class="flex items-center justify-between pt-1">
            <Button variant="outline" @click="logout">
              <Icon class="h-4 w-4" name="log-out"/>
              {{ $t('user.logout') }}
            </Button>
            <Button :disabled="saving" @click="save">
              <Icon v-if="saving" class="h-4 w-4 animate-spin" name="loader-circle"/>
              <Icon v-else class="h-4 w-4" name="save"/>
              {{ $t('common.save') }}
            </Button>
          </div>
        </CardContent>
      </Card>
    </template>
  </div>
</template>
