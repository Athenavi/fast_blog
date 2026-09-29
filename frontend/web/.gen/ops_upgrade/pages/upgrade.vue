<script lang="ts" setup>
/**
 * 在线升级（ops 域）
 *
 * 对齐 v3 `/ops/upgrade/*`：status / check / apply。
 * - status：当前版本 + app_path + in_progress + 升级历史；
 * - check：检查更新，结果内联展示（latest_version / has_update / source / detail）；
 * - apply：后端二选一实现——立即执行（started/message）或干跑（dry_run/ready/checks），
 *   页面按返回字段分支渲染；in_progress=true 时检查/升级按钮禁用。
 *
 * 追加（批次 18）：升级设置（重启命令，GET/PUT settings）、版本明细（versions）、
 * 路径策略（paths）、本地更新包（packages + 下载）、执行预演（plan）、真实升级（execute）、
 * 升级备份与回滚（backups / rollback）。保存重启命令、真实升级与回滚均为危险操作：
 * 一律先二次确认，并把逐步结果如实展示（execute / rollback 需 confirm=true）。
 */
import {Download, Refresh, RefreshLeft, View} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, onMounted, ref, watch} from 'vue'

import {
  upgradeApi,
  type UpgradeApplyCheck,
  type UpgradeApplyResult,
  type UpgradeBackupItem,
  type UpgradeCheckResult,
  type UpgradeExecuteResult,
  type UpgradeHistoryItem,
  type UpgradePackageItem,
  type UpgradePathPolicy,
  type UpgradePlan,
  type UpgradeSettings,
  type UpgradeStatus,
  type UpgradeVersionInfo,
  type UpgradeVersions,
} from '@/api'
import {formatDateTime, formatFileSize} from '@/utils/format'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.ops.upgrade.title',
  permission: 'module_ops:upgrade:view',
})

const {t} = useI18n()

const loading = ref(false)
/** 加载失败（用于错误态与重试） */
const loadFailed = ref(false)
const checking = ref(false)
const applying = ref(false)

const status = ref<UpgradeStatus | null>(null)
const checkResult = ref<UpgradeCheckResult | null>(null)
const applyResult = ref<UpgradeApplyResult | null>(null)

const inProgress = computed(() => status.value?.in_progress ?? false)

async function load(): Promise<void> {
  loading.value = true
  try {
    status.value = await upgradeApi.status()
  } catch {
    // 失败时置错误态，避免把「请求失败」显示成「暂无数据」
    loadFailed.value = true
    status.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)

/** 检查更新 */
async function onCheck(): Promise<void> {
  checking.value = true
  try {
    checkResult.value = await upgradeApi.check()
  } finally {
    checking.value = false
  }
}

/** 执行升级：确认后调用 apply，按 started / dry_run 分支渲染 */
async function onApply(): Promise<void> {
  await ElMessageBox.confirm(t('admin.ops.upgrade.applyConfirm'), t('admin.common.notice'), {
    type: 'warning',
  })
  applying.value = true
  applyResult.value = null
  try {
    const res = await upgradeApi.apply()
    applyResult.value = res
    if (res.started) {
      ElMessage.success(res.message || t('admin.ops.upgrade.applyStarted'))
      await load()
    }
  } finally {
    applying.value = false
  }
}

// ---- 状态 / 来源映射 ----
type TagType = 'success' | 'warning' | 'danger'

/** 历史状态 → tag 颜色：成功绿 / 失败红 / 其余（进行中、等待中、未知）按 warning */
function statusTagType(rowStatus: string): TagType {
  const s = (rowStatus || '').toLowerCase()
  if (['success', 'succeeded', 'completed', 'done', 'ok', 'finished'].includes(s)) return 'success'
  if (['failed', 'failure', 'error', 'aborted', 'cancelled', 'canceled'].includes(s)) return 'danger'
  return 'warning'
}

const STATUS_LABEL_KEYS: Record<string, string> = {
  success: 'admin.ops.upgrade.statusSuccess',
  succeeded: 'admin.ops.upgrade.statusSuccess',
  completed: 'admin.ops.upgrade.statusSuccess',
  done: 'admin.ops.upgrade.statusSuccess',
  ok: 'admin.ops.upgrade.statusSuccess',
  finished: 'admin.ops.upgrade.statusSuccess',
  failed: 'admin.ops.upgrade.statusFailed',
  failure: 'admin.ops.upgrade.statusFailed',
  error: 'admin.ops.upgrade.statusFailed',
  aborted: 'admin.ops.upgrade.statusFailed',
  cancelled: 'admin.ops.upgrade.statusFailed',
  canceled: 'admin.ops.upgrade.statusFailed',
  running: 'admin.ops.upgrade.statusRunning',
  in_progress: 'admin.ops.upgrade.statusRunning',
  pending: 'admin.ops.upgrade.statusPending',
}

function statusLabel(rowStatus: string): string {
  const key = STATUS_LABEL_KEYS[(rowStatus || '').toLowerCase()]
  return key ? t(key) : rowStatus
}

const SOURCE_LABEL_KEYS: Record<string, string> = {
  remote: 'admin.ops.upgrade.sourceRemote',
  local_releases: 'admin.ops.upgrade.sourceLocalReleases',
  none: 'admin.ops.upgrade.sourceNone',
}

function sourceLabel(source: string): string {
  const key = SOURCE_LABEL_KEYS[source]
  return key ? t(key) : source
}

// ---------------------------------------------------------------- 升级设置（重启命令）
const settingsLoading = ref(false)
const settingsSaving = ref(false)
const settings = ref<UpgradeSettings | null>(null)
const restartCommand = ref('')

async function loadSettings(): Promise<void> {
  settingsLoading.value = true
  try {
    const data = await upgradeApi.getSettings()
    settings.value = data
    restartCommand.value = data.restart_command ?? ''
  } catch {
    settings.value = null
  } finally {
    settingsLoading.value = false
  }
}

/** 重启命令会被服务端真实执行，保存前二次确认 */
async function onSaveSettings(): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.ops.upgrade.saveSettingsConfirm'),
    t('admin.ops.upgrade.dangerousOperation'),
    {type: 'warning'},
  )
  settingsSaving.value = true
  try {
    const saved = await upgradeApi.saveSettings({restart_command: restartCommand.value.trim()})
    settings.value = saved
    restartCommand.value = saved.restart_command ?? ''
    ElMessage.success(t('admin.ops.upgrade.settingsSaved'))
  } finally {
    settingsSaving.value = false
  }
}

// ---------------------------------------------------------------- 版本明细
const versionsLoading = ref(false)
const versions = ref<UpgradeVersions | null>(null)

const VERSION_GROUP_LABEL_KEYS: Record<string, string> = {
  release: 'admin.ops.upgrade.versionRelease',
  database: 'admin.ops.upgrade.versionDatabase',
  author: 'admin.ops.upgrade.versionAuthor',
  backend: 'admin.ops.upgrade.versionBackend',
  frontend: 'admin.ops.upgrade.versionFrontend',
}

function versionGroupLabel(key: string): string {
  const labelKey = VERSION_GROUP_LABEL_KEYS[key]
  return labelKey ? t(labelKey) : key
}

const versionGroups = computed<Record<string, UpgradeVersionInfo>>(() => {
  const data = versions.value
  if (!data) return {}
  return {
    release: data.release,
    database: data.database,
    author: data.author,
    backend: data.backend,
    frontend: data.frontend,
  }
})

async function loadVersions(): Promise<void> {
  versionsLoading.value = true
  try {
    versions.value = await upgradeApi.versions()
  } catch {
    versions.value = null
  } finally {
    versionsLoading.value = false
  }
}

// ---------------------------------------------------------------- 路径策略
const pathsLoading = ref(false)
const paths = ref<UpgradePathPolicy | null>(null)

async function loadPaths(): Promise<void> {
  pathsLoading.value = true
  try {
    paths.value = await upgradeApi.paths()
  } catch {
    paths.value = null
  } finally {
    pathsLoading.value = false
  }
}

// ---------------------------------------------------------------- 本地更新包
const packagesLoading = ref(false)
const packages = ref<UpgradePackageItem[]>([])
const packagesTotal = ref(0)
const downloading = ref<string | null>(null)

async function loadPackages(): Promise<void> {
  packagesLoading.value = true
  try {
    const data = await upgradeApi.packages()
    packages.value = data.items
    packagesTotal.value = data.total
  } catch {
    packages.value = []
    packagesTotal.value = 0
  } finally {
    packagesLoading.value = false
  }
}

async function onDownload(row: UpgradePackageItem): Promise<void> {
  downloading.value = row.filename
  try {
    await upgradeApi.downloadPackage(row.filename)
    ElMessage.success(t('admin.ops.upgrade.downloadStarted', {name: row.filename}))
  } finally {
    downloading.value = null
  }
}

// ---------------------------------------------------------------- 升级计划 / 真实升级
const planTarget = ref('')
const planLoading = ref(false)
const planResult = ref<UpgradePlan | null>(null)
const executing = ref(false)
const runMigration = ref(true)
const clearCache = ref(true)
const stopService = ref('')
const opResult = ref<UpgradeExecuteResult | null>(null)

/** 检查更新拿到 latest_version 后，自动带入目标版本（用户仍可改） */
watch(checkResult, (value) => {
  if (value?.latest_version && !planTarget.value) planTarget.value = value.latest_version
})

/** 执行预演（只读）：列出将替换 / 将跳过的文件 */
async function onPlan(): Promise<void> {
  const target = planTarget.value.trim()
  if (!target) {
    ElMessage.warning(t('admin.ops.upgrade.targetVersionRequired'))
    return
  }
  planLoading.value = true
  planResult.value = null
  try {
    planResult.value = await upgradeApi.plan(target)
  } catch {
    planResult.value = null
  } finally {
    planLoading.value = false
  }
}

/** **真实升级**：确认后带 confirm=true 执行；结果（含逐步明细）如实展示 */
async function onExecute(): Promise<void> {
  const target = planTarget.value.trim()
  if (!target) {
    ElMessage.warning(t('admin.ops.upgrade.targetVersionRequired'))
    return
  }
  await ElMessageBox.confirm(
    t('admin.ops.upgrade.executeConfirm', {version: target}),
    t('admin.ops.upgrade.dangerousOperation'),
    {
      type: 'error',
      confirmButtonText: t('admin.ops.upgrade.executeButtonConfirm'),
      confirmButtonClass: 'el-button--danger',
    },
  )
  executing.value = true
  opResult.value = null
  try {
    const result = await upgradeApi.execute({
      target_version: target,
      confirm: true,
      run_migration: runMigration.value,
      clear_cache: clearCache.value,
      stop_service: stopService.value.trim() || null,
    })
    opResult.value = result
    if (result.started) ElMessage.success(t('admin.ops.upgrade.executeStarted'))
    else if (result.ok) ElMessage.success(t('admin.ops.upgrade.executeDoneSuccess'))
    else ElMessage.error(t('admin.ops.upgrade.executeDoneFailed'))
    await load()
  } finally {
    executing.value = false
  }
}

// ---------------------------------------------------------------- 升级备份 / 回滚
const backupsLoading = ref(false)
const backups = ref<UpgradeBackupItem[]>([])
const backupsTotal = ref(0)
const rollingBack = ref<string | null>(null)

async function loadBackups(): Promise<void> {
  backupsLoading.value = true
  try {
    const data = await upgradeApi.backups(20)
    backups.value = data.items
    backupsTotal.value = data.total
  } catch {
    backups.value = []
    backupsTotal.value = 0
  } finally {
    backupsLoading.value = false
  }
}

/** 回滚会用备份覆盖当前代码文件，确认后带 confirm=true 执行 */
async function onRollback(row: UpgradeBackupItem): Promise<void> {
  await ElMessageBox.confirm(
    t('admin.ops.upgrade.rollbackConfirm', {id: row.backup_id}),
    t('admin.ops.upgrade.dangerousOperation'),
    {
      type: 'error',
      confirmButtonText: t('admin.ops.upgrade.rollbackButtonConfirm'),
      confirmButtonClass: 'el-button--danger',
    },
  )
  rollingBack.value = row.backup_id
  opResult.value = null
  try {
    opResult.value = await upgradeApi.rollback({backup_id: row.backup_id, confirm: true})
    ElMessage.success(t('admin.ops.upgrade.rollbackDone'))
    await load()
  } finally {
    rollingBack.value = null
  }
}

onMounted(async () => {
  await Promise.all([loadSettings(), loadVersions(), loadPaths(), loadPackages(), loadBackups()])
})
</script>

<template>
  <div class="page-container">
    <!-- 当前版本 + 操作 -->
    <el-card v-loading="loading" class="mb-4" shadow="never">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div class="text-xs text-fg-subtle">{{ $t('admin.ops.upgrade.currentVersion') }}</div>
          <div class="mt-1 flex items-center gap-3">
            <span class="text-3xl font-semibold text-fg">{{ status?.current_version || '—' }}</span>
            <el-tag v-if="inProgress" size="small" type="warning">
              {{ $t('admin.ops.upgrade.upgrading') }}
            </el-tag>
          </div>
          <div class="mt-2 text-xs break-all text-fg-subtle">
            {{ $t('admin.ops.upgrade.appPath') }}：{{ status?.app_path || '—' }}
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <el-button :icon="Refresh" :loading="loading" @click="load">
            {{ $t('admin.common.refresh') }}
          </el-button>
          <el-button
            v-auth="'module_ops:upgrade:execute'"
            :disabled="inProgress"
            :loading="checking"
            plain
            type="primary"
            @click="onCheck"
          >
            {{ $t('admin.ops.upgrade.checkUpdate') }}
          </el-button>
          <el-button
            v-auth="'module_ops:upgrade:execute'"
            :disabled="inProgress"
            :loading="applying"
            type="primary"
            @click="onApply"
          >
            {{ $t('admin.ops.upgrade.apply') }}
          </el-button>
        </div>
      </div>

      <!-- 检查更新结果（内联展示） -->
      <el-alert
        v-if="checkResult"
        :closable="false"
        :type="checkResult.has_update ? 'success' : 'info'"
        class="mt-4"
      >
        <div class="text-sm text-fg">
          <span>{{ $t('admin.ops.upgrade.latestVersion') }}：{{ checkResult.latest_version || '—' }}</span>
          <el-tag :type="checkResult.has_update ? 'success' : 'info'" class="ml-2" size="small">
            {{ checkResult.has_update ? $t('admin.ops.upgrade.hasUpdate') : $t('admin.ops.upgrade.noUpdate') }}
          </el-tag>
        </div>
        <div class="mt-1 text-xs text-fg-subtle">
          <span>{{ $t('admin.ops.upgrade.source') }}：{{ sourceLabel(checkResult.source) }}</span>
          <span v-if="checkResult.detail" class="ml-3">{{ checkResult.detail }}</span>
        </div>
      </el-alert>

      <!-- apply 结果分支渲染 -->
      <template v-if="applyResult">
        <!-- 干跑形态：dry_run + ready + checks -->
        <div v-if="applyResult.dry_run" class="mt-4">
          <el-alert
            :closable="false"
            :title="applyResult.ready ? $t('admin.ops.upgrade.dryRunReady') : $t('admin.ops.upgrade.dryRunNotReady')"
            :type="applyResult.ready ? 'success' : 'warning'"
            class="mb-2"
          />
          <div class="mb-2 text-sm font-medium text-fg">{{ $t('admin.ops.upgrade.checks') }}</div>
          <el-table :data="applyResult.checks ?? []" border size="small">
            <el-table-column :label="$t('admin.ops.upgrade.checkName')" min-width="180" prop="name"/>
            <el-table-column :label="$t('admin.common.status')" width="110">
              <template #default="{ row }">
                <el-tag :type="(row as UpgradeApplyCheck).passed ? 'success' : 'danger'" size="small">
                  {{
                    (row as UpgradeApplyCheck).passed
                      ? $t('admin.ops.upgrade.checkPassed')
                      : $t('admin.ops.upgrade.checkFailed')
                  }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              :label="$t('admin.ops.upgrade.checkDetail')"
              min-width="240"
              prop="detail"
              show-overflow-tooltip
            />
          </el-table>
        </div>

        <!-- 立即执行形态：started + message（started 已在脚本里刷新状态） -->
        <el-alert
          v-else
          :closable="false"
          :description="applyResult.message"
          :title="applyResult.started ? $t('admin.ops.upgrade.applyStarted') : $t('admin.ops.upgrade.applyNotStarted')"
          :type="applyResult.started ? 'success' : 'info'"
          class="mt-4"
        />
      </template>
    </el-card>

    <!-- 升级历史 -->
    <el-card shadow="never">
      <template #header>
        <span>{{ $t('admin.ops.upgrade.history') }}</span>
      </template>
      <AdminTableSkeleton v-if="loading && !(status?.history ?? []).length" :rows="5"/>

      <AdminEmpty
        v-else-if="!loading && !(status?.history ?? []).length"
        :title="loadFailed ? $t('admin.common.loadFailed') : $t('admin.common.empty')"
        :variant="loadFailed ? 'error' : 'default'"
      >
        <el-button v-if="loadFailed" :icon="Refresh" @click="load()">
          {{ $t('admin.common.retry') }}
        </el-button>
      </AdminEmpty>

      <el-table v-else v-loading="loading" :data="status?.history ?? []" border stripe>
        <el-table-column :label="$t('admin.ops.upgrade.targetVersion')" min-width="120" prop="target_version"/>
        <el-table-column :label="$t('admin.common.status')" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTagType((row as UpgradeHistoryItem).status)" size="small">
              {{ statusLabel((row as UpgradeHistoryItem).status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.ops.upgrade.startedAt')" min-width="170" show-overflow-tooltip>
          <template #default="{ row }">{{ (row as UpgradeHistoryItem).started_at || '—' }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.ops.upgrade.finishedAt')" min-width="170" show-overflow-tooltip>
          <template #default="{ row }">{{ (row as UpgradeHistoryItem).finished_at || '—' }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.ops.upgrade.message')" min-width="220" prop="message"
                         show-overflow-tooltip>
          <template #default="{ row }">{{ (row as UpgradeHistoryItem).message || '—' }}</template>
        </el-table-column>
        <template #empty>{{ $t('admin.ops.upgrade.noHistory') }}</template>
      </el-table>
    </el-card>

    <!-- 升级设置（重启命令会被服务端真实执行） -->
    <el-card v-loading="settingsLoading" class="mt-4" shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ $t('admin.ops.upgrade.settingsTitle') }}</span>
          <el-button
            v-auth="'module_ops:upgrade:execute'"
            :loading="settingsSaving"
            link
            type="primary"
            @click="onSaveSettings"
          >
            {{ $t('admin.ops.upgrade.saveSettings') }}
          </el-button>
        </div>
      </template>
      <p class="hint">{{ $t('admin.ops.upgrade.restartCommandHint') }}</p>
      <el-form v-if="settings" label-width="160px" size="small" @submit.prevent>
        <el-form-item :label="$t('admin.ops.upgrade.restartCommand')">
          <el-input
            v-model="restartCommand"
            :placeholder="$t('admin.ops.upgrade.restartCommandPlaceholder')"
            clearable
          />
        </el-form-item>
        <el-form-item :label="$t('admin.ops.upgrade.settingsStatus')">
          <el-tag :type="settings.configured ? 'success' : 'info'" size="small">
            {{
              settings.configured
                ? $t('admin.ops.upgrade.settingsConfigured')
                : $t('admin.ops.upgrade.settingsNotConfigured')
            }}
          </el-tag>
        </el-form-item>
      </el-form>
      <AdminEmpty v-else :title="$t('admin.common.loadFailed')" variant="error">
        <el-button :icon="Refresh" @click="loadSettings()">{{ $t('admin.common.retry') }}</el-button>
      </AdminEmpty>
    </el-card>

    <!-- 版本明细（release / database / author + 前后端） -->
    <el-card v-loading="versionsLoading" class="mt-4" shadow="never">
      <template #header>
        <span>{{ $t('admin.ops.upgrade.versionsTitle') }}</span>
      </template>
      <el-descriptions v-if="versions" :column="1" border size="small">
        <el-descriptions-item
          v-for="(info, group) in versionGroups"
          :key="group"
          :label="versionGroupLabel(group)"
        >
          <div v-if="Object.keys(info).length" class="kv">
            <div v-for="(value, key) in info" :key="key" class="kv__row">
              <span class="kv__key">{{ key }}</span>
              <span class="kv__value">{{ value }}</span>
            </div>
          </div>
          <span v-else class="text-fg-subtle">{{ $t('admin.common.empty') }}</span>
        </el-descriptions-item>
      </el-descriptions>
      <AdminEmpty v-else :title="$t('admin.common.loadFailed')" variant="error">
        <el-button :icon="Refresh" @click="loadVersions()">{{ $t('admin.common.retry') }}</el-button>
      </AdminEmpty>
    </el-card>

    <!-- 路径策略（会替换哪些代码 / 绝不触碰哪些数据） -->
    <el-card v-loading="pathsLoading" class="mt-4" shadow="never">
      <template #header>
        <span>{{ $t('admin.ops.upgrade.pathsTitle') }}</span>
      </template>
      <p class="hint">{{ $t('admin.ops.upgrade.pathsHint') }}</p>
      <template v-if="paths">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item :label="$t('admin.ops.upgrade.pathsProjectRoot')">
            {{ paths.project_root }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.ops.upgrade.pathsReleasesDir')">
            {{ paths.releases_dir }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.ops.upgrade.pathsBackupRoot')">
            {{ paths.backup_root }}
          </el-descriptions-item>
        </el-descriptions>
        <el-row :gutter="16" class="mt-2">
          <el-col :span="12">
            <div class="path-group">
              <div class="path-group__title path-group__title--allow">
                {{ $t('admin.ops.upgrade.pathsAllowedPrefixes') }}
              </div>
              <div class="path-group__list">
                <div v-for="item in paths.allowed_prefixes" :key="item" class="path-group__item">{{ item }}</div>
              </div>
            </div>
            <div class="path-group">
              <div class="path-group__title path-group__title--allow">
                {{ $t('admin.ops.upgrade.pathsAllowedFiles') }}
              </div>
              <div class="path-group__list">
                <div v-for="item in paths.allowed_files" :key="item" class="path-group__item">{{ item }}</div>
              </div>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="path-group">
              <div class="path-group__title path-group__title--protect">
                {{ $t('admin.ops.upgrade.pathsProtectedDirs') }}
              </div>
              <div class="path-group__list">
                <div v-for="item in paths.protected_dirs" :key="item" class="path-group__item">{{ item }}</div>
              </div>
            </div>
            <div class="path-group">
              <div class="path-group__title path-group__title--protect">
                {{ $t('admin.ops.upgrade.pathsProtectedFiles') }}
              </div>
              <div class="path-group__list">
                <div v-for="item in paths.protected_files" :key="item" class="path-group__item">{{ item }}</div>
              </div>
            </div>
          </el-col>
        </el-row>
      </template>
      <AdminEmpty v-else :title="$t('admin.common.loadFailed')" variant="error">
        <el-button :icon="Refresh" @click="loadPaths()">{{ $t('admin.common.retry') }}</el-button>
      </AdminEmpty>
    </el-card>

    <!-- 本地更新包清单 + 下载 -->
    <el-card v-loading="packagesLoading" class="mt-4" shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ $t('admin.ops.upgrade.packagesTitle') }}</span>
          <el-button :icon="Refresh" link @click="loadPackages()">{{ $t('admin.common.refresh') }}</el-button>
        </div>
      </template>
      <p class="hint">{{ $t('admin.ops.upgrade.packagesHint') }}</p>
      <AdminTableSkeleton v-if="packagesLoading && !packages.length" :rows="3"/>
      <AdminEmpty
        v-else-if="!packagesLoading && !packages.length"
        :title="$t('admin.ops.upgrade.packagesEmpty')"
      />
      <el-table v-else :data="packages" border size="small" stripe>
        <el-table-column
          :label="$t('admin.ops.upgrade.packageFilename')"
          min-width="220"
          prop="filename"
          show-overflow-tooltip
        />
        <el-table-column :label="$t('admin.ops.upgrade.packageVersion')" prop="version" width="140"/>
        <el-table-column :label="$t('admin.ops.upgrade.packageSize')" width="110">
          <template #default="{ row }">{{ formatFileSize(row.size) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.ops.upgrade.packageModifiedAt')" min-width="170">
          <template #default="{ row }">{{ formatDateTime(row.modified_at) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.ops.upgrade.packageSha256')" width="120">
          <template #default="{ row }">
            <el-tag :type="row.sha256_file ? 'success' : 'info'" size="small">
              {{
                row.sha256_file
                  ? $t('admin.ops.upgrade.packageSha256Yes')
                  : $t('admin.ops.upgrade.packageSha256No')
              }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="110">
          <template #default="{ row }">
            <el-button
              v-auth="'module_ops:upgrade:view'"
              :icon="Download"
              :loading="downloading === row.filename"
              link
              type="primary"
              @click="onDownload(row)"
            >
              {{ $t('admin.ops.upgrade.download') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <p v-if="packages.length" class="hint">{{ $t('admin.ops.upgrade.packagesTotal', {n: packagesTotal}) }}</p>
    </el-card>

    <!-- 升级计划预览（只读）+ 真实升级入口 -->
    <el-card class="mt-4" shadow="never">
      <template #header>
        <span>{{ $t('admin.ops.upgrade.planTitle') }}</span>
      </template>
      <p class="hint">{{ $t('admin.ops.upgrade.planHint') }}</p>
      <el-form :inline="true" @submit.prevent>
        <el-form-item :label="$t('admin.ops.upgrade.targetVersionLabel')">
          <el-input
            v-model="planTarget"
            :placeholder="$t('admin.ops.upgrade.targetVersionPlaceholder')"
            clearable
            style="width: 260px"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            v-auth="'module_ops:upgrade:execute'"
            :icon="View"
            :loading="planLoading"
            plain
            type="primary"
            @click="onPlan"
          >
            {{ $t('admin.ops.upgrade.planButton') }}
          </el-button>
        </el-form-item>
      </el-form>

      <div v-if="planResult" class="plan-result">
        <el-alert
          :closable="false"
          :title="$t('admin.ops.upgrade.planSummary', {replace: planResult.will_replace_count, skipped: planResult.skipped_count})"
          type="info"
        />
        <div class="hint">
          {{ $t('admin.ops.upgrade.planPackage') }}：{{ planResult.package || '—' }}
          <span v-if="planResult.package_detail">（{{ planResult.package_detail }}）</span>
        </div>
        <el-alert
          v-if="planResult.collisions_with_protected.length"
          :closable="false"
          :title="$t('admin.ops.upgrade.planCollisions')"
          class="mt-2"
          type="warning"
        >
          <div v-for="item in planResult.collisions_with_protected" :key="item" class="text-xs">{{ item }}</div>
        </el-alert>
        <el-collapse class="mt-2">
          <el-collapse-item :title="$t('admin.ops.upgrade.planWillReplaceCount', {n: planResult.will_replace_count})">
            <div class="plan-list">
              <div v-for="item in planResult.will_replace" :key="item">{{ item }}</div>
              <div v-if="!planResult.will_replace.length" class="text-fg-subtle">{{ $t('admin.common.empty') }}</div>
            </div>
          </el-collapse-item>
          <el-collapse-item :title="$t('admin.ops.upgrade.planSkippedCount', {n: planResult.skipped_count})">
            <div class="plan-list">
              <div v-for="item in planResult.skipped" :key="item">{{ item }}</div>
              <div v-if="!planResult.skipped.length" class="text-fg-subtle">{{ $t('admin.common.empty') }}</div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>

      <el-divider/>

      <div class="execute-area">
        <div class="text-sm font-medium text-fg">{{ $t('admin.ops.upgrade.executeTitle') }}</div>
        <p class="hint">{{ $t('admin.ops.upgrade.executeHint') }}</p>
        <div class="flex flex-wrap items-center gap-4 mb-2">
          <el-checkbox v-model="runMigration">{{ $t('admin.ops.upgrade.runMigration') }}</el-checkbox>
          <el-checkbox v-model="clearCache">{{ $t('admin.ops.upgrade.clearCache') }}</el-checkbox>
        </div>
        <el-form label-width="220px" size="small" @submit.prevent>
          <el-form-item :label="$t('admin.ops.upgrade.stopService')">
            <el-input
              v-model="stopService"
              :placeholder="$t('admin.ops.upgrade.stopServicePlaceholder')"
              clearable
            />
            <div class="hint">{{ $t('admin.ops.upgrade.stopServiceHint') }}</div>
          </el-form-item>
        </el-form>
        <el-button
          v-auth="'module_ops:upgrade:execute'"
          :disabled="inProgress"
          :loading="executing"
          type="danger"
          @click="onExecute"
        >
          {{ $t('admin.ops.upgrade.executeButton') }}
        </el-button>
      </div>
    </el-card>

    <!-- 操作结果（真实升级 / 回滚，逐步如实展示） -->
    <el-card v-if="opResult" class="mt-4" shadow="never">
      <template #header>
        <span>{{ $t('admin.ops.upgrade.operationResult') }}</span>
      </template>
      <el-alert
        :closable="false"
        :title="opResult.started
          ? $t('admin.ops.upgrade.executeStarted')
          : opResult.ok
            ? $t('admin.ops.upgrade.operationOk')
            : $t('admin.ops.upgrade.operationFailed')"
        :type="opResult.ok ? 'success' : (opResult.started ? 'info' : 'error')"
      />
      <div v-if="opResult.started" class="hint">{{ opResult.detail || '—' }}</div>
      <template v-else>
        <el-descriptions :column="2" border class="mt-2" size="small">
          <el-descriptions-item :label="$t('admin.ops.upgrade.fromVersion')">
            {{ opResult.from_version || '—' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.ops.upgrade.toVersion')">
            {{ opResult.target_version || '—' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.ops.upgrade.filesReplaced')">
            {{ opResult.files_replaced ?? 0 }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.ops.upgrade.filesSkipped')">
            {{ opResult.skipped ?? 0 }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.ops.upgrade.backupId')">
            {{ opResult.backup_id || '—' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.ops.upgrade.needRestart')">
            <el-tag :type="opResult.need_restart ? 'warning' : 'success'" size="small">
              {{ opResult.need_restart ? $t('admin.common.yes') : $t('admin.common.no') }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
        <div v-if="opResult.restart_detail" class="hint">
          {{ $t('admin.ops.upgrade.restartDetail') }}：{{ opResult.restart_detail }}
        </div>
        <div v-if="(opResult.steps ?? []).length" class="mt-2">
          <div class="mb-2 text-sm font-medium text-fg">{{ $t('admin.ops.upgrade.steps') }}</div>
          <el-table :data="opResult.steps ?? []" border size="small">
            <el-table-column
              :label="$t('admin.ops.upgrade.stepName')"
              min-width="200"
              prop="step"
              show-overflow-tooltip
            />
            <el-table-column :label="$t('admin.common.status')" width="100">
              <template #default="{ row }">
                <el-tag :type="row.ok ? 'success' : 'danger'" size="small">
                  {{ row.ok ? $t('admin.ops.upgrade.checkPassed') : $t('admin.ops.upgrade.checkFailed') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              :label="$t('admin.ops.upgrade.stepDetail')"
              min-width="260"
              prop="detail"
              show-overflow-tooltip
            />
          </el-table>
        </div>
      </template>
    </el-card>

    <!-- 升级备份 + 回滚 -->
    <el-card v-loading="backupsLoading" class="mt-4" shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ $t('admin.ops.upgrade.backupsTitle') }}</span>
          <el-button :icon="Refresh" link @click="loadBackups()">{{ $t('admin.common.refresh') }}</el-button>
        </div>
      </template>
      <p class="hint">{{ $t('admin.ops.upgrade.backupsHint') }}</p>
      <AdminEmpty
        v-if="!backupsLoading && !backups.length"
        :title="$t('admin.ops.upgrade.backupsEmpty')"
      />
      <el-table v-else :data="backups" border row-key="backup_id" size="small" stripe>
        <el-table-column
          :label="$t('admin.ops.upgrade.backupIdCol')"
          min-width="200"
          prop="backup_id"
          show-overflow-tooltip
        />
        <el-table-column :label="$t('admin.ops.upgrade.backupFrom')" width="130">
          <template #default="{ row }">{{ row.from_version || '—' }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.ops.upgrade.backupTarget')" width="130">
          <template #default="{ row }">{{ row.target_version || '—' }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.ops.upgrade.backupFiles')" prop="files" width="90"/>
        <el-table-column :label="$t('admin.ops.upgrade.backupCreatedAt')" min-width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="120">
          <template #default="{ row }">
            <el-button
              v-auth="'module_ops:upgrade:execute'"
              :icon="RefreshLeft"
              :loading="rollingBack === row.backup_id"
              link
              type="warning"
              @click="onRollback(row)"
            >
              {{ $t('admin.ops.upgrade.rollbackButton') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <p v-if="backups.length" class="hint">{{ $t('admin.ops.upgrade.backupsTotal', {n: backupsTotal}) }}</p>
    </el-card>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.hint {
  margin: 8px 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.kv {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kv__row {
  display: flex;
  gap: 8px;
  font-size: 12px;
}

.kv__key {
  min-width: 140px;
  color: var(--el-text-color-secondary);
}

.path-group {
  margin-bottom: 12px;
}

.path-group__title {
  margin-bottom: 4px;
  font-size: 12px;
  font-weight: 600;
}

.path-group__title--allow {
  color: var(--el-color-primary);
}

.path-group__title--protect {
  color: var(--el-color-danger);
}

.path-group__list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.path-group__item {
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--el-fill-color-light);
  font-family: monospace;
  font-size: 12px;
}

.plan-result {
  margin-top: 8px;
}

.plan-list {
  max-height: 240px;
  overflow: auto;
  font-family: monospace;
  font-size: 12px;
}

.execute-area {
  margin-top: 8px;
}
</style>
