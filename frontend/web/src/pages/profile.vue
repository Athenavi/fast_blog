<script lang="ts" setup>
/**
 * 个人中心
 *
 * 使用 v3 的 `mobile/user` 域：资料读写与统计。
 * 该页依赖登录态（存于本地存储），在 `nuxt.config.ts` 中已设为 `ssr: false`，
 * 并由 `middleware: 'auth'` 负责未登录时跳转登录页。
 */

import {mobileApi, type MobileProfile, type MobileProfileUpdate, type MobileUserStats} from '@/api'
import {useUserStore} from '@/store/modules/user'

definePageMeta({layout: 'default', middleware: 'auth', title: '个人中心'})

const userStore = useUserStore()

const loading = ref(true)
const saving = ref(false)
const message = ref('')
const error = ref('')

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
    error.value = '加载个人资料失败，请稍后重试'
  } finally {
    loading.value = false
  }
})

async function save(): Promise<void> {
  message.value = ''
  error.value = ''

  if (form.password && form.password.length < 8) {
    error.value = '新密码至少 8 位'
    return
  }

  // 只提交发生变化的字段
  const payload: MobileProfileUpdate = {}
  if (form.bio !== (profile.value?.bio || '')) payload.bio = form.bio
  if (form.profile_picture !== (profile.value?.profile_picture || '')) {
    payload.profile_picture = form.profile_picture
  }
  if (form.locale !== (profile.value?.locale || '')) payload.locale = form.locale
  if (form.password) payload.password = form.password

  if (!Object.keys(payload).length) {
    message.value = '没有需要保存的改动'
    return
  }

  saving.value = true
  try {
    profile.value = await mobileApi.updateProfile(payload)
    form.password = ''
    message.value = '已保存'
  } catch {
    error.value = '保存失败，请稍后重试'
  } finally {
    saving.value = false
  }
}

async function logout(): Promise<void> {
  await userStore.logout()
  await navigateTo('/', {replace: true})
}

useSeoMeta({title: '个人中心', robots: 'noindex'})
</script>

<template>
  <div class="mx-auto max-w-3xl px-4 py-10">
    <h1 class="text-2xl font-bold tracking-tight text-fg">个人中心</h1>

    <div v-if="loading" class="mt-6 space-y-3">
      <Skeleton class="h-24 w-full"/>
      <Skeleton class="h-64 w-full"/>
    </div>

    <template v-else>
      <!-- 概览 -->
      <Card class="mt-6">
        <CardContent class="flex flex-wrap items-center gap-5 p-5">
          <div class="flex h-14 w-14 items-center justify-center overflow-hidden rounded-pill bg-surface-soft">
            <img v-if="profile?.profile_picture" :src="profile.profile_picture" alt="头像"
                 class="h-full w-full object-cover">
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
              <p class="text-xs text-fg-subtle">文章</p>
            </div>
            <div class="text-center">
              <p class="text-lg font-semibold text-fg">{{ stats?.comments ?? 0 }}</p>
              <p class="text-xs text-fg-subtle">评论</p>
            </div>
            <div class="text-center">
              <p class="text-lg font-semibold text-fg">{{ stats?.likes_received ?? 0 }}</p>
              <p class="text-xs text-fg-subtle">获赞</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- 编辑资料 -->
      <Card class="mt-5">
        <CardHeader>
          <CardTitle class="text-base">编辑资料</CardTitle>
          <CardDescription>用户名与邮箱不可自助修改，其余字段可直接保存。</CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <div>
            <label class="mb-1.5 block text-sm font-medium text-fg">头像地址</label>
            <Input v-model="form.profile_picture" placeholder="https://…（留空表示无头像）"/>
          </div>

          <div>
            <label class="mb-1.5 block text-sm font-medium text-fg">个人简介</label>
            <textarea
              v-model="form.bio"
              class="w-full rounded-control border border-line px-3 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
              maxlength="500"
              placeholder="介绍一下自己（最多 500 字）"
              rows="3"
            />
          </div>

          <div class="grid gap-4 sm:grid-cols-2">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">界面语言</label>
              <Input v-model="form.locale" placeholder="如 zh-CN"/>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-fg">新密码</label>
              <Input v-model="form.password" placeholder="留空表示不修改（至少 8 位）" type="password"/>
            </div>
          </div>

          <p v-if="error" class="rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">{{ error }}</p>
          <p v-else-if="message" class="rounded-control bg-success-soft px-3 py-2 text-sm text-success">
            {{ message }}
          </p>

          <div class="flex items-center justify-between pt-1">
            <Button variant="outline" @click="logout">
              <Icon class="h-4 w-4" name="log-out"/>
              退出登录
            </Button>
            <Button :disabled="saving" @click="save">
              <Icon v-if="saving" class="h-4 w-4 animate-spin" name="loader-circle"/>
              <Icon v-else class="h-4 w-4" name="save"/>
              保存
            </Button>
          </div>
        </CardContent>
      </Card>
    </template>
  </div>
</template>
