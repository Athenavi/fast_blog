<script lang="ts" setup>
/**
 * 安全中心（T5-11 批次 3）
 *
 * 对齐 v3 `/system/security`：总览聚合（24h）+ 登录尝试列表 + 令牌黑名单。
 * 锁定账户管理由 `/system/log` 覆盖，本页不重复。
 */
import {ElMessage, ElMessageBox} from '@/utils/feedback'
// 追加：异常检测 / 安全报告所需的响应式与类型（既有 import 保持不变）
import {computed, onMounted, reactive, ref} from 'vue'

import {type BlacklistItem, type LoginAttemptItem, securityApi, type SecurityOverview,} from '@/api'
import type {PageQuery} from '@/api/types'
import {useAdminList} from '@/composables/useAdminList'

import type {
  AnomalyItem,
  AnomalyResult,
  AnomalyThresholds,
  SecurityReport,
  SecurityReportHistoryItem,
  SuspiciousIp,
} from '@/api/modules/security'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.system.security.title',
  permission: 'module_system:security:view',
})

const {t} = useI18n()

const activeTab = ref<'attempts' | 'blacklist' | 'anomalies' | 'report'>('attempts')
const overview = ref<SecurityOverview | null>(null)

async function loadOverview(): Promise<void> {
  try {
    overview.value = await securityApi.overview()
  } catch {
    overview.value = null
  }
}

onMounted(loadOverview)

/** 统计卡：依赖 overview 响应式重建 */
const stats = computed<Array<{ label: string; value: number | string }>>(() => {
  const o = overview.value
  if (!o) return []
  return [
    {label: t('admin.system.security.statAttempts'), value: o.attempts_24h},
    {label: t('admin.system.security.statFailures'), value: o.failures_24h},
    {label: t('admin.system.security.statSuccessRate'), value: `${(o.success_rate * 100).toFixed(1)}%`},
    {label: t('admin.system.security.statLocked'), value: o.locked_users},
    {label: t('admin.system.security.statBlacklist'), value: o.blacklist_count},
  ]
})

// ---- 登录尝试（筛选条件写入 URL）----
interface AttemptQueryForm extends PageQuery {
  username?: string
  is_success?: boolean
}

const attempts = useAdminList<LoginAttemptItem, AttemptQueryForm>({
  fetcher: (params) => securityApi.attempts(params),
  defaultQuery: {username: '', is_success: undefined},
  syncUrl: true,
})

// ---- 令牌黑名单（无筛选条件，因此不写 URL，避免与上一个列表争用 query）----
const blacklist = useAdminList<BlacklistItem, PageQuery>({
  fetcher: (params) => securityApi.blacklist(params),
})

async function onDeleteBlacklist(row: BlacklistItem) {
  await ElMessageBox.confirm(t('admin.system.security.deleteBlacklistConfirm'), t('admin.common.notice'), {
    type: 'warning',
  })
  await securityApi.removeBlacklist(row.id)
  ElMessage.success(t('admin.common.delete'))
  await Promise.all([loadOverview(), blacklist.reload()])
}

// ================================================================ 异常行为检测
const anomalyResult = ref<AnomalyResult | null>(null)
const anomalyLoading = ref(false)

async function loadAnomalies(): Promise<void> {
  anomalyLoading.value = true
  try {
    anomalyResult.value = await securityApi.anomalies()
  } catch {
    anomalyResult.value = null
  } finally {
    anomalyLoading.value = false
  }
}

// 阈值编辑：打开时从检测结果里拷贝真实阈值，不写死默认值
const thresholdVisible = ref(false)
const thresholdSaving = ref(false)
const thresholdForm = reactive<AnomalyThresholds>({} as AnomalyThresholds)

function openThresholds(): void {
  const current = anomalyResult.value?.thresholds
  if (!current) {
    ElMessage.warning(t('admin.system.security.anomalyEmptyDesc'))
    return
  }
  Object.assign(thresholdForm, current)
  thresholdVisible.value = true
}

async function submitThresholds(): Promise<void> {
  thresholdSaving.value = true
  try {
    const merged = await securityApi.updateAnomalyThresholds({...thresholdForm})
    ElMessage.success(t('admin.system.security.thresholdsSaved'))
    thresholdVisible.value = false
    if (anomalyResult.value) anomalyResult.value = {...anomalyResult.value, thresholds: merged}
    await loadAnomalies()
  } finally {
    thresholdSaving.value = false
  }
}

// 异常类型 / 严重程度 → i18n 键映射（后端返回英文枚举，展示走 i18n）
const ANOMALY_TYPE_KEY: Record<string, string> = {
  brute_force: 'typeBruteForce',
  credential_spray: 'typeCredentialSpray',
  unusual_hours: 'typeUnusualHours',
  rate_abuse: 'typeRateAbuse',
}
const SEVERITY_KEY: Record<string, string> = {
  critical: 'severityCritical',
  high: 'severityHigh',
  medium: 'severityMedium',
}
const SEVERITY_TAG: Record<string, string> = {
  critical: 'danger',
  high: 'warning',
  medium: 'info',
}

function typeLabel(type: string): string {
  const key = ANOMALY_TYPE_KEY[type]
  return key ? t(`admin.system.security.${key}`) : type
}

function severityLabel(severity: string): string {
  const key = SEVERITY_KEY[severity]
  return key ? t(`admin.system.security.${key}`) : severity
}

// ================================================================ 安全周期报表
const reportKind = ref<'weekly' | 'monthly'>('weekly')
const reportLoading = ref(false)
const report = ref<SecurityReport | null>(null)
const archiving = ref(false)

async function loadReport(): Promise<void> {
  reportLoading.value = true
  try {
    report.value = reportKind.value === 'weekly'
      ? await securityApi.weeklyReport()
      : await securityApi.monthlyReport()
  } finally {
    reportLoading.value = false
  }
}

async function archiveReport(): Promise<void> {
  archiving.value = true
  try {
    await securityApi.archiveReport(reportKind.value)
    ElMessage.success(t('admin.system.security.reportArchived'))
    await loadHistory()
  } finally {
    archiving.value = false
  }
}

const reportHistoryList = ref<SecurityReportHistoryItem[]>([])
const historyLoading = ref(false)
const historyTotal = ref(0)
const historyType = ref<'' | 'weekly' | 'monthly'>('')

async function loadHistory(): Promise<void> {
  historyLoading.value = true
  try {
    const result = await securityApi.reportHistory({
      report_type: historyType.value || undefined,
      limit: 20,
    })
    reportHistoryList.value = result.reports
    historyTotal.value = result.count
  } catch {
    reportHistoryList.value = []
    historyTotal.value = 0
  } finally {
    historyLoading.value = false
  }
}

/** Record<string, number> → 表格可渲染的行数组（用于分布类展示） */
function toRows(record: Record<string, number> | undefined): Array<{ name: string; value: number }> {
  return Object.entries(record ?? {}).map(([name, value]) => ({name, value}))
}

onMounted(() => {
  void loadAnomalies()
  void loadHistory()
})
</script>

<template>
  <AdminPage :desc="$t('admin.system.security.desc')" :title="$t('admin.system.security.title')">
    <!-- 统计卡：页面级信息，放在列表壳之外 -->
    <div v-if="stats.length" class="mb-4 grid grid-cols-2 gap-3 md:grid-cols-5">
      <el-card v-for="item in stats" :key="item.label" shadow="never">
        <div class="text-xs text-fg-subtle">{{ item.label }}</div>
        <div class="mt-1 text-xl font-semibold text-fg">{{ item.value }}</div>
      </el-card>
    </div>

    <el-tabs v-model="activeTab">
      <!-- 登录尝试 -->
      <el-tab-pane :label="$t('admin.system.security.tabAttempts')" name="attempts">
        <AdminListShell
          :empty-desc="attempts.hasFilters.value
            ? $t('admin.system.security.emptyFiltered')
            : $t('admin.system.security.emptyDesc')"
          :empty-title="$t('admin.system.security.emptyTitle')"
          :failed="attempts.failed.value"
          :loading="attempts.loading.value"
          :page="attempts.page.value"
          :page-size="attempts.pageSize.value"
          :rows="attempts.rows.value"
          :selectable="false"
          :total="attempts.total.value"
          @refresh="attempts.reload"
          @reset="attempts.reset"
          @search="attempts.search"
          @page-change="attempts.onPageChange"
          @size-change="attempts.onSizeChange"
        >
          <template #filters>
            <el-form-item :label="$t('admin.system.security.username')">
              <el-input
                v-model="attempts.query.username"
                :placeholder="$t('admin.system.security.usernamePlaceholder')"
                clearable
                style="width: 180px"
                @keyup.enter="attempts.search()"
              />
            </el-form-item>
            <el-form-item :label="$t('admin.system.security.result')">
              <el-select
                v-model="attempts.query.is_success"
                :placeholder="$t('admin.common.all')"
                clearable
                style="width: 110px"
              >
                <el-option :label="$t('admin.system.security.resultSuccess')" :value="true"/>
                <el-option :label="$t('admin.system.security.resultFailure')" :value="false"/>
              </el-select>
            </el-form-item>
          </template>

          <el-table-column label="ID" prop="id" width="80"/>
          <el-table-column :label="$t('admin.system.security.username')" min-width="130" prop="username"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.security.ipAddress')" min-width="130" prop="ip_address"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.security.result')" width="90">
            <template #default="{ row }">
              <el-tag :type="(row as LoginAttemptItem).is_success ? 'success' : 'danger'" size="small">
                {{
                  (row as LoginAttemptItem).is_success
                    ? $t('admin.system.security.resultSuccess')
                    : $t('admin.system.security.resultFailure')
                }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.system.security.failureReason')" min-width="150" prop="failure_reason"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.security.userAgent')" min-width="200" prop="user_agent"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.common.createdAt')" min-width="170" prop="created_at"
                           show-overflow-tooltip/>
        </AdminListShell>
      </el-tab-pane>

      <!-- 令牌黑名单 -->
      <el-tab-pane :label="$t('admin.system.security.tabBlacklist')" name="blacklist">
        <AdminListShell
          :empty-desc="$t('admin.system.security.blacklistEmptyDesc')"
          :empty-title="$t('admin.system.security.blacklistEmptyTitle')"
          :failed="blacklist.failed.value"
          :loading="blacklist.loading.value"
          :page="blacklist.page.value"
          :page-size="blacklist.pageSize.value"
          :rows="blacklist.rows.value"
          :selectable="false"
          :total="blacklist.total.value"
          @refresh="blacklist.reload"
          @page-change="blacklist.onPageChange"
          @size-change="blacklist.onSizeChange"
        >
          <el-table-column label="ID" prop="id" width="80"/>
          <el-table-column :label="$t('admin.system.security.tokenIdentifier')" min-width="220"
                           prop="token_identifier" show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.security.reason')" min-width="150" prop="reason"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.security.expiresAt')" min-width="170" prop="expires_at"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.common.createdAt')" min-width="170" prop="created_at"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.common.actions')" fixed="right" width="100">
            <template #default="{ row }">
              <el-button
                v-auth="'module_system:security:delete'"
                link
                type="danger"
                @click="onDeleteBlacklist(row as BlacklistItem)"
              >
                {{ $t('admin.common.delete') }}
              </el-button>
            </template>
          </el-table-column>
        </AdminListShell>
      </el-tab-pane>

      <!-- 异常行为检测：真表窗口聚合 + 可疑 IP 排行 + 可调阈值 -->
      <el-tab-pane :label="$t('admin.system.security.tabAnomalies')" name="anomalies">
        <div class="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
          <el-card shadow="never">
            <div class="text-xs text-fg-subtle">{{ $t('admin.system.security.statTotal') }}</div>
            <div class="mt-1 text-xl font-semibold text-fg">{{ anomalyResult?.summary.total ?? 0 }}</div>
          </el-card>
          <el-card shadow="never">
            <div class="text-xs text-fg-subtle">{{ $t('admin.system.security.statCritical') }}</div>
            <div class="mt-1 text-xl font-semibold text-fg">
              {{ anomalyResult?.summary.by_severity.critical ?? 0 }}
            </div>
          </el-card>
          <el-card shadow="never">
            <div class="text-xs text-fg-subtle">{{ $t('admin.system.security.statHigh') }}</div>
            <div class="mt-1 text-xl font-semibold text-fg">
              {{ anomalyResult?.summary.by_severity.high ?? 0 }}
            </div>
          </el-card>
          <el-card shadow="never">
            <div class="text-xs text-fg-subtle">{{ $t('admin.system.security.statMedium') }}</div>
            <div class="mt-1 text-xl font-semibold text-fg">
              {{ anomalyResult?.summary.by_severity.medium ?? 0 }}
            </div>
          </el-card>
        </div>

        <div class="mb-3 flex flex-wrap items-center gap-2">
          <el-alert v-if="anomalyResult" :closable="false" :title="anomalyResult.data_source" show-icon
                    type="info"/>
          <el-button :loading="anomalyLoading" type="primary" @click="loadAnomalies">
            {{ $t('admin.system.security.anomalyRefresh') }}
          </el-button>
          <el-button v-auth="'module_system:setting:edit'" @click="openThresholds">
            {{ $t('admin.system.security.editThresholds') }}
          </el-button>
        </div>

        <el-table v-loading="anomalyLoading" :data="anomalyResult?.items ?? []" border size="small" stripe>
          <el-table-column :label="$t('admin.system.security.anomalyType')" width="150">
            <template #default="{ row }">{{ typeLabel((row as AnomalyItem).type) }}</template>
          </el-table-column>
          <el-table-column :label="$t('admin.system.security.severity')" width="100">
            <template #default="{ row }">
              <el-tag :type="(SEVERITY_TAG[(row as AnomalyItem).severity] || 'info') as never" size="small">
                {{ severityLabel((row as AnomalyItem).severity) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('admin.system.security.target')" min-width="120" prop="target"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.security.ipAddress')" min-width="130" prop="ip_address"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.security.count')" align="right" prop="count" width="90"/>
          <el-table-column :label="$t('admin.system.security.threshold')" align="right" prop="threshold"
                           width="90"/>
          <el-table-column :label="$t('admin.system.security.detail')" min-width="260" prop="detail"
                           show-overflow-tooltip/>
        </el-table>

        <el-divider>{{ $t('admin.system.security.topSuspiciousIps') }}</el-divider>
        <el-table :data="anomalyResult?.top_suspicious_ips ?? []" border size="small" stripe>
          <el-table-column :label="$t('admin.system.security.ipAddress')" min-width="150" prop="ip_address"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.security.score')" align="right" prop="score" width="100"/>
          <el-table-column :label="$t('admin.system.security.hitTypes')" min-width="200">
            <template #default="{ row }">
              <el-tag v-for="(item, index) in (row as SuspiciousIp).anomalies" :key="index" class="mr-1"
                      size="small">
                {{ typeLabel(item) }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 安全报告：周报 / 月报生成 + 归档 + 历史 -->
      <el-tab-pane :label="$t('admin.system.security.tabReport')" name="report">
        <div class="mb-3 flex flex-wrap items-center gap-2">
          <el-radio-group v-model="reportKind">
            <el-radio-button value="weekly">{{ $t('admin.system.security.weekly') }}</el-radio-button>
            <el-radio-button value="monthly">{{ $t('admin.system.security.monthly') }}</el-radio-button>
          </el-radio-group>
          <el-button :loading="reportLoading" type="primary" @click="loadReport">
            {{ $t('admin.system.security.generateReport') }}
          </el-button>
          <el-button v-auth="'module_system:security:view'" :loading="archiving" @click="archiveReport">
            {{ $t('admin.system.security.archiveReport') }}
          </el-button>
        </div>

        <template v-if="report">
          <div class="mb-3 text-sm text-fg-subtle">
            {{ report.period.start }} ~ {{ report.period.end }} · {{ report.period.days }}
          </div>

          <div class="mb-4 grid grid-cols-2 gap-3 md:grid-cols-3">
            <el-card v-if="report.security_score" shadow="never">
              <div class="text-xs text-fg-subtle">{{ $t('admin.system.security.securityScore') }}</div>
              <div class="mt-1 text-xl font-semibold text-fg">{{ report.security_score.score }}</div>
            </el-card>
            <el-card v-if="report.security_score" shadow="never">
              <div class="text-xs text-fg-subtle">{{ $t('admin.system.security.grade') }}</div>
              <div class="mt-1 text-xl font-semibold text-fg">{{ report.security_score.grade }}</div>
            </el-card>
            <el-card shadow="never">
              <div class="text-xs text-fg-subtle">{{ $t('admin.system.security.statAuditEvents') }}</div>
              <div class="mt-1 text-xl font-semibold text-fg">{{ report.summary.total_audit_events }}</div>
            </el-card>
            <el-card shadow="never">
              <div class="text-xs text-fg-subtle">{{ $t('admin.system.security.statFailedOperations') }}</div>
              <div class="mt-1 text-xl font-semibold text-fg">{{ report.summary.failed_operations }}</div>
            </el-card>
            <el-card shadow="never">
              <div class="text-xs text-fg-subtle">{{ $t('admin.system.security.statAuditFailureRate') }}</div>
              <div class="mt-1 text-xl font-semibold text-fg">{{ report.summary.audit_failure_rate }}%</div>
            </el-card>
            <el-card shadow="never">
              <div class="text-xs text-fg-subtle">{{ $t('admin.system.security.statLoginAttempts') }}</div>
              <div class="mt-1 text-xl font-semibold text-fg">{{ report.summary.total_login_attempts }}</div>
            </el-card>
            <el-card shadow="never">
              <div class="text-xs text-fg-subtle">{{ $t('admin.system.security.statFailedLogins') }}</div>
              <div class="mt-1 text-xl font-semibold text-fg">{{ report.summary.failed_logins }}</div>
            </el-card>
            <el-card shadow="never">
              <div class="text-xs text-fg-subtle">{{ $t('admin.system.security.statLoginFailureRate') }}</div>
              <div class="mt-1 text-xl font-semibold text-fg">{{ report.summary.login_failure_rate }}%</div>
            </el-card>
          </div>

          <el-row :gutter="12">
            <el-col :md="12">
              <el-divider>{{ $t('admin.system.security.auditByLevel') }}</el-divider>
              <el-table :data="toRows(report.audit.by_level)" border size="small" stripe>
                <el-table-column :label="$t('admin.system.security.name')" prop="name"
                                 show-overflow-tooltip/>
                <el-table-column :label="$t('admin.system.security.count')" align="right" prop="value"
                                 width="100"/>
              </el-table>
              <el-divider>{{ $t('admin.system.security.auditByStatus') }}</el-divider>
              <el-table :data="toRows(report.audit.by_status)" border size="small" stripe>
                <el-table-column :label="$t('admin.system.security.name')" prop="name"
                                 show-overflow-tooltip/>
                <el-table-column :label="$t('admin.system.security.count')" align="right" prop="value"
                                 width="100"/>
              </el-table>
            </el-col>
            <el-col :md="12">
              <el-divider>{{ $t('admin.system.security.topActions') }}</el-divider>
              <el-table :data="toRows(report.audit.top_actions)" border size="small" stripe>
                <el-table-column :label="$t('admin.system.security.name')" prop="name"
                                 show-overflow-tooltip/>
                <el-table-column :label="$t('admin.system.security.count')" align="right" prop="value"
                                 width="100"/>
              </el-table>
              <el-divider>{{ $t('admin.system.security.topFailedIps') }}</el-divider>
              <el-table :data="toRows(report.logins.top_failed_ips)" border size="small" stripe>
                <el-table-column :label="$t('admin.system.security.ipAddress')" prop="name"
                                 show-overflow-tooltip/>
                <el-table-column :label="$t('admin.system.security.count')" align="right" prop="value"
                                 width="100"/>
              </el-table>
            </el-col>
          </el-row>

          <el-divider>{{ $t('admin.system.security.reportTrend') }}</el-divider>
          <el-table :data="report.trend" border size="small" stripe>
            <el-table-column :label="$t('admin.system.security.day')" prop="day" width="130"/>
            <el-table-column :label="$t('admin.system.security.auditEvents')" align="right" prop="audit_events"
                             width="120"/>
            <el-table-column :label="$t('admin.system.security.failedLogins')" align="right"
                             prop="failed_logins" width="120"/>
          </el-table>
        </template>
        <el-empty v-else :description="$t('admin.system.security.reportEmpty')"/>

        <el-divider>{{ $t('admin.system.security.reportHistory') }}</el-divider>
        <div class="mb-2 flex flex-wrap items-center gap-2">
          <el-select v-model="historyType" clearable style="width: 160px">
            <el-option :label="$t('admin.system.security.weekly')" value="weekly"/>
            <el-option :label="$t('admin.system.security.monthly')" value="monthly"/>
          </el-select>
          <el-button :loading="historyLoading" @click="loadHistory">
            {{ $t('admin.common.refresh') }}
          </el-button>
          <span class="text-xs text-fg-subtle">{{ historyTotal }}</span>
        </div>
        <el-table v-loading="historyLoading" :data="reportHistoryList" border size="small" stripe>
          <el-table-column label="ID" prop="id" width="80"/>
          <el-table-column :label="$t('admin.system.security.reportName')" min-width="200" prop="report_name"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.security.reportType')" min-width="150" prop="report_type"
                           show-overflow-tooltip/>
          <el-table-column :label="$t('admin.system.security.reportFormat')" prop="format" width="90"/>
          <el-table-column :label="$t('admin.system.security.reportGeneratedAt')" min-width="170"
                           prop="generated_at" show-overflow-tooltip/>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 调整异常检测阈值（增量更新，未知键由后端拒绝） -->
    <el-drawer v-model="thresholdVisible" :title="$t('admin.system.security.editThresholds')"
               destroy-on-close size="460px">
      <el-form v-if="thresholdForm" :model="thresholdForm" label-width="180px">
        <el-form-item :label="$t('admin.system.security.thresholdBruteForceFailures')">
          <el-input-number v-model="thresholdForm.brute_force_failures" :max="1000" :min="1"
                           style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.security.thresholdBruteForceWindowMinutes')">
          <el-input-number v-model="thresholdForm.brute_force_window_minutes" :max="1440" :min="1"
                           style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.security.thresholdSprayUsernames')">
          <el-input-number v-model="thresholdForm.spray_usernames" :max="1000" :min="2"
                           style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.security.thresholdSprayWindowMinutes')">
          <el-input-number v-model="thresholdForm.spray_window_minutes" :max="1440" :min="1"
                           style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.security.thresholdUnusualHourStart')">
          <el-input-number v-model="thresholdForm.unusual_hour_start" :max="23" :min="0"
                           style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.security.thresholdUnusualHourEnd')">
          <el-input-number v-model="thresholdForm.unusual_hour_end" :max="23" :min="0"
                           style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.security.thresholdUnusualHourLogins')">
          <el-input-number v-model="thresholdForm.unusual_hour_logins" :max="1000" :min="1"
                           style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.security.thresholdUnusualHourWindowHours')">
          <el-input-number v-model="thresholdForm.unusual_hour_window_hours" :max="720" :min="1"
                           style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.security.thresholdRateAbuseActions')">
          <el-input-number v-model="thresholdForm.rate_abuse_actions" :max="100000" :min="1"
                           style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.security.thresholdRateAbuseWindowMinutes')">
          <el-input-number v-model="thresholdForm.rate_abuse_window_minutes" :max="1440" :min="1"
                           style="width: 100%"/>
        </el-form-item>
        <el-form-item :label="$t('admin.system.security.thresholdMaxItems')">
          <el-input-number v-model="thresholdForm.max_items" :max="500" :min="1" style="width: 100%"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="thresholdVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="thresholdSaving" type="primary" @click="submitThresholds">
          {{ $t('admin.common.save') }}
        </el-button>
      </template>
    </el-drawer>
  </AdminPage>
</template>
