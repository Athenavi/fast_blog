<script lang="ts" setup>
import {nextTick, ref} from 'vue'

/**
 * 抽屉表单壳：内容型实体的编辑统一走右侧抽屉（比弹窗更适合长表单，
 * 且不打断列表浏览）。保存中按钮自动 loading，footer 可插入额外操作。
 *
 * 新增：打开后自动聚焦第一个可输入字段（`focusFirstField`）。
 *
 * 用法：
 *   <AdminFormDrawer v-model="visible" :title="…" :loading="saving" @confirm="submit">
 *     <el-form …/>
 *   </AdminFormDrawer>
 */
const props = withDefaults(
  defineProps<{
    modelValue: boolean
    title?: string
    /** 抽屉宽度（数字按 px 处理） */
    size?: number | string
    loading?: boolean
    confirmText?: string
    /** 关闭前拦截（如未保存提示），返回 false 可阻止关闭 */
    beforeClose?: () => boolean | Promise<boolean>
  }>(),
  {size: 560},
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'confirm'): void
}>()

const contentRef = ref<HTMLElement | null>(null)

/**
 * 打开后把焦点交给第一个可输入字段。
 *
 * 此前抽屉打开后焦点仍留在触发按钮上，用户必须再点一次输入框才能开始敲键盘。
 * 这里包一层自己的容器再去查询（而不是 `.el-drawer__body`），避免依赖 Element Plus 的内部结构。
 */
async function focusFirstField(): Promise<void> {
  await nextTick()
  const target = contentRef.value?.querySelector<HTMLElement>(
    'input:not([type="hidden"]):not([disabled]), textarea:not([disabled]), select:not([disabled])',
  )
  target?.focus()
}

async function handleClose(): Promise<void> {
  if (props.beforeClose) {
    const allowed = await props.beforeClose()
    if (!allowed) return
  }
  emit('update:modelValue', false)
}
</script>

<template>
  <el-drawer
    :before-close="handleClose"
    :model-value="modelValue"
    :size="size"
    :title="title"
    append-to-body
    destroy-on-close
    @opened="focusFirstField"
  >
    <div ref="contentRef">
      <slot/>
    </div>

    <template #footer>
      <div class="admin-drawer__footer">
        <slot name="footer-extra"/>
        <span class="admin-drawer__spacer"/>
        <el-button @click="handleClose">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="loading" type="primary" @click="$emit('confirm')">
          {{ confirmText ?? $t('admin.common.save') }}
        </el-button>
      </div>
    </template>
  </el-drawer>
</template>

<style scoped>
.admin-drawer__footer {
  display: flex;
  align-items: center;
  gap: 8px;
}

.admin-drawer__spacer {
  flex: 1 1 auto;
}
</style>
