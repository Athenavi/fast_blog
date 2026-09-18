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
import {useAppStore} from '@/store/modules/app'
import {usePermissionStore} from '@/store/modules/permission'
import {useUserStore} from '@/store/modules/user'

const appStore = useAppStore()
const userStore = useUserStore()
const permissionStore = usePermissionStore()
const route = useRoute()
const router = useRouter()

const {t} = useI18n()

const unread = ref(0)

const breadcrumbs = computed(() =>
  route.matched
    .map((item) => (item.meta?.title as string | undefined) ?? '')
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
  color: #4b5563;
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
  color: #4b5563;
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
  color: #374151;
}
</style>
