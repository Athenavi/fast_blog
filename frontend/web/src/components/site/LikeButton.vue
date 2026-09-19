<script lang="ts" setup>
/**
 * 文章点赞按钮（T4-9 / §16.2）
 *
 * 数据源：v3 `mobile/article/{id}/like`（per-user 幂等切换）与
 * `/{id}/like/status`（匿名可查）。原 astro 实现是 `plugins/article-likes`
 * 的 React 组件；当时 v2 动作端点仅超管可调、对普通读者必然 403，
 * 因此这是该能力第一次真正可用。
 *
 * 与原版差异：
 *  - 未登录不再隐藏按钮，点击跳登录页（原版直接 return null）；
 *  - 配色全部走语义令牌（原版硬编码 red-* / gray-*）；
 *  - 状态请求在 mounted 后进行（SSR 首屏用服务端下发的 likes 计数）。
 */
import {storeToRefs} from 'pinia'

import {mobileApi} from '@/api'
import {useUserStore} from '@/store/modules/user'

const props = defineProps<{
  articleId: number
  /** SSR 下发的点赞计数，客户端拿到最新状态前先展示它 */
  initialLikes?: number
}>()

const {t} = useI18n()
const userStore = useUserStore()
const {isLoggedIn} = storeToRefs(userStore)

const liked = ref(false)
const count = ref(props.initialLikes ?? 0)
const busy = ref(false)

onMounted(async () => {
  try {
    const status = await mobileApi.likeStatus(props.articleId)
    liked.value = status.liked
    count.value = status.likes
  } catch {
    /* 状态拉取失败不阻塞阅读，保持服务端计数 */
  }
})

async function onClick() {
  if (busy.value) return
  if (!isLoggedIn.value) {
    await navigateTo('/login')
    return
  }
  busy.value = true
  try {
    const status = await mobileApi.toggleLike(props.articleId)
    liked.value = status.liked
    count.value = status.likes
  } catch {
    /* 失败静默：计数以服务端下一次拉取为准 */
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <button
    :class="liked
      ? 'border-danger bg-danger-soft text-danger'
      : 'border-line text-fg-muted hover:border-danger hover:text-danger'"
    :disabled="busy"
    class="inline-flex items-center gap-1.5 rounded-control border px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50"
    type="button"
    @click="onClick"
  >
    <Icon :class="liked ? 'fill-current' : ''" class="h-4 w-4" name="heart"/>
    <span>{{ count > 0 ? count : (liked ? t('article.liked') : t('article.likes')) }}</span>
  </button>
</template>
