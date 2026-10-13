<script lang="ts" setup>
/**
 * 响应式图片（性能优先版）
 *
 * **为什么不再用 `@nuxt/image`**：后端已提供内容寻址的变体端点
 * `/api/v3/content/media/{id}/variant/{thumb|small|medium|large}`，它自带
 * * 真实宽度档位（200/480/800/1600）与 `srcset` 描述符一一对应；
 * * `Accept` 协商（avif → webp → 原格式，响应带 `Vary: Accept`），同一 URL 即可
 *   让浏览器自动取最小够用的格式，无需 `<picture>` 再写多份 `<source>`；
 * * 内容寻址落盘 + 懒生成，服务端只编码一次、所有客户端复用。
 * 交给 `@nuxt/image` 反而多一层处理且拿不到这些能力，所以这里直接手写 `srcset`。
 *
 * 性能要点：`srcset`+`sizes` 让浏览器按视口/DPR 取最小够用尺寸；显式 `width/height`
 * 消除 CLS；首屏 `eager` 配 `fetchpriority=high`，其余 `lazy`+`async` 解码。
 *
 * 用法（与旧版完全一致）：
 * ```vue
 * <ResponsiveImage src="/api/v3/content/media/1/file" alt="封面" aspect="16/9" sizes="sm:100vw md:50vw lg:33vw"/>
 * ```
 */
import {cn} from '@/lib/utils'

const props = withDefaults(
  defineProps<{
    src?: string | null
    alt?: string
    /** 宽高比，如 '16/9'；用于占位与 width/height 推导，避免布局跳动 */
    aspect?: string
    /** 断点提示，兼容原有写法（'xs:100vw sm:50vw lg:33vw'），内部转成标准 CSS sizes */
    sizes?: string
    class?: string
    /** 首屏图片设为 true */
    eager?: boolean
    /** 圆角等由外层控制，这里只追加额外类 */
    rounded?: string
  }>(),
  {alt: '', aspect: '16/9', sizes: 'xs:100vw sm:50vw lg:33vw', eager: false, rounded: ''},
)

/** 与后端 `content/media/variants.py` 的 SIZES 保持一致（名称 → 最大宽度） */
const VARIANT_SIZES: Array<[string, number]> = [
  ['thumb', 200],
  ['small', 480],
  ['medium', 800],
  ['large', 1600],
]

/** 断点名 → CSS 最小宽度（与 Tailwind 默认断点一致） */
const BREAKPOINTS: Record<string, string> = {
  xs: '0px',
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
}

const failed = ref(false)
const loaded = ref(false)

const isRemote = computed(() => /^https?:\/\//.test(props.src ?? ''))

/** 从 `/api/v3/content/media/{id}/file` 解析媒体 ID；非媒体库 URL 返回 null */
const mediaId = computed(() => {
  const matched = /\/content\/media\/(\d+)\//.exec(props.src ?? '')
  return matched ? matched[1] : null
})

/** 只有媒体库图片才有多档变体；外链图片保持原样输出 */
const srcset = computed(() => {
  if (!mediaId.value) return undefined
  return VARIANT_SIZES.map(([name, width]) => `/api/v3/content/media/${mediaId.value}/variant/${name} ${width}w`).join(
    ', ',
  )
})

/** 无 `srcset` 支持时的兜底：中间档 */
const resolvedSrc = computed(() =>
  mediaId.value ? `/api/v3/content/media/${mediaId.value}/variant/medium` : (props.src ?? ''),
)

/** 把 'xs:100vw sm:50vw lg:33vw' 转成标准 `sizes`（大断点在前，末项兜底） */
const cssSizes = computed(() => {
  const entries = (props.sizes ?? '')
    .split(/\s+/)
    .filter(Boolean)
    .map((token) => {
      const [key, width] = token.includes(':') ? token.split(':') : ['', token]
      return {min: BREAKPOINTS[key ?? ''] ?? null, width: width ?? token}
    })

  const conditional = entries
    .filter((item): item is { min: string; width: string } => Boolean(item.min) && item.min !== '0px')
    .sort((a, b) => Number.parseFloat(b.min) - Number.parseFloat(a.min))
    .map((item) => `(min-width: ${item.min}) ${item.width}`)

  const fallback = entries.find((item) => !item.min || item.min === '0px')?.width ?? '100vw'
  return [...conditional, fallback].join(', ')
})

/** 由 aspect 推导固有尺寸（防 CLS），宽度取最大档上限 */
const dimensions = computed(() => {
  const [w, h] = (props.aspect ?? '16/9').split('/').map(Number)
  const width = VARIANT_SIZES[VARIANT_SIZES.length - 1]![1]
  const height = w && h ? Math.round((width * h) / w) : Math.round(width * (9 / 16))
  return {width, height}
})

/** 用普通对象挂 fetchpriority：HTML 标准属性，直接写在模板上 vue-tsc 会报类型错 */
const extraAttrs = computed<Record<string, string>>(() => ({
  fetchpriority: props.eager ? 'high' : 'auto',
}))
</script>

<template>
  <div
    :class="cn('relative overflow-hidden bg-surface-soft', props.rounded, props.class)"
    :style="{aspectRatio: props.aspect}"
  >
    <!-- 媒体库图片：多档变体 + Accept 协商格式（外链图片不带 srcset，原样输出） -->
    <img
      v-if="props.src && !failed"
      :class="[loaded ? 'opacity-100' : 'opacity-0', 'h-full w-full object-cover transition-opacity duration-300']"
      :alt="props.alt"
      :decoding="props.eager ? 'sync' : 'async'"
      :height="isRemote ? undefined : dimensions.height"
      :sizes="srcset ? cssSizes : undefined"
      :loading="props.eager ? 'eager' : 'lazy'"
      :src="resolvedSrc"
      :srcset="srcset"
      :width="isRemote ? undefined : dimensions.width"
      v-bind="extraAttrs"
      @error="failed = true"
      @load="loaded = true"
    >

    <Skeleton v-if="props.src && !loaded && !failed" class="absolute inset-0 h-full w-full"/>

    <div v-if="!props.src || failed" class="absolute inset-0 flex items-center justify-center">
      <Icon class="h-6 w-6 text-fg-subtle" name="image"/>
    </div>
  </div>
</template>
