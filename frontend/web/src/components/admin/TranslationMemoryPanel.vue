<script lang="ts" setup>
/**
 * 翻译管理 · 翻译记忆库面板
 *
 * 从 `pages/system/translation.vue` 的「翻译记忆库」标签页抽出：记忆库统计、相似匹配、
 * 新增 / 更新记忆、清空记忆、导入记忆、导出记忆（真实文件下载）。
 *
 * ## 加载时机与原实现保持一致
 *
 * 原页面在 `@tab-change` 里**切到本标签才加载**，触发 `loadMemoryStats()`，并靠原
 * `loadedTabs` 去重。这里用 `active` 属性 + `watch(immediate)` 还原；新增 / 清空 /
 * 导入成功后都会重新拉一次统计（与原实现相同）。
 */
import {Delete, Download, Refresh, Upload} from '@element-plus/icons-vue'
import {reactive, ref, watch} from 'vue'

import {type MemoryStats, type MemorySuggestResult, translationApi} from '@/api'
import {ElMessage, ElMessageBox} from '@/utils/feedback'

const props = defineProps<{
  /** 本标签页是否激活 */
  active: boolean
}>()

const {t} = useI18n()

const memLoading = ref(false)
const memStats = ref<MemoryStats | null>(null)

async function loadMemoryStats(): Promise<void> {
  memLoading.value = true
  const [res] = await Promise.allSettled([translationApi.memoryStats()])
  if (res.status === 'fulfilled') memStats.value = res.value
  memLoading.value = false
}

// ---- 相似匹配
const suggestLoading = ref(false)
const suggestForm = reactive<{
  source_text: string
  source_lang: string
  target_lang: string
  threshold: number | undefined
  limit: number
}>({source_text: '', source_lang: '', target_lang: '', threshold: undefined, limit: 10})
const suggestResult = ref<MemorySuggestResult | null>(null)

async function runSuggest(): Promise<void> {
  if (!suggestForm.source_text.trim() || !suggestForm.source_lang.trim() || !suggestForm.target_lang.trim()) {
    ElMessage.warning(t('admin.system.translation.memory.suggestRequired'))
    return
  }
  suggestLoading.value = true
  try {
    suggestResult.value = await translationApi.memorySuggest({
      source_text: suggestForm.source_text,
      source_lang: suggestForm.source_lang.trim(),
      target_lang: suggestForm.target_lang.trim(),
      threshold: suggestForm.threshold,
      limit: suggestForm.limit,
    })
  } finally {
    suggestLoading.value = false
  }
}

// ---- 新增 / 更新记忆
const addSaving = ref(false)
const addForm = reactive({source_text: '', target_text: '', source_lang: '', target_lang: '', context: ''})

async function saveMemory(): Promise<void> {
  if (!addForm.source_text.trim() || !addForm.source_lang.trim() || !addForm.target_lang.trim()) {
    ElMessage.warning(t('admin.system.translation.memory.addRequired'))
    return
  }
  addSaving.value = true
  try {
    await translationApi.addMemory({
      source_text: addForm.source_text,
      target_text: addForm.target_text,
      source_lang: addForm.source_lang.trim(),
      target_lang: addForm.target_lang.trim(),
      context: addForm.context,
    })
    ElMessage.success(t('admin.system.translation.memory.saved'))
    await loadMemoryStats()
  } finally {
    addSaving.value = false
  }
}

// ---- 清空记忆
const clearSaving = ref(false)
const clearPair = ref('')

async function clearMemory(): Promise<void> {
  try {
    await ElMessageBox.confirm(
      clearPair.value
        ? t('admin.system.translation.memory.clearPairConfirm', {pair: clearPair.value})
        : t('admin.system.translation.memory.clearConfirm'),
      t('admin.common.notice'),
      {type: 'warning'},
    )
  } catch {
    return
  }
  clearSaving.value = true
  try {
    await translationApi.clearMemory(clearPair.value.trim() || undefined)
    ElMessage.success(t('admin.system.translation.memory.cleared'))
    clearPair.value = ''
    await loadMemoryStats()
  } finally {
    clearSaving.value = false
  }
}

// ---- 导入记忆
const memImportSaving = ref(false)
const memImportForm = reactive({content: '', merge: true})

async function importMemory(): Promise<void> {
  if (!memImportForm.content.trim()) {
    ElMessage.warning(t('admin.system.translation.memory.importRequired'))
    return
  }
  memImportSaving.value = true
  try {
    await translationApi.importMemory({content: memImportForm.content, merge: memImportForm.merge})
    ElMessage.success(t('admin.system.translation.memory.imported'))
    await loadMemoryStats()
  } finally {
    memImportSaving.value = false
  }
}

// ---- 导出记忆（真实文件下载）
const memExporting = ref(false)

async function downloadMemory(): Promise<void> {
  memExporting.value = true
  try {
    await translationApi.exportMemory()
  } finally {
    memExporting.value = false
  }
}

// ---- 加载时机：切到本标签才触发（对应原 openTab 的 'memory' 分支），只触发一次
let loaded = false
watch(
  () => props.active,
  (isActive) => {
    if (!isActive || loaded) return
    loaded = true
    void loadMemoryStats()
  },
  {immediate: true},
)
</script>

<template>
  <!-- 记忆库统计 -->
  <section class="tcard mb-3">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.memory.statsTitle') }}</span>
      <el-button :icon="Refresh" :loading="memLoading" @click="loadMemoryStats">
        {{ $t('admin.common.refresh') }}
      </el-button>
    </div>
    <div class="result-grid mb-3">
      <div class="result-item">
        <span class="result-label">{{ $t('admin.system.translation.memory.totalEntries') }}</span>
        <span class="result-value">{{ memStats?.total_entries ?? 0 }}</span>
      </div>
      <div class="result-item">
        <span class="result-label">{{ $t('admin.system.translation.memory.languagePairs') }}</span>
        <span class="result-value">{{ memStats?.language_pairs ?? 0 }}</span>
      </div>
    </div>
    <p class="sub-title mb-2">{{ $t('admin.system.translation.memory.pairsDetail') }}</p>
    <el-table :data="memStats?.pairs_detail ?? []" border size="small" stripe>
      <el-table-column :label="$t('admin.system.translation.memory.pair')" min-width="160" prop="pair"/>
      <el-table-column :label="$t('admin.system.translation.memory.sourceLang')" prop="source_lang"
                       width="130"/>
      <el-table-column :label="$t('admin.system.translation.memory.targetLang')" prop="target_lang"
                       width="130"/>
      <el-table-column :label="$t('admin.system.translation.memory.entryCount')" align="right"
                       prop="entry_count" width="120"/>
    </el-table>
  </section>

  <!-- 相似匹配 -->
  <section class="tcard mb-3">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.memory.suggestTitle') }}</span>
    </div>
    <el-form :model="suggestForm" label-width="120px">
      <el-form-item :label="$t('admin.system.translation.memory.sourceText')">
        <el-input v-model="suggestForm.source_text" :rows="2" type="textarea"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.memory.sourceLang')">
        <el-input v-model="suggestForm.source_lang" placeholder="en" style="max-width: 200px"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.memory.targetLang')">
        <el-input v-model="suggestForm.target_lang" placeholder="zh-CN" style="max-width: 200px"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.memory.threshold')">
        <el-input-number v-model="suggestForm.threshold" :max="1" :min="0" :precision="2" :step="0.1"
                         style="width: 180px"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.memory.limit')">
        <el-input-number v-model="suggestForm.limit" :max="100" :min="1" style="width: 180px"/>
      </el-form-item>
    </el-form>
    <div class="actions-row">
      <el-button :loading="suggestLoading" type="primary" @click="runSuggest">
        {{ $t('admin.system.translation.memory.suggest') }}
      </el-button>
    </div>
    <template v-if="suggestResult">
      <p class="sub-title mt-3 mb-2">{{ $t('admin.system.translation.memory.matches') }}</p>
      <el-table v-if="suggestResult.matches.length" :data="suggestResult.matches" border size="small"
                stripe>
        <el-table-column :label="$t('admin.system.translation.memory.sourceText')" min-width="200"
                         prop="source" show-overflow-tooltip/>
        <el-table-column :label="$t('admin.system.translation.memory.targetText')" min-width="200"
                         prop="target" show-overflow-tooltip/>
        <el-table-column :label="$t('admin.system.translation.memory.similarity')" align="right"
                         prop="similarity" width="120"/>
        <el-table-column :label="$t('admin.system.translation.memory.matchType')" align="center" width="110">
          <template #default="{ row }">
            <el-tag :type="row.match_type === 'exact' ? 'success' : 'info'" size="small">
              {{
                row.match_type === 'exact'
                  ? $t('admin.system.translation.memory.exact')
                  : $t('admin.system.translation.memory.fuzzy')
              }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.system.translation.memory.context')" min-width="140"
                         prop="context" show-overflow-tooltip/>
        <el-table-column :label="$t('admin.system.translation.memory.usageCount')" align="right"
                         prop="usage_count" width="100"/>
      </el-table>
      <el-empty v-else :description="$t('admin.system.translation.memory.noMatches')" :image-size="60"/>
    </template>
  </section>

  <!-- 新增 / 更新记忆 -->
  <section class="tcard mb-3">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.memory.addTitle') }}</span>
    </div>
    <el-form :model="addForm" label-width="120px">
      <el-form-item :label="$t('admin.system.translation.memory.sourceText')">
        <el-input v-model="addForm.source_text" :rows="2" type="textarea"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.memory.targetText')">
        <el-input v-model="addForm.target_text" :rows="2" type="textarea"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.memory.sourceLang')">
        <el-input v-model="addForm.source_lang" placeholder="en" style="max-width: 200px"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.memory.targetLang')">
        <el-input v-model="addForm.target_lang" placeholder="zh-CN" style="max-width: 200px"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.memory.context')">
        <el-input v-model="addForm.context" :maxlength="500" style="max-width: 320px"/>
      </el-form-item>
    </el-form>
    <div class="actions-row">
      <el-button v-auth="'module_system:setting:edit'" :loading="addSaving" type="primary" @click="saveMemory">
        {{ $t('admin.system.translation.memory.add') }}
      </el-button>
    </div>
  </section>

  <!-- 清空 / 导入 / 导出 -->
  <section class="tcard mb-3">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.memory.clearTitle') }}</span>
    </div>
    <p class="hint mb-2">{{ $t('admin.system.translation.memory.clearHint') }}</p>
    <div class="inline-form">
      <el-input v-model="clearPair"
                :placeholder="$t('admin.system.translation.memory.languagePairPlaceholder')"
                style="max-width: 260px"/>
      <el-button v-auth="'module_system:setting:edit'" :icon="Delete" :loading="clearSaving" type="danger"
                 @click="clearMemory">
        {{ $t('admin.system.translation.memory.clear') }}
      </el-button>
    </div>
  </section>

  <section class="tcard mb-3">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.memory.importTitle') }}</span>
    </div>
    <el-form :model="memImportForm" label-width="120px">
      <el-form-item :label="$t('admin.system.translation.memory.importContent')">
        <el-input v-model="memImportForm.content" :autosize="{minRows: 4, maxRows: 12}" type="textarea"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.memory.importMerge')">
        <el-switch v-model="memImportForm.merge"/>
      </el-form-item>
    </el-form>
    <div class="actions-row">
      <el-button v-auth="'module_system:setting:edit'" :icon="Upload" :loading="memImportSaving" type="primary"
                 @click="importMemory">
        {{ $t('admin.system.translation.memory.import') }}
      </el-button>
    </div>
  </section>

  <section class="tcard">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.memory.exportTitle') }}</span>
    </div>
    <p class="hint mb-2">{{ $t('admin.system.translation.memory.exportHint') }}</p>
    <el-button :icon="Download" :loading="memExporting" type="primary" @click="downloadMemory">
      {{ $t('admin.system.translation.memory.export') }}
    </el-button>
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

.sub-title {
  font-size: 13px;
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

.result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px 20px;
}

.result-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-label {
  font-size: 12px;
  color: var(--color-fg-subtle, #909399);
}

.result-value {
  font-size: 14px;
  color: var(--color-fg, #303133);
  word-break: break-all;
}

.mb-2 {
  margin-bottom: 8px;
}

.mb-3 {
  margin-bottom: 16px;
}

.mt-3 {
  margin-top: 16px;
}
</style>
