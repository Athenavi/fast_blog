<script lang="ts" setup>
/**
 * 进程监督（ops 域）
 *
 * 对齐 v3 `/ops/supervisor/*`：登记（GET/PUT `/process`）、三层健康检查
 * （`/process/{name}/health`）、日志（`/process/{name}/log`）、受控启停
 * （`/process/{name}/{start|stop|restart}`，固定带 `confirm=true`）。
 *
 * 如实呈现是硬要求（后端同样如此）：
 * - 状态由三层探测（pid / 端口 / HTTP）判定，未配置的层显示「未配置」而不是「不通」；
 * - 指标在无 `pid_file` 或 psutil 缺失时显示后端给的原因，不显示假的 0；
 * - 动作**只按登记命令执行**：未登记命令 / 命令返回非 0 / 超时都会把原因原样展示；
 * - 保存是**整体替换**且校验不过时后端不落库 —— 页面保留编辑态并列出 issues。
 */
import {Delete, Document, Edit, Plus, Refresh, RefreshRight, VideoPause, VideoPlay} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from '@/utils/feedback'
import {computed, onMounted, reactive, ref} from 'vue'

import {
  type SupervisorAction,
  type SupervisorActionResult,
  supervisorApi,
  type SupervisorLog,
  type SupervisorProcess,
  type SupervisorProcessPayload,
} from '@/api'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
  title: 'admin.ops.supervisor.title',
  permission: 'module_ops:supervisor:view',
})

const {t} = useI18n()

// ---------------------------------------------------------------- 登记列表
const loading = ref(false)
const processes = ref<SupervisorProcess[]>([])
const updatedAt = ref<string | null>(null)
const issues = ref<string[]>([])
const probingName = ref<string | null>(null)

const runningCount = computed(
  () => processes.value.filter((row) => row.is_active && row.probe?.healthy).length,
)
const notRunningCount = computed(
  () => processes.value.filter((row) => row.is_active && !row.probe?.healthy).length,
)
const disabledCount = computed(() => processes.value.filter((row) => !row.is_active).length)

async function load(): Promise<void> {
  loading.value = true
  try {
    const data = await supervisorApi.list()
    processes.value = data.processes ?? []
    updatedAt.value = data.updated_at ?? null
    issues.value = data.issues ?? []
  } finally {
    loading.value = false
  }
}

onMounted(load)

/** 只提交登记字段（剥离 probe / metrics，后端按 Payload 校验） */
function toPayload(row: SupervisorProcessPayload): SupervisorProcessPayload {
  return {
    name: row.name,
    description: row.description ?? null,
    start_command: row.start_command ?? null,
    stop_command: row.stop_command ?? null,
    restart_command: row.restart_command ?? null,
    pid_file: row.pid_file ?? null,
    log_file: row.log_file ?? null,
    health: {
      host: row.health?.host || '127.0.0.1',
      port: row.health?.port ?? null,
      url: row.health?.url ?? null,
    },
    is_active: row.is_active,
  }
}

/** 整体替换保存；issues 非空表示后端**没有落库**，此时保留编辑态 */
async function saveAll(next: SupervisorProcessPayload[], onSuccess?: () => void): Promise<boolean> {
  const data = await supervisorApi.save(next)
  if (data.issues?.length) {
    issues.value = data.issues
    void ElMessage.warning(t('admin.ops.supervisor.saveIssues'))
    return false
  }
  issues.value = []
  processes.value = data.processes ?? []
  updatedAt.value = data.updated_at ?? null
  ElMessage.success(t('admin.ops.supervisor.saved'))
  onSuccess?.()
  return true
}

// ---------------------------------------------------------------- 状态 / 探测展示
type StatusKey = 'running' | 'stopped' | 'unknown' | 'disabled'

/** 状态判定：停用 > 探明在跑 > 探明没跑 > 未知（三层都没配） */
function statusOf(row: SupervisorProcess): StatusKey {
  if (!row.is_active) return 'disabled'
  if (row.probe?.healthy) return 'running'
  const {alive, port_open: portOpen, http_ok: httpOk} = row.probe ?? {}
  if (alive === false || portOpen === false || httpOk === false) return 'stopped'
  return 'unknown'
}

const STATUS_TAG: Record<StatusKey, 'success' | 'danger' | 'warning' | 'info'> = {
  running: 'success',
  stopped: 'danger',
  unknown: 'warning',
  disabled: 'info',
}

const STATUS_LABEL_KEYS: Record<StatusKey, string> = {
  running: 'admin.ops.supervisor.statusRunning',
  stopped: 'admin.ops.supervisor.statusStopped',
  unknown: 'admin.ops.supervisor.statusUnknown',
  disabled: 'admin.ops.supervisor.statusDisabled',
}

function statusTag(row: SupervisorProcess): 'success' | 'danger' | 'warning' | 'info' {
  return STATUS_TAG[statusOf(row)]
}

function statusLabel(row: SupervisorProcess): string {
  return t(STATUS_LABEL_KEYS[statusOf(row)])
}

/** 单层探测值 → 三态文案 / 颜色（null = 未配置，不能当成「不通」） */
function layerLabel(value: boolean | null | undefined): string {
  if (value === true) return t('admin.ops.supervisor.layerOk')
  if (value === false) return t('admin.ops.supervisor.layerFail')
  return t('admin.ops.supervisor.layerNotConfigured')
}

function layerTag(value: boolean | null | undefined): 'success' | 'danger' | 'info' {
  if (value === true) return 'success'
  if (value === false) return 'danger'
  return 'info'
}

/** 秒 → 人读时长（指标里的运行时长） */
function formatUptime(seconds?: number | null): string {
  if (!seconds || seconds < 0) return '—'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (days) return `${days}d ${hours}h`
  if (hours) return `${hours}h ${minutes}m`
  if (minutes) return `${minutes}m ${seconds % 60}s`
  return `${seconds}s`
}

/** 指标摘要；不可用时如实显示后端给的原因 */
function metricsSummary(row: SupervisorProcess): string {
  const metrics = row.metrics
  if (!metrics?.available) {
    return metrics?.detail || t('admin.ops.supervisor.metricsUnavailable')
  }
  return t('admin.ops.supervisor.metricsSummary', {
    cpu: metrics.cpu_percent ?? 0,
    mem: metrics.memory_rss_mb ?? 0,
    threads: metrics.threads ?? 0,
    uptime: formatUptime(metrics.uptime_seconds),
  })
}

/** 已登记 / 未登记的命令标签 */
function commandTags(row: SupervisorProcess): Array<{ label: string; registered: boolean }> {
  return [
    {label: t('admin.ops.supervisor.start'), registered: Boolean(row.start_command)},
    {label: t('admin.ops.supervisor.stop'), registered: Boolean(row.stop_command)},
    {label: t('admin.ops.supervisor.restart'), registered: Boolean(row.restart_command)},
  ]
}

/** 单进程重新探测（走 /health，只更新这一行） */
async function probeOne(row: SupervisorProcess): Promise<void> {
  probingName.value = row.name
  try {
    const result = await supervisorApi.health(row.name)
    const index = processes.value.findIndex((item) => item.name === row.name)
    const current = index >= 0 ? processes.value[index] : undefined
    if (current) {
      processes.value[index] = {
        ...current,
        probe: {
          healthy: result.healthy,
          alive: result.alive ?? null,
          port_open: result.port_open ?? null,
          http_ok: result.http_ok ?? null,
          detail: result.detail ?? [],
        },
      }
    }
  } finally {
    probingName.value = null
  }
}

// ---------------------------------------------------------------- 受控启停
const ACTION_LABEL_KEYS: Record<SupervisorAction, string> = {
  start: 'admin.ops.supervisor.start',
  stop: 'admin.ops.supervisor.stop',
  restart: 'admin.ops.supervisor.restart',
}

const actingKey = ref<string | null>(null)
const actionVisible = ref(false)
const actionResult = ref<SupervisorActionResult | null>(null)
const actionTitle = ref('')

async function runAction(row: SupervisorProcess, action: SupervisorAction): Promise<void> {
  const label = t(ACTION_LABEL_KEYS[action])
  try {
    await ElMessageBox.confirm(
      t('admin.ops.supervisor.actionConfirm', {name: row.name, action: label}),
      t('admin.common.notice'),
      {type: 'warning'},
    )
  } catch {
    return
  }

  actingKey.value = `${row.name}:${action}`
  try {
    const result = await supervisorApi.act(row.name, action)
    if (result.ok) {
      void ElMessage.success(t('admin.ops.supervisor.actionDone', {action: label}))
    } else {
      // 未登记命令 / 命令返回非 0 / 超时：把后端给的原因与控制台输出原样展示
      actionResult.value = result
      actionTitle.value = `${label} · ${row.name}`
      actionVisible.value = true
    }
    await load()
  } finally {
    actingKey.value = null
  }
}

// ---------------------------------------------------------------- 编辑登记
interface ProcessForm {
  name: string
  description: string
  start_command: string
  stop_command: string
  restart_command: string
  pid_file: string
  log_file: string
  host: string
  port: number | null
  url: string
  is_active: boolean
}

function emptyForm(): ProcessForm {
  return {
    name: '',
    description: '',
    start_command: '',
    stop_command: '',
    restart_command: '',
    pid_file: '',
    log_file: '',
    host: '127.0.0.1',
    port: null,
    url: '',
    is_active: true,
  }
}

const editVisible = ref(false)
const saving = ref(false)
const editingName = ref<string | null>(null)
const form = reactive<ProcessForm>(emptyForm())

function openCreate(): void {
  editingName.value = null
  Object.assign(form, emptyForm())
  editVisible.value = true
}

function openEdit(row: SupervisorProcess): void {
  editingName.value = row.name
  Object.assign(form, {
    name: row.name,
    description: row.description ?? '',
    start_command: row.start_command ?? '',
    stop_command: row.stop_command ?? '',
    restart_command: row.restart_command ?? '',
    pid_file: row.pid_file ?? '',
    log_file: row.log_file ?? '',
    host: row.health?.host || '127.0.0.1',
    port: row.health?.port ?? null,
    url: row.health?.url ?? '',
    is_active: row.is_active,
  })
  editVisible.value = true
}

const NAME_PATTERN = /^[A-Za-z0-9._-]+$/
const MAX_COMMAND_LENGTH = 500

/** 前端先挡一遍明显错误（后端仍会校验；两边不一致时以后端 issues 为准） */
function validateForm(): string | null {
  const name = form.name.trim()
  if (!name) return t('admin.ops.supervisor.nameRequired')
  if (!NAME_PATTERN.test(name)) return t('admin.ops.supervisor.nameInvalid')
  const duplicated = processes.value.some(
    (row) => row.name === name && row.name !== editingName.value,
  )
  if (duplicated) return t('admin.ops.supervisor.nameDuplicate')
  const commands = [form.start_command, form.stop_command, form.restart_command]
  if (commands.some((command) => command.trim().length > MAX_COMMAND_LENGTH)) {
    return t('admin.ops.supervisor.commandTooLong')
  }
  return null
}

async function submitForm(): Promise<void> {
  const invalid = validateForm()
  if (invalid) {
    void ElMessage.warning(invalid)
    return
  }

  const payload: SupervisorProcessPayload = {
    name: form.name.trim(),
    description: form.description.trim() || null,
    start_command: form.start_command.trim() || null,
    stop_command: form.stop_command.trim() || null,
    restart_command: form.restart_command.trim() || null,
    pid_file: form.pid_file.trim() || null,
    log_file: form.log_file.trim() || null,
    health: {
      host: form.host.trim() || '127.0.0.1',
      port: form.port ?? null,
      url: form.url.trim() || null,
    },
    is_active: form.is_active,
  }

  const next = processes.value.map(toPayload)
  const index = next.findIndex((item) => item.name === editingName.value)
  if (index >= 0) next[index] = payload
  else next.push(payload)

  saving.value = true
  try {
    const saved = await saveAll(next)
    if (saved) editVisible.value = false
  } finally {
    saving.value = false
  }
}

async function removeRow(row: SupervisorProcess): Promise<void> {
  try {
    await ElMessageBox.confirm(
      t('admin.ops.supervisor.removeConfirm', {name: row.name}),
      t('admin.common.notice'),
      {type: 'warning'},
    )
  } catch {
    return
  }
  const next = processes.value.filter((item) => item.name !== row.name).map(toPayload)
  await saveAll(next)
  ElMessage.success(t('admin.ops.supervisor.removed'))
}

// ---------------------------------------------------------------- 日志
const logVisible = ref(false)
const logLoading = ref(false)
const logTarget = ref('')
const logResult = ref<SupervisorLog | null>(null)
const logLines = ref(200)

async function reloadLog(): Promise<void> {
  if (!logTarget.value) return
  logLoading.value = true
  try {
    logResult.value = await supervisorApi.log(logTarget.value, logLines.value)
  } finally {
    logLoading.value = false
  }
}

async function openLog(row: SupervisorProcess): Promise<void> {
  logTarget.value = row.name
  logResult.value = null
  logVisible.value = true
  await reloadLog()
}
</script>

<template>
  <div class="page-container">
    <!-- 概览 + 登记入口 -->
    <el-card v-loading="loading" class="overview" shadow="never">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div class="text-xs text-fg-subtle">{{ $t('admin.ops.supervisor.title') }}</div>
          <div class="stats">
            <span class="stat">
              <b>{{ processes.length }}</b>
              <span>{{ $t('admin.ops.supervisor.statTotal') }}</span>
            </span>
            <span class="stat">
              <b class="text-success">{{ runningCount }}</b>
              <span>{{ $t('admin.ops.supervisor.statRunning') }}</span>
            </span>
            <span class="stat">
              <b class="text-danger">{{ notRunningCount }}</b>
              <span>{{ $t('admin.ops.supervisor.statNotRunning') }}</span>
            </span>
            <span class="stat">
              <b>{{ disabledCount }}</b>
              <span>{{ $t('admin.ops.supervisor.statDisabled') }}</span>
            </span>
          </div>
          <div class="mt-2 text-xs break-all text-fg-subtle">
            {{ $t('admin.ops.supervisor.hint') }}
          </div>
          <div v-if="updatedAt" class="mt-1 text-xs text-fg-subtle">
            {{ $t('admin.ops.supervisor.updatedAt') }}：{{ updatedAt }}
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <el-button v-auth="'module_ops:supervisor:config'" :icon="Plus" type="primary" @click="openCreate">
            {{ $t('admin.ops.supervisor.register') }}
          </el-button>
          <el-button :icon="Refresh" :loading="loading" @click="load">
            {{ $t('admin.common.refresh') }}
          </el-button>
        </div>
      </div>

      <!-- 保存被拒时后端返回 issues 且**不落库**，这里原样列出 -->
      <el-alert
        v-if="issues.length"
        class="mt-3"
        closable
        type="error"
        @close="issues = []"
      >
        <template #title>{{ $t('admin.ops.supervisor.saveIssues') }}</template>
        <ul class="issue-list">
          <li v-for="issue in issues" :key="issue">{{ issue }}</li>
        </ul>
      </el-alert>
    </el-card>

    <!-- 进程登记 + 实时状态 -->
    <el-card class="mt-4" shadow="never">
      <AdminTableSkeleton v-if="loading && !processes.length" :rows="5"/>
      <AdminEmpty v-else-if="!loading && !processes.length" :title="$t('admin.common.empty')"/>
      <el-table v-else v-loading="loading" :data="processes" row-key="name">
        <el-table-column :label="$t('admin.ops.supervisor.process')" min-width="180">
          <template #default="{ row }">
            <div class="font-medium">{{ (row as SupervisorProcess).name }}</div>
            <div v-if="(row as SupervisorProcess).description" class="text-xs text-fg-subtle">
              {{ (row as SupervisorProcess).description }}
            </div>
          </template>
        </el-table-column>

        <el-table-column :label="$t('admin.common.status')" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTag(row as SupervisorProcess)" size="small">
              {{ statusLabel(row as SupervisorProcess) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="$t('admin.ops.supervisor.health')" min-width="300">
          <template #default="{ row }">
            <div class="flex flex-wrap items-center gap-1">
              <el-tooltip :show-after="200" placement="top">
                <template #content>
                  <div class="probe-detail">
                    <div v-for="(line, index) in (row as SupervisorProcess).probe?.detail ?? []" :key="index">
                      {{ line }}
                    </div>
                    <div v-if="!((row as SupervisorProcess).probe?.detail ?? []).length">
                      {{ $t('admin.ops.supervisor.healthNoDetail') }}
                    </div>
                  </div>
                </template>
                <span class="flex flex-wrap items-center gap-1">
                  <el-tag :type="layerTag((row as SupervisorProcess).probe?.alive)" size="small">
                    {{ $t('admin.ops.supervisor.layerPid') }}：{{ layerLabel((row as SupervisorProcess).probe?.alive) }}
                  </el-tag>
                  <el-tag :type="layerTag((row as SupervisorProcess).probe?.port_open)" size="small">
                    {{
                      $t('admin.ops.supervisor.layerPort')
                    }}：{{ layerLabel((row as SupervisorProcess).probe?.port_open) }}
                  </el-tag>
                  <el-tag :type="layerTag((row as SupervisorProcess).probe?.http_ok)" size="small">
                    HTTP：{{ layerLabel((row as SupervisorProcess).probe?.http_ok) }}
                  </el-tag>
                </span>
              </el-tooltip>
              <el-button
                :icon="RefreshRight"
                :loading="probingName === (row as SupervisorProcess).name"
                link
                size="small"
                type="primary"
                @click="probeOne(row as SupervisorProcess)"
              >
                {{ $t('admin.ops.supervisor.reprobe') }}
              </el-button>
            </div>
          </template>
        </el-table-column>

        <el-table-column :label="$t('admin.ops.supervisor.metrics')" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <span :class="(row as SupervisorProcess).metrics?.available ? '' : 'text-xs text-fg-subtle'">
              {{ metricsSummary(row as SupervisorProcess) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column :label="$t('admin.ops.supervisor.commands')" min-width="170">
          <template #default="{ row }">
            <el-tag
              v-for="item in commandTags(row as SupervisorProcess)"
              :key="item.label"
              :effect="item.registered ? 'light' : 'plain'"
              :type="item.registered ? 'success' : 'info'"
              class="tag-gap"
              size="small"
            >
              {{ item.label }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="$t('admin.common.actions')" fixed="right" width="290">
          <template #default="{ row }">
            <el-button
              v-auth="'module_ops:supervisor:execute'"
              :icon="VideoPlay"
              :loading="actingKey === `${(row as SupervisorProcess).name}:start`"
              link
              type="primary"
              @click="runAction(row as SupervisorProcess, 'start')"
            >
              {{ $t('admin.ops.supervisor.start') }}
            </el-button>
            <el-button
              v-auth="'module_ops:supervisor:execute'"
              :icon="VideoPause"
              :loading="actingKey === `${(row as SupervisorProcess).name}:stop`"
              link
              type="warning"
              @click="runAction(row as SupervisorProcess, 'stop')"
            >
              {{ $t('admin.ops.supervisor.stop') }}
            </el-button>
            <el-button
              v-auth="'module_ops:supervisor:execute'"
              :icon="RefreshRight"
              :loading="actingKey === `${(row as SupervisorProcess).name}:restart`"
              link
              type="warning"
              @click="runAction(row as SupervisorProcess, 'restart')"
            >
              {{ $t('admin.ops.supervisor.restart') }}
            </el-button>
            <el-button :icon="Document" link type="primary" @click="openLog(row as SupervisorProcess)">
              {{ $t('admin.ops.supervisor.viewLog') }}
            </el-button>
            <el-button
              v-auth="'module_ops:supervisor:config'"
              :icon="Edit"
              link
              type="primary"
              @click="openEdit(row as SupervisorProcess)"
            >
              {{ $t('admin.common.edit') }}
            </el-button>
            <el-button
              v-auth="'module_ops:supervisor:config'"
              :icon="Delete"
              link
              type="danger"
              @click="removeRow(row as SupervisorProcess)"
            >
              {{ $t('admin.common.delete') }}
            </el-button>
          </template>
        </el-table-column>

        <template #empty>{{ $t('admin.ops.supervisor.noProcesses') }}</template>
      </el-table>
    </el-card>

    <!-- 登记编辑（整体替换保存，校验不过则不落库） -->
    <el-dialog
      v-model="editVisible"
      :title="editingName ? t('admin.ops.supervisor.editProcess') : t('admin.ops.supervisor.createProcess')"
      destroy-on-close
      width="660px"
    >
      <el-form :model="form" label-width="120px">
        <el-form-item :label="$t('admin.ops.supervisor.processName')" required>
          <el-input v-model="form.name" :placeholder="$t('admin.ops.supervisor.namePlaceholder')" maxlength="100"/>
          <div class="form-hint">{{ $t('admin.ops.supervisor.nameHint') }}</div>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.supervisor.description')">
          <el-input v-model="form.description" maxlength="200"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.supervisor.startCommand')">
          <el-input v-model="form.start_command" :placeholder="$t('admin.ops.supervisor.commandPlaceholder')"
                    maxlength="500"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.supervisor.stopCommand')">
          <el-input v-model="form.stop_command" :placeholder="$t('admin.ops.supervisor.commandPlaceholder')"
                    maxlength="500"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.supervisor.restartCommand')">
          <el-input v-model="form.restart_command" :placeholder="$t('admin.ops.supervisor.commandPlaceholder')"
                    maxlength="500"/>
        </el-form-item>
        <div class="form-hint">{{ $t('admin.ops.supervisor.commandHint') }}</div>
        <el-form-item :label="$t('admin.ops.supervisor.pidFile')">
          <el-input v-model="form.pid_file" placeholder="storage/run/api.pid"/>
          <div class="form-hint">{{ $t('admin.ops.supervisor.pidFileHint') }}</div>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.supervisor.logFile')">
          <el-input v-model="form.log_file" placeholder="logs/api.log"/>
          <div class="form-hint">{{ $t('admin.ops.supervisor.logFileHint') }}</div>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.supervisor.healthHost')">
          <el-input v-model="form.host" placeholder="127.0.0.1"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.supervisor.healthPort')">
          <el-input-number v-model="form.port" :controls="false" :max="65535" :min="1" style="width: 160px"/>
        </el-form-item>
        <el-form-item :label="$t('admin.ops.supervisor.healthUrl')">
          <el-input v-model="form.url" placeholder="http://127.0.0.1:9421/api/v3/system/health"/>
        </el-form-item>
        <div class="form-hint">{{ $t('admin.ops.supervisor.healthHint') }}</div>
        <el-form-item :label="$t('admin.ops.supervisor.active')">
          <el-switch v-model="form.is_active"/>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editVisible = false">{{ $t('admin.common.cancel') }}</el-button>
        <el-button :loading="saving" type="primary" @click="submitForm">{{ $t('admin.common.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- 进程日志（只允许 logs/ 与 storage/logs/） -->
    <el-drawer v-model="logVisible" :size="620" :title="t('admin.ops.supervisor.logTitle', {name: logTarget})">
      <div class="log-toolbar">
        <el-select v-model="logLines" style="width: 130px" @change="reloadLog">
          <el-option :label="$t('admin.ops.supervisor.lines100')" :value="100"/>
          <el-option :label="$t('admin.ops.supervisor.lines200')" :value="200"/>
          <el-option :label="$t('admin.ops.supervisor.lines500')" :value="500"/>
          <el-option :label="$t('admin.ops.supervisor.lines1000')" :value="1000"/>
        </el-select>
        <el-button :icon="Refresh" :loading="logLoading" @click="reloadLog">
          {{ $t('admin.common.refresh') }}
        </el-button>
      </div>

      <el-alert
        v-if="logResult && !logResult.available"
        :closable="false"
        :title="$t('admin.ops.supervisor.logUnavailable')"
        type="warning"
      >
        <div>{{ logResult.detail }}</div>
      </el-alert>

      <template v-else-if="logResult">
        <div class="log-meta">
          <span>{{ $t('admin.ops.supervisor.logPath') }}：{{ logResult.path || '—' }}</span>
          <span class="ml-3">{{ $t('admin.ops.supervisor.logTotalLines', {n: logResult.total_lines}) }}</span>
        </div>
        <pre v-loading="logLoading"
             class="log-body">{{ logResult.lines.join('\n') || $t('admin.ops.supervisor.logEmpty') }}</pre>
      </template>
    </el-drawer>

    <!-- 动作失败详情（未登记命令 / 非 0 返回 / 超时都会走到这里） -->
    <el-dialog v-model="actionVisible" :title="actionTitle" width="620px">
      <template v-if="actionResult">
        <el-alert :closable="false" :title="$t('admin.ops.supervisor.actionFailed')" type="error">
          <div>{{ actionResult.detail }}</div>
        </el-alert>
        <el-descriptions :column="1" border class="mt-3" size="small">
          <el-descriptions-item :label="$t('admin.ops.supervisor.actionCommand')">
            {{ actionResult.command || $t('admin.ops.supervisor.actionNoCommand') }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.ops.supervisor.actionReturnCode')">
            {{ actionResult.returncode ?? '—' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('admin.ops.supervisor.actionDuration')">
            {{ actionResult.duration_ms ?? '—' }} ms
          </el-descriptions-item>
        </el-descriptions>
        <div v-if="actionResult.output" class="mt-3">
          <div class="text-xs text-fg-subtle">{{ $t('admin.ops.supervisor.actionOutput') }}</div>
          <pre class="output-body">{{ actionResult.output }}</pre>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.overview {
  margin-bottom: 0;
}

.stats {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-top: 6px;
}

.stat {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.stat b {
  font-size: 22px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.text-success {
  color: var(--el-color-success);
}

.text-danger {
  color: var(--el-color-danger);
}

.issue-list {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  line-height: 1.7;
}

.probe-detail {
  max-width: 420px;
  line-height: 1.6;
}

.tag-gap {
  margin-right: 4px;
}

.form-hint {
  font-size: 12px;
  line-height: 1.6;
  color: var(--el-text-color-secondary);
}

.log-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.log-meta {
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.log-body,
.output-body {
  max-height: 60vh;
  padding: 10px;
  overflow: auto;
  font-family: var(--el-font-family-mono, ui-monospace, monospace);
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}

.output-body {
  max-height: 240px;
  margin: 6px 0 0;
}
</style>
