<script lang="ts" setup>
const {t} = useI18n()
/** 前台顶部导航（阅读优先：窄容器、克制的分割线、克制的动效） */

import {useUserStore} from '@/store/modules/user'

const props = defineProps<{ siteName?: string }>()

const userStore = useUserStore()

const NAV = [
  {label: t('site.navHome'), to: '/'},
  {label: t('site.navArticles'), to: '/articles'},
  {label: t('site.navCategories'), to: '/categories'},
  {label: t('site.navPoints'), to: '/points'},
  {label: t('site.navBadges'), to: '/badges'},
  {label: t('site.navAbout'), to: '/about'},
]

const mobileOpen = ref(false)
const route = useRoute()
const isActive = (to: string) => (to === '/' ? route.path === '/' : route.path.startsWith(to))
</script>

<template>
  <header class="sticky top-0 z-40 border-b border-line bg-surface/85 backdrop-blur">
    <div class="mx-auto flex h-14 max-w-wide items-center gap-4 px-4">
      <NuxtLink class="text-base font-semibold tracking-tight text-fg" to="/">
        {{ props.siteName || 'FastBlog' }}
      </NuxtLink>

      <nav class="hidden items-center gap-1 md:flex">
        <NuxtLink
          v-for="item in NAV"
          :key="item.to"
          :to="item.to"
          :class="isActive(item.to) ? 'bg-surface-soft font-medium text-fg' : 'text-fg-muted hover:bg-surface-soft hover:text-fg'"
          class="rounded-control px-3 py-1.5 text-sm transition-colors"
        >
          {{ item.label }}
        </NuxtLink>
      </nav>

      <div class="ml-auto flex items-center gap-1">
        <NuxtLink
          class="inline-flex h-9 w-9 items-center justify-center rounded-control text-fg-muted transition-colors hover:bg-surface-soft hover:text-fg"
          :aria-label="$t('admin.common.search')"
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
          :aria-label="$t('site.menuAriaLabel')"
          class="inline-flex h-9 w-9 items-center justify-center rounded-control text-fg-muted hover:bg-surface-soft md:hidden"
          @click="mobileOpen = !mobileOpen"
        >
          <Icon class="h-5 w-5" name="menu"/>
        </button>
      </div>
    </div>

    <nav v-if="mobileOpen" class="border-t border-line md:hidden">
      <NuxtLink
        v-for="item in NAV"
        :key="item.to"
        :to="item.to"
        class="block px-4 py-2.5 text-sm text-fg-muted hover:bg-surface-soft"
        @click="mobileOpen = false"
      >
        {{ item.label }}
      </NuxtLink>
      <ClientOnly>
        <NuxtLink
          v-if="userStore.isLoggedIn"
          class="block px-4 py-2.5 text-sm text-fg-muted hover:bg-surface-soft"
          to="/profile"
          @click="mobileOpen = false"
        >
          {{ $t('user.center') }}
        </NuxtLink>
      </ClientOnly>
    </nav>
  </header>
</template>
