<script lang="ts" setup>
/**
 * 文章草稿预览（公开端点，无鉴权）
 *
 * 路由：`/articles/preview/{token}`。持有作者签发的预览令牌即可读取该文章
 * **未发布**的草稿内容（`GET /content/article/public/preview/{token}`）。
 *
 * 后端对「令牌不存在 / 已过期 / 口令错误 / 文章已删」一律返回同一句文案，
 * 因此页面无法区分失败原因：首次不带口令请求，若失败则给出可选的口令重试入口。
 * 口令走请求头 `X-Preview-Password`（后端契约，避免出现在 URL 与访问日志）。
 *
 * 不复用 `ArticleDetailView`：它带有 VIP 解锁、点赞、评论、浏览量上报等前台互动，
 * 而预览返回的是后端白名单字段（不含 likes / author_id 等），且草稿不应触发这些副作用。
 */
import {formatDateTime} from '@/utils/format'

const {t} = useI18n()
const route = useRoute()
const token = String(route.params.token)

interface PreviewArticle {
  id: number
  title?: string | null
  slug?: string | null
  excerpt?: string | null
  cover_image?: string | null
  category?: number | null
  tags?: string[]
  content?: string | null
  language_code?: string | null
  status?: number | null
  published_at?: string | null
  created_at?: string | null
  updated_at?: string | null
}

interface PreviewMeta {
  view_count?: number | null
  max_views?: number | null
  expires_at?: string | null
}

interface PreviewEnvelope {
  code: number
  msg: string
  data: { article: PreviewArticle; preview: PreviewMeta }
}

const article = ref<PreviewArticle | null>(null)
const meta = ref<PreviewMeta | null>(null)
const loading = ref(true)
const failed = ref(false)
const password = ref('')

async function loadPreview(): Promise<void> {
  loading.value = true
  failed.value = false
  try {
    const resp = await $fetch<PreviewEnvelope>(
      `${API_PREFIX}/content/article/public/preview/${encodeURIComponent(token)}`,
      {
        headers: password.value ? {'X-Preview-Password': password.value} : undefined,
        credentials: 'omit',
      },
    )
    if (resp?.code === CODE_SUCCESS) {
      article.value = resp.data.article
      meta.value = resp.data.preview
      return
    }
    failed.value = true
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}

await loadPreview()

useSeoMeta({
  title: () => article.value?.title || t('article.preview.badge'),
  robots: 'noindex, nofollow',
})
</script>

<template>
  <div class="mx-auto max-w-read px-4 py-10">
    <p v-if="loading" class="py-16 text-center text-fg-subtle">
      {{ $t('article.preview.loading') }}
    </p>

    <article v-else-if="article">
      <div class="flex flex-wrap items-center gap-2">
        <Badge variant="warning">{{ $t('article.preview.badge') }}</Badge>
        <span class="text-xs text-fg-subtle">{{ $t('article.preview.toolbar') }}</span>
      </div>

      <h1 class="mt-4 text-2xl font-bold leading-tight tracking-tight text-fg sm:text-3xl">
        {{ article.title }}
      </h1>

      <div v-if="meta" class="mt-3 flex flex-wrap items-center gap-3 text-sm text-fg-subtle">
        <span>{{ $t('article.preview.views', {n: meta.view_count ?? 0}) }}</span>
        <span v-if="meta.max_views">{{ $t('article.preview.maxViews', {n: meta.max_views}) }}</span>
        <span v-if="meta.expires_at">
          {{ $t('article.preview.expiresAt', {time: formatDateTime(meta.expires_at)}) }}
        </span>
      </div>

      <img
        v-if="article.cover_image"
        :alt="article.title || ''"
        :src="article.cover_image"
        class="mt-7 w-full rounded-card object-cover" decoding="async"
      >

      <p v-if="article.excerpt" class="mt-5 text-base leading-relaxed text-fg-muted">
        {{ article.excerpt }}
      </p>

      <div
        class="prose-content mt-9"
        v-html="article.content || ('<p>' + $t('site.noContent') + '</p>')"
      />

      <div v-if="article.tags && article.tags.length" class="mt-6 flex flex-wrap gap-2">
        <Badge v-for="tag in article.tags" :key="tag" variant="secondary">{{ tag }}</Badge>
      </div>
    </article>

    <div v-else class="rounded-card border border-line bg-surface p-8 text-center">
      <h1 class="text-lg font-semibold text-fg">{{ $t('article.preview.invalidTitle') }}</h1>
      <p class="mt-2 text-sm text-fg-muted">{{ $t('article.preview.invalidDesc') }}</p>

      <div class="mx-auto mt-5 max-w-sm text-left">
        <label class="text-xs text-fg-subtle">{{ $t('article.preview.passwordLabel') }}</label>
        <input
          v-model="password"
          :placeholder="$t('article.preview.passwordPlaceholder')"
          class="mt-1 w-full rounded-control border border-line bg-surface px-3 py-2 text-sm text-fg"
          type="password"
        >
        <Button class="mt-3 w-full" @click="loadPreview">
          {{ $t('article.preview.retry') }}
        </Button>
      </div>
    </div>
  </div>
</template>
