<script lang="ts" setup>
/**
 * 区块：site-header —— 页头
 *
 * 参数：`showTitle`（默认 true）、`showNav`（默认 true）、`sticky`（默认 false）。
 *
 * 站点名与导航取自 `useSiteInfo()` / `useSiteNav()` —— 与布局**同一份**数据，
 * 不额外发请求。这样主题重排页头时不会把首屏数据拉成两遍。
 */
import {useSiteInfo} from '@/composables/useSiteInfo'
import {useSiteNav} from '@/composables/useSiteNav'

import type {BlockContext} from './types'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

const site = await useSiteInfo()
const nav = await useSiteNav()

const showTitle = computed(() => props.propsData.showTitle !== false)
const showNav = computed(() => props.propsData.showNav !== false)
const stickyClass = computed(() => (props.propsData.sticky === true ? 'sticky top-0 z-20' : ''))

const navItems = computed(() => nav.value ?? [])
</script>

<template>
  <header :class="['border-b border-line bg-surface', stickyClass, props.blockClass]">
    <div class="mx-auto flex max-w-wide items-center justify-between gap-4 px-4 py-4">
      <NuxtLink v-if="showTitle" class="text-lg font-semibold tracking-tight text-fg" to="/">
        {{ site.site_name || 'FastBlog' }}
      </NuxtLink>

      <nav v-if="showNav && navItems.length" class="flex flex-wrap gap-4">
        <NuxtLink
          v-for="item in navItems"
          :key="item.url"
          :to="item.url"
          class="t-muted text-sm transition-colors hover:text-fg"
        >
          {{ item.title }}
        </NuxtLink>
      </nav>
    </div>
  </header>
</template>
