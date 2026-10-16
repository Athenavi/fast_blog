<script lang="ts" setup>
/**
 * 区块：site-footer —— 页脚
 *
 * 参数：`copyright`（自定义版权文案；不填则用「站点名 + 当前年」）、
 * `showPoweredBy`（布尔，默认 false）。
 *
 * 站点名取自 `useSiteInfo()`；年份在**渲染时**取（SSR 与客户端同一次渲染内一致）。
 */
import {useSiteInfo} from '@/composables/useSiteInfo'

import type {BlockContext} from './types'

const props = defineProps<{
  propsData: Record<string, unknown>
  context: BlockContext
  blockClass?: string
}>()

const site = await useSiteInfo()

const copyright = computed(() => {
  const raw = props.propsData.copyright
  if (typeof raw === 'string' && raw.trim()) return raw
  return `© ${new Date().getFullYear()} ${site.value.site_name || 'FastBlog'}`
})

const showPoweredBy = computed(() => props.propsData.showPoweredBy === true)
</script>

<template>
  <footer :class="['border-t border-line bg-surface-soft', props.blockClass]">
    <div class="mx-auto flex max-w-wide flex-col gap-2 px-4 py-8">
      <p class="t-muted text-sm">{{ copyright }}</p>
      <p v-if="showPoweredBy" class="t-muted text-xs">Powered by FastBlog</p>
    </div>
  </footer>
</template>
