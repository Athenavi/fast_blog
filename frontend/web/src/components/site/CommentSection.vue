<script lang="ts" setup>
/**
 * 文章评论区
 *
 * 此前**前台完全没有评论入口**：评论只能在后台被管理，读者无处发言。
 * 后端其实早已提供 `mobile/comment`（评论树 / 发表 / 点赞，公开读已做隐私过滤），
 * 这里把它接上。
 *
 * 几个刻意选择：
 *  - 树**展平**成一维再渲染（用缩进表示层级）——回复层级可以很深，
 *    展平比递归组件更简单可靠，也不会出现递归自引用的 SSR 问题；
 *  - 提交成功后重新拉取：新评论可能要过审才可见，所以提示"通过审核后显示"，
 *    而不是乐观插入一条其实不会出现的评论；
 *  - 未登录时保留表单位（换成登录引导），让读者知道"这里可以评论"。
 */
import {computed, onMounted, ref} from 'vue'

import {mobileApi, type MobileCommentItem} from '@/api'
import {formatDateTime} from '@/utils/format'
import {useUserStore} from '@/store/modules/user'

const props = defineProps<{ articleId: number }>()

const {t} = useI18n()
const userStore = useUserStore()

const tree = ref<MobileCommentItem[]>([])
const loading = ref(false)
const failed = ref(false)

const draft = ref('')
const submitting = ref(false)
const replyTarget = ref<{ id: number; name: string } | null>(null)
const notice = ref('')
const noticeOk = ref(true)

/** 展平评论树：`depth` 决定缩进 */
const flat = computed(() => {
  const out: Array<{ node: MobileCommentItem; depth: number }> = []
  const walk = (nodes: MobileCommentItem[], depth: number): void => {
    for (const node of nodes) {
      out.push({node, depth})
      if (node.children?.length) walk(node.children, depth + 1)
    }
  }
  walk(tree.value, 0)
  return out
})

const total = computed(() => flat.value.length)

async function load(): Promise<void> {
  loading.value = true
  failed.value = false
  try {
    tree.value = await mobileApi.commentTree(props.articleId)
  } catch {
    failed.value = true
    tree.value = []
  } finally {
    loading.value = false
  }
}

function startReply(node: MobileCommentItem): void {
  replyTarget.value = {id: node.id, name: node.author_name || String(node.user_id ?? '')}
  notice.value = ''
}

function cancelReply(): void {
  replyTarget.value = null
}

async function submit(): Promise<void> {
  const content = draft.value.trim()
  if (!content || submitting.value) return
  submitting.value = true
  notice.value = ''
  try {
    await mobileApi.createComment({
      article_id: props.articleId,
      content,
      parent_id: replyTarget.value?.id ?? null,
    })
    draft.value = ''
    replyTarget.value = null
    noticeOk.value = true
    notice.value = t('article.commentPending')
    await load()
  } catch {
    noticeOk.value = false
    notice.value = t('article.commentFailed')
  } finally {
    submitting.value = false
  }
}

/** 点赞：后端幂等切换，前端只做本地计数更新 */
async function like(node: MobileCommentItem): Promise<void> {
  if (!userStore.isLoggedIn) return
  try {
    const result = await mobileApi.likeComment(node.id)
    node.likes = result.likes ?? Math.max(0, (node.likes ?? 0) + (result.liked ? 1 : -1))
  } catch {
    /* 失败提示由 request 拦截器统一给出 */
  }
}

function maxLengthHint(): string {
  return `${draft.value.length}/5000`
}

onMounted(load)
</script>

<template>
  <section :aria-label="t('article.comments')" class="mt-14">
    <h2 class="flex items-center gap-2 text-lg font-semibold text-fg">
      <Icon class="h-4.5 w-4.5 text-fg-muted" name="message-square"/>
      {{ t('article.commentsTitle') }}
      <span v-if="total" class="text-sm font-normal text-fg-subtle">{{ t('article.commentCount', {n: total}) }}</span>
    </h2>

    <!-- 发表 -->
    <div class="mt-4 rounded-card border border-line bg-surface p-4">
      <template v-if="userStore.isLoggedIn">
        <p v-if="replyTarget" class="mb-2 flex items-center gap-2 text-xs text-fg-muted">
          {{ t('article.reply') }} @{{ replyTarget.name }}
          <button class="text-primary hover:underline" type="button" @click="cancelReply">
            {{ t('article.cancelReply') }}
          </button>
        </p>
        <textarea
          v-model="draft"
          :aria-label="t('article.commentPlaceholder')"
          :placeholder="t('article.commentPlaceholder')"
          class="w-full resize-y rounded-control border border-line bg-surface px-3 py-2 text-sm text-fg outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          maxlength="5000"
          rows="3"
        />
        <div class="mt-2 flex items-center justify-between gap-3">
          <span class="text-xs text-fg-subtle">{{ maxLengthHint() }}</span>
          <Button :disabled="submitting || !draft.trim()" size="sm" type="button" @click="submit">
            <Icon v-if="submitting" class="h-4 w-4 animate-spin" name="loader-circle"/>
            {{ submitting ? t('article.commentSubmitting') : t('article.commentSubmit') }}
          </Button>
        </div>
      </template>

      <p v-else class="flex flex-wrap items-center gap-2 text-sm text-fg-muted">
        {{ t('article.commentLoginHint') }}
        <NuxtLink class="text-primary hover:underline" to="/login">{{ t('site.goLogin') }}</NuxtLink>
      </p>

      <p v-if="notice" :class="['mt-2 text-sm', noticeOk ? 'text-success' : 'text-danger']">{{ notice }}</p>
    </div>

    <!-- 列表 -->
    <div v-if="loading && !flat.length" class="mt-5 space-y-3">
      <Skeleton v-for="i in 3" :key="i" class="h-16 w-full"/>
    </div>

    <ErrorState
      v-else-if="failed"
      :title="t('common.networkError')"
      class="mt-5"
      @retry="load"
    />

    <EmptyState v-else-if="!flat.length" :title="t('article.commentEmpty')" class="mt-5" compact/>

    <ul v-else class="mt-5 space-y-4">
      <li
        v-for="entry in flat"
        :key="entry.node.id"
        :style="{marginLeft: `${Math.min(entry.depth, 3) * 16}px`}"
        class="rounded-card border border-line bg-surface p-3.5"
      >
        <div class="flex items-center gap-2 text-xs text-fg-subtle">
          <span
            class="flex h-6 w-6 items-center justify-center rounded-pill bg-surface-soft text-[11px] font-medium text-fg-muted"
          >
            {{ (entry.node.author_name || '?').slice(0, 1).toUpperCase() }}
          </span>
          <span class="font-medium text-fg-muted">{{ entry.node.author_name || `#${entry.node.user_id ?? ''}` }}</span>
          <span>{{ formatDateTime(entry.node.created_at) }}</span>
        </div>

        <p class="mt-2 whitespace-pre-wrap break-words text-sm leading-relaxed text-fg">{{ entry.node.content }}</p>

        <div class="mt-2 flex items-center gap-3 text-xs">
          <button
            :aria-label="t('article.reply')"
            class="inline-flex items-center gap-1 text-fg-muted transition-colors hover:text-primary"
            type="button"
            @click="startReply(entry.node)"
          >
            <Icon class="h-3.5 w-3.5" name="arrow-right"/>
            {{ t('article.reply') }}
          </button>
          <button
            :aria-label="$t('article.likes')"
            :disabled="!userStore.isLoggedIn"
            class="inline-flex items-center gap-1 text-fg-muted transition-colors hover:text-primary disabled:cursor-not-allowed disabled:opacity-60"
            type="button"
            @click="like(entry.node)"
          >
            <Icon class="h-3.5 w-3.5" name="heart"/>
            {{ entry.node.likes ?? 0 }}
          </button>
        </div>
      </li>
    </ul>
  </section>
</template>
