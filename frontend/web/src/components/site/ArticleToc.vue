<script lang="ts" setup>
/**
 * 文章目录（TOC）
 *
 * 长文的第一需求是"能在小节之间跳"。这里只做一件事：把 `h2/h3` 渲染成目录，
 * 并跟随滚动高亮当前小节。
 *
 * 为什么用滚动位置而不是 IntersectionObserver：一屏可能完全落在某个小节内部
 * （没有元素进出视口），观察器会漏掉"当前在哪一节"；按"最后一个越过基准线的标题"判断更稳。
 */
import {onBeforeUnmount, onMounted, ref, watch} from 'vue'

interface TocHeading {
  id: string
  text: string
  level: number
}

const props = defineProps<{ headings: TocHeading[] }>()

const activeId = ref('')

/** 顶栏高度（sticky header）+ 余量：标题滚到这个位置以下就算"已进入该节" */
const OFFSET = 96

function onScroll(): void {
  if (!props.headings.length) return
  let current = props.headings[0]?.id ?? ''
  for (const heading of props.headings) {
    const el = document.getElementById(heading.id)
    if (!el) continue
    if (el.getBoundingClientRect().top - OFFSET <= 0) current = heading.id
  }
  activeId.value = current
}

function scrollTo(id: string): void {
  const el = document.getElementById(id)
  if (!el) return
  el.scrollIntoView({behavior: 'smooth', block: 'start'})
  activeId.value = id
  // 同步地址栏锚点，方便读者复制"指向某一节"的链接
  if (import.meta.client) window.history.replaceState(null, '', `#${id}`)
}

onMounted(() => {
  onScroll()
  window.addEventListener('scroll', onScroll, {passive: true})
})

onBeforeUnmount(() => {
  if (import.meta.client) window.removeEventListener('scroll', onScroll)
})

watch(
  () => props.headings,
  () => onScroll(),
)
</script>

<template>
  <nav v-if="headings.length" :aria-label="$t('article.toc')" class="toc">
    <p class="toc__title">{{ $t('article.toc') }}</p>
    <ul class="toc__list">
      <li v-for="heading in headings" :key="heading.id">
        <a
          :aria-current="activeId === heading.id ? 'location' : undefined"
          :class="[
            'toc__link',
            heading.level === 3 ? 'toc__link--sub' : '',
            activeId === heading.id ? 'is-active' : '',
          ]"
          :href="`#${heading.id}`"
          @click.prevent="scrollTo(heading.id)"
        >
          {{ heading.text }}
        </a>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.toc {
  font-size: 0.875rem;
}

.toc__title {
  display: flex;
  gap: 0.375rem;
  align-items: center;
  margin: 0 0 0.5rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-fg-subtle);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.toc__list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 0;
  margin: 0;
  list-style: none;
  border-left: 1px solid var(--color-line);
}

.toc__link {
  display: block;
  padding: 0.3rem 0 0.3rem 0.75rem;
  margin-left: -1px;
  color: var(--color-fg-muted);
  border-left: 2px solid transparent;
  transition: color 0.12s ease, border-color 0.12s ease;
}

.toc__link:hover {
  color: var(--color-fg);
  border-left-color: var(--color-line-strong);
}

.toc__link.is-active {
  font-weight: 500;
  color: var(--color-primary);
  border-left-color: var(--color-primary);
}

.toc__link--sub {
  padding-left: 1.5rem;
  font-size: 0.8125rem;
}
</style>
