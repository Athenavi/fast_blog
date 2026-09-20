<script lang="ts" setup>
/**
 * 在线升级（ops 域）
 *
 * 对齐 v3 `/ops/upgrade/*`：status / check / apply。
 * - status：当前版本 + app_path + in_progress + 升级历史；
 * - check：检查更新，结果内联展示（latest_version / has_update / source / detail）；
 * - apply：后端二选一实现——立即执行（started/message）或干跑（dry_run/ready/checks），
 *   页面按返回字段分支渲染；in_progress=true 时检查/升级按钮禁用。
 */
import {Refresh} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, onMounted, ref} from 'vue'

import {
  upgradeApi,
  type UpgradeApplyCheck,
  type UpgradeApplyResult,
  type UpgradeCheckResult,
  type UpgradeHistoryItem,
  type UpgradeStatus,
} from '@/api'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.ops.upgrade.title',
  permission: 'module_ops:upgrade:view',
})

const {t} = useI18n()

const loading = ref(false)
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
      <el-table v-loading="loading" :data="status?.history ?? []" border stripe>
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
  </div>
</template>
