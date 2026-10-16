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
      unique-opened
      router
      @select="emit('navigate')"
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

import {menuLabel} from '@/utils/menus'
import {useAppStore} from '@/store/modules/app'
import {usePermissionStore} from '@/store/modules/permission'

/**
 * 后台导航菜单
 *
 * `collapsed` 不传时跟随 `appStore.sidebarCollapsed`（宽屏常驻侧边栏）；
 * 窄屏把菜单放进抽屉时必须显式传 `false`，否则抽屉会沿用"已折叠"状态只剩图标。
 */
const props = defineProps<{ collapsed?: boolean }>()

const emit = defineEmits<{ (event: 'navigate'): void }>()

const appStore = useAppStore()
const permissionStore = usePermissionStore()
const route = useRoute()

const {t, te} = useI18n()

const collapsed = computed(() => props.collapsed ?? appStore.sidebarCollapsed)

/** 菜单文案：与命令面板共用同一份实现（`menu.<name>` → title 回退） */
function label(item: AdminMenuItem): string {
  return menuLabel(item, (key) => t(key), (key) => te(key))
}

/** 高亮当前路径：优先精确匹配，其次匹配父级 */
const activeMenu = computed(() => route.path)
</script>

<style scoped>
.sidebar {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--admin-sidebar-bg);
}

.sidebar__logo {
  height: 56px;
  line-height: 56px;
  text-align: center;
  color: var(--admin-sidebar-fg-active);
  font-weight: 600;
  font-size: 15px;
  white-space: nowrap;
  overflow: hidden;
  border-bottom: 1px solid var(--admin-sidebar-line);
}

/* 菜单颜色全部走令牌（EP 的 menu 变量 + 后台令牌），支持深浅色与自选配色 */
.sidebar :deep(.el-menu) {
  --el-menu-bg-color: var(--admin-sidebar-bg);
  --el-menu-text-color: var(--admin-sidebar-fg);
  --el-menu-active-color: var(--admin-sidebar-fg-active);
  --el-menu-hover-bg-color: color-mix(in oklab, var(--admin-sidebar-bg) 85%, white);
  --el-menu-item-height: 44px;
  --el-menu-sub-item-height: 40px;
  border-right: none;
}

.sidebar :deep(.el-menu-item.is-active) {
  background-color: color-mix(in oklab, var(--admin-primary) 42%, var(--admin-sidebar-bg));
}

.sidebar :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  color: var(--admin-sidebar-fg-active);
}
</style>
