<script lang="ts" setup>
const props = defineProps<{ siteName?: string; footer?: string; icp?: string }>()
const year = new Date().getFullYear()
</script>

<template>
  <footer class="border-t border-slate-200 bg-slate-50">
    <div
      class="mx-auto flex max-w-5xl flex-col gap-2 px-4 py-8 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
      <p>© {{ year }} {{ props.siteName || 'FastBlog' }}. All rights reserved.</p>
      <p v-if="props.footer" class="text-slate-400">{{ props.footer }}</p>
      <a v-if="props.icp" class="text-slate-400 hover:text-slate-600" href="https://beian.miit.gov.cn" rel="noopener"
         target="_blank">
        {{ props.icp }}
      </a>
    </div>
  </footer>
</template>
