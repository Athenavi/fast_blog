<script lang="ts" setup>
/** 前台顶部导航（阅读优先：窄容器、克制的分割线、克制的动效） */
import {useUserStore} from '@/store/modules/user'

const {t} = useI18n()

const props = defineProps<{ siteName?: string }>()

const userStore = useUserStore()

/**
 * 导航分两层：
 *  - **主导航**只放内容入口（首页/文章/分类/关注/群聊）——此前 9 项平铺，
 *    社区功能与内容入口并列，扫视成本高；
 *  - 专家 / 积分 / 勋章 / 关于 收进「更多」，需要时才展开。
 *
 * 两者都用 `computed`：此前是 setup 期求值的普通数组，**切换语言后导航文案不会更新**。
 */
const PRIMARY_NAV = computed(() => [
  {label: t('site.navHome'), to: '/'},
  {label: t('site.navArticles'), to: '/articles'},
  {label: t('site.navCategories'), to: '/categories'},
  {label: t('site.navFeed'), to: '/feed'},
  {label: t('site.navChat'), to: '/chat'},
])

const MORE_NAV = computed(() => [
  {label: t('site.navExperts'), to: '/experts'},
  {label: t('site.navPoints'), to: '/points'},
  {label: t('site.navBadges'), to: '/badges'},
  {label: t('site.navAbout'), to: '/about'},
])

/** 移动端抽屉里一次列全（不需要二级展开） */
const ALL_NAV = computed(() => [...PRIMARY_NAV.value, ...MORE_NAV.value])

const mobileOpen = ref(false)
const moreOpen = ref(false)
const route = useRoute()

function isActive(to: string): boolean {
  return to === '/' ? route.path === '/' : route.path.startsWith(to)
}

/** 「更多」里含当前页时，父级也要高亮 */
const moreActive = computed(() => MORE_NAV.value.some((item) => isActive(item.to)))

function closeMenus(): void {
  mobileOpen.value = false
  moreOpen.value = false
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') closeMenus()
}

/** 移动端抽屉打开时锁住 body 滚动，否则背景会跟着滑 */
watch(mobileOpen, (open) => {
  if (!import.meta.client) return
  document.body.style.overflow = open ? 'hidden' : ''
})

watch([mobileOpen, moreOpen], ([mobile, more]) => {
  if (!import.meta.client) return
  if (mobile || more) document.addEventListener('keydown', onKeydown)
  else document.removeEventListener('keydown', onKeydown)
})

/** 「更多」下拉：点面板外部收起 */
function onDocumentClick(event: MouseEvent): void {
  if (!moreOpen.value) return
  const target = event.target as HTMLElement | null
  if (target?.closest('[data-more-menu]')) return
  moreOpen.value = false
}

onMounted(() => document.addEventListener('click', onDocumentClick))

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick)
  document.removeEventListener('keydown', onKeydown)
  if (import.meta.client) document.body.style.overflow = ''
})
</script>

<template>
  <!-- 顶部安全区：PWA/全屏模式下避免被刘海或状态栏遮挡 -->
  <header
    class="sticky top-0 z-40 border-b border-line bg-surface/85 backdrop-blur"
    style="padding-top: env(safe-area-inset-top, 0px)"
  >
    <div class="mx-auto flex h-14 max-w-wide items-center gap-4 px-4">
      <NuxtLink class="text-base font-semibold tracking-tight text-fg" to="/">
        {{ props.siteName || 'FastBlog' }}
      </NuxtLink>

      <nav :aria-label="$t('site.menuAriaLabel')" class="hidden items-center gap-1 md:flex">
        <NuxtLink
          v-for="item in PRIMARY_NAV"
          :key="item.to"
          :aria-current="isActive(item.to) ? 'page' : undefined"
          :to="item.to"
          :class="isActive(item.to) ? 'bg-surface-soft font-medium text-fg' : 'text-fg-muted hover:bg-surface-soft hover:text-fg'"
          class="rounded-control px-3 py-1.5 text-sm transition-colors"
        >
          {{ item.label }}
        </NuxtLink>

        <!-- 更多 -->
        <div class="relative" data-more-menu>
          <button
            :aria-expanded="moreOpen"
            :class="moreActive ? 'bg-surface-soft font-medium text-fg' : 'text-fg-muted hover:bg-surface-soft hover:text-fg'"
            aria-haspopup="true"
            class="inline-flex items-center gap-1 rounded-control px-3 py-1.5 text-sm transition-colors"
            type="button"
            @click.stop="moreOpen = !moreOpen"
          >
            {{ $t('site.navMore') }}
            <Icon class="h-3.5 w-3.5" name="arrow-down"/>
          </button>

          <div
            v-if="moreOpen"
            class="absolute left-0 z-50 mt-1 w-40 rounded-card border border-line bg-surface p-1 shadow-lg"
          >
            <NuxtLink
              v-for="item in MORE_NAV"
              :key="item.to"
              :aria-current="isActive(item.to) ? 'page' : undefined"
              :class="isActive(item.to) ? 'font-medium text-fg' : 'text-fg-muted hover:text-fg'"
              :to="item.to"
              class="block rounded-control px-3 py-1.5 text-sm transition-colors hover:bg-surface-soft"
              @click="moreOpen = false"
            >
              {{ item.label }}
            </NuxtLink>
          </div>
        </div>
      </nav>

      <div class="ml-auto flex items-center gap-1">
        <NuxtLink
          class="inline-flex h-9 w-9 items-center justify-center rounded-control text-fg-muted transition-colors hover:bg-surface-soft hover:text-fg"
          :aria-label="$t('site.navSearch')"
          to="/search"
        >
          <Icon class="h-4 w-4" name="search"/>
        </NuxtLink>

        <ThemeSwitcher/>

        <ClientOnly>
          <template #fallback>
            <NuxtLink
              class="hidden rounded-control px-3 py-1.5 text-sm text-fg-muted transition-colors hover:bg-surface-soft hover:text-fg md:inline-flex"
              to="/login"
            >
              {{ $t('login.loginButton') }}
            </NuxtLink>
          </template>

          <NuxtLink
            v-if="userStore.isLoggedIn"
            class="hidden max-w-[10rem] items-center gap-2 rounded-control px-3 py-1.5 text-sm text-fg transition-colors hover:bg-surface-soft md:inline-flex"
            to="/profile"
          >
            <span class="truncate">{{ userStore.displayName }}</span>
          </NuxtLink>
          <NuxtLink
            v-else
            class="hidden rounded-control px-3 py-1.5 text-sm text-fg-muted transition-colors hover:bg-surface-soft hover:text-fg md:inline-flex"
            to="/login"
          >
            {{ $t('login.loginButton') }}
          </NuxtLink>
        </ClientOnly>

        <button
          :aria-controls="mobileOpen ? 'site-mobile-nav' : undefined"
          :aria-expanded="mobileOpen"
          :aria-label="mobileOpen ? $t('site.closeMenuAriaLabel') : $t('site.menuAriaLabel')"
          class="inline-flex h-9 w-9 items-center justify-center rounded-control text-fg-muted hover:bg-surface-soft md:hidden"
          type="button"
          @click="mobileOpen = !mobileOpen"
        >
          <Icon :name="mobileOpen ? 'x' : 'menu'" class="h-5 w-5"/>
        </button>
      </div>
    </div>

    <!-- 移动端抽屉：带过渡，打开时锁滚动，Esc 可关 -->
    <Transition name="sheet">
      <nav
        v-if="mobileOpen"
        id="site-mobile-nav"
        :aria-label="$t('site.menuAriaLabel')"
        class="border-t border-line bg-surface md:hidden"
      >
        <NuxtLink
          v-for="item in ALL_NAV"
          :key="item.to"
          :aria-current="isActive(item.to) ? 'page' : undefined"
          :class="isActive(item.to) ? 'font-medium text-fg' : 'text-fg-muted hover:bg-surface-soft'"
          :to="item.to"
          class="block px-4 py-2.5 text-sm"
          @click="closeMenus"
        >
          {{ item.label }}
        </NuxtLink>
        <ClientOnly>
          <NuxtLink
            v-if="userStore.isLoggedIn"
            class="block px-4 py-2.5 text-sm text-fg-muted hover:bg-surface-soft"
            to="/profile"
            @click="closeMenus"
          >
            {{ $t('user.center') }}
          </NuxtLink>
        </ClientOnly>
      </nav>
    </Transition>
  </header>
</template>

<style scoped>
.sheet-enter-active,
.sheet-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.sheet-enter-from,
.sheet-leave-to {
  opacity: 0;
  transform: translateY(-0.5rem);
}
</style>
