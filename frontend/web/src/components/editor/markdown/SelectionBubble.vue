<script lang="ts" setup>
/**
 * 选区气泡横菜单
 *
 * 取代原来那条吸顶的格式工具栏：工具栏要占一整行、还要跟正文抢吸顶位置，
 * 而改格式这件事只在**选中了字**的时候才有意义 —— 所以把它做成跟着选区走的一条浮窗
 * （飞书、Notion、Google Docs 都是这个形状）。
 *
 * 这里只放行内标记（加粗 / 斜体 / 删除线 / 行内代码）和链接：标题、列表、引用这些
 * 是**整行**的事，选中一段文字去改它们，用户看不出改了哪几行，所以归「+」/「/」块菜单。
 *
 * 按钮上只拦 `mousedown` 的默认动作（不拦冒泡），点完编辑器不会丢焦点、选区不会被冲掉；
 * 链接输入条那一栏**不能**拦 mousedown，否则输入框拿不到焦点。
 */
import type {IconName} from '@/lib/icons'

export interface MarkItem {
  id: string
  title: string
  icon: IconName
  active: boolean
}

const props = defineProps<{
  /** 读屏用的分组名 */
  label: string
  marks: MarkItem[]
  /** 「链接」；选区已经在一条链接里时换成「修改链接」 */
  linkTitle: string
  linkActive: boolean
  linkOpen: boolean
  linkValue: string
  linkPlaceholder: string
  applyText: string
  cancelText: string
}>()

const emit = defineEmits<{
  (e: 'run', id: string): void
  (e: 'open-link'): void
  (e: 'close-link'): void
  (e: 'submit-link', url: string): void
}>()

const input = ref<HTMLInputElement | null>(null)
const draft = ref('')

/** 每次展开都从选区现状重新填一遍：连着改两条链接时不能留着上一条的地址 */
watch(
  () => props.linkOpen,
  (open) => {
    if (!open) return
    draft.value = props.linkValue
    void nextTick(() => {
      input.value?.focus()
      input.value?.select()
    })
  },
)

function submit(): void {
  emit('submit-link', draft.value.trim())
}
</script>

<template>
  <div :aria-label="label" class="md-bub" role="toolbar">
    <div v-if="!linkOpen" class="md-bub__row">
      <button
        v-for="mark in marks"
        :key="mark.id"
        :aria-pressed="mark.active"
        :class="{'is-active': mark.active}"
        :title="mark.title"
        class="md-bub__btn"
        type="button"
        @click="emit('run', mark.id)"
        @mousedown.prevent
      >
        <Icon :name="mark.icon" class="h-4 w-4"/>
      </button>
      <span aria-hidden="true" class="md-bub__sep"/>
      <button
        :aria-expanded="linkOpen"
        :aria-pressed="linkActive"
        :class="{'is-active': linkActive}"
        :title="linkTitle"
        class="md-bub__btn"
        type="button"
        @click="emit('open-link')"
        @mousedown.prevent
      >
        <Icon name="link" class="h-4 w-4"/>
      </button>
    </div>

    <div v-else class="md-bub__row">
      <input
        ref="input"
        :aria-label="linkTitle"
        :placeholder="linkPlaceholder"
        v-model="draft"
        class="md-bub__input"
        type="url"
        @keydown.enter.prevent="submit"
        @keydown.esc.prevent="emit('close-link')"
      >
      <button :title="applyText" class="md-bub__btn" type="button" @click="submit">
        <Icon name="check" class="h-4 w-4"/>
      </button>
      <button :title="cancelText" class="md-bub__btn" type="button" @click="emit('close-link')">
        <Icon name="x" class="h-4 w-4"/>
      </button>
    </div>
  </div>
</template>

<style scoped>
.md-bub {
  display: inline-flex;
  align-items: center;
  padding: 3px;
  border: 1px solid var(--color-line);
  border-radius: 10px;
  background: var(--color-surface);
  box-shadow: 0 8px 24px rgb(15 23 42 / 16%);
}

.md-bub__row {
  display: flex;
  gap: 2px;
  align-items: center;
}

.md-bub__btn {
  display: inline-flex;
  flex: none;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: var(--color-fg-muted);
  cursor: pointer;
  transition: background-color 0.12s ease, color 0.12s ease;
}

.md-bub__btn:hover {
  background: var(--color-surface-soft);
  color: var(--color-fg);
}

.md-bub__btn.is-active {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.md-bub__btn:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 1px;
}

.md-bub__sep {
  flex: none;
  width: 1px;
  height: 16px;
  margin: 0 2px;
  background: var(--color-line);
}

/*
 * 输入框要留出协议头的宽度：`https://` 被截成 `http` 会让人以为已经填好了。
 * 链接条是这里唯一的宽元素，整条气泡会因此比纯按钮那一栏宽 —— 展开前后宽度不同，
 * 但它是靠**选区中心**定位的（父组件给的 left + translateX(-50%)），所以不会跳位。
 */
.md-bub__input {
  box-sizing: border-box;
  width: 210px;
  height: 26px;
  padding: 0 8px;
  border: 1px solid var(--color-line);
  border-radius: 7px;
  background: var(--color-surface);
  font: inherit;
  font-size: 12px;
  color: var(--color-fg);
}

.md-bub__input:focus {
  outline: none;
  border-color: var(--color-primary);
}
</style>
