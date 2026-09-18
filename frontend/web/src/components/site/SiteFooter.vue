<script lang="ts" setup>
const props = defineProps<{ siteName?: string; footer?: string; icp?: string }>()
const year = new Date().getFullYear()
</script>

<template>
  <footer class="border-t border-line bg-surface-soft">
    <div
      class="mx-auto flex max-w-wide flex-col gap-2 px-4 py-8 text-sm text-fg-muted sm:flex-row sm:items-center sm:justify-between">
      <p>© {{ year }} {{ props.siteName || 'FastBlog' }}</p>
      <p v-if="props.footer" class="text-fg-subtle">{{ props.footer }}</p>
      <a
        v-if="props.icp"
        class="text-fg-subtle transition-colors hover:text-fg-muted"
        href="https://beian.miit.gov.cn"
        rel="noopener"
        target="_blank"
      >
        {{ props.icp }}
      </a>
    </div>
  </footer>
</template>
