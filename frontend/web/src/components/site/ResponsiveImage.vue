<script lang="ts" setup>
/**
 * 响应式图片
 *
 * 对应原 astro 的 `ResponsiveImage.tsx`。
 *
 * astro 侧是自己拼 `srcset` + `IntersectionObserver`；Nuxt 里交给 **`@nuxt/image`**：
 * 它按 `screens` 生成多档宽度、按 `format` 输出 webp/avif、并自动处理 `loading` 与宽高比。
 * 因此这个组件的职责只剩「统一占位与比例」，不再重复实现图片处理。
 *
 * 用法：
 * ```vue
 * <ResponsiveImage src="/media/foo.jpg" alt="封面" aspect="16/9" sizes="sm:100vw md:50vw"/>
 * ```
 */
import {cn} from '@/lib/utils'

const props = withDefaults(
  defineProps<{
    src?: string | null
    alt?: string
    /** 宽高比，如 '16/9'；用于占位，避免加载时布局跳动 */
    aspect?: string
    /** 交给 @nuxt/image 的 sizes 提示 */
    sizes?: string
    class?: string
    /** 首屏图片设为 true */
    eager?: boolean
    /** 圆角等由外层控制，这里只追加额外类 */
    rounded?: string
  }>(),
  {alt: '', aspect: '16/9', sizes: 'xs:100vw sm:50vw lg:33vw', eager: false, rounded: ''},
)

const failed = ref(false)
const loaded = ref(false)

const isRemote = computed(() => /^https?:\/\//.test(props.src ?? ''))
</script>

<template>
  <div
    :class="cn('relative overflow-hidden bg-surface-soft', props.rounded, props.class)"
    :style="{aspectRatio: props.aspect}"
  >
    <!-- 本地/媒体库图片走 @nuxt/image 优化；外链图片原样输出 -->
    <NuxtImg
      v-if="props.src && !failed && !isRemote"
      :alt="props.alt"
      :class="loaded ? 'opacity-100' : 'opacity-0'"
      :loading="props.eager ? 'eager' : 'lazy'"
      :sizes="props.sizes"
      :src="props.src"
      class="h-full w-full object-cover transition-opacity duration-300"
      format="webp"
      @error="failed = true"
      @load="loaded = true"
    />

    <img
      v-else-if="props.src && !failed"
      :alt="props.alt"
      :src="props.src"
      class="h-full w-full object-cover"
      decoding="async"
      loading="lazy"
      @error="failed = true"
      @load="loaded = true"
    >

    <Skeleton v-if="props.src && !loaded && !failed" class="absolute inset-0 h-full w-full"/>

    <div v-if="!props.src || failed" class="absolute inset-0 flex items-center justify-center">
      <Icon class="h-6 w-6 text-fg-subtle" name="image"/>
    </div>
  </div>
</template>
