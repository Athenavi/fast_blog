<script lang="ts" setup>
/**
 * 抽屉表单壳：内容型实体的编辑统一走右侧抽屉（比弹窗更适合长表单，
 * 且不打断列表浏览）。保存中按钮自动 loading，footer 可插入额外操作。
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
  >
    <slot/>

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
