<script lang="ts" setup>
/** 前台顶部导航：站点名 + 主导航 + 搜索入口 */
import {Menu, Search} from '@lucide/vue'

const props = defineProps<{ siteName?: string }>()

const NAV = [
  {label: '首页', to: '/'},
  {label: '文章', to: '/articles'},
  {label: '分类', to: '/categories'},
  {label: '关于', to: '/about'},
]

const mobileOpen = ref(false)
const route = useRoute()
const isActive = (to: string) => (to === '/' ? route.path === '/' : route.path.startsWith(to))
</script>

<template>
  <header class="sticky top-0 z-40 w-full border-b border-slate-200 bg-white/85 backdrop-blur">
    <div class="mx-auto flex h-14 max-w-5xl items-center gap-4 px-4">
      <NuxtLink class="text-lg font-semibold tracking-tight text-slate-900" to="/">
        {{ props.siteName || 'FastBlog' }}
      </NuxtLink>

      <nav class="hidden items-center gap-1 md:flex">
        <NuxtLink
          v-for="item in NAV"
          :key="item.to"
          :class="isActive(item.to) ? 'bg-slate-100 font-medium text-slate-900' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'"
          :to="item.to"
          class="rounded-md px-3 py-1.5 text-sm transition-colors"
        >
          {{ item.label }}
        </NuxtLink>
      </nav>

      <div class="ml-auto flex items-center gap-2">
        <NuxtLink
          aria-label="搜索"
          class="inline-flex h-9 w-9 items-center justify-center rounded-md text-slate-600 transition-colors hover:bg-slate-100"
          to="/search"
        >
          <Search class="h-4 w-4"/>
        </NuxtLink>
        <NuxtLink
          class="hidden rounded-md px-3 py-1.5 text-sm text-slate-600 transition-colors hover:bg-slate-100 md:inline-flex"
          to="/login"
        >
          登录
        </NuxtLink>
        <button
          aria-label="菜单"
          class="inline-flex h-9 w-9 items-center justify-center rounded-md text-slate-600 hover:bg-slate-100 md:hidden"
          @click="mobileOpen = !mobileOpen"
        >
          <Menu class="h-5 w-5"/>
        </button>
      </div>
    </div>

    <nav v-if="mobileOpen" class="border-t border-slate-200 md:hidden">
      <NuxtLink
        v-for="item in NAV"
        :key="item.to"
        :to="item.to"
        class="block px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50"
        @click="mobileOpen = false"
      >
        {{ item.label }}
      </NuxtLink>
    </nav>
  </header>
</template>
