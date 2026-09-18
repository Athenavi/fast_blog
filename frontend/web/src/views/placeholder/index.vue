<template>
  <div class="page-container">
    <el-card shadow="never">
      <el-result
        icon="info"
        :title="title"
        sub-title="该页面的业务实现将在 Phase 8 完成；Phase 7 先打通登录、权限、菜单与请求链路。"
      >
        <template #extra>
          <el-button type="primary" @click="router.push('/dashboard')">返回仪表盘</el-button>
        </template>
      </el-result>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import {computed} from 'vue'
import {useRoute, useRouter} from 'vue-router'

const route = useRoute()
const router = useRouter()

const title = computed(() => (route.meta?.title as string | undefined) ?? '页面')
</script>
