<script lang="ts" setup>
/**
 * 文章目录（TOC）
 *
 * 长文的第一需求是"能在小节之间跳"。这里做三件事：把 `h2/h3` 渲染成带编号的目录、
 * 跟随滚动高亮当前小节、在窄屏上折起来（否则目录先占掉半屏，正文被推到折叠线以下）。
 *
 * 为什么用滚动位置而不是 IntersectionObserver：一屏可能完全落在某个小节内部
 * （没有元素进出视口），观察器会漏掉"当前在哪一节"；按"最后一个越过基准线的标题"判断更稳。
 *
 * 编号在前端算（`01` / `1.2`），不依赖正文里的标题序号 —— 作者写的是 `##`，
 * 编号是版式，两件事不该绑在一起：删掉一节时不用手动改后面的号。
 */
import {computed, onBeforeUnmount, onMounted, ref, watch} from 'vue'

interface TocHeading {
  id: string
  text: string
  level: number
}

const props = defineProps<{ headings: TocHeading[] }>()

const activeId = ref('')
/** 窄屏折叠态；宽屏由 CSS 忽略它（见样式里那条 min-width 查询） */
const open = ref(false)

const numbered = computed(() => {
  let sec = 0
  let sub = 0
  return props.headings.map((heading) => {
    if (heading.level <= 2) {
      sec += 1
      sub = 0
    } else {
      sub += 1
    }
    return {
      ...heading,
      num: heading.level <= 2 ? String(sec).padStart(2, '0') : `${sec}.${sub}`,
    }
  })
})

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
  // 窄屏上点完就该把目录收起来，否则它一直占着正文上方的空间
  if (window.matchMedia('(max-width: 1023px)').matches) open.value = false
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
  <nav
    v-if="headings.length"
    :aria-label="$t('article.toc')"
    :data-open="open ? 'true' : 'false'"
    class="toc"
  >
    <div class="toc__head">
      <p class="toc__title">{{ $t('article.toc') }}</p>
      <button
        :aria-expanded="open"
        class="toc__toggle"
        type="button"
        @click="open = !open"
      >
        <Icon class="toc__toggle-icon" name="chevron-down"/>
        <span>{{ open ? $t('article.collapseToc') : $t('article.expandToc') }}</span>
      </button>
    </div>

    <ul class="toc__list">
      <li v-for="heading in numbered" :key="heading.id">
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
          <span class="toc__num">{{ heading.num }}</span>
          <span class="toc__text">{{ heading.text }}</span>
        </a>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.toc {
  font-size: 0.875rem;
}

.toc__head {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.toc__title {
  display: flex;
  gap: 0.375rem;
  align-items: center;
  margin: 0;
  font-family: var(--font-mono);
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--color-fg-subtle);
  text-transform: uppercase;
  letter-spacing: 0.2em;
}

/* 折叠开关只在窄屏出现；宽屏目录常驻，按钮留着只会让人以为能关 */
.toc__toggle {
  display: inline-flex;
  gap: 0.25rem;
  align-items: center;
  padding: 0.15rem 0.4rem;
  font-size: 0.75rem;
  color: var(--color-fg-muted);
  cursor: pointer;
  background: none;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-control);
}

.toc__toggle-icon {
  width: 0.875rem;
  height: 0.875rem;
  transition: transform 0.15s ease;
}

.toc[data-open='true'] .toc__toggle-icon {
  transform: rotate(180deg);
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
  display: flex;
  gap: 0.5rem;
  align-items: baseline;
  padding: 0.3rem 0.5rem 0.3rem 0.7rem;
  margin-left: -1px;
  color: var(--color-fg-muted);
  border-left: 2px solid transparent;
  transition: color 0.12s ease, border-color 0.12s ease, background-color 0.12s ease;
}

/* 编号走等宽：一列数字要能对齐 */
.toc__num {
  flex: none;
  min-width: 2ch;
  font-family: var(--font-mono);
  font-size: 0.6875rem;
  color: var(--color-fg-subtle);
}

.toc__text {
  min-width: 0;
}

.toc__link:hover {
  color: var(--color-fg);
  border-left-color: var(--color-line-strong);
}

.toc__link.is-active {
  font-weight: 500;
  color: var(--color-primary);
  background: var(--color-surface-soft);
  border-left-color: var(--color-primary);
}

.toc__link.is-active .toc__num {
  color: var(--color-primary);
}

.toc__link--sub {
  padding-left: 1.6rem;
  font-size: 0.8125rem;
}

/* ---------------------------------------------------------------- 折叠与常驻
 * 窄屏：`data-open='false'` 时只留标题行。
 * 宽屏：目录常驻，折叠态被下面的查询原样覆盖掉（选择器写法保持一致，
 * 因此靠**源码顺序**取胜，不需要 `!important`）。
 */
.toc[data-open='false'] .toc__list {
  display: none;
}

@media (min-width: 1024px) {
  .toc__toggle {
    display: none;
  }

  .toc__head {
    margin-bottom: 0.5rem;
  }

  .toc[data-open='false'] .toc__list,
  .toc[data-open='true'] .toc__list {
    display: flex;
  }
}
</style>
