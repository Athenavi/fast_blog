<script lang="ts" setup>
/**
 * 外观切换：深浅色 + 自选主色
 *
 * 唯一允许出现「字面色值」的地方——配色圆点必须显示该配色本身的颜色，
 * 无法用语义令牌表达。其余组件一律使用令牌。
 */

import {ACCENTS, THEME_MODES, useTheme} from '@/composables/useTheme'
import {cn} from '@/lib/utils'

const {theme, accent, isDark, setTheme, setAccent} = useTheme()

const open = ref(false)

/** 预览色：仅用于色板示意 */
const ACCENT_SWATCH: Record<string, string> = {
  blue: '#2f6fed',
  violet: '#7c3aed',
  emerald: '#0d9f6e',
  rose: '#e11d48',
  amber: '#d97706',
}

const MODE_ICON = {light: 'sun', dark: 'moon', system: 'monitor'} as const

function close(): void {
  open.value = false
}

// 生命周期钩子必须在 setup 同步阶段注册（不能嵌在 onMounted 回调内）
onMounted(() => document.addEventListener('click', close))
onBeforeUnmount(() => document.removeEventListener('click', close))
</script>

<template>
  <ClientOnly>
    <div class="relative" @click.stop>
      <button
        :aria-label="$t('site.themeSettingsAria')"
        class="inline-flex h-9 w-9 items-center justify-center rounded-control text-fg-muted transition-colors hover:bg-surface-soft hover:text-fg"
        type="button"
        @click="open = !open"
      >
        <Icon v-if="!isDark" class="h-4 w-4" name="sun"/>
        <Icon v-else class="h-4 w-4" name="moon"/>
      </button>

      <div
        v-if="open"
        class="absolute right-0 z-50 mt-2 w-56 rounded-card border border-line bg-surface p-2 shadow-lg"
      >
        <p class="px-2 py-1.5 text-xs font-medium text-fg-subtle">{{ $t('site.appearanceLabel') }}</p>
        <button
          v-for="item in THEME_MODES"
          :key="item.value"
          :class="theme === item.value ? 'text-fg' : 'text-fg-muted'"
          class="flex w-full items-center gap-2 rounded-control px-2 py-1.5 text-sm transition-colors hover:bg-surface-soft"
          type="button"
          @click="setTheme(item.value)"
        >
          <Icon :name="MODE_ICON[item.value]" class="h-4 w-4"/>
          <span>{{ $t(`site.${item.labelKey}`) }}</span>
          <Icon v-if="theme === item.value" class="ml-auto h-4 w-4 text-primary" name="check"/>
        </button>

        <div class="my-2 border-t border-line"/>

        <p class="flex items-center gap-1.5 px-2 py-1.5 text-xs font-medium text-fg-subtle">
          <Icon class="h-3.5 w-3.5" name="palette"/>
          {{ $t('site.accentLabel') }}
        </p>
        <div class="flex items-center gap-2 px-2 py-1.5">
          <button
            v-for="item in ACCENTS"
            :key="item.value"
            :aria-label="$t(`site.${item.labelKey}`)"
            :class="cn('ring-2', accent === item.value ? 'ring-line-strong' : 'ring-transparent')"
            :style="{backgroundColor: ACCENT_SWATCH[item.value]}"
            :title="$t(`site.${item.labelKey}`)"
            class="h-6 w-6 rounded-full ring-offset-2 ring-offset-surface transition-all"
            type="button"
            @click="setAccent(item.value)"
          />
        </div>
      </div>
    </div>

    <template #fallback>
      <span class="inline-block h-9 w-9"/>
    </template>
  </ClientOnly>
</template>
