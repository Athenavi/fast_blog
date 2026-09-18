<template>
  <div class="error-page">
    <el-result icon="error" title="404" sub-title="页面不存在或已被移除">
      <template #extra>
        <el-button type="primary" @click="router.push('/dashboard')">返回仪表盘</el-button>
      </template>
    </el-result>
  </div>
</template>

<script setup lang="ts">
import {useRouter} from 'vue-router'

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
