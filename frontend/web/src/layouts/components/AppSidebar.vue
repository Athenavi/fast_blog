<template>
  <div class="sidebar">
    <div class="sidebar__logo">
      <span v-if="!collapsed">{{ $t('admin.consoleTitle') }}</span>
      <span v-else>FB</span>
    </div>

    <el-menu
      :default-active="activeMenu"
      :collapse="collapsed"
      :collapse-transition="false"
      background-color="#1f2937"
      text-color="#cbd5e1"
      active-text-color="#ffffff"
      unique-opened
      router
    >
      <template v-for="menu in permissionStore.menus" :key="menu.path">
        <el-sub-menu v-if="menu.children?.length" :index="menu.path">
          <template #title>
            <el-icon v-if="menu.icon">
              <component :is="menu.icon"/>
            </el-icon>
            <span>{{ label(menu) }}</span>
          </template>
          <el-menu-item v-for="child in menu.children ?? []" :key="child.path" :index="child.path">
            {{ label(child) }}
          </el-menu-item>
        </el-sub-menu>

        <el-menu-item v-else :index="menu.path">
          <el-icon v-if="menu.icon">
            <component :is="menu.icon"/>
          </el-icon>
          <template #title>{{ label(menu) }}</template>
        </el-menu-item>
      </template>
    </el-menu>
  </div>
</template>

<script setup lang="ts">
import {computed} from 'vue'

import type {AdminMenuItem} from '@/utils/menus'

import {useAppStore} from '@/store/modules/app'
import {usePermissionStore} from '@/store/modules/permission'

const appStore = useAppStore()
const permissionStore = usePermissionStore()
const route = useRoute()

const {t, te} = useI18n()

const collapsed = computed(() => appStore.sidebarCollapsed)

/** 菜单文案：优先取 `menu.<name>` 翻译；缺失时回退到 menus.ts 里的中文 title（便于渐进式 i18n） */
function label(item: AdminMenuItem): string {
  const key = `menu.${item.name}`
  return te(key) ? t(key) : item.title || item.name
}

/** 高亮当前路径：优先精确匹配，其次匹配父级 */
const activeMenu = computed(() => route.path)
</script>

<style scoped>
.sidebar {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.sidebar__logo {
  height: 56px;
  line-height: 56px;
  text-align: center;
  color: #fff;
  font-weight: 600;
  font-size: 15px;
  white-space: nowrap;
  overflow: hidden;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.sidebar :deep(.el-menu) {
  border-right: none;
}
</style>
