<script lang="ts" setup>
/**
 * 数据导出（/system/export，system 域）
 *
 * 对齐后端 `src/api/v3/modules/system/export` 的 3 个端点：
 *   - GET  /templates        → 左侧资源清单（含每种资源的字段清单，来自 `EXPORT_RESOURCES`）；
 *   - POST /preview          → 「预览」按钮，表格展示前 N 行 JSON；
 *   - GET  /{resource}.csv   → 「导出 CSV」按钮，真实文件下载（`Content-Disposition: attachment`）。
 *
 * 权限分层如实呈现：三个端点都需入口权限 `module_analytics:report:view`；导出 / 预览还会按
 * 该资源登记的细粒度查看权限再校验一次，无权时后端返回 **403**（不是空数据），此时页面
 * 明确提示「权限不足」并给出所需权限码。
 */
import {Download, Refresh, View} from '@element-plus/icons-vue'
import {ElMessage} from '@/utils/feedback'
import {computed, onMounted, ref} from 'vue'

import {
  type ExportPreviewRequest,
  type ExportPreviewResult,
  type ExportResource,
  type ExportRow,
  systemExportApi,
} from '@/api'
import {localTimeZone} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.exportPage.title',
  permission: 'module_analytics:report:view',
})

const {t} = useI18n()

/** 预览行数（与后端 `ExportPreviewRequest.limit` 默认一致，后端上限 200） */
const PREVIEW_ROWS = 20

const loading = ref(false)
const failed = ref(false)
const resources = ref<ExportResource[]>([])
const activeResource = ref('')

const previewLoading = ref(false)
const exporting = ref(false)
const preview = ref<ExportPreviewResult | null>(null)
/** 最近一次预览 / 导出是否因缺该资源的细粒度权限被拒（403） */
const permissionDenied = ref(false)

const filterKeyword = ref('')
const filterRange = ref<[string, string] | null>(null)

/** 后端对不带时区偏移的时间按 UTC 解释，这里标出浏览器时区，减少歧义 */
const timezone = localTimeZone()

const activeSpec = computed<ExportResource | null>(
  () => resources.value.find((item) => item.resource === activeResource.value) ?? null,
)
const activeFields = computed(() => activeSpec.value?.fields ?? [])

/** 关键词 / 时间范围过滤（空值一律不发送，交回后端默认语义） */
function currentFilters(): Pick<ExportPreviewRequest, 'keyword' | 'start' | 'end'> {
  return {
    keyword: filterKeyword.value.trim() || null,
    start: filterRange.value?.[0] ?? null,
    end: filterRange.value?.[1] ?? null,
  }
}

/** 把单个单元格值格式化成可读文本（null→'-'、bool→是/否、复合→JSON） */
function formatCell(value: unknown): string {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'boolean') return value ? t('admin.common.yes') : t('admin.common.no')
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

/** 只读加载（`Promise.allSettled`：任一失败不影响其余，失败态单独呈现） */
async function load(): Promise<void> {
  loading.value = true
  failed.value = false
  const [templatesResult] = await Promise.allSettled([systemExportApi.templates()])
  if (templatesResult.status === 'fulfilled') {
    resources.value = templatesResult.value.resources
    const firstResource = resources.value[0]
    if (!activeResource.value && firstResource) {
      activeResource.value = firstResource.resource
    }
  } else {
    resources.value = []
    failed.value = true
  }
  loading.value = false
}

/** 切换资源：清空上一次预览与权限提示，避免串数据 */
function selectResource(resource: string): void {
  if (resource === activeResource.value) return
  activeResource.value = resource
  preview.value = null
  permissionDenied.value = false
}

/** 统一错误处理：403 视为「权限不足」（拦截器已弹后端 msg，这里额外给页面级提示） */
function handleError(error: unknown): void {
  const status = (error as { response?: { status?: number } } | undefined)?.response?.status
  if (status === 403) {
    permissionDenied.value = true
  }
  // 其它错误的提示已由 request 拦截器统一弹出
}

async function runPreview(): Promise<void> {
  if (!activeResource.value) return
  permissionDenied.value = false
  previewLoading.value = true
  try {
    preview.value = await systemExportApi.preview({
      resource: activeResource.value,
      limit: PREVIEW_ROWS,
      ...currentFilters(),
    })
  } catch (error) {
    preview.value = null
    handleError(error)
  } finally {
    previewLoading.value = false
  }
}

async function runExport(): Promise<void> {
  if (!activeResource.value) return
  permissionDenied.value = false
  exporting.value = true
  try {
    const result = await systemExportApi.downloadCsv(activeResource.value, currentFilters())
    ElMessage.success(t('admin.system.exportPage.exported', {name: result.filename}))
  } catch (error) {
    handleError(error)
  } finally {
    exporting.value = false
  }
}

onMounted(load)
</script>

<template>
  <AdminPage :desc="$t('admin.system.exportPage.desc')" :title="$t('admin.system.exportPage.title')">
    <template #actions>
      <el-button :icon="Refresh" :loading="loading" @click="load">
        {{ $t('admin.system.exportPage.refresh') }}
      </el-button>
    </template>

    <el-alert
      v-if="failed"
      :closable="false"
      :title="$t('admin.system.exportPage.loadFailed')"
      class="mb-3"
      show-icon
      type="error"
    />

    <el-alert
      v-if="permissionDenied"
      :closable="false"
      class="mb-3"
      show-icon
      type="warning"
    >
      <template #title>{{ $t('admin.system.exportPage.permissionDenied') }}</template>
      <div class="permission-hint">
        {{
          $t('admin.system.exportPage.permissionDeniedHint', {
            code: activeSpec?.permission ?? '-',
          })
        }}
      </div>
    </el-alert>

    <div class="export-layout">
      <!-- 左侧：资源清单 -->
      <aside class="export-card export-aside">
        <div class="export-card__title">{{ $t('admin.system.exportPage.resourceSection') }}</div>
        <div v-loading="loading" class="export-aside__body">
          <ul v-if="resources.length" class="export-resource-list">
            <li
              v-for="item in resources"
              :key="item.resource"
              :class="['export-resource', {'is-active': item.resource === activeResource}]"
              @click="selectResource(item.resource)"
            >
              <span class="export-resource__label">{{ item.label }}</span>
              <code class="export-resource__code">{{ item.resource }}</code>
            </li>
          </ul>
          <el-empty
            v-else-if="!loading"
            :description="$t('admin.system.exportPage.resourceEmpty')"
            :image-size="60"
          />
        </div>
      </aside>

      <!-- 右侧：字段清单 + 过滤 + 预览 / 导出 -->
      <section class="export-main">
        <div class="export-card mb-3">
          <div class="export-card__head">
            <span class="export-card__title">
              {{ $t('admin.system.exportPage.fieldSection') }}
              <template v-if="activeSpec">· {{ activeSpec.label }}</template>
            </span>
            <span v-if="activeFields.length" class="export-card__meta">
              {{ $t('admin.system.exportPage.fieldCount', {n: activeFields.length}) }}
            </span>
          </div>
          <p v-if="activeSpec" class="export-hint">
            {{ $t('admin.system.exportPage.requiredPermission') }}：<code>{{ activeSpec.permission }}</code>
          </p>
          <el-table
            v-if="activeFields.length"
            :data="activeFields"
            border
            max-height="240"
            size="small"
            stripe
          >
            <el-table-column :label="$t('admin.system.exportPage.fieldKey')" prop="key" width="220"/>
            <el-table-column :label="$t('admin.system.exportPage.fieldLabel')" prop="label"/>
          </el-table>
        </div>

        <div class="export-card mb-3">
          <div class="export-card__head">
            <span class="export-card__title">{{ $t('admin.system.exportPage.filterRange') }}</span>
          </div>
          <p class="export-hint mb-2">{{ $t('admin.system.exportPage.filterHint') }}</p>
          <el-form :inline="true" class="export-filter">
            <el-form-item :label="$t('admin.system.exportPage.filterKeyword')">
              <el-input
                v-model="filterKeyword"
                :disabled="!activeResource"
                :placeholder="$t('admin.system.exportPage.keywordPlaceholder')"
                clearable
                style="width: 240px"
                @keyup.enter="runPreview"
              />
            </el-form-item>
            <el-form-item :label="$t('admin.system.exportPage.filterRange')">
              <el-date-picker
                v-model="filterRange"
                :disabled="!activeResource"
                end-placeholder=""
                range-separator="→"
                start-placeholder=""
                type="datetimerange"
                value-format="YYYY-MM-DDTHH:mm:ss"
              />
            </el-form-item>
            <el-form-item>
              <el-button
                :disabled="!activeResource"
                :icon="View"
                :loading="previewLoading"
                type="primary"
                @click="runPreview"
              >
                {{ $t('admin.system.exportPage.preview') }}
              </el-button>
              <el-button
                :disabled="!activeResource"
                :icon="Download"
                :loading="exporting"
                @click="runExport"
              >
                {{ $t('admin.system.exportPage.exportCsv') }}
              </el-button>
            </el-form-item>
          </el-form>
          <p class="export-hint">{{ $t('admin.system.exportPage.timezoneHint', {tz: timezone}) }}</p>
        </div>

        <div class="export-card">
          <div class="export-card__head">
            <span class="export-card__title">{{ $t('admin.system.exportPage.previewSection') }}</span>
            <span v-if="preview" class="export-card__meta">
              {{ $t('admin.system.exportPage.fieldCount', {n: preview.count}) }}
            </span>
          </div>
          <p class="export-hint mb-2">{{ $t('admin.system.exportPage.previewHint', {n: PREVIEW_ROWS}) }}</p>
          <el-table
            v-if="preview && preview.rows.length"
            v-loading="previewLoading"
            :data="preview.rows"
            border
            size="small"
            stripe
          >
            <el-table-column
              v-for="col in preview.columns"
              :key="col.key"
              :label="col.label"
              min-width="150"
              show-overflow-tooltip
            >
              <template #default="{ row }">
                {{ formatCell((row as ExportRow)[col.key]) }}
              </template>
            </el-table-column>
          </el-table>
          <el-empty
            v-else
            :description="$t('admin.system.exportPage.previewEmpty')"
            :image-size="60"
          />
        </div>
      </section>
    </div>
  </AdminPage>
</template>

<style scoped>
.export-layout {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.export-aside {
  flex: 0 0 240px;
  max-width: 240px;
}

.export-main {
  flex: 1 1 auto;
  min-width: 0;
}

.export-card {
  padding: 16px 18px;
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-line, #e5e7eb);
  border-radius: 8px;
}

.export-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.export-card__title {
  font-size: 15px;
  font-weight: 600;
}

.export-card__meta {
  font-size: 12px;
  color: var(--color-fg-subtle, #909399);
}

.export-aside__body {
  min-height: 80px;
}

.export-resource-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.export-resource {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  cursor: pointer;
  border-radius: 6px;
}

.export-resource:hover {
  background: var(--color-surface-soft, #f5f7fa);
}

.export-resource.is-active {
  background: var(--el-color-primary-light-9, #ecf5ff);
  color: var(--el-color-primary, #409eff);
}

.export-resource__code {
  font-size: 12px;
  color: var(--color-fg-subtle, #909399);
}

.export-hint {
  margin: 0;
  font-size: 12px;
  color: var(--color-fg-subtle, #909399);
}

.export-filter {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.permission-hint {
  margin-top: 4px;
  font-size: 12px;
}

.mb-2 {
  margin-bottom: 8px;
}

.mb-3 {
  margin-bottom: 16px;
}

@media (max-width: 900px) {
  .export-layout {
    flex-direction: column;
  }

  .export-aside {
    flex-basis: auto;
    width: 100%;
    max-width: none;
  }
}
</style>
