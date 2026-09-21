<template>
  <div class="header">
    <el-icon class="header__collapse" @click="appStore.toggleSidebar()">
      <Fold v-if="!appStore.sidebarCollapsed"/>
      <Expand v-else/>
    </el-icon>

    <el-breadcrumb separator="/" class="header__breadcrumb">
      <el-breadcrumb-item v-for="item in breadcrumbs" :key="item">{{ item }}</el-breadcrumb-item>
    </el-breadcrumb>

    <div class="header__right">
      <el-dropdown @command="onThemeCommand">
        <el-icon :title="$t('admin.theme.toggle')" class="header__icon">
          <Moon v-if="isDark"/>
          <Sunny v-else/>
        </el-icon>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="light">{{ $t('admin.theme.light') }}</el-dropdown-item>
            <el-dropdown-item command="dark">{{ $t('admin.theme.dark') }}</el-dropdown-item>
            <el-dropdown-item command="system">{{ $t('admin.theme.system') }}</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <LanguageSwitcher/>

      <el-badge :value="unread" :hidden="unread === 0" class="header__badge">
        <el-icon class="header__icon" @click="goNotifications">
          <Bell/>
        </el-icon>
      </el-badge>

      <el-dropdown @command="onCommand">
        <span class="header__user">
          <el-avatar :size="28" :src="userStore.userInfo?.profile_picture || undefined">
            {{ userStore.displayName.slice(0, 1).toUpperCase() }}
          </el-avatar>
          <span class="header__username">{{ userStore.displayName }}</span>
          <el-tag v-if="userStore.isSuperuser" size="small" type="danger">{{ $t('admin.superuser') }}</el-tag>
          <el-icon><ArrowDown/></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout" divided>{{ $t('admin.logout') }}</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup lang="ts">
import {computed, onMounted, ref} from 'vue'
import {ElMessageBox} from '@/utils/feedback'

import {notificationApi} from '@/api'
import {type ThemeMode, useTheme} from '@/composables/useTheme'
import {useAppStore} from '@/store/modules/app'
import {usePermissionStore} from '@/store/modules/permission'
import {useUserStore} from '@/store/modules/user'

const appStore = useAppStore()
const userStore = useUserStore()
const permissionStore = usePermissionStore()
const {isDark, setTheme} = useTheme()
const route = useRoute()
const router = useRouter()

const {t, te} = useI18n()

/** 头部主题切换：浅色 / 深色 / 跟随系统（与前台共用同一份偏好，见 useTheme） */
function onThemeCommand(command: string): void {
  setTheme(command as ThemeMode)
}

const unread = ref(0)

const breadcrumbs = computed(() =>
  route.matched
    .map((item) => {
      // definePageMeta 的 title 现在存 i18n key（t() 不能在模块作用域求值，见 HANDOVER §17）；
      // te() 判 key 存在后翻译，普通文案原样回退（与菜单的渐进式策略一致）
      const title = item.meta?.title as string | undefined
      if (!title) return ''
      return te(title) ? t(title) : title
    })
    .filter((title) => Boolean(title)),
)

async function loadUnread(): Promise<void> {
  try {
    const data = await notificationApi.unreadCount()
    unread.value = data.unread
  } catch {
    unread.value = 0
  }
}

function goNotifications(): void {
  router.push('/ops/notification')
}

async function onCommand(command: string): Promise<void> {
  if (command === 'logout') {
    await ElMessageBox.confirm(t('admin.logoutConfirm'), t('admin.notice'), {type: 'warning'})
    await userStore.logout()
    permissionStore.reset()
    router.push('/login')
  }
}

onMounted(loadUnread)
</script>

<style scoped>
.header {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 16px;
}

.header__collapse {
  font-size: 18px;
  cursor: pointer;
  color: var(--admin-fg-muted);
}

.header__breadcrumb {
  flex: 1;
}

.header__right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header__icon {
  font-size: 18px;
  cursor: pointer;
  color: var(--admin-fg-muted);
}

.header__user {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  outline: none;
}

.header__username {
  font-size: 14px;
  color: var(--admin-fg);
}
</style>
