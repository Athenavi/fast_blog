<script lang="ts" setup>
/**
 * 后台页面壳：统一标题区（标题 / 描述 / 右侧操作）+ 内容间距。
 *
 * 用法：
 *   &lt;AdminPage :title="页面标题" :desc="页面描述"&gt;
 *     &lt;template #actions&gt;…右侧操作按钮…&lt;/template&gt;
 *     …内容…
 *   &lt;/AdminPage&gt;
 */
defineProps<{
  title?: string
  desc?: string
}>()
</script>

<template>
  <div class="admin-page">
    <header v-if="title || desc || $slots.actions" class="admin-page__header">
      <div>
        <h1 v-if="title" class="admin-page__title">{{ title }}</h1>
        <p v-if="desc" class="admin-page__desc">{{ desc }}</p>
      </div>
      <div v-if="$slots.actions" class="admin-page__actions">
        <slot name="actions"/>
      </div>
    </header>

    <slot/>
  </div>
</template>
