<template>
  <div class="header">
    <button
      :aria-expanded="narrow ? appStore.mobileSidebarOpen : !appStore.sidebarCollapsed"
      :aria-label="toggleLabel"
      :title="toggleLabel"
      class="header__icon-btn"
      type="button"
      @click="onToggleSidebar"
    >
      <Menu v-if="narrow"/>
      <Fold v-else-if="!appStore.sidebarCollapsed"/>
      <Expand v-else/>
    </button>

    <el-breadcrumb v-if="!narrow" class="header__breadcrumb" separator="/">
      <el-breadcrumb-item v-for="item in breadcrumbs" :key="item">{{ item }}</el-breadcrumb-item>
    </el-breadcrumb>
    <span v-else class="header__spacer"/>

    <div class="header__right">
      <button
        :aria-label="$t('admin.command.open')"
        :title="`${$t('admin.command.open')} (${shortcutHint})`"
        class="header__search"
        type="button"
        @click="appStore.toggleCommandPalette()"
      >
        <Search class="header__search-icon"/>
        <span v-if="!narrow" class="header__search-text">{{ $t('admin.command.placeholder') }}</span>
        <kbd v-if="!narrow" class="header__kbd">{{ shortcutHint }}</kbd>
      </button>

      <el-dropdown trigger="click" @command="onThemeCommand">
        <button :aria-label="$t('admin.theme.toggle')" :title="$t('admin.theme.toggle')" class="header__icon-btn"
                type="button">
          <Moon v-if="isDark"/>
          <Sunny v-else/>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="light">{{ $t('admin.theme.light') }}</el-dropdown-item>
            <el-dropdown-item command="dark">{{ $t('admin.theme.dark') }}</el-dropdown-item>
            <el-dropdown-item command="system">{{ $t('admin.theme.system') }}</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <LanguageSwitcher/>

      <el-badge :hidden="unread === 0" :value="unread" class="header__badge">
        <button :aria-label="unreadLabel" :title="unreadLabel" class="header__icon-btn" type="button"
                @click="goNotifications">
          <Bell/>
        </button>
      </el-badge>

      <el-dropdown trigger="click" @command="onCommand">
        <button :aria-label="$t('admin.accountMenu')" class="header__user" type="button">
          <el-avatar :size="28" :src="userStore.userInfo?.profile_picture || undefined">
            {{ userStore.displayName.slice(0, 1).toUpperCase() }}
          </el-avatar>
          <span v-if="!narrow" class="header__username">{{ userStore.displayName }}</span>
          <el-tag v-if="userStore.isSuperuser && !narrow" size="small" type="danger">{{
              $t('admin.superuser')
            }}
          </el-tag>
          <ArrowDown/>
        </button>
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
import {computed, onBeforeUnmount, onMounted, ref, watch} from 'vue'
import {ElMessageBox} from '@/utils/feedback'

import {notificationApi} from '@/api'
import {type ThemeMode, useTheme} from '@/composables/useTheme'
import {useAppStore} from '@/store/modules/app'
import {usePermissionStore} from '@/store/modules/permission'
import {useUserStore} from '@/store/modules/user'

/**
 * 后台顶栏
 *
 * `narrow` 由后台布局传入（<lg）：窄屏时侧边栏改抽屉，这里的折叠按钮变成"打开导航"，
 * 面包屑与用户名收起，把宽度让给操作区。
 *
 * 所有图标控件都是真实 `<button>`：可 Tab、可 Enter 触发、带 `aria-label`/`title`。
 * 两个下拉统一 `trigger="click"` —— 默认的 hover 触发在触屏设备上根本打不开。
 */
const props = withDefaults(defineProps<{ narrow?: boolean }>(), {narrow: false})

const appStore = useAppStore()
const userStore = useUserStore()
const permissionStore = usePermissionStore()
const {isDark, setTheme} = useTheme()
const route = useRoute()
const router = useRouter()

const {t, te} = useI18n()

const toggleLabel = computed(() => {
  if (props.narrow) return t('admin.nav.open')
  return appStore.sidebarCollapsed ? t('admin.nav.expand') : t('admin.nav.collapse')
})

const unreadLabel = computed(() =>
  unread.value > 0 ? t('admin.notification.unread', {n: unread.value}) : t('admin.notification.title'),
)

function onToggleSidebar(): void {
  if (props.narrow) appStore.openMobileSidebar()
  else appStore.toggleSidebar()
}

/** 头部主题切换：浅色 / 深色 / 跟随系统（与前台共用同一份偏好，见 useTheme） */
function onThemeCommand(command: string): void {
  setTheme(command as ThemeMode)
}

const unread = ref(0)

/** 快捷键提示文案按平台显示（Windows/Linux 用 Ctrl，macOS 用 ⌘） */
const shortcutHint = ref('Ctrl+K')

onMounted(() => {
  const platform = `${navigator.userAgent} ${navigator.platform ?? ''}`
  if (/Mac|iPhone|iPad/i.test(platform)) shortcutHint.value = '⌘K'
})

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

/**
 * 未读数刷新
 *
 * 此前只在 `onMounted` 拉一次：停留在同一页面时新通知永远不会出现。
 * 现在按 60s 轮询（页面不可见时跳过，省流量/省电），并在站内跳转后立刻刷新一次
 * ——用户刚操作完，是最可能产生新通知的时刻。
 */
const UNREAD_POLL_INTERVAL = 60_000
let unreadTimer: number | null = null

function onVisibilityChange(): void {
  if (document.visibilityState === 'visible') void loadUnread()
}

onMounted(() => {
  void loadUnread()
  unreadTimer = window.setInterval(() => {
    if (document.visibilityState === 'visible') void loadUnread()
  }, UNREAD_POLL_INTERVAL)
  document.addEventListener('visibilitychange', onVisibilityChange)
})

onBeforeUnmount(() => {
  if (unreadTimer !== null) window.clearInterval(unreadTimer)
  document.removeEventListener('visibilitychange', onVisibilityChange)
})

watch(
  () => route.fullPath,
  () => void loadUnread(),
)
</script>

<style scoped>
.header {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 8px;
}

.header__spacer {
  flex: 1 1 auto;
}

.header__icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  font-size: 18px;
  color: var(--admin-fg-muted);
  cursor: pointer;
  background: transparent;
  border: none;
  border-radius: var(--admin-radius-sm);
  transition: background-color 0.12s ease, color 0.12s ease;
}

.header__icon-btn:hover {
  color: var(--admin-fg);
  background-color: var(--admin-surface-hover);
}

.header__icon-btn:focus-visible {
  outline: 2px solid var(--admin-primary);
  outline-offset: 2px;
}

.header__breadcrumb {
  flex: 1;
  margin-left: 4px;
}

/* 命令面板入口：宽屏显示成"伪搜索框"，窄屏只留图标 */
.header__search {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  height: 32px;
  padding: 0 8px;
  color: var(--admin-fg-muted);
  cursor: pointer;
  background: var(--admin-surface-soft);
  border: 1px solid var(--admin-line);
  border-radius: var(--admin-radius-sm);
  transition: border-color 0.12s ease, color 0.12s ease;
}

.header__search:hover {
  color: var(--admin-fg);
  border-color: var(--admin-line-strong);
}

.header__search:focus-visible {
  outline: 2px solid var(--admin-primary);
  outline-offset: 2px;
}

.header__search-icon {
  font-size: 15px;
}

.header__search-text {
  max-width: 180px;
  overflow: hidden;
  font-size: 13px;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.header__kbd {
  padding: 0 4px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--admin-fg-subtle);
  border: 1px solid var(--admin-line);
  border-radius: 4px;
}

.header__right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header__user {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 2px 6px;
  color: inherit;
  cursor: pointer;
  background: transparent;
  border: none;
  border-radius: var(--admin-radius-sm);
  transition: background-color 0.12s ease;
}

.header__user:hover {
  background-color: var(--admin-surface-hover);
}

.header__user:focus-visible {
  outline: 2px solid var(--admin-primary);
  outline-offset: 2px;
}

.header__username {
  font-size: 14px;
  color: var(--admin-fg);
}
</style>
