<script lang="ts" setup>
/**
 * 屏幕选项（/system/screen-options，system 域）
 *
 * 跨页面的「每页 UI 偏好」：显示哪些列、每页条数、排序等，按 `page` 分组持久化在
 * `system_settings`（键 `screen_options.{user_id}`）。偏好恒属当前登录用户自己，
 * 接口不接受 `user_id` 参数 —— 不存在越权面，仓库里也没有既有页面可承载，故独立建页。
 *
 * 对齐 v3 `controller.py` 的全部 7 个端点：
 *   GET    /              全部页面偏好 → 主列表（load）
 *   GET    /{page}        单页偏好（默认值补齐）→ 「查看生效值」查询区
 *   PUT    /{page}        整体覆盖单页 → 卡片「整体覆盖」对话框
 *   PATCH  /{page}/{key}  修改单项 → 「新增 / 编辑选项」对话框
 *   DELETE /{page}/{key}  删除单项 → 行内删除
 *   DELETE /{page}        删除整页 → 卡片「删除整页」
 *   DELETE /              重置全部 → 顶部「重置全部」
 *
 * 权限：后端此模块**只需登录**（`codes.py` 无 `screen_options:*`）。沿用本仓库
 * 「无专属权限码的系统工具」惯例（同 maintenance / translation / accessibility），
 * 页面取 `module_system:setting:view`、写操作取 `module_system:setting:edit`。
 */
import {computed, onMounted, ref} from 'vue'

import {screenOptionsApi, type ScreenOptionsAll, type ScreenOptionsPageMap} from '@/api'
import {ElMessage, ElMessageBox} from '@/utils/feedback'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.screenOptions.title',
  permission: 'module_system:setting:view',
})

const {t} = useI18n()

/** 表格行的展示结构：键 / 原始值（编辑时回填）/ 展示文本 */
interface OptionRow {
  key: string
  raw: unknown
  display: string
}

/** 一个页面的展示块 */
interface PageBlock {
  page: string
  entries: OptionRow[]
}

const loading = ref(false)
const loadFailed = ref(false)
/** GET / 的原始结果：page → { key: value }（不做默认值补齐） */
const allOptions = ref<ScreenOptionsAll>({})

/** 值的展示文本：字符串原样，其余 JSON 化（序列化失败时降级为 String） */
function formatValue(value: unknown): string {
  if (typeof value === 'string') return value
  try {
    const encoded = JSON.stringify(value)
    return encoded === undefined ? String(value) : encoded
  } catch {
    return String(value)
  }
}

/** 把文本解析为选项值：合法 JSON 按其值，否则按字符串处理；空串当空字符串 */
function parseValue(text: string): unknown {
  const trimmed = text.trim()
  if (trimmed === '') return ''
  try {
    return JSON.parse(trimmed)
  } catch {
    return text
  }
}

/** 主列表：按 page 名排序，页内选项按键名排序 */
const pageList = computed<PageBlock[]>(() =>
  Object.entries(allOptions.value)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([page, options]) => ({
      page,
      entries: Object.entries(options)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, raw]) => ({key, raw, display: formatValue(raw)})),
    })),
)

// ── 单页生效值查询（GET /{page}，默认值补齐） ─────────────────────────
const previewInput = ref('')
/** 已成功查询过的 page（刷新时一并重取，保证与主列表同步） */
const previewedPage = ref('')
const previewResult = ref<ScreenOptionsPageMap | null>(null)
const previewFailed = ref(false)

const previewRows = computed<OptionRow[]>(() =>
  Object.entries(previewResult.value ?? {})
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, raw]) => ({key, raw, display: formatValue(raw)})),
)

async function runPreview(): Promise<void> {
  const page = previewInput.value.trim()
  if (!page) {
    ElMessage.warning(t('admin.system.screenOptions.pageRequired'))
    return
  }
  try {
    previewResult.value = await screenOptionsApi.getPage(page)
    previewedPage.value = page
    previewFailed.value = false
  } catch {
    // 失败提示由 request 层统一弹出
    previewResult.value = null
    previewedPage.value = ''
    previewFailed.value = true
  }
}

// ── 只读加载：GET /（若已有预览页则一并重取 GET /{page}） ─────────────────
/**
 * 只读加载统一走 `Promise.allSettled`：即便将来追加更多只读源（如逐页默认值预览），
 * 单个源失败也不会拖垮其余展示，错误归因仍是「整块加载失败」。
 */
async function load(): Promise<void> {
  loading.value = true
  loadFailed.value = false
  previewFailed.value = false

  const hasPreview = previewedPage.value !== ''
  const allPromise = screenOptionsApi.getAll()
  const previewPromise = hasPreview ? screenOptionsApi.getPage(previewedPage.value) : null

  const [allOutcome, previewOutcome] = await Promise.allSettled([allPromise, previewPromise] as const)

  if (allOutcome.status === 'fulfilled') {
    allOptions.value = allOutcome.value
  } else {
    allOptions.value = {}
    loadFailed.value = true
  }

  if (hasPreview) {
    if (previewOutcome.status === 'fulfilled') {
      previewResult.value = previewOutcome.value
    } else {
      previewResult.value = null
      previewFailed.value = true
    }
  }

  loading.value = false
}

// ── 单项：新增 / 编辑（PATCH /{page}/{key}） ──────────────────────────
const optionDialogOpen = ref(false)
const optionSaving = ref(false)
const optionPage = ref('')
const optionKey = ref('')
const optionValueText = ref('')
/** 编辑已有项时键名不可改；新增时为 true */
const optionIsNew = ref(true)

function openAddOption(page: string): void {
  optionPage.value = page
  optionKey.value = ''
  optionValueText.value = ''
  optionIsNew.value = true
  optionDialogOpen.value = true
}

function openEditOption(page: string, key: string, raw: unknown): void {
  optionPage.value = page
  optionKey.value = key
  optionValueText.value = typeof raw === 'string' ? raw : formatValue(raw)
  optionIsNew.value = false
  optionDialogOpen.value = true
}

async function submitOption(): Promise<void> {
  const key = optionKey.value.trim()
  if (!key) {
    ElMessage.warning(t('admin.system.screenOptions.optionKeyRequired'))
    return
  }
  optionSaving.value = true
  try {
    await screenOptionsApi.patchOption(optionPage.value, key, parseValue(optionValueText.value))
    ElMessage.success(t('admin.system.screenOptions.optionSaved'))
    optionDialogOpen.value = false
    await load()
  } finally {
    optionSaving.value = false
  }
}

// ── 单项删除（DELETE /{page}/{key}） ─────────────────────────────────
async function onDeleteOption(page: string, key: string): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.system.screenOptions.deleteOptionConfirm', {page, key}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await screenOptionsApi.deleteOption(page, key)
  ElMessage.success(t('admin.common.deleted'))
  await load()
}

// ── 整体覆盖单页（PUT /{page}） ──────────────────────────────────────
const overrideDialogOpen = ref(false)
const overrideSaving = ref(false)
const overridePage = ref('')
const overrideText = ref('')

function openOverride(page: string): void {
  overridePage.value = page
  // 以当前存储值预填，便于增删键后整体提交
  const current = allOptions.value[page] ?? {}
  overrideText.value = JSON.stringify(current, null, 2)
  overrideDialogOpen.value = true
}

async function submitOverride(): Promise<void> {
  let parsed: unknown
  try {
    parsed = JSON.parse(overrideText.value)
  } catch {
    ElMessage.error(t('admin.system.screenOptions.overrideInvalid'))
    return
  }
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    ElMessage.error(t('admin.system.screenOptions.overrideInvalid'))
    return
  }
  overrideSaving.value = true
  try {
    await screenOptionsApi.setPage(overridePage.value, parsed as ScreenOptionsPageMap)
    ElMessage.success(t('admin.system.screenOptions.overridden'))
    overrideDialogOpen.value = false
    await load()
  } finally {
    overrideSaving.value = false
  }
}

// ── 删除整页（DELETE /{page}） ───────────────────────────────────────
async function onDeletePage(page: string): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.system.screenOptions.deletePageConfirm', {page}),
    t('admin.common.notice'),
    {type: 'warning'},
  )
  await screenOptionsApi.deletePage(page)
  ElMessage.success(t('admin.common.deleted'))
  await load()
}

// ── 重置全部（DELETE /） ─────────────────────────────────────────────
async function resetAll(): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.system.screenOptions.resetConfirm'),
    t('admin.common.danger'),
    {type: 'warning'},
  )
  const result = await screenOptionsApi.resetAll()
  ElMessage.success(t('admin.system.screenOptions.resetDone', {n: result?.removed_pages ?? 0}))
  previewedPage.value = ''
  previewResult.value = null
  await load()
}

onMounted(load)
</script>

<template>
  <AdminPage :desc="$t('admin.system.screenOptions.desc')" :title="$t('admin.system.screenOptions.title')">
    <template #actions>
      <el-button :loading="loading" @click="load">
        <Icon class="mr-1 h-3.5 w-3.5" name="refresh-cw"/>
        {{ $t('admin.common.refresh') }}
      </el-button>
      <el-button v-auth="'module_system:setting:edit'" class="ml-2" type="danger" @click="resetAll">
        <Icon class="mr-1 h-3.5 w-3.5" name="trash-2"/>
        {{ $t('admin.system.screenOptions.resetAll') }}
      </el-button>
    </template>

    <!-- 单页生效值查询：GET /{page}（缺省项用后端默认值补齐） -->
    <el-card class="mb-4" shadow="never">
      <template #header>
        <span class="font-medium">{{ $t('admin.system.screenOptions.previewTitle') }}</span>
        <span class="ml-2 text-xs text-fg-subtle">{{ $t('admin.system.screenOptions.previewHint') }}</span>
      </template>

      <div class="flex flex-wrap items-center gap-3">
        <el-input
          v-model="previewInput"
          :placeholder="$t('admin.system.screenOptions.previewPagePlaceholder')"
          class="max-w-xs"
          @keyup.enter="runPreview"
        />
        <el-button type="primary" @click="runPreview">
          {{ $t('admin.system.screenOptions.previewRun') }}
        </el-button>
      </div>

      <p v-if="previewFailed" class="mt-3 rounded-control bg-danger-soft px-3 py-2 text-sm text-danger">
        {{ $t('admin.system.screenOptions.previewFailed') }}
      </p>

      <el-table v-else-if="previewRows.length" :data="previewRows" border class="mt-3" size="small">
        <el-table-column :label="$t('admin.system.screenOptions.colKey')" min-width="180" prop="key"/>
        <el-table-column :label="$t('admin.system.screenOptions.colValue')" min-width="240">
          <template #default="{row}"><span class="screen-options__value">{{ row.display }}</span></template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 加载失败 -->
    <AdminEmpty
      v-if="loadFailed"
      :desc="$t('admin.system.screenOptions.loadFailedDesc')"
      :title="$t('admin.common.loadFailed')"
      variant="error"
    >
      <el-button @click="load">{{ $t('admin.common.retry') }}</el-button>
    </AdminEmpty>

    <!-- 空态 -->
    <AdminEmpty
      v-else-if="!loading && pageList.length === 0"
      :desc="$t('admin.system.screenOptions.emptyDesc')"
      :title="$t('admin.system.screenOptions.empty')"
    />

    <!-- 每页一块 -->
    <template v-else>
      <el-card v-for="block in pageList" :key="block.page" class="mb-4" shadow="never">
        <template #header>
          <div class="flex flex-wrap items-center gap-2">
            <span class="font-medium">{{ block.page }}</span>
            <span class="text-xs text-fg-subtle">
              {{ $t('admin.system.screenOptions.optionCount', {n: block.entries.length}) }}
            </span>
            <span class="ml-auto"/>
            <el-button v-auth="'module_system:setting:edit'" size="small" @click="openAddOption(block.page)">
              {{ $t('admin.system.screenOptions.addOption') }}
            </el-button>
            <el-button v-auth="'module_system:setting:edit'" plain size="small" type="primary"
                       @click="openOverride(block.page)">
              {{ $t('admin.system.screenOptions.override') }}
            </el-button>
            <el-button v-auth="'module_system:setting:edit'" plain size="small" type="danger"
                       @click="onDeletePage(block.page)">
              {{ $t('admin.system.screenOptions.deletePage') }}
            </el-button>
          </div>
        </template>

        <el-table v-if="block.entries.length" :data="block.entries" border size="small">
          <el-table-column :label="$t('admin.system.screenOptions.colKey')" min-width="180" prop="key"/>
          <el-table-column :label="$t('admin.system.screenOptions.colValue')" min-width="240">
            <template #default="{row}"><span class="screen-options__value">{{ row.display }}</span></template>
          </el-table-column>
          <el-table-column :label="$t('admin.common.actions')" width="150">
            <template #default="{row}">
              <el-button v-auth="'module_system:setting:edit'" link size="small" type="primary"
                         @click="openEditOption(block.page, row.key, row.raw)">
                {{ $t('admin.common.edit') }}
              </el-button>
              <el-button v-auth="'module_system:setting:edit'" link size="small" type="danger"
                         @click="onDeleteOption(block.page, row.key)">
                {{ $t('admin.common.delete') }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <p v-else class="text-sm text-fg-subtle">{{ $t('admin.system.screenOptions.emptyPage') }}</p>
      </el-card>
    </template>

    <!-- 新增 / 编辑单项（PATCH /{page}/{key}） -->
    <el-dialog
      v-model="optionDialogOpen"
      :title="optionIsNew
        ? $t('admin.system.screenOptions.optionDialogAddTitle', {page: optionPage})
        : $t('admin.system.screenOptions.optionDialogEditTitle', {page: optionPage})"
      width="560px"
    >
      <el-form label-width="90px">
        <el-form-item :label="$t('admin.system.screenOptions.optionKey')">
          <el-input
            v-model="optionKey"
            :disabled="!optionIsNew"
            :placeholder="$t('admin.system.screenOptions.optionKeyPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('admin.system.screenOptions.optionValue')">
          <el-input
            v-model="optionValueText"
            :placeholder="$t('admin.system.screenOptions.optionValuePlaceholder')"
            :rows="4"
            type="textarea"
          />
          <p class="mt-1 text-xs text-fg-subtle">{{ $t('admin.system.screenOptions.optionValueHint') }}</p>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="optionDialogOpen = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="optionSaving" type="primary" @click="submitOption">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 整体覆盖单页（PUT /{page}） -->
    <el-dialog
      v-model="overrideDialogOpen"
      :title="$t('admin.system.screenOptions.overrideTitle', {page: overridePage})"
      width="620px"
    >
      <p class="mb-2 text-sm text-fg-muted">{{ $t('admin.system.screenOptions.overrideHint') }}</p>
      <el-input v-model="overrideText" :rows="10" type="textarea"/>
      <template #footer>
        <el-button @click="overrideDialogOpen = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="overrideSaving" type="primary" @click="submitOverride">
          {{ $t('admin.system.screenOptions.overrideSave') }}
        </el-button>
      </template>
    </el-dialog>
  </AdminPage>
</template>

<style scoped>
.screen-options__value {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  word-break: break-all;
}
</style>
