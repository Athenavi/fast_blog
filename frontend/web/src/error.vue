<script lang="ts" setup>
/**
 * Nuxt 全局错误页（404 / 500）
 *
 * Nuxt 用 `error.vue` 统一接管未匹配路由与运行时错误。
 * 这里只用 Tailwind + shadcn-vue 组件，因为前台错误页会在服务端渲染
 * （Element Plus 仅在客户端注册，不能用于 SSR 输出）。
 */
const props = defineProps<{
  error: { statusCode: number; statusMessage?: string; message?: string }
}>()

const isNotFound = computed(() => props.error?.statusCode === 404)
const title = computed(() => String(props.error?.statusCode ?? 500))
const subtitle = computed(() =>
  isNotFound.value
    ? '页面不存在或已被移除'
    : props.error?.statusMessage || props.error?.message || '服务异常，请稍后重试',
)

function goHome(): void {
  clearError({redirect: '/'})
}
</script>

<template>
  <div class="flex min-h-screen flex-col items-center justify-center gap-3 px-4 text-center">
    <p class="text-5xl font-bold tracking-tight text-slate-900">{{ title }}</p>
    <p class="max-w-md text-slate-500">{{ subtitle }}</p>
    <div class="mt-3 flex gap-3">
      <Button @click="goHome">返回首页</Button>
      <NuxtLink to="/articles">
        <Button variant="outline">浏览文章</Button>
      </NuxtLink>
    </div>
  </div>
</template>
