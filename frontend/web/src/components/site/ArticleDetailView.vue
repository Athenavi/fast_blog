<script lang="ts" setup>
/**
 * 文章正文：`/articles/[slug]` 与 `/articles/id/[id]` 共用
 *
 * 阅读优先：正文限制在 `max-w-read`（约 46rem），行高与段间距放宽。
 * 正文相关样式全部基于设计令牌，因此深浅色与自定义配色会自动生效。
 *
 * **VIP 文章（`is_vip_only`）的正文不在公开详情里下发**（服务端返回 `locked: true` + 摘要），
 * 因此这里分两步：SSR 先渲染"需要 VIP"的卡片；客户端若已登录，自动调
 * `GET /mobile/article/{id}/content`（等级达标或作者本人）把正文换上去。
 */

import {mobileApi} from '@/api'
import type {ArticleDetail} from '@/types/content'
import {useUserStore} from '@/store/modules/user'

const props = defineProps<{ article: ArticleDetail }>()

const {t} = useI18n()
const userStore = useUserStore()
const publishedAt = computed(() => props.article.published_at || props.article.created_at)

const rewardOpen = ref(false)

/** 作者不能给自己打赏（后端会 400），本人文章不显示打赏按钮 */
const canReward = computed(
  () => Boolean(props.article.author_id) && props.article.author_id !== userStore.userInfo?.id,
)

// ---------------------------------------------------------------- VIP 正文
const content = ref<string>(props.article.content || '')
const locked = ref(Boolean(props.article.locked))
const loadingContent = ref(false)
const contentError = ref('')
const requiredLevel = computed(() => Math.max(props.article.required_vip_level ?? 0, 1))

async function loadGatedContent(): Promise<void> {
  if (!userStore.isLoggedIn) {
    await navigateTo('/login')
    return
  }
  loadingContent.value = true
  contentError.value = ''
  try {
    const data = await mobileApi.gatedContent(props.article.id)
    content.value = data.content || ''
    locked.value = false
  } catch (thrown) {
    contentError.value = thrown instanceof Error ? thrown.message : t('common.networkError')
  } finally {
    loadingContent.value = false
  }
}

/** 已登录的 VIP 用户不该看到"先锁后开"的闪烁，进页面就自动换正文 */
onMounted(() => {
  if (locked.value && userStore.isLoggedIn) void loadGatedContent()
})
</script>

<template>
  <article class="mx-auto max-w-read px-4 py-12">
    <header>
      <h1 class="text-2xl font-bold leading-tight tracking-tight text-fg sm:text-3xl">
        {{ props.article.title }}
      </h1>

      <div class="mt-4 flex flex-wrap items-center gap-4 text-sm text-fg-subtle">
        <span class="inline-flex items-center gap-1.5">
          <Icon class="h-4 w-4" name="calendar-days"/>
          {{ formatDate(publishedAt) }}
        </span>
        <span v-if="props.article.views" class="inline-flex items-center gap-1.5">
          <Icon class="h-4 w-4" name="eye"/>
          {{ $t('article.viewsCount', {n: props.article.views}) }}
        </span>
        <Badge v-for="tag in props.article.tags || []" :key="tag" variant="secondary">{{ tag }}</Badge>
        <Badge v-if="props.article.is_vip_only" variant="warning">
          {{ $t('vip.premiumBadge', {level: requiredLevel}) }}
        </Badge>
        <LikeButton v-if="props.article.id" :article-id="props.article.id" :initial-likes="props.article.likes ?? 0"/>
        <ClientOnly>
          <Button v-if="canReward" size="sm" variant="outline" @click="rewardOpen = true">
            <Icon class="h-4 w-4" name="gift"/>
            {{ $t('tipping.rewardAuthor') }}
          </Button>
        </ClientOnly>
      </div>
    </header>

    <img
      v-if="props.article.cover_image"
      :alt="props.article.title"
      :src="props.article.cover_image"
      class="mt-7 w-full rounded-card object-cover" decoding="async"
    >

    <!-- 需要 VIP：正文未下发 -->
    <section
      v-if="locked"
      class="mt-9 rounded-card border border-line bg-surface p-6 text-center"
    >
      <div class="flex justify-center">
        <span class="flex h-12 w-12 items-center justify-center rounded-pill bg-primary-soft text-primary">
          <Icon class="h-6 w-6" name="lock"/>
        </span>
      </div>
      <h2 class="mt-3 text-base font-semibold text-fg">{{ $t('vip.lockedTitle') }}</h2>
      <p class="mt-1.5 text-sm text-fg-muted">{{ $t('vip.lockedHint', {level: requiredLevel}) }}</p>
      <p v-if="props.article.summary" class="mx-auto mt-3 max-w-read text-sm leading-relaxed text-fg-muted">
        {{ props.article.summary }}
      </p>

      <p v-if="contentError" class="mt-3 text-sm text-danger">{{ contentError }}</p>

      <div class="mt-4 flex flex-wrap items-center justify-center gap-2">
        <Button v-if="!userStore.isLoggedIn" @click="loadGatedContent()">
          <Icon class="h-4 w-4" name="user"/>
          {{ $t('site.goLogin') }}
        </Button>
        <template v-else>
          <Button :disabled="loadingContent" variant="outline" @click="loadGatedContent()">
            <Icon v-if="loadingContent" class="h-4 w-4 animate-spin" name="loader-circle"/>
            {{ $t('vip.retryRead') }}
          </Button>
          <NuxtLink to="/vip">
            <Button>
              <Icon class="h-4 w-4" name="credit-card"/>
              {{ $t('vip.subscribe') }}
            </Button>
          </NuxtLink>
        </template>
      </div>
    </section>

    <!-- eslint-disable-next-line vue/no-v-html -- 正文来自后台编辑器 -->
    <div v-else class="prose-content mt-9" v-html="content || ('<p>' + $t('site.noContent') + '</p>')"/>

    <RewardDialog
      v-if="props.article.author_id"
      v-model="rewardOpen"
      :article-id="props.article.id"
      :author-id="props.article.author_id"
      :author-name="props.article.author_name"/>
  </article>
</template>
