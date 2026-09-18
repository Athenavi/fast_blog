<script lang="ts" setup>
import {computed, defineAsyncComponent} from 'vue'

/**
 * 插件后台页面宿主（Nuxt 版）
 *
 * 对应 astro 侧由 scripts/scan-plugin-frontend.mjs 生成的 proxy 页面：
 * 插件的 manifest 把后台页统一登记在 `/admin/plugin-pages/<slug>`，
 * 这里按 slug 找到路由登记并动态加载对应组件。
 *
 * 迁移状态：插件页面组件正从 React（.tsx）分批重写为 Vue（.vue）。
 * 没有同名 .vue 的插件显示「待迁移」占位；原 React 实现仍在
 * `plugins/<slug>/frontend/`，不受影响。
 *
 * `.plugin-registry.ts` / `.plugin-pages/_loader.ts` 由 prescan 生成
 * （见 package.json 的 prescan / prebuild / predev），仓库不提交。
 */
import {pluginPageModules} from '~/.plugin-pages/_loader'
import {pluginNavItems, pluginPageRoutes} from '~/.plugin-registry'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
})

const route = useRoute()

const slug = computed(() => String(route.params.slug ?? ''))

const current = computed(
  () => pluginPageRoutes.find((item) => item.slug === slug.value) ?? null,
)

const currentNav = computed(
  () => pluginNavItems.find((item) => item.slug === slug.value) ?? null,
)

const title = computed(() => current.value?.title || currentNav.value?.label || slug.value)

/** 同目录下的兄弟页面（同一插件的其他路由），用于页面内导航 */
const siblings = computed(() => pluginPageRoutes.filter((item) => item.slug === slug.value))

/** manifest 的 component 形如 './admin/Page.tsx'，Vue 版取同名 .vue */
const asyncComponent = computed(() => {
  const page = current.value
  if (!page) return null
  const rel = page.component.replace(/^\.\//, '').replace(/\.tsx?$/, '.vue')
  const loader = pluginPageModules[`./${page.slug}/${rel}`]
  return loader ? defineAsyncComponent(loader) : null
})
</script>

<template>
  <div class="plugin-page-host">
    <el-breadcrumb separator="/">
      <el-breadcrumb-item>{{ $t('admin.pluginPages.plugins') }}</el-breadcrumb-item>
      <el-breadcrumb-item>{{ title }}</el-breadcrumb-item>
    </el-breadcrumb>

    <div class="plugin-page-host__body">
      <component :is="asyncComponent" v-if="asyncComponent"/>

      <el-empty v-else-if="current" :description="$t('admin.pluginPages.notMigrated', {title})">
        <p class="plugin-page-host__hint">
          {{ $t('admin.pluginPages.originalReact') }} <code>{{
            current.component
          }}</code>{{ $t('admin.pluginPages.locatedAt') }}<code>plugins/{{ slug }}/frontend/</code>.
        </p>
        <p class="plugin-page-host__hint">
          {{ $t('admin.pluginPages.rewriteHint') }}
        </p>
        <p v-if="siblings.length > 1" class="plugin-page-host__hint">
          {{ $t('admin.pluginPages.otherRoutes', {routes: siblings.map((item) => item.path).join('、')}) }}
        </p>
      </el-empty>

      <el-empty v-else :description="$t('admin.pluginPages.pluginPageNotFound')"/>
    </div>
  </div>
</template>

<style scoped>
.plugin-page-host {
  padding: 16px;
}

.plugin-page-host__body {
  margin-top: 16px;
}

.plugin-page-host__hint {
  margin: 4px 0;
  font-size: 13px;
  opacity: 0.75;
}
</style>
