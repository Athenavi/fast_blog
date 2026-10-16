<script lang="ts" setup>
/**
 * 前台统一确认对话框
 *
 * 为什么自建：前台此前直接用 `window.confirm`（删除投稿、删除媒体、清空离线缓存），
 * 而后台统一走 `ElMessageBox`。原生 confirm 在移动端外观最差、按钮文案无法本地化
 * （中文系统是"确定/取消"、英文系统是"OK/Cancel"），也无法表达"这是危险操作"。
 * 这里用语义令牌 + 自研浮层统一，不引入 Element Plus（前台首包不该为它买单）。
 *
 * 用法：
 *   <ConfirmDialog v-model="confirmOpen" danger :title="…" :description="…" @confirm="doDelete"/>
 */
import {onBeforeUnmount, watch} from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    title?: string
    description?: string
    confirmText?: string
    cancelText?: string
    /** 危险操作（删除等）用红色主按钮 */
    danger?: boolean
    /** 确认处理中（避免重复点击） */
    loading?: boolean
  }>(),
  {title: '', description: '', confirmText: '', cancelText: '', danger: false, loading: false},
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'confirm'): void
}>()

const {t} = useI18n()

function close(): void {
  if (props.loading) return
  emit('update:modelValue', false)
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') close()
}

watch(
  () => props.modelValue,
  (open) => {
    if (!import.meta.client) return
    if (open) window.addEventListener('keydown', onKeydown)
    else window.removeEventListener('keydown', onKeydown)
  },
)

onBeforeUnmount(() => {
  if (import.meta.client) window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      aria-modal="true"
      class="fixed inset-0 z-[70] flex items-center justify-center bg-canvas/80 p-4 backdrop-blur-sm"
      role="alertdialog"
      @click.self="close"
    >
      <div class="w-full max-w-sm rounded-card border border-line bg-surface p-5 shadow-lg">
        <p class="text-sm font-semibold text-fg">{{ title || t('common.confirm') }}</p>
        <p v-if="description" class="mt-1.5 text-sm leading-relaxed text-fg-muted">{{ description }}</p>

        <div class="mt-4 flex justify-end gap-2">
          <Button size="sm" type="button" variant="outline" @click="close">
            {{ cancelText || t('common.cancel') }}
          </Button>
          <Button
            :disabled="loading"
            :variant="danger ? 'danger' : 'default'"
            size="sm"
            type="button"
            @click="emit('confirm')"
          >
            {{ confirmText || t('common.confirm') }}
          </Button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
