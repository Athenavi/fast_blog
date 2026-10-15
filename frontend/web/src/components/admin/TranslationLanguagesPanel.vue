<script lang="ts" setup>
/**
 * 翻译管理 · 语言与区域面板
 *
 * 从 `pages/system/translation.vue` 的「语言与区域」标签页抽出：支持语言列表、语言识别、
 * 区域信息列表、时间本地化，外加新增 / 覆盖自定义语言的抽屉（原页面把它放在
 * `</el-tabs>` 之外，但触发按钮就在本标签页的工具栏里，所以跟着一起搬过来）。
 *
 * 与页面之间只需要两件事通信：
 *  - `languages`（双向）—— 语言列表是**跨标签页共享的状态**：词条 / 统计与进度 /
 *    导入导出三个标签页的下拉要靠它过滤，所以不能锁在本组件里；
 *  - `active` —— 本标签页是否激活。原页面在 `onMounted` 里就 `openTab('languages')`，
 *    即**默认标签挂载即加载**，这里用 `active` + `watch(immediate)` 还原同一时机。
 *
 * 加载只做一次：原页面靠 `loadedTabs.languages` 去重（切回本标签不会重复请求），
 * 这里用本地的 `loaded` 标记还原，`saveLanguage` 成功后的主动刷新走同一函数。
 */
import {Plus, Refresh} from '@element-plus/icons-vue'
import {reactive, ref, watch} from 'vue'

import {
  type DetectResult,
  type LanguageItem,
  type LocaleInfo,
  type LocalizeResult,
  type TextDirection,
  translationApi,
} from '@/api'
import {ElMessage} from '@/utils/feedback'

const props = defineProps<{
  /** 本标签页是否激活（默认标签就是它，故挂载即加载） */
  active: boolean
  /** 语言列表（跨标签共享，由页面持有） */
  languages: LanguageItem[]
}>()

const emit = defineEmits<{
  (e: 'update:languages', value: LanguageItem[]): void
}>()

const {t} = useI18n()

const langLoading = ref(false)
const langFailed = ref(false)
const localeList = ref<LocaleInfo[]>([])

async function loadLanguagesTab(): Promise<void> {
  langLoading.value = true
  langFailed.value = false
  const [langs, locs] = await Promise.allSettled([
    translationApi.languages(),
    translationApi.locales(),
  ])
  if (langs.status === 'fulfilled') emit('update:languages', langs.value)
  if (locs.status === 'fulfilled') localeList.value = locs.value
  if (langs.status === 'rejected' || locs.status === 'rejected') langFailed.value = true
  langLoading.value = false
}

// ---- 语言识别
const detectLoading = ref(false)
const detectInput = ref('')
const detectResult = ref<DetectResult | null>(null)

async function runDetect(): Promise<void> {
  if (!detectInput.value.trim()) {
    ElMessage.warning(t('admin.system.translation.languages.detectRequired'))
    return
  }
  detectLoading.value = true
  try {
    detectResult.value = await translationApi.detectLanguage(detectInput.value.trim())
  } finally {
    detectLoading.value = false
  }
}

// ---- 时间本地化
const localizeLoading = ref(false)
const localizeForm = reactive({dt: '', locale: '', timezone: ''})
const localizeResult = ref<LocalizeResult | null>(null)

async function runLocalize(): Promise<void> {
  if (!localizeForm.dt) {
    ElMessage.warning(t('admin.system.translation.languages.localizeRequired'))
    return
  }
  localizeLoading.value = true
  try {
    localizeResult.value = await translationApi.localize({
      dt: localizeForm.dt,
      locale: localizeForm.locale || undefined,
      timezone: localizeForm.timezone || undefined,
    })
  } finally {
    localizeLoading.value = false
  }
}

// ---- 新增 / 覆盖自定义语言
const langFormVisible = ref(false)
const langSaving = ref(false)
const langForm = reactive<{
  code: string
  name: string
  native_name: string
  direction: TextDirection
}>({code: '', name: '', native_name: '', direction: 'ltr'})

function openLangCreate(): void {
  Object.assign(langForm, {code: '', name: '', native_name: '', direction: 'ltr'})
  langFormVisible.value = true
}

async function saveLanguage(): Promise<void> {
  if (!langForm.code.trim()) {
    ElMessage.warning(t('admin.system.translation.languages.codeRequired'))
    return
  }
  langSaving.value = true
  try {
    await translationApi.upsertLanguage({
      code: langForm.code.trim(),
      name: langForm.name.trim() || undefined,
      native_name: langForm.native_name.trim() || undefined,
      direction: langForm.direction,
    })
    ElMessage.success(t('admin.system.translation.languages.saved'))
    langFormVisible.value = false
    await loadLanguagesTab()
  } finally {
    langSaving.value = false
  }
}

// ---- 加载时机：默认标签，挂载即加载；之后切回不再重复拉取（对应原 loadedTabs 去重）
let loaded = false
watch(
  () => props.active,
  (isActive) => {
    if (!isActive || loaded) return
    loaded = true
    void loadLanguagesTab()
  },
  {immediate: true},
)
</script>

<template>
  <el-alert
    v-if="langFailed"
    :closable="false"
    :title="$t('admin.common.loadFailed')"
    class="mb-3"
    show-icon
    type="error"
  />

  <!-- 支持语言列表 -->
  <section class="tcard mb-3">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.languages.listTitle') }}</span>
      <div class="actions-row">
        <el-button :icon="Refresh" :loading="langLoading" @click="loadLanguagesTab">
          {{ $t('admin.common.refresh') }}
        </el-button>
        <el-button v-auth="'module_system:setting:edit'" :icon="Plus" type="primary" @click="openLangCreate">
          {{ $t('admin.system.translation.languages.add') }}
        </el-button>
      </div>
    </div>
    <el-table v-loading="langLoading" :data="languages" border size="small" stripe>
      <el-table-column :label="$t('admin.system.translation.languages.code')" prop="code" width="120"/>
      <el-table-column :label="$t('admin.system.translation.languages.name')" min-width="180" prop="name"/>
      <el-table-column :label="$t('admin.system.translation.languages.nativeName')" min-width="140"
                       prop="native_name"/>
      <el-table-column :label="$t('admin.system.translation.languages.direction')" prop="direction" width="100"/>
      <el-table-column :label="$t('admin.system.translation.languages.isDefault')" align="center" width="100">
        <template #default="{ row }">
          <el-tag v-if="(row as LanguageItem).is_default" effect="dark" size="small" type="success">
            {{ $t('admin.system.translation.languages.defaultTag') }}
          </el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
    </el-table>
  </section>

  <!-- 语言识别 -->
  <section class="tcard mb-3">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.languages.detectTitle') }}</span>
    </div>
    <div class="inline-form">
      <el-input
        v-model="detectInput"
        :placeholder="$t('admin.system.translation.languages.acceptLanguagePlaceholder')"
        style="max-width: 360px"
        @keyup.enter="runDetect"
      />
      <el-button :loading="detectLoading" type="primary" @click="runDetect">
        {{ $t('admin.system.translation.languages.detect') }}
      </el-button>
    </div>
    <div v-if="detectResult" class="result-grid mt-3">
      <div class="result-item">
        <span class="result-label">{{ $t('admin.system.translation.languages.acceptLanguage') }}</span>
        <span class="result-value">{{ detectResult.accept_language || '-' }}</span>
      </div>
      <div class="result-item">
        <span class="result-label">{{ $t('admin.system.translation.languages.detected') }}</span>
        <span class="result-value">{{ detectResult.language }}</span>
      </div>
      <div class="result-item">
        <span class="result-label">{{ $t('admin.system.translation.languages.defaultLanguage') }}</span>
        <span class="result-value">{{ detectResult.default_language }}</span>
      </div>
    </div>
  </section>

  <!-- 区域信息列表 -->
  <section class="tcard mb-3">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.languages.localesTitle') }}</span>
    </div>
    <el-table :data="localeList" border size="small" stripe>
      <el-table-column :label="$t('admin.system.translation.languages.locale')" prop="locale" width="110"/>
      <el-table-column :label="$t('admin.system.translation.languages.timezone')" min-width="150"
                       prop="timezone"/>
      <el-table-column :label="$t('admin.system.translation.languages.firstDayOfWeek')" align="center"
                       prop="first_day_of_week" width="120"/>
      <el-table-column :label="$t('admin.system.translation.languages.currency')" width="150">
        <template #default="{ row }">
          {{ (row as LocaleInfo).currency.symbol }} {{ (row as LocaleInfo).currency.code }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('admin.system.translation.languages.dateFormat')" min-width="140">
        <template #default="{ row }">{{ (row as LocaleInfo).formats.date }}</template>
      </el-table-column>
      <el-table-column :label="$t('admin.system.translation.languages.datetimeFormat')" min-width="180">
        <template #default="{ row }">{{ (row as LocaleInfo).formats.datetime }}</template>
      </el-table-column>
      <el-table-column :label="$t('admin.system.translation.languages.timeFormat')" min-width="120">
        <template #default="{ row }">{{ (row as LocaleInfo).formats.time }}</template>
      </el-table-column>
    </el-table>
  </section>

  <!-- 时间本地化 -->
  <section class="tcard">
    <div class="tcard__head">
      <span class="tcard__title">{{ $t('admin.system.translation.languages.localizeTitle') }}</span>
    </div>
    <el-form :model="localizeForm" label-width="120px">
      <el-form-item :label="$t('admin.system.translation.languages.dt')">
        <el-date-picker
          v-model="localizeForm.dt"
          :placeholder="$t('admin.system.translation.languages.dtPlaceholder')"
          style="width: 100%"
          type="datetime"
          value-format="YYYY-MM-DDTHH:mm:ss"
        />
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.languages.localizeLocale')">
        <el-select v-model="localizeForm.locale" clearable filterable style="width: 100%">
          <el-option v-for="item in localeList" :key="item.locale" :label="item.locale"
                     :value="item.locale"/>
        </el-select>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.languages.localizeTimezone')">
        <el-input v-model="localizeForm.timezone" placeholder="Asia/Shanghai"/>
      </el-form-item>
    </el-form>
    <div class="actions-row">
      <el-button :loading="localizeLoading" type="primary" @click="runLocalize">
        {{ $t('admin.system.translation.languages.localize') }}
      </el-button>
    </div>
    <div v-if="localizeResult" class="result-grid mt-3">
      <div class="result-item">
        <span class="result-label">{{ $t('admin.system.translation.languages.resultDate') }}</span>
        <span class="result-value">{{ localizeResult.date }}</span>
      </div>
      <div class="result-item">
        <span class="result-label">{{ $t('admin.system.translation.languages.resultTime') }}</span>
        <span class="result-value">{{ localizeResult.time }}</span>
      </div>
      <div class="result-item">
        <span class="result-label">{{ $t('admin.system.translation.languages.resultDatetime') }}</span>
        <span class="result-value">{{ localizeResult.datetime }}</span>
      </div>
      <div class="result-item">
        <span class="result-label">{{ $t('admin.system.translation.languages.resultRelative') }}</span>
        <span class="result-value">{{ localizeResult.relative }}</span>
      </div>
    </div>
  </section>

  <!-- 新增 / 覆盖自定义语言 -->
  <el-drawer v-model="langFormVisible" :title="$t('admin.system.translation.languages.formTitle')"
             destroy-on-close size="440px">
    <el-form :model="langForm" label-width="120px">
      <el-form-item :label="$t('admin.system.translation.languages.formCode')" required>
        <el-input v-model="langForm.code" placeholder="pt-BR"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.languages.formName')">
        <el-input v-model="langForm.name" placeholder="Portuguese (Brazil)"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.languages.formNativeName')">
        <el-input v-model="langForm.native_name" placeholder="Português"/>
      </el-form-item>
      <el-form-item :label="$t('admin.system.translation.languages.formDirection')">
        <el-select v-model="langForm.direction" style="width: 100%">
          <el-option :label="$t('admin.system.translation.languages.dirLtr')" value="ltr"/>
          <el-option :label="$t('admin.system.translation.languages.dirRtl')" value="rtl"/>
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="langFormVisible = false">{{ $t('admin.common.cancel') }}</el-button>
      <el-button :loading="langSaving" type="primary" @click="saveLanguage">
        {{ $t('admin.system.translation.languages.save') }}
      </el-button>
    </template>
  </el-drawer>
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

.mb-3 {
  margin-bottom: 16px;
}

.mt-3 {
  margin-top: 16px;
}
</style>
