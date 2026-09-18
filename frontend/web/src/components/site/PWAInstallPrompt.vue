<script lang="ts" setup>
/**
 * PWA 安装提示
 *
 * 对应原 astro 的 `PWAInstallPrompt.tsx`。
 *
 * 实现要点：浏览器在"可安装"时会触发 `beforeinstallprompt`，必须先 `preventDefault()`
 * 才能自己接管弹窗时机；用户拒绝后记到 localStorage，避免反复打扰。
 * 这些是浏览器原生事件，**无需任何依赖**（PWA 的 manifest/SW 由 `@vite-pwa/nuxt` 提供）。
 */
const PROMPT_KEY = 'fb-pwa-dismissed'

const deferred = ref<{ prompt: () => Promise<void>; userChoice?: Promise<unknown> } | null>(null)
const visible = ref(false)
const installing = ref(false)

function onBeforeInstall(event: Event): void {
  // 阻止浏览器自带的迷你提示条，改用我们的弹窗
  event.preventDefault()
  deferred.value = event as never
  if (!localStorage.getItem(PROMPT_KEY)) visible.value = true
}

function onInstalled(): void {
  visible.value = false
  deferred.value = null
}

async function install(): Promise<void> {
  if (!deferred.value) return
  installing.value = true
  try {
    await deferred.value.prompt()
    visible.value = false
  } finally {
    installing.value = false
    deferred.value = null
  }
}

function dismiss(): void {
  visible.value = false
  localStorage.setItem(PROMPT_KEY, '1')
}

onMounted(() => {
  window.addEventListener('beforeinstallprompt', onBeforeInstall)
  window.addEventListener('appinstalled', onInstalled)
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeinstallprompt', onBeforeInstall)
  window.removeEventListener('appinstalled', onInstalled)
})
</script>

<template>
  <ClientOnly>
    <div
      v-if="visible"
      aria-label="安装应用"
      class="fixed bottom-4 left-1/2 z-50 w-[min(92vw,26rem)] -translate-x-1/2 rounded-card border border-line bg-surface p-4 shadow-lg"
      role="dialog"
    >
      <div class="flex items-start gap-3">
        <img alt="" class="h-10 w-10 flex-shrink-0 rounded-control" src="/icon.svg">

        <div class="min-w-0 flex-1">
          <p class="text-sm font-medium text-fg">把 FastBlog 装到桌面</p>
          <p class="mt-1 text-xs leading-relaxed text-fg-muted">
            安装后可全屏阅读、支持离线缓存，启动更快。
          </p>
        </div>

        <button
          aria-label="关闭"
          class="inline-flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-control text-fg-subtle transition-colors hover:bg-surface-soft hover:text-fg"
          type="button"
          @click="dismiss"
        >
          <Icon class="h-4 w-4" name="x"/>
        </button>
      </div>

      <div class="mt-3 flex justify-end gap-2">
        <Button size="sm" variant="outline" @click="dismiss">以后再说</Button>
        <Button :disabled="installing" size="sm" @click="install">
          <Icon v-if="installing" class="h-4 w-4 animate-spin" name="loader-circle"/>
          {{ installing ? '安装中…' : '立即安装' }}
        </Button>
      </div>
    </div>
  </ClientOnly>
</template>
