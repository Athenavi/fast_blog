<script lang="ts" setup>
/**
 * 延迟加载图片（含占位骨架）
 *
 * 对应原 astro 的 `SkeletonProvider.tsx` 里的 `LazyImage`。
 *
 * 命名注意：不要用 `Lazy*` 前缀——那是 Nuxt 给动态导入组件保留的（`<LazyXxx>`）。
 *
 * 为什么不用 `@nuxt/image`：那个模块的价值是自动 srcset/格式转换（需要图像处理服务），
 * 而这里要解决的是「进入视口才加载 + 加载前不跳动」，用 IntersectionObserver + CSS
 * `aspect-ratio` 就能做到，**零新增依赖**。将来接入图像服务时替换本组件即可。
 */
import {cn} from '@/lib/utils'

const props = withDefaults(
  defineProps<{
    src?: string | null
    alt?: string
    /** 占位比例，如 '16/9'；用于避免加载时布局跳动 */
    aspect?: string
    class?: string
    /** 首屏图片可设 true，跳过懒加载 */
    eager?: boolean
  }>(),
  {alt: '', aspect: '16/9', eager: false},
)

const root = ref<HTMLElement | null>(null)
const inView = ref(false)
const loaded = ref(false)
const failed = ref(false)
let observer: IntersectionObserver | null = null

onMounted(() => {
  // 首屏图、或不支持 IntersectionObserver 时直接加载
  if (props.eager || typeof IntersectionObserver === 'undefined') {
    inView.value = true
    return
  }
  observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        inView.value = true
        observer?.disconnect()
        observer = null
      }
    },
    // 提前 240px 预加载，滚动时不易看到空位
    {rootMargin: '240px 0px'},
  )
  if (root.value) observer.observe(root.value)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
})
</script>

<template>
  <div
    ref="root"
    :class="cn('relative overflow-hidden bg-surface-soft', props.class)"
    :style="{aspectRatio: props.aspect}"
  >
    <img
      v-if="inView && props.src && !failed"
      :alt="props.alt"
      :class="loaded ? 'opacity-100' : 'opacity-0'"
      :src="props.src"
      class="h-full w-full object-cover transition-opacity duration-300"
      decoding="async"
      loading="lazy"
      @error="failed = true"
      @load="loaded = true"
    >

    <Skeleton v-if="!loaded && !failed" class="absolute inset-0 h-full w-full"/>

    <div v-if="failed" class="absolute inset-0 flex items-center justify-center">
      <Icon class="h-6 w-6 text-fg-subtle" name="image"/>
    </div>
  </div>
</template>
