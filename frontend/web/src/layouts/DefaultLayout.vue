<template>
  <el-container class="layout">
    <el-aside :width="appStore.sidebarCollapsed ? '64px' : '210px'" class="layout__aside">
      <AppSidebar/>
    </el-aside>

    <el-container>
      <el-header height="56px" class="layout__header">
        <AppHeader/>
      </el-header>

      <el-main class="layout__main">
        <router-view/>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import {useAppStore} from '@/store/modules/app'

import AppHeader from './components/AppHeader.vue'
import AppSidebar from './components/AppSidebar.vue'

const appStore = useAppStore()
</script>

<style scoped>
.layout {
  height: 100%;
}

.layout__aside {
  background-color: #1f2937;
  transition: width 0.2s ease;
  overflow-x: hidden;
}

.layout__header {
  display: flex;
  align-items: center;
  background-color: #fff;
  border-bottom: 1px solid #e5e7eb;
  padding: 0 16px;
}

.layout__main {
  background-color: #f5f7fa;
  padding: 0;
  overflow-y: auto;
}
</style>
