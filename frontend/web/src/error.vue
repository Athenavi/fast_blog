<script lang="ts" setup>
/**
 * 全局错误页（404 / 500）
 *
 * Nuxt 用 `error.vue` 统一接管未匹配路由与运行时错误。
 * 内容参考了原 astro `404.astro`：给出搜索入口与推荐去向，而不是只有一句报错。
 * 只用 Tailwind + 语义令牌，保证 SSR 输出与主题切换都正确。
 */

const props = defineProps<{
  error: { statusCode: number; statusMessage?: string; message?: string }
}>()

const isNotFound = computed(() => props.error?.statusCode === 404)
const title = computed(() => String(props.error?.statusCode ?? 500))

const headline = computed(() => (isNotFound.value ? '哎呀，页面走丢了' : '服务出了点问题'))
const subtitle = computed(() =>
  isNotFound.value
    ? '页面不存在或已被移除，你可以搜索一下，或从下面的入口继续浏览。'
    : props.error?.statusMessage || props.error?.message || '请稍后重试，或返回首页。',
)

const keyword = ref('')

function goSearch(): void {
  const q = keyword.value.trim()
  if (!q) return
  clearError({redirect: `/search?q=${encodeURIComponent(q)}`})
}

function goHome(): void {
  clearError({redirect: '/'})
}
</script>

<template>
  <div class="flex min-h-screen flex-col items-center justify-center px-4 py-16 text-center">
    <p class="text-6xl font-bold tracking-tight text-fg">{{ title }}</p>
    <p class="mt-4 text-lg font-medium text-fg">{{ headline }}</p>
    <p class="mt-2 max-w-read text-sm leading-relaxed text-fg-muted">{{ subtitle }}</p>

    <form v-if="isNotFound" class="mt-8 flex w-full max-w-sm gap-2" @submit.prevent="goSearch">
      <Input v-model="keyword" placeholder="搜索文章…"/>
      <Button class="shrink-0" type="submit">
        <Icon class="h-4 w-4" name="search"/>
        搜索
      </Button>
    </form>

    <div class="mt-8 flex flex-wrap justify-center gap-3">
      <Button @click="goHome">返回首页</Button>
      <NuxtLink to="/articles">
        <Button variant="outline">浏览文章</Button>
      </NuxtLink>
      <NuxtLink to="/categories">
        <Button variant="outline">按分类浏览</Button>
      </NuxtLink>
    </div>
  </div>
</template>
