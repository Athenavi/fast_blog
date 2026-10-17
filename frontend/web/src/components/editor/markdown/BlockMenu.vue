<script lang="ts" setup>
/**
 * 块类型菜单
 *
 * 「+」和「/」共用这一个组件：两边喂的是同一张 `BLOCK_ITEMS` 表，
 * 差别只在位置（加号贴在行左边的槽里，斜杠跟着光标）和有没有筛选词。
 *
 * **没有自己的键盘处理**：焦点始终留在编辑器里，方向键与回车由编辑器那条键位表
 * 拦下来（见 `setup.ts` 的 `uiKeymap`），父组件改 `highlight` 再回传选中项。
 * 组件里再挂一个 keydown 的话，两个来源都能改高亮，早晚互相抢。
 */
import type {IconName} from '@/lib/icons'

export interface BlockMenuItem {
  id: string
  title: string
  icon?: IconName
  text?: string
  active: boolean
}

const props = defineProps<{
  /** 读屏用的分组名 */
  label: string
  items: BlockMenuItem[]
  /** 键盘当前停在哪一项（没有鼠标时也保证有一项是可回车插入的） */
  highlight: string | null
  emptyText: string
  /** 斜杠那条才显示的提示 */
  hint?: string
  /**
   * 整块菜单的最大高度（px）。
   *
   * 由父组件给：它已经为了「往上翻还是往下放」算过同一个数，这里再写一遍 CSS 常量
   * 就是两个来源，改一处就会出现「菜单被裁掉一行但父组件以为它有那么高」。
   */
  maxHeight?: number
}>()

const emit = defineEmits<{
  (e: 'pick', id: string): void
  (e: 'hover', id: string): void
}>()

const list = ref<HTMLElement | null>(null)

/** 键盘走到列表末尾时把那一项滚进视野（菜单自己会滚，正文不会） */
watch(
  () => props.highlight,
  (id) => {
    if (!id) return
    void nextTick(() => {
      list.value
        ?.querySelector<HTMLElement>(`[data-item="${id}"]`)
        ?.scrollIntoView({block: 'nearest'})
    })
  },
)
</script>

<template>
  <!-- mousedown 一律拦掉：编辑器不能因为点了菜单就丢焦点，
       丢了焦点，选区与撤销栈的归属都会跟着变，插入的位置也就不对了 -->
  <div
    :aria-label="label"
    :style="maxHeight ? {maxHeight: `${maxHeight}px`} : {}"
    class="md-blk"
    role="menu"
    @mousedown.prevent
  >
    <div ref="list" class="md-blk__list">
      <p v-if="!items.length" class="md-blk__empty">{{ emptyText }}</p>
      <button
        v-for="item in items"
        :key="item.id"
        :class="{'is-hl': item.id === highlight}"
        :data-item="item.id"
        class="md-blk__item"
        role="menuitem"
        type="button"
        @click="emit('pick', item.id)"
        @mouseenter="emit('hover', item.id)"
      >
        <span class="md-blk__icon">
          <Icon v-if="item.icon" :name="item.icon" class="h-4 w-4"/>
          <span v-else class="md-blk__glyph">{{ item.text }}</span>
        </span>
        <span class="md-blk__title">{{ item.title }}</span>
        <Icon v-if="item.active" aria-hidden="true" class="md-blk__mark h-4 w-4" name="check"/>
      </button>
    </div>
    <p v-if="hint" class="md-blk__hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
/*
 * 尺寸由父组件算（它知道屏幕还剩多少地方），这里只画内容；
 * 宽度固定 260px —— 与父组件的 MENU_W 必须一致，两处各写一个数字就会错位。
 */
.md-blk {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  width: 260px;
  padding: 4px;
  overflow: hidden;
  border: 1px solid var(--color-line);
  border-radius: 12px;
  background: var(--color-surface);
  box-shadow: 0 10px 30px rgb(15 23 42 / 16%);
}

/* 高度被 `max-height` 夹住时由这一项来滚：弹性项不设 min-height: 0 是不会收缩的 */
.md-blk__list {
  flex: 0 1 auto;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.md-blk__item {
  display: flex;
  gap: 10px;
  align-items: center;
  width: 100%;
  height: 34px;
  padding: 0 8px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--color-fg);
  font: inherit;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
}

.md-blk__item.is-hl {
  background: var(--color-primary-soft);
}

.md-blk__icon {
  display: inline-flex;
  flex: none;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  color: var(--color-fg-muted);
}

.md-blk__glyph {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.md-blk__title {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 已是的项打勾：这一列不占宽度以外的空间，避免菜单宽度随语言变化 */
.md-blk__mark {
  flex: none;
  color: var(--color-primary);
}

.md-blk__empty {
  padding: 10px 8px;
  margin: 0;
  font-size: 12px;
  color: var(--color-fg-subtle);
}

.md-blk__hint {
  flex: none;
  padding: 6px 8px 2px;
  margin: 4px 0 0;
  border-top: 1px solid var(--color-line);
  font-size: 11px;
  color: var(--color-fg-subtle);
}
</style>
