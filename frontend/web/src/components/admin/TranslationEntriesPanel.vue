<script lang="ts" setup>
/**
 * 翻译管理 · 词条与语言包面板
 *
 * 从 `pages/system/translation.vue` 的「词条与语言包」标签页抽出：整包词条浏览、
 * 取单条词条、写单条词条、覆盖 / 合并语言包。
 *
 * ## 加载时机与原实现保持一致
 *
 * 原页面在 `@tab-change` 里**切到本标签才加载**，且只做一件事：
 * `ensureLanguages()` —— 兜底保证语言列表可用（本标签页的下拉要靠它过滤；真正的
 * 词条数据都是用户点按钮才拉）。这里用 `active` 属性 + `watch(immediate)` 还原，
 * 并保留原 `loadedTabs` 的去重：切回本标签不再重复触发。
 *
 * 语言列表是跨标签共享状态、由页面持有，所以这里只 `:languages` 读它；需要兜底加载时
 * 通过 `ensure-languages` 事件请页面去拉（页面统一维护那一份列表）。
 */
import {Refresh} from '@element-plus/icons-vue'
import {computed, reactive, ref, watch} from 'vue'

import {type BundleResult, type EntryResult, type LanguageItem, translationApi} from '@/api'
import {ElMessage} from '@/utils/feedback'

const props = defineProps<{
  /** 本标签页是否激活 */
  active: boolean
  /** 语言列表（跨标签共享，由页面持有） */
  languages: LanguageItem[]
}>()

const emit = defineEmits<{
  /** 请页面兜底加载语言列表（下拉需要它，但加载与持有都在页面侧） */
  (e: 'ensure-languages'): void
}>()

const {t} = useI18n()

const STATUSES = ['translated', 'pending', 'reviewed'] as const

function statusLabel(status: string): string {
  if (status === 'translated') return t('admin.system.translation.entries.statusTranslated')
  if (status === 'reviewed') return t('admin.system.translation.entries.statusReviewed')
  return t('admin.system.translation.entries.statusPending')
}

const entryLocale = ref('')
const bundleLoading = ref(false)
const bundleFailed = ref(false)
const bundle = ref<BundleResult | null>(null)

const bundleRows = computed(() =>
  Object.entries(bundle.value?.entries ?? {}).map(([key, value]) => ({key, value})),
)

async function loadBundle(): Promise<void> {
  if (!entryLocale.value) return
  bundleLoading.value = true
  bundleFailed.value = false
  try {
    bundle.value = await translationApi.getBundle(entryLocale.value)
  } catch {
    bundle.value = null
    bundleFailed.value = true
  } finally {
    bundleLoading.value = false
  }
}

// ---- 取单条词条
const entryLookupLoading = ref(false)
const entryLookup = reactive({key: '', locale: '', default: ''})
const entryLookupResult = ref<EntryResult | null>(null)

async function fetchEntry(): Promise<void> {
  if (!entryLookup.key.trim()) {
    ElMessage.warning(t('admin.system.translation.entries.keyRequired'))
    return
  }
  entryLookupLoading.value = true
  try {
    entryLookupResult.value = await translationApi.getEntry({
      key: entryLookup.key.trim(),
      locale: entryLookup.locale || undefined,
      default: entryLookup.default || undefined,
    })
  } finally {
    entryLookupLoading.value = false
  }
}

// ---- 写单条词条
const entrySaving = ref(false)
const entryForm = reactive({locale: '', key: '', value: '', status: ''})

async function saveEntry(): Promise<void> {
  if (!entryForm.locale.trim()) {
    ElMessage.warning(t('admin.system.translation.entries.localeRequired'))
    return
  }
  if (!entryForm.key.trim()) {
    ElMessage.warning(t('admin.system.translation.entries.keyRequired'))
    return
  }
  entrySaving.value = true
  try {
    await translationApi.setEntry({
      locale: entryForm.locale.trim(),
      key: entryForm.key.trim(),
      value: entryForm.value,
      status: entryForm.status || undefined,
    })
    ElMessage.success(t('admin.system.translation.entries.entrySaved'))
    if (entryLocale.value === entryForm.locale.trim()) await loadBundle()
  } finally {
    entrySaving.value = false
  }
}

// ---- 覆盖 / 合并语言包
const replaceSaving = ref(false)
const replaceForm = reactive<{ locale: string; merge: boolean; status: string; dataText: string }>({
  locale: '',
  merge: true,
  status: '',
  dataText: '',
})

async function replaceBundle(): Promise<void> {
  if (!replaceForm.locale.trim()) {
    ElMessage.warning(t('admin.system.translation.entries.localeRequired'))
    return
  }
  let data: Record<string, string>
  try {
    const parsed: unknown = JSON.parse(replaceForm.dataText || '{}')
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      throw new Error('not-object')
    }
    data = parsed as Record<string, string>
  } catch {
    ElMessage.warning(t('admin.system.translation.entries.badJson'))
    return
  }
  replaceSaving.value = true
  try {
    await translationApi.replaceBundle(replaceForm.locale.trim(), {
      data,
      merge: replaceForm.merge,
      status: replaceForm.status || undefined,
    })
    ElMessage.success(t('admin.system.translation.entries.replaced'))
    if (entryLocale.value === replaceForm.locale.trim()) await loadBundle()
  } finally {
    replaceSaving.value = false
  }
}

// ---- 加载时机：切到本标签才触发（对应原 openTab 的 'entries' 分支），只触发一次
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
  <!-- 整包词条 -->
  <section class="tcard mb-3">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.entries.bundleTitle') }}</span>
      <div class="actions-row">
        <el-select v-model="entryLocale" :placeholder="$t('admin.system.translation.entries.selectLocale')"
                   filterable style="width: 200px">
          <el-option v-for="item in languages" :key="item.code"
                     :label="`${item.native_name} (${item.code})`" :value="item.code"/>
        </el-select>
        <el-button :icon="Refresh" :loading="bundleLoading" @click="loadBundle">
          {{ $t('admin.system.translation.entries.load') }}
        </el-button>
      </div>
    </div>
    <el-alert
      v-if="bundleFailed"
      :closable="false"
      :title="$t('admin.common.loadFailed')"
      class="mb-3"
      show-icon
      type="error"
    />
    <p v-if="bundle" class="hint mb-2">
      {{ $t('admin.system.translation.entries.bundleCount', {n: bundle.count}) }}
    </p>
    <el-table v-if="bundleRows.length" v-loading="bundleLoading" :data="bundleRows" border size="small"
              stripe>
      <el-table-column :label="$t('admin.system.translation.entries.key')" min-width="260" prop="key"/>
      <el-table-column :label="$t('admin.system.translation.entries.value')" min-width="260" prop="value"
                       show-overflow-tooltip/>
    </el-table>
    <el-empty v-else :description="$t('admin.system.translation.entries.empty')" :image-size="60"/>
  </section>

  <!-- 取单条词条 -->
  <section class="tcard mb-3">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.entries.entryTitle') }}</span>
    </div>
    <el-form :model="entryLookup" inline>
      <el-form-item :label="$t('admin.system.translation.entries.entryKey')">
        <el-input v-model="entryLookup.key" clearable style="width: 220px"
                  @keyup.enter="fetchEntry"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.entries.selectLocale')">
        <el-select v-model="entryLookup.locale" clearable filterable style="width: 180px">
          <el-option v-for="item in languages" :key="item.code" :label="item.code"
                     :value="item.code"/>
        </el-select>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.entries.entryDefault')">
        <el-input v-model="entryLookup.default" clearable style="width: 200px"/>
      </el-form-item>
      <el-form-item>
        <el-button :loading="entryLookupLoading" type="primary" @click="fetchEntry">
          {{ $t('admin.system.translation.entries.getEntry') }}
        </el-button>
      </el-form-item>
    </el-form>
    <div v-if="entryLookupResult" class="result-grid mt-2">
      <div class="result-item">
        <span class="result-label">{{ $t('admin.system.translation.entries.entryValueResult') }}</span>
        <span class="result-value">{{ entryLookupResult.value }}</span>
      </div>
      <div class="result-item">
        <span class="result-label">{{ $t('admin.system.translation.entries.entrySource') }}</span>
        <span class="result-value">{{ entryLookupResult.source }}</span>
      </div>
    </div>
  </section>

  <!-- 写单条词条 -->
  <section class="tcard mb-3">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.entries.setTitle') }}</span>
    </div>
    <el-form :model="entryForm" label-width="110px">
      <el-form-item :label="$t('admin.system.translation.entries.selectLocale')">
        <el-input v-model="entryForm.locale" placeholder="zh-CN" style="max-width: 220px"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.entries.entryKey')">
        <el-input v-model="entryForm.key" placeholder="home.title" style="max-width: 320px"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.entries.entryValue')">
        <el-input v-model="entryForm.value" :rows="2" type="textarea"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.entries.entryStatus')">
        <el-select v-model="entryForm.status" clearable style="width: 200px">
          <el-option v-for="item in STATUSES" :key="item" :label="statusLabel(item)" :value="item"/>
        </el-select>
      </el-form-item>
    </el-form>
    <div class="actions-row">
      <el-button v-auth="'module_system:setting:edit'" :loading="entrySaving" type="primary"
                 @click="saveEntry">
        {{ $t('admin.system.translation.entries.saveEntry') }}
      </el-button>
    </div>
  </section>

  <!-- 覆盖 / 合并语言包 -->
  <section class="tcard">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.entries.replaceTitle') }}</span>
    </div>
    <p class="hint mb-2">{{ $t('admin.system.translation.entries.replaceHint') }}</p>
    <el-form :model="replaceForm" label-width="110px">
      <el-form-item :label="$t('admin.system.translation.entries.selectLocale')">
        <el-input v-model="replaceForm.locale" placeholder="zh-CN" style="max-width: 220px"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.entries.replaceMerge')">
        <el-switch v-model="replaceForm.merge"/>
        <span class="hint ml-2">
          {{
            replaceForm.merge
              ? $t('admin.system.translation.entries.mergeOptionMerge')
              : $t('admin.system.translation.entries.mergeOptionReplace')
          }}
        </span>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.entries.replaceStatus')">
        <el-select v-model="replaceForm.status" clearable style="width: 200px">
          <el-option v-for="item in STATUSES" :key="item" :label="statusLabel(item)" :value="item"/>
        </el-select>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.entries.replaceData')">
        <el-input v-model="replaceForm.dataText" :autosize="{minRows: 4, maxRows: 12}" type="textarea"/>
      </el-form-item>
    </el-form>
    <div class="actions-row">
      <el-button v-auth="'module_system:setting:edit'" :loading="replaceSaving" type="primary"
                 @click="replaceBundle">
        {{ $t('admin.system.translation.entries.replace') }}
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

.mt-2 {
  margin-top: 8px;
}

.ml-2 {
  margin-left: 8px;
}
</style>
