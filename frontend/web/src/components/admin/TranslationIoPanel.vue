<script lang="ts" setup>
/**
 * 翻译管理 · 导入导出面板
 *
 * 从 `pages/system/translation.vue` 的「导入导出」标签页抽出：导出词条（真实文件下载）、
 * 导入词条。
 *
 * ## 加载时机与原实现保持一致
 *
 * 原页面在 `@tab-change` 里**切到本标签才加载**，且只做一件事：`ensureLanguages()`
 * —— 兜底保证语言列表可用（导出下拉要靠它过滤；真正的导入导出都是用户点按钮才动）。
 * 这里用 `active` 属性 + `watch(immediate)` 还原，并保留原 `loadedTabs` 去重。
 *
 * 语言列表由页面持有，本组件只 `:languages` 读它；兜底加载通过 `ensure-languages`
 * 事件请页面去拉。
 */
import {Download, Upload} from '@element-plus/icons-vue'
import {reactive, ref, watch} from 'vue'

import {type LanguageItem, translationApi, type TranslationFormat} from '@/api'
import {ElMessage} from '@/utils/feedback'

const props = defineProps<{
  /** 本标签页是否激活 */
  active: boolean
  /** 语言列表（跨标签共享，由页面持有） */
  languages: LanguageItem[]
}>()

const emit = defineEmits<{
  /** 请页面兜底加载语言列表（导出下拉需要它，但加载与持有都在页面侧） */
  (e: 'ensure-languages'): void
}>()

const {t} = useI18n()

const STATUSES = ['translated', 'pending', 'reviewed'] as const
const FORMATS: TranslationFormat[] = ['json', 'csv', 'po', 'xliff', 'yaml']

function statusLabel(status: string): string {
  if (status === 'translated') return t('admin.system.translation.entries.statusTranslated')
  if (status === 'reviewed') return t('admin.system.translation.entries.statusReviewed')
  return t('admin.system.translation.entries.statusPending')
}

const exportForm = reactive<{ locale: string; format: TranslationFormat }>({locale: '', format: 'json'})
const exporting = ref(false)

async function downloadExport(): Promise<void> {
  if (!exportForm.locale.trim()) {
    ElMessage.warning(t('admin.system.translation.io.exportRequired'))
    return
  }
  exporting.value = true
  try {
    await translationApi.exportTranslations(exportForm.locale.trim(), exportForm.format)
  } finally {
    exporting.value = false
  }
}

const importing = ref(false)
const importForm = reactive<{
  content: string
  format: TranslationFormat
  locale: string
  merge: boolean
  status: string
}>({content: '', format: 'json', locale: '', merge: true, status: ''})

async function runImport(): Promise<void> {
  if (!importForm.content.trim()) {
    ElMessage.warning(t('admin.system.translation.io.importContentRequired'))
    return
  }
  importing.value = true
  try {
    await translationApi.importTranslations({
      content: importForm.content,
      format: importForm.format,
      locale: importForm.locale || undefined,
      merge: importForm.merge,
      status: importForm.status || undefined,
    })
    ElMessage.success(t('admin.system.translation.io.imported'))
  } finally {
    importing.value = false
  }
}

// ---- 加载时机：切到本标签才触发（对应原 openTab 的 'io' 分支），只触发一次
let loaded = false
watch(
  () => props.active,
  (isActive) => {
    if (!isActive || loaded) return
    loaded = true
    emit('ensure-languages')
  },
  {immediate: true},
)
</script>

<template>
  <!-- 导出词条 -->
  <section class="tcard mb-3">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.io.exportTitle') }}</span>
    </div>
    <p class="hint mb-2">{{ $t('admin.system.translation.io.exportHint') }}</p>
    <div class="inline-form">
      <el-select v-model="exportForm.locale" :placeholder="$t('admin.system.translation.io.exportLocale')" filterable
                 style="width: 220px">
        <el-option v-for="item in languages" :key="item.code"
                   :label="`${item.native_name} (${item.code})`" :value="item.code"/>
      </el-select>
      <el-select v-model="exportForm.format" style="width: 140px">
        <el-option v-for="item in FORMATS" :key="item" :label="item" :value="item"/>
      </el-select>
      <el-button :icon="Download" :loading="exporting" type="primary" @click="downloadExport">
        {{ $t('admin.system.translation.io.export') }}
      </el-button>
    </div>
  </section>

  <!-- 导入词条 -->
  <section class="tcard">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.io.importTitle') }}</span>
    </div>
    <p class="hint mb-2">{{ $t('admin.system.translation.io.importHint') }}</p>
    <el-form :model="importForm" label-width="120px">
      <el-form-item :label="$t('admin.system.translation.io.importFormat')">
        <el-select v-model="importForm.format" style="width: 200px">
          <el-option v-for="item in FORMATS" :key="item" :label="item" :value="item"/>
        </el-select>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.io.importLocale')">
        <el-input v-model="importForm.locale" placeholder="zh-CN" style="max-width: 200px"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.io.importMerge')">
        <el-switch v-model="importForm.merge"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.io.importStatus')">
        <el-select v-model="importForm.status" clearable style="width: 200px">
          <el-option v-for="item in STATUSES" :key="item" :label="statusLabel(item)" :value="item"/>
        </el-select>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.io.importContent')">
        <el-input v-model="importForm.content" :autosize="{minRows: 6, maxRows: 16}" type="textarea"/>
      </el-form-item>
    </el-form>
    <div class="actions-row">
      <el-button v-auth="'module_system:setting:edit'" :icon="Upload" :loading="importing" type="primary"
                 @click="runImport">
        {{ $t('admin.system.translation.io.import') }}
      </el-button>
    </div>
  </section>
</template>

<style scoped>
.tcard {
  padding: 16px 18px;
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-line, #e5e7eb);
  border-radius: 8px;
}

.tcard__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.tcard__title {
  font-size: 15px;
  font-weight: 600;
}

.hint {
  margin: 0;
  font-size: 12px;
  color: var(--color-fg-subtle, #909399);
}

.inline-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.actions-row {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.mb-2 {
  margin-bottom: 8px;
}

.mb-3 {
  margin-bottom: 16px;
}
</style>
