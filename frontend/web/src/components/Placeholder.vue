<script lang="ts" setup>
/**
 * 后台占位页：业务实现将在后续阶段补全。
 * 用 `title` 显示当前页面名称，避免为每个占位页复制模板。
 */
defineProps<{ title: string }>()
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <el-result :sub-title="$t('admin.shared.Placeholder.theBusinessImplementationForThisPageWillBeCompletedInALaterPhase')" :title="title"
                 icon="info">
        <template #extra>
          <el-button type="primary" @click="navigateTo('/dashboard')">{{
              $t('admin.shared.Placeholder.backToDashboard')
            }}
          </el-button>
        </template>
      </el-result>
    </el-card>
  </div>
</template>
