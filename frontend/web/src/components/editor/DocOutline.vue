<script lang="ts" setup>
/**
 * 编辑页的大纲栏
 *
 * 长文写作的第一需求是「知道文里有几节、并且能跳过去」。阅读页那套目录
 * （`components/site/ArticleToc.vue`）在这里用不了，两个硬差异：
 *   1. 它监听 `window` 滚动并用 `document.getElementById` 找锚点 —— 而编辑区
 *      的标题在 ProseMirror 里**没有 id**（往文档里塞 id 会污染 Yjs 协作与撤销栈），
 *      且滚动容器在后台布局下是 `el-main` 而不是 window；
 *   2. 它把点击写成 `#id` 地址栏锚点 —— 编辑页里那会让路由以为要跳转，
 *      还会触发未保存离开确认。
 *
 * 所以这里按**序号**定位（见 `utils/content.ts` 的说明），点击用 `button`
 * 而不是 `a`：不产生 href，也就不会碰地址栏与路由。
 */
import type {OutlineItem} from '@/utils/content'

const props = withDefaults(
  defineProps<{
    items: OutlineItem[]
    /** 当前可见小节对应的序号；-1 = 还没有任何一节越过基准线 */
    activeIndex?: number
  }>(),
  {activeIndex: -1},
)

const emit = defineEmits<{ (e: 'select', index: number): void }>()

const {t} = useI18n()

/**
 * 缩进以**文里实际最浅的一级**为基准。
 *
 * 文章正文普遍从「标题 2」开始（「标题 1」留给页面顶部那个大标题输入框），
 * 若直接按 `level` 算左内边距，整栏会白左边距一大截，看起来像少了一层。
 */
const baseLevel = computed(() => props.items.reduce((min, item) => Math.min(min, item.level), 6))

function indentOf(level: number): string {
  return `${Math.max(0, level - baseLevel.value) * 14}px`
}
</script>

<template>
  <nav :aria-label="$t('editor.doc.outline')" class="doc-outline">
    <p class="doc-outline__caption">{{ $t('editor.doc.outline') }}</p>

    <p v-if="!items.length" class="doc-outline__empty">{{ $t('editor.doc.outlineEmpty') }}</p>

    <ul v-else class="doc-outline__list">
      <li v-for="item in items" :key="item.index">
        <button
          :aria-current="item.index === activeIndex ? 'true' : undefined"
          :class="{'is-active': item.index === activeIndex}"
          :style="{'--outline-indent': indentOf(item.level)}"
          :title="item.text"
          class="doc-outline__link"
          type="button"
          @click="emit('select', item.index)"
        >
          {{ item.text }}
        </button>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.doc-outline {
  font-size: 13px;
  min-width: 0;
}

.doc-outline__caption {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-fg-subtle);
}

/* 没有标题时也要占住这块版面：目录栏凭空消失会让人以为按钮坏了 */
.doc-outline__empty {
  margin: 0;
  padding: 8px 10px;
  border-radius: var(--radius-control);
  background: var(--color-surface-soft);
  font-size: 12px;
  line-height: 1.6;
  color: var(--color-fg-muted);
}

.doc-outline__list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.doc-outline__link {
  display: block;
  width: 100%;
  padding: 5px 8px 5px calc(9px + var(--outline-indent, 0px));
  margin-left: -1px;
  border: none;
  border-left: 2px solid var(--color-line);
  border-radius: 0 var(--radius-control) var(--radius-control) 0;
  background: transparent;
  font: inherit;
  color: var(--color-fg-muted);
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  transition: color 0.12s ease, background-color 0.12s ease, border-color 0.12s ease;
}

.doc-outline__link:hover {
  color: var(--color-fg);
  background: var(--color-surface-soft);
  border-left-color: var(--color-line-strong);
}

/* 当前小节：主色描边 + 主色文字。刻意**不换底色** —— 底色会把整栏的节奏打乱，
   而描边在长列表里更容易扫视定位 */
.doc-outline__link.is-active {
  font-weight: 500;
  color: var(--color-primary);
  border-left-color: var(--color-primary);
}

.doc-outline__link:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: -2px;
}
</style>
