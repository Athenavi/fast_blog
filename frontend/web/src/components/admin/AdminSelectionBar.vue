<script lang="ts" setup>
/**
 * 批量操作条：表格选中行后浮出，左侧显示选中数量，右侧放批量的具体动作。
 *
 * 用法：
 *   <AdminSelectionBar :count="list.selectedCount.value" @clear="list.clearSelection">
 *     <el-button type="danger" plain>批量删除</el-button>
 *   </AdminSelectionBar>
 */
import {Close} from '@element-plus/icons-vue'

defineProps<{ count: number }>()
defineEmits<{ (event: 'clear'): void }>()

const {t} = useI18n()
</script>

<template>
  <transition name="admin-sel-fade">
    <div v-if="count > 0" class="admin-selection-bar">
      <span class="admin-selection-bar__count">{{ t('admin.common.selectedItems', {n: count}) }}</span>
      <span class="admin-selection-bar__spacer"/>
      <slot/>
      <el-button :icon="Close" link @click="$emit('clear')">
        {{ $t('admin.common.clearSelection') }}
      </el-button>
    </div>
  </transition>
</template>

<style scoped>
.admin-sel-fade-enter-active,
.admin-sel-fade-leave-active {
  transition: opacity 0.15s ease;
}

.admin-sel-fade-enter-from,
.admin-sel-fade-leave-to {
  opacity: 0;
}
</style>
