<script lang="ts" setup>
/**
 * 文章正文：`/articles/[slug]` 与 `/articles/id/[id]` 共用
 *
 * 版式：简报体（editorial）。正文宽度由 `--read-measure` 决定（默认 46rem，读者可切宽/切字号），
 * 标题区是「栏目眉 + 大号衬线标题 + 署名行 + 一条 2px 粗线」，小节自己编号（CSS counter，
 * 见 styles/index.css 的 `.prose--editorial`），宽屏右侧留一条粘性的目录轨。
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

import {mobileApi} from '@/api/public'
import type {ArticleDetail, ArticleItem} from '@/types/content'
import {estimateReadingMinutes, renderArticleBody, type TocHeading} from '@/utils/article-body'
import {FONT_SIZES, useReadingPrefs, WIDTHS} from '@/composables/useReadingPrefs'
import {useUserStore} from '@/store/modules/user'
import {formatDate} from '@/utils/format'

const props = defineProps<{ article: ArticleDetail }>()

const {t} = useI18n()
const userStore = useUserStore()
const {fontSize, width, setSize, setWidth} = useReadingPrefs()
const publishedAt = computed(() => props.article.published_at || props.article.created_at)

// ---------------------------------------------------------------- 标题区
/**
 * 栏目眉：正文没有分类名（详情接口只给 `category_id`），第一个标签是最贴近"这一篇属于哪一栏"的信息。
 * 它已经出现在眉位，标签行里就不再重复一次。
 */
const kicker = computed(() => (props.article.tags?.[0] ?? '').trim())
const tagList = computed(() => props.article.tags ?? [])
const kickerTags = computed(() => (kicker.value ? tagList.value.slice(1) : tagList.value))

/** 阅读时长（估算法则与理由见 `utils/article-body.ts`） */
const readingMinutes = computed(() => estimateReadingMinutes(content.value))

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

/**
 * 正文 HTML 与目录：锚点与首段标记都在渲染前由纯字符串处理完成（见 `utils/article-body.ts`），
 * 所以 SSR 首屏就带锚点，读者复制出去的 `#小节` 链接能直接落地。
 */
const processed = computed(() => renderArticleBody(content.value))

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
 *
 * ## 为什么高亮要**等代码块进入视口**才做
 *
 * 原先挂载时对**全文所有** `<pre>` 逐个 `hljs.highlightElement()`。博客正文里
 * 十几个代码块是常态，每个都要重新切词、构建 DOM 片段并把整段 innerHTML 换掉 ——
 * 这是一串**同步的长任务**，全部压在首屏水合之后，正好落在 Interaction to Next Paint
 * 的采样窗口里：读者点开文章想滚动/点按钮时会感到明显卡顿，而这十几个代码块里
 * 往往只有第一个是可见的。
 *
 * 现在：复制按钮照旧立刻挂（纯 DOM 追加，代价可忽略，用户随时可能去点），
 * 高亮交给 `IntersectionObserver`，提前 400px 预热 —— 滚动到之前就已经着色完毕，
 * 看不到"先黑后彩"的闪烁。
 *
 * 顺带把 highlight.js 的下载时机也推迟了：没有代码块进入视口，这一包就永远不下载。
 */
type Highlighter = { highlightElement: (el: HTMLElement) => void }

/** highlight.js 只下载一次（动态 import 本身有缓存，这里再兜一层避免并发重复） */
let highlighterPromise: Promise<Highlighter> | null = null

function loadHighlighter(): Promise<Highlighter> {
  highlighterPromise ??= import('@/lib/highlight').then((mod) => mod.hljs as Highlighter)
  return highlighterPromise
}

/** 视口观察器：进入视口的代码块交给 highlight.js，之后不再观察 */
let blockObserver: IntersectionObserver | null = null

async function highlightBlocks(blocks: HTMLElement[]): Promise<void> {
  const hljs = await loadHighlighter()
  blocks.forEach((pre) => {
    pre.querySelectorAll<HTMLElement>('code').forEach((node) => {
      if (node.dataset.highlighted !== 'yes') hljs.highlightElement(node)
    })
  })
}

/** 给代码块挂"复制"按钮（幂等：重复调用不会挂第二个） */
function attachCopyButton(pre: HTMLElement): void {
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
}

async function enhanceCodeBlocks(): Promise<void> {
  if (!import.meta.client) return
  const blocks = Array.from(document.querySelectorAll<HTMLElement>('.prose-content pre'))
  if (!blocks.length) return

  blocks.forEach(attachCopyButton)

  const pending = blocks.filter((pre) => pre.querySelector('code[data-highlighted="yes"]') === null)
  if (!pending.length) return

  // 环境不支持 IntersectionObserver（或 SSR 预渲染的极简浏览器）：退回一次性高亮
  if (typeof IntersectionObserver === 'undefined') {
    await highlightBlocks(pending)
    return
  }

  blockObserver?.disconnect()
  blockObserver = new IntersectionObserver(
    (entries) => {
      const entered = entries
        .filter((entry) => entry.isIntersecting)
        .map((entry) => entry.target as HTMLElement)
      if (!entered.length) return
      entered.forEach((pre) => blockObserver?.unobserve(pre))
      void highlightBlocks(entered)
    },
    // 提前 400px 预热：滚到之前就着色完，避免"先黑后彩"
    {rootMargin: '400px 0px'},
  )
  pending.forEach((pre) => blockObserver?.observe(pre))
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
  blockObserver?.disconnect()
  blockObserver = null
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

    <div class="fb-page-shell px-4 py-10">
      <header class="masthead">
        <div class="masthead__top">
          <p class="masthead__kicker">{{ kicker || $t('article.kickerFallback') }}</p>

          <div class="masthead__tools">
            <LikeButton v-if="props.article.id" :article-id="props.article.id"
                        :initial-likes="props.article.likes ?? 0"/>

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
                    v-for="option in FONT_SIZES"
                    :key="option.value"
                    :aria-pressed="fontSize === option.value"
                    :class="['reading-settings__chip', fontSize === option.value ? 'is-active' : '']"
                    type="button"
                    @click="setSize(option.value)"
                  >
                    {{ $t(`article.${option.label}`) }}
                  </button>
                </div>

                <p class="reading-settings__label">{{ $t('article.lineWidth') }}</p>
                <div class="reading-settings__row">
                  <button
                    v-for="option in WIDTHS"
                    :key="option.value"
                    :aria-pressed="width === option.value"
                    :class="['reading-settings__chip', width === option.value ? 'is-active' : '']"
                    type="button"
                    @click="setWidth(option.value)"
                  >
                    {{ $t(`article.${option.label}`) }}
                  </button>
                </div>
              </div>
            </details>

            <span v-if="shareNotice" class="masthead__notice">{{ shareNotice }}</span>
          </div>
        </div>

        <h1 class="masthead__title">{{ props.article.title }}</h1>

        <p class="masthead__byline">
          <span v-if="props.article.author_name">{{ props.article.author_name }}</span>
          <span>{{ formatDate(publishedAt) }}</span>
          <span>{{ $t('article.readingMinutes', {n: readingMinutes}) }}</span>
          <span v-if="props.article.views">{{ $t('article.viewsCount', {n: props.article.views}) }}</span>
        </p>

        <p v-if="kickerTags.length || props.article.is_vip_only" class="masthead__tags">
          <Badge v-for="tag in kickerTags" :key="tag" variant="secondary">{{ tag }}</Badge>
          <Badge v-if="props.article.is_vip_only" variant="warning">
            {{ $t('vip.premiumBadge', {level: requiredLevel}) }}
          </Badge>
        </p>

        <!-- 2px 粗线：简报体的"刊头下沿"，把标题区与正文一次性分开 -->
        <div aria-hidden="true" class="masthead__rule"/>
      </header>

      <!-- 正文封面就是本文的 LCP 元素：走变体 + 高优先级，不做淡入（见 ResponsiveImage） -->
      <ResponsiveImage
        v-if="props.article.cover_image"
        :alt="props.article.title"
        :src="props.article.cover_image"
        class="mt-7 w-full rounded-card"
        eager
        sizes="xs:100vw md:736px"
      ></ResponsiveImage>

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
        <!-- 正文 + 目录轨：宽屏两栏（正文列宽 = `--read-measure`，轨 15.5rem 粘性）；
             窄屏折成上下两段，目录落在正文之前（见 ArticleToc 的折叠） -->
        <div :class="['article-body mt-9', processed.headings.length ? 'article-body--toc' : '']">
          <div
            class="prose-content prose--editorial min-w-0"
            @click="onContentClick"
            v-html="processed.html || ('<p>' + $t('site.noContent') + '</p>')"
          />

          <aside v-if="processed.headings.length" class="article-body__rail">
            <ArticleToc :headings="processed.headings"/>
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
/* ---------------- 标题区（刊头） ---------------- */
.masthead__top {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  align-items: center;
  justify-content: space-between;
}

/* 眉位：等宽 + 字距拉开，明确"这是栏目，不是标题的一部分" */
.masthead__kicker {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-primary);
  text-transform: uppercase;
  letter-spacing: 0.18em;
}

.masthead__tools {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.masthead__notice {
  font-size: 0.75rem;
  color: var(--color-success);
}

.masthead__title {
  margin: 1.25rem 0 0;
  font-family: var(--font-serif);
  font-size: clamp(1.75rem, 1.2rem + 2.2vw, 2.75rem);
  font-weight: 600;
  line-height: 1.22;
  color: var(--color-fg);
  letter-spacing: -0.015em;
  text-wrap: balance;
}

.masthead__byline {
  display: flex;
  flex-wrap: wrap;
  margin: 0.75rem 0 0;
  font-family: var(--font-sans);
  font-size: 0.8125rem;
  color: var(--color-fg-muted);
}

/* 分隔点写在 CSS 上，而不是夹在文本里：某一项 v-if 掉了不会留下多余的一个「·」 */
.masthead__byline > span + span::before {
  margin: 0 0.45rem;
  color: var(--color-line-strong);
  content: '·';
}

.masthead__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
  margin: 0.75rem 0 0;
}

.masthead__rule {
  margin-top: 1.25rem;
  border-top: 2px solid var(--color-fg);
}

/* ---------------- 正文 + 目录轨 ----------------
 * 窄屏：折成上下两段，目录用 order 提到正文之前（DOM 顺序仍是正文在前，
 * 这样读屏与打印都先读到内容）。
 */
.article-body--toc {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.article-body__rail {
  order: -1;
}

@media (min-width: 1024px) {
  .article-body--toc {
    display: grid;
    grid-template-columns: minmax(0, var(--read-measure, 46rem)) 15.5rem;
    gap: 2.5rem;
    align-items: start;
  }

  .article-body__rail {
    position: sticky;
    top: 5rem;
    order: 0;
  }
}

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
