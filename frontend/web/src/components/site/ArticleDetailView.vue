<script lang="ts" setup>
/**
 * 文章正文：`/articles/[slug]` 与 `/articles/id/[id]` 共用
 *
 * 阅读优先：正文限制在 `max-w-read`（约 46rem，读者可切宽/切字号），行高与段间距放宽。
 * 正文相关样式全部基于设计令牌，因此深浅色与自定义配色会自动生效。
 *
 * **VIP 文章（`is_vip_only`）的正文不在公开详情里下发**（服务端返回 `locked: true` + 摘要），
 * 因此这里分两步：SSR 先渲染"需要 VIP"的卡片；客户端若已登录，自动调
 * `GET /mobile/article/{id}/content`（等级达标或作者本人）把正文换上去。
 *
 * 阅读增强（此前完全没有）：阅读进度、目录、字号/行宽、分享、正文图片查看、
 * 代码复制、相关文章、评论区。标题 id 与目录在**渲染前**由 HTML 字符串处理出来，
 * 所以 SSR 输出就带锚点，分享出去的链接可以直接定位到小节。
 */
import {computed, nextTick, onBeforeUnmount, onMounted, ref, watch} from 'vue'

import {mobileApi} from '@/api'
import type {ArticleItem} from '@/types/content'
import type {ArticleDetail} from '@/types/content'
import {useReadingPrefs} from '@/composables/useReadingPrefs'
import {useUserStore} from '@/store/modules/user'
import {formatDate} from '@/utils/format'

interface TocHeading {
  id: string
  text: string
  level: number
}

const props = defineProps<{ article: ArticleDetail }>()

const {t} = useI18n()
const userStore = useUserStore()
const {fontSize, width, fontSizeClass, widthClass} = useReadingPrefs()
const publishedAt = computed(() => props.article.published_at || props.article.created_at)

/** 阅读设置的选项声明（放在 script 里，模板只负责渲染与调用 setter） */
const FONT_OPTIONS: Array<{ key: 'sm' | 'md' | 'lg'; label: string }> = [
  {key: 'sm', label: 'fontSmall'},
  {key: 'md', label: 'fontMedium'},
  {key: 'lg', label: 'fontLarge'},
]
const WIDTH_OPTIONS: Array<{ key: 'narrow' | 'wide'; label: string }> = [
  {key: 'narrow', label: 'widthNarrow'},
  {key: 'wide', label: 'widthWide'},
]

function setFontSize(key: 'sm' | 'md' | 'lg'): void {
  fontSize.value = key
}

function setWidth(key: 'narrow' | 'wide'): void {
  width.value = key
}

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

// ---------------------------------------------------------------- 目录与锚点
function slugify(text: string): string {
  const slug = text
    .toLowerCase()
    .replace(/[^\w\u4e00-\u9fff]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40)
  return slug || 'section'
}

/**
 * 给 h2/h3 注入稳定 id 并抽取目录。
 * 纯字符串处理（不用 DOM API），所以 SSR 阶段就能产出带锚点的 HTML。
 */
const processed = computed<{ html: string; headings: TocHeading[] }>(() => {
  const headings: TocHeading[] = []
  const html = (content.value || '').replace(
    /<h([23])\b([^>]*)>([\s\S]*?)<\/h\1>/gi,
    (match, level: string, attrs: string, inner: string) => {
      const text = String(inner)
        .replace(/<[^>]*>/g, '')
        .trim()
      if (!text) return match
      const existing = /\sid="([^"]+)"/.exec(String(attrs))?.[1]
      const id = existing ?? `sec-${headings.length + 1}-${slugify(text)}`
      headings.push({id, text, level: Number(level)})
      return existing ? match : `<h${level}${attrs} id="${id}">${inner}</h${level}>`
    },
  )
  return {html, headings}
})

// ---------------------------------------------------------------- 阅读进度
const progress = ref(0)

function onScroll(): void {
  if (!import.meta.client) return
  const doc = document.documentElement
  const total = doc.scrollHeight - doc.clientHeight
  progress.value = total > 0 ? Math.min(100, Math.max(0, (doc.scrollTop / total) * 100)) : 0
}

// ---------------------------------------------------------------- 分享
const shareNotice = ref('')

async function share(): Promise<void> {
  if (!import.meta.client) return
  const url = window.location.href
  // 优先用系统分享（移动端体验最好），不可用时回退到复制链接
  const nav = navigator as Navigator & { share?: (data: { title?: string; url?: string }) => Promise<void> }
  if (typeof nav.share === 'function') {
    try {
      await nav.share({title: props.article.title ?? '', url})
      return
    } catch {
      /* 用户取消或平台不支持：继续走复制 */
    }
  }
  try {
    await navigator.clipboard.writeText(url)
    shareNotice.value = t('article.linkCopied')
    window.setTimeout(() => {
      shareNotice.value = ''
    }, 2000)
  } catch {
    shareNotice.value = url
  }
}

// ---------------------------------------------------------------- 正文图片查看
const lightboxIndex = ref<number | null>(null)

const contentImages = computed(() =>
  Array.from(processed.value.html.matchAll(/<img[^>]+src="([^"]+)"/gi)).map((match) => match[1] ?? ''),
)

function onContentClick(event: MouseEvent): void {
  const target = event.target as HTMLElement | null
  if (!target || target.tagName !== 'IMG') return
  const src = (target as HTMLImageElement).src
  const index = contentImages.value.findIndex((url) => src.includes(url) || url.includes(src))
  lightboxIndex.value = index >= 0 ? index : 0
}

// ---------------------------------------------------------------- 代码高亮 + 复制
/**
 * SSR 出来的 `<pre><code class="language-xxx">` 是纯文本，挂载后按语言着色；
 * 同时给每个代码块挂一个"复制"按钮（此前只能手动选中）。
 */
async function enhanceCodeBlocks(): Promise<void> {
  if (!import.meta.client) return
  const blocks = document.querySelectorAll<HTMLElement>('.prose-content pre')
  if (!blocks.length) return

  const {hljs} = await import('@/lib/highlight')
  blocks.forEach((pre) => {
    pre.querySelectorAll<HTMLElement>('code').forEach((node) => {
      if (node.dataset.highlighted !== 'yes') hljs.highlightElement(node)
    })
    if (pre.dataset.copyAttached === 'yes') return
    pre.dataset.copyAttached = 'yes'
    const button = document.createElement('button')
    button.type = 'button'
    button.className = 'code-copy'
    button.textContent = t('article.copyCode')
    button.addEventListener('click', () => {
      const code = pre.querySelector('code')?.textContent ?? ''
      void navigator.clipboard.writeText(code).then(() => {
        button.textContent = t('article.codeCopied')
        window.setTimeout(() => {
          button.textContent = t('article.copyCode')
        }, 1800)
      })
    })
    pre.appendChild(button)
  })
}

// ---------------------------------------------------------------- 相关文章
const related = ref<ArticleItem[]>([])

async function loadRelated(): Promise<void> {
  if (!props.article.id) return
  try {
    const result = await apiPage<ArticleItem>('/content/article/public/list', {
      page: 1,
      page_size: 6,
      ...(props.article.category_id ? {category_id: props.article.category_id} : {}),
    })
    related.value = result.items.filter((item) => item.id !== props.article.id).slice(0, 4)
  } catch {
    related.value = []
  }
}

/** 已登录的 VIP 用户不该看到"先锁后开"的闪烁，进页面就自动换正文 */
onMounted(() => {
  if (locked.value && userStore.isLoggedIn) void loadGatedContent()
  void nextTick(enhanceCodeBlocks)
  void loadRelated()
  onScroll()
  window.addEventListener('scroll', onScroll, {passive: true})
})

onBeforeUnmount(() => {
  if (import.meta.client) window.removeEventListener('scroll', onScroll)
})

watch(content, () => void nextTick(enhanceCodeBlocks))
</script>

<template>
  <article class="relative">
    <!-- 阅读进度：贴在顶栏下方的一条细线 -->
    <div
      :style="{width: `${progress}%`}"
      aria-hidden="true"
      class="fixed left-0 top-14 z-30 h-0.5 bg-primary transition-[width] duration-150"
    />

    <div :class="['mx-auto px-4 py-10', widthClass]">
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
        </div>

        <div class="mt-4 flex flex-wrap items-center gap-2">
          <LikeButton v-if="props.article.id" :article-id="props.article.id" :initial-likes="props.article.likes ?? 0"/>

          <ClientOnly>
            <Button v-if="canReward" size="sm" variant="outline" @click="rewardOpen = true">
              <Icon class="h-4 w-4" name="gift"/>
              {{ $t('tipping.rewardAuthor') }}
            </Button>
          </ClientOnly>

          <!-- 分享 -->
          <Button :aria-label="$t('article.share')" size="sm" variant="outline" @click="share">
            <Icon class="h-4 w-4" name="share"/>
            {{ $t('article.share') }}
          </Button>

          <!-- 阅读设置：用原生 details 实现，零额外 JS 与依赖 -->
          <details class="reading-settings">
            <summary class="reading-settings__summary">
              <Icon class="h-4 w-4" name="type"/>
              {{ $t('article.readingSettings') }}
            </summary>
            <div class="reading-settings__panel">
              <p class="reading-settings__label">{{ $t('article.fontSize') }}</p>
              <div class="reading-settings__row">
                <button
                  v-for="option in FONT_OPTIONS"
                  :key="option.key"
                  :aria-pressed="fontSize === option.key"
                  :class="['reading-settings__chip', fontSize === option.key ? 'is-active' : '']"
                  type="button"
                  @click="setFontSize(option.key)"
                >
                  {{ $t(`article.${option.label}`) }}
                </button>
              </div>

              <p class="reading-settings__label">{{ $t('article.lineWidth') }}</p>
              <div class="reading-settings__row">
                <button
                  v-for="option in WIDTH_OPTIONS"
                  :key="option.key"
                  :aria-pressed="width === option.key"
                  :class="['reading-settings__chip', width === option.key ? 'is-active' : '']"
                  type="button"
                  @click="setWidth(option.key)"
                >
                  {{ $t(`article.${option.label}`) }}
                </button>
              </div>
            </div>
          </details>

          <span v-if="shareNotice" class="text-xs text-success">{{ shareNotice }}</span>
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

      <template v-else>
        <!-- 正文 + 目录：宽屏两栏，窄屏目录在前 -->
        <div :class="['mt-9 gap-8', processed.headings.length ? 'lg:grid lg:grid-cols-[minmax(0,1fr)_13rem]' : '']">
          <div
            :class="fontSizeClass"
            class="prose-content min-w-0"
            @click="onContentClick"
            v-html="processed.html || ('<p>' + $t('site.noContent') + '</p>')"
          />

          <aside v-if="processed.headings.length" class="order-first mb-6 lg:order-none lg:mb-0">
            <div class="lg:sticky lg:top-20">
              <ArticleToc :headings="processed.headings"/>
            </div>
          </aside>
        </div>

        <!-- 相关文章 -->
        <section v-if="related.length" class="mt-14">
          <h2 class="text-lg font-semibold text-fg">{{ $t('article.related') }}</h2>
          <ul class="mt-4 grid gap-4 sm:grid-cols-2">
            <li v-for="item in related" :key="item.id">
              <NuxtLink
                :to="item.slug ? `/articles/${item.slug}` : `/articles/id/${item.id}`"
                class="flex gap-3 rounded-card border border-line bg-surface p-3 transition-colors hover:border-line-strong"
              >
                <span class="min-w-0 flex-1">
                  <span class="block truncate text-sm font-medium text-fg">{{ item.title }}</span>
                  <span class="mt-1 block text-xs text-fg-subtle">
                    {{ formatDate(item.published_at || item.created_at) }}
                  </span>
                </span>
              </NuxtLink>
            </li>
          </ul>
        </section>

        <!-- 评论区（此前前台完全没有入口） -->
        <CommentSection :article-id="props.article.id"/>
      </template>
    </div>

    <ImageLightbox v-model:index="lightboxIndex" :images="contentImages"/>

    <RewardDialog
      v-if="props.article.author_id"
      v-model="rewardOpen"
      :article-id="props.article.id"
      :author-id="props.article.author_id"
      :author-name="props.article.author_name"/>
  </article>
</template>

<style scoped>
.reading-settings {
  position: relative;
}

.reading-settings__summary {
  display: inline-flex;
  gap: 0.375rem;
  align-items: center;
  height: 2rem;
  padding: 0 0.75rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-fg);
  list-style: none;
  cursor: pointer;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-control);
}

.reading-settings__summary::-webkit-details-marker {
  display: none;
}

.reading-settings__panel {
  position: absolute;
  right: 0;
  z-index: 20;
  width: 13rem;
  padding: 0.75rem;
  margin-top: 0.5rem;
  background: var(--color-surface);
  border: 1px solid var(--color-line);
  border-radius: var(--radius-card);
  box-shadow: 0 10px 30px rgb(15 23 42 / 12%);
}

.reading-settings__label {
  margin: 0 0 0.375rem;
  font-size: 0.75rem;
  color: var(--color-fg-subtle);
}

.reading-settings__row {
  display: flex;
  gap: 0.375rem;
  margin-bottom: 0.625rem;
}

.reading-settings__chip {
  flex: 1;
  padding: 0.25rem 0.5rem;
  font-size: 0.8125rem;
  color: var(--color-fg-muted);
  cursor: pointer;
  background: var(--color-surface-soft);
  border: 1px solid transparent;
  border-radius: var(--radius-control);
}

.reading-settings__chip.is-active {
  font-weight: 500;
  color: var(--color-primary);
  border-color: var(--color-primary);
}
</style>
