<template>
  <div class="error-page">
    <el-result icon="warning" sub-title="抱歉，你没有访问该页面的权限" title="403">
      <template #extra>
        <el-button type="primary" @click="router.push('/dashboard')">返回仪表盘</el-button>
      </template>
    </el-result>
  </div>
</template>

<script lang="ts" setup>

const router = useRouter()
</script>

<style scoped>
.error-page {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}
</style>
