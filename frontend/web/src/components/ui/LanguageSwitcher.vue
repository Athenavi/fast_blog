<script lang="ts" setup>
/**
 * 语言切换器
 *
 * 用 `@nuxtjs/i18n` 的 `setLocale()` 切换语言 —— 因为配置是 `strategy: 'no_prefix'`，
 * URL 保持不变，所以这是纯客户端行为，不需要跳转。
 *
 * 用**原生 `<select>`** 而不是 Element Plus 的 `el-dropdown`：这样同一个组件
 * 在前台（Tailwind 令牌语境）和后台（Element Plus 语境）都能直接使用，
 * 不用为了一个下拉去耦合 UI 库。样式只引用语义令牌。
 *
 * 对应 astro 版 `components/LanguageSwitcher.tsx` —— 那边是 i18n 尚未启用时的占位实现。
 */
const {locale, locales, setLocale} = useI18n()

const options = computed(() =>
  (locales.value as Array<{ code: string; name?: string }>).map((item) => ({
    code: item.code,
    name: item.name || item.code,
  })),
)

const current = computed(() => String(locale.value))

async function change(event: Event): Promise<void> {
  const code = (event.target as HTMLSelectElement).value
  if (code === current.value) return
  await setLocale(code as 'zh-CN' | 'en')
}
</script>

<template>
  <label :title="$t('common.language')" class="lang-switcher">
    <Icon class="lang-switcher__icon" name="languages"/>
    <select :value="current" class="lang-switcher__select" @change="change">
      <option v-for="item in options" :key="item.code" :value="item.code">{{ item.name }}</option>
    </select>
  </label>
</template>

<style scoped>
.lang-switcher {
  display: inline-flex;
  gap: 4px;
  align-items: center;
  padding: 2px 6px;
  color: var(--color-fg-muted);
  cursor: pointer;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-control);
}

.lang-switcher__icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.lang-switcher__select {
  font-size: 12px;
  color: inherit;
  cursor: pointer;
  background: transparent;
  border: none;
  outline: none;
}
</style>
