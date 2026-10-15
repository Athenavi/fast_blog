<script lang="ts" setup>
/**
 * 翻译管理（`/system/translation`，system 域）—— 页面壳
 *
 * 对齐后端 27 个端点（`modules/system/translation/controller.py`），按 el-tabs 分 6 组：
 *   1. 语言与区域  2. 词条与语言包  3. 统计与进度
 *   4. 翻译记忆库  5. 机器翻译      6. 导入导出
 *
 * **本文件现在只负责标签容器与一处跨标签共享状态**：六个标签页的内容已各自拆成
 * `components/admin/Translation*Panel.vue`。
 *
 * 跨标签共享的是 `languageList`：它由「语言与区域」标签页加载并展示，同时被
 * 「词条与语言包」「统计与进度」「导入导出」三个标签页的下拉用来过滤，所以留在页面，
 * 用 `v-model:languages` 双向绑定到语言面板，其余面板只读。原页面还有个 `ensureLanguages`
 * 兜底（切到词条 / 导入导出时若列表为空则补拉一次），也留在页面，由子面板用
 * `ensure-languages` 事件触发。
 *
 * 加载时机与原实现等价。原页面用 `onMounted` + `@tab-change`（`openTab`）按标签懒加载，
 * 并用 `loadedTabs` 去重；现在每个面板改用 `active` 属性 + `watch(immediate)` 还原
 * 「切到该标签才加载」，并各自保留同名的本地 `loaded` 标记去重 —— 默认标签
 * 「语言与区域」挂载即加载，其余标签切到才加载，都只加载一次。
 *
 * 权限：本模块无专用权限码，主权限取 `module_system:setting:view`，写操作用
 * `module_system:setting:edit`（按钮级用 `v-auth`）。机器翻译未配置密钥的诚实降级由
 * `TranslationMtPanel` 负责。
 *
 * 顺带删掉一个死常量：原页面的 `statusTagType` 定义了却从未被引用。
 */
import {type LanguageItem, translationApi} from '@/api'
import {ref} from 'vue'

import TranslationEntriesPanel from '@/components/admin/TranslationEntriesPanel.vue'
import TranslationIoPanel from '@/components/admin/TranslationIoPanel.vue'
import TranslationLanguagesPanel from '@/components/admin/TranslationLanguagesPanel.vue'
import TranslationMemoryPanel from '@/components/admin/TranslationMemoryPanel.vue'
import TranslationMtPanel from '@/components/admin/TranslationMtPanel.vue'
import TranslationProgressPanel from '@/components/admin/TranslationProgressPanel.vue'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.translation.title',
  permission: 'module_system:setting:view',
})

/** 当前标签页（六个标签页的内容各自独立成组件，见文件头说明） */
const activeTab = ref('languages')

/**
 * 语言列表 —— **唯一的跨标签共享状态**。
 *
 * 由「语言与区域」标签页加载并展示；「词条与语言包」「统计与进度」「导入导出」的下拉
 * 都要靠它过滤，所以放在页面而不是塞进某个面板里。
 */
const languageList = ref<LanguageItem[]>([])

/**
 * 兜底加载语言列表。
 *
 * 原 `openTab` 在切到「词条与语言包」/「导入导出」时会调它：只有当列表还空着
 * （例如「语言与区域」那次加载失败了）才补拉一次，避免下拉没有可选项。
 */
async function ensureLanguages(): Promise<void> {
  if (languageList.value.length) return
  const [langs] = await Promise.allSettled([translationApi.languages()])
  if (langs.status === 'fulfilled') languageList.value = langs.value
}
</script>

<template>
  <AdminPage :desc="$t('admin.system.translation.desc')" :title="$t('admin.system.translation.title')">
    <el-tabs v-model="activeTab">
      <!-- 1. 语言与区域 -->
      <el-tab-pane :label="$t('admin.system.translation.tabs.languages')" name="languages">
        <TranslationLanguagesPanel
          v-model:languages="languageList"
          :active="activeTab === 'languages'"
        />
      </el-tab-pane>

      <!-- 2. 词条与语言包 -->
      <el-tab-pane :label="$t('admin.system.translation.tabs.entries')" name="entries">
        <TranslationEntriesPanel
          :active="activeTab === 'entries'"
          :languages="languageList"
          @ensure-languages="ensureLanguages"
        />
      </el-tab-pane>

      <!-- 3. 统计与进度 -->
      <el-tab-pane :label="$t('admin.system.translation.tabs.progress')" name="progress">
        <TranslationProgressPanel :active="activeTab === 'progress'" :languages="languageList"/>
      </el-tab-pane>

      <!-- 4. 翻译记忆库 -->
      <el-tab-pane :label="$t('admin.system.translation.tabs.memory')" name="memory">
        <TranslationMemoryPanel :active="activeTab === 'memory'"/>
      </el-tab-pane>

      <!-- 5. 机器翻译 -->
      <el-tab-pane :label="$t('admin.system.translation.tabs.mt')" name="mt">
        <TranslationMtPanel :active="activeTab === 'mt'"/>
      </el-tab-pane>

      <!-- 6. 导入导出 -->
      <el-tab-pane :label="$t('admin.system.translation.tabs.io')" name="io">
        <TranslationIoPanel
          :active="activeTab === 'io'"
          :languages="languageList"
          @ensure-languages="ensureLanguages"
        />
      </el-tab-pane>
    </el-tabs>
  </AdminPage>
</template>
